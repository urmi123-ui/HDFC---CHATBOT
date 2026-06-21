from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Protocol

from app.classifier import QueryClass, classify_query
from app.formatter import ChatResponse
from app.orchestrator import answer_factual_query
from app.refusal import build_out_of_scope_refusal, build_pii_refusal, build_refusal
from app.retriever import RetrievalResult, Retriever, get_retriever
from app.sanitize import SanitizeReason, sanitize_message

logger = logging.getLogger(__name__)

REFUSAL_CLASSES = {
    QueryClass.ADVISORY,
    QueryClass.COMPARISON,
    QueryClass.PERFORMANCE,
    QueryClass.OUT_OF_SCOPE,
    QueryClass.GREETING,
}


class GeneratorProtocol(Protocol):
    def generate(self, question: str, chunks: tuple) -> object: ...


@dataclass(frozen=True)
class ChatMeta:
    query_class: str
    refusal: bool
    resolved_slug: str | None
    detected_section: str | None
    top_distance: float | None
    latency_ms: int


def handle_chat(
    message: str,
    *,
    retriever: Retriever | None = None,
    generator: GeneratorProtocol | None = None,
) -> tuple[ChatResponse, ChatMeta]:
    started = time.perf_counter()
    retriever = retriever or get_retriever()
    sanitized = sanitize_message(message)

    if sanitized.reason == SanitizeReason.EMPTY:
        raise ValueError("Message must not be empty")
    if sanitized.reason == SanitizeReason.TOO_LONG:
        raise ValueError("Message is too long")
    if sanitized.blocked:
        response = build_pii_refusal()
        meta = _build_meta(
            query_class="pii_blocked",
            refusal=True,
            retrieval=None,
            started=started,
        )
        logger.info("chat pii_blocked latency_ms=%s", meta.latency_ms)
        return response, meta

    classification = classify_query(sanitized.text)
    query_class = classification.query_class

    if query_class in REFUSAL_CLASSES:
        response = build_refusal(query_class)
        meta = _build_meta(
            query_class=query_class.value,
            refusal=True,
            retrieval=None,
            started=started,
        )
        logger.info(
            "chat refusal query_class=%s reason=%s latency_ms=%s",
            meta.query_class,
            classification.reason,
            meta.latency_ms,
        )
        return response, meta

    if not retriever.is_ready():
        raise RuntimeError("Vector index is not loaded")

    retrieval = retriever.retrieve(sanitized.text)
    if not retrieval.chunks:
        response = build_out_of_scope_refusal()
        meta = _build_meta(
            query_class=QueryClass.OUT_OF_SCOPE.value,
            refusal=True,
            retrieval=retrieval,
            started=started,
        )
        logger.info(
            "chat out_of_scope_empty_retrieval resolved_slug=%s latency_ms=%s",
            meta.resolved_slug,
            meta.latency_ms,
        )
        return response, meta

    try:
        response = answer_factual_query(
            sanitized.text,
            retriever=retriever,
            generator=generator,
            retrieval=retrieval,
        )
    except Exception:
        logger.exception("chat generation_failed query_class=%s", query_class.value)
        raise

    meta = _build_meta(
        query_class=query_class.value,
        refusal=response.is_refusal,
        retrieval=retrieval,
        started=started,
    )
    logger.info(
        "chat factual query_class=%s resolved_slug=%s section=%s top_distance=%s latency_ms=%s",
        meta.query_class,
        meta.resolved_slug,
        meta.detected_section,
        meta.top_distance,
        meta.latency_ms,
    )
    return response, meta


def _build_meta(
    *,
    query_class: str,
    refusal: bool,
    retrieval: RetrievalResult | None,
    started: float,
) -> ChatMeta:
    top_distance = retrieval.chunks[0].distance if retrieval and retrieval.chunks else None
    return ChatMeta(
        query_class=query_class,
        refusal=refusal,
        resolved_slug=retrieval.resolved_slug if retrieval else None,
        detected_section=retrieval.detected_section if retrieval else None,
        top_distance=top_distance,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )

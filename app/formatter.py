from __future__ import annotations

from dataclasses import asdict, dataclass

from app.corpus import DISCLAIMER
from app.retriever import RetrievalResult, RetrievedChunk


@dataclass(frozen=True)
class ChatResponse:
    answer: str
    citation_url: str
    last_updated: str
    is_refusal: bool
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict:
        return asdict(self)


def _latest_last_updated(chunks: tuple[RetrievedChunk, ...]) -> str:
    dates = [chunk.last_updated for chunk in chunks if chunk.last_updated]
    return max(dates) if dates else ""


def _primary_citation_url(retrieval: RetrievalResult) -> str:
    if retrieval.resolved_source_url:
        return retrieval.resolved_source_url
    if retrieval.chunks:
        return retrieval.chunks[0].source_url
    return ""


def link_only_fallback(retrieval: RetrievalResult) -> ChatResponse:
    citation_url = _primary_citation_url(retrieval)
    scheme_name = retrieval.resolved_scheme_name or "the requested scheme"
    if citation_url:
        answer = (
            f"I couldn't verify a precise answer from indexed sources for {scheme_name}. "
            f"Please refer to the official scheme page for the latest details."
        )
        last_updated = _latest_last_updated(retrieval.chunks) or ""
    else:
        answer = (
            "I couldn't verify a precise answer from indexed sources. "
            "This assistant covers 12 HDFC schemes on Groww — please name a supported scheme."
        )
        last_updated = ""

    return ChatResponse(
        answer=answer,
        citation_url=citation_url,
        last_updated=last_updated,
        is_refusal=False,
    )


def format_factual_response(
    answer: str,
    retrieval: RetrievalResult,
) -> ChatResponse:
    citation_url = _primary_citation_url(retrieval)
    return ChatResponse(
        answer=answer.strip(),
        citation_url=citation_url,
        last_updated=_latest_last_updated(retrieval.chunks),
        is_refusal=False,
    )

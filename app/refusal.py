from __future__ import annotations

from datetime import UTC, datetime

from app.classifier import QueryClass
from app.corpus import AMFI_EDUCATION_URL, DISCLAIMER, SEBI_EDUCATION_URL, load_corpus_scheme_names
from app.formatter import ChatResponse


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _scheme_list_text() -> str:
    names = load_corpus_scheme_names()
    if not names:
        return "the supported HDFC schemes in this assistant"
    if len(names) <= 3:
        return ", ".join(names)
    preview = ", ".join(names[:3])
    return f"{preview}, and {len(names) - 3} other supported HDFC schemes"


def build_refusal(query_class: QueryClass) -> ChatResponse:
    if query_class == QueryClass.ADVISORY:
        answer = (
            "I can only answer factual questions about HDFC schemes in my corpus, such as expense ratio, "
            "exit load, or fund manager details. I cannot provide investment advice or recommend which fund to choose."
        )
    elif query_class == QueryClass.COMPARISON:
        answer = (
            "I cannot compare funds or rank them. I can answer factual questions about one supported HDFC scheme at a time, "
            "such as expense ratio, exit load, or fund manager details."
        )
    elif query_class == QueryClass.PERFORMANCE:
        answer = (
            "I cannot quote or project returns. For performance information, please refer to the official scheme page "
            "or consult AMFI/SEBI educational resources."
        )
    elif query_class == QueryClass.GREETING:
        answer = (
            "Hello. I am a facts-only HDFC mutual fund FAQ assistant. "
            f"I can answer objective questions about {_scheme_list_text()}."
        )
    else:
        answer = (
            "That question is outside the scope of this assistant. "
            f"I can answer factual questions about {_scheme_list_text()}."
        )

    return ChatResponse(
        answer=answer,
        citation_url=AMFI_EDUCATION_URL,
        last_updated=_today(),
        is_refusal=True,
        disclaimer=DISCLAIMER,
    )


def build_pii_refusal() -> ChatResponse:
    return ChatResponse(
        answer=(
            "Your message appears to contain personal or sensitive information. "
            "Please do not share PAN, Aadhaar, account numbers, phone numbers, or email addresses. "
            "Ask a factual question without personal details."
        ),
        citation_url=SEBI_EDUCATION_URL,
        last_updated=_today(),
        is_refusal=True,
        disclaimer=DISCLAIMER,
    )


def build_out_of_scope_refusal() -> ChatResponse:
    return build_refusal(QueryClass.OUT_OF_SCOPE)

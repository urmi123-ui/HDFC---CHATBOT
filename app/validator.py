from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.corpus import load_corpus_urls
from app.retriever import RetrievedChunk

MAX_SENTENCES = 3

ADVISORY_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bshould i invest\b",
        r"\bshould you invest\b",
        r"\brecommend\b",
        r"\brecommended\b",
        r"\bgood fund\b",
        r"\bbetter fund\b",
        r"\bbuy\b",
        r"\bsell\b",
        r"\bhold\b",
        r"\bsuitable for\b",
        r"\byou should\b",
        r"\bi suggest\b",
        r"\bconsider investing\b",
    )
)

PERFORMANCE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bcagr\b",
        r"\bpast returns?\b",
        r"\bannualized return\b",
        r"\boutperform(ed|s|ing)?\b",
        r"\bnav growth\b",
        r"\b\d+\s*year[s]?\s+return\b",
        r"\breturns?\s+of\s+\d",
    )
)

PERCENTAGE_PATTERN = re.compile(r"\d+\.?\d*\s*%")
NUMBER_PATTERN = re.compile(r"\d+\.?\d*")
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    answer: str
    issues: tuple[str, ...] = field(default_factory=tuple)


def count_sentences(text: str) -> int:
    cleaned = text.strip()
    if not cleaned:
        return 0
    parts = [part for part in SENTENCE_SPLIT_PATTERN.split(cleaned) if part.strip()]
    return len(parts)


def truncate_to_sentences(text: str, max_sentences: int = MAX_SENTENCES) -> str:
    cleaned = text.strip()
    if not cleaned:
        return cleaned
    parts = [part.strip() for part in SENTENCE_SPLIT_PATTERN.split(cleaned) if part.strip()]
    if len(parts) <= max_sentences:
        return cleaned
    truncated = " ".join(parts[:max_sentences])
    if truncated and truncated[-1] not in ".!?":
        truncated += "."
    return truncated


def _combined_chunk_text(chunks: tuple[RetrievedChunk, ...]) -> str:
    return "\n".join(chunk.text for chunk in chunks).lower()


def _extract_grounding_numbers(text: str) -> list[str]:
    numbers: list[str] = []
    for match in NUMBER_PATTERN.finditer(text):
        value = match.group()
        if len(value) >= 2 or "." in value:
            numbers.append(value)
    return numbers


def _contains_advisory_language(text: str) -> bool:
    return any(pattern.search(text) for pattern in ADVISORY_PATTERNS)


def _contains_performance_language(text: str) -> bool:
    return any(pattern.search(text) for pattern in PERFORMANCE_PATTERNS)


def _numbers_grounded(answer: str, chunks: tuple[RetrievedChunk, ...]) -> bool:
    chunk_text = _combined_chunk_text(chunks)
    for number in _extract_grounding_numbers(answer):
        if number.lower() not in chunk_text:
            return False
    return True


def _percentages_allowed(answer: str, detected_section: str | None, chunks: tuple[RetrievedChunk, ...]) -> bool:
    if not PERCENTAGE_PATTERN.search(answer):
        return True

    allowed_sections = {"expense_ratio", "exit_load", "tax"}
    if detected_section in allowed_sections:
        return _numbers_grounded(answer, chunks)

    if _contains_performance_language(answer):
        return False

    return _numbers_grounded(answer, chunks)


def validate_answer(
    answer: str,
    chunks: tuple[RetrievedChunk, ...],
    *,
    detected_section: str | None = None,
    citation_url: str | None = None,
    allowlist: frozenset[str] | None = None,
) -> ValidationResult:
    issues: list[str] = []
    normalized = answer.strip()
    if not normalized:
        issues.append("empty_answer")

    working = truncate_to_sentences(normalized, MAX_SENTENCES)
    if count_sentences(normalized) > MAX_SENTENCES and count_sentences(working) <= MAX_SENTENCES:
        pass
    elif count_sentences(normalized) > MAX_SENTENCES:
        issues.append("too_many_sentences")

    if _contains_advisory_language(working):
        issues.append("advisory_language")

    if _contains_performance_language(working):
        issues.append("performance_language")

    if not _numbers_grounded(working, chunks):
        issues.append("ungrounded_numbers")

    if not _percentages_allowed(working, detected_section, chunks):
        issues.append("ungrounded_percentages")

    if citation_url is not None:
        urls = allowlist or load_corpus_urls()
        if citation_url not in urls:
            issues.append("invalid_citation")

    return ValidationResult(ok=not issues, answer=working, issues=tuple(issues))

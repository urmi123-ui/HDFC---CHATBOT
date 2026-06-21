from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from app.retriever import OTHER_AMC_KEYWORDS, load_schemes, resolve_scheme


class QueryClass(str, Enum):
    FACTUAL = "factual"
    ADVISORY = "advisory"
    COMPARISON = "comparison"
    PERFORMANCE = "performance"
    OUT_OF_SCOPE = "out_of_scope"
    GREETING = "greeting"


ADVISORY_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bshould i invest\b",
        r"\bshould you invest\b",
        r"\bshould i buy\b",
        r"\bshould i sell\b",
        r"\bshud i invst\b",
        r"\brecommend\b",
        r"\brecommended\b",
        r"\bgood enough to invest\b",
        r"\bgood fund\b",
        r"\bbetter fund\b",
        r"\bbuy\b",
        r"\bsell\b",
        r"\bhold\b",
        r"\bsuitable for\b",
        r"\bis it safe\b",
        r"\ba safe fund\b",
        r"\bwhich fund should\b",
        r"\bkya mujhe invest karna chahiye\b",
        r"\bmost people pick\b",
        r"\bhow much should i allocate\b",
    )
)

COMPARISON_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bwhich is better\b",
        r"\bwhich fund is better\b",
        r"\bcompare\b",
        r"\bcomparison\b",
        r"\bvs\.?\b",
        r"\bversus\b",
        r"\blower load\b",
        r"\bhigher return\b",
        r"\bcompare returns\b",
    )
)

PERFORMANCE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bwhat returns\b",
        r"\bexpected returns\b",
        r"\breturns will i get\b",
        r"\bhow much will i earn\b",
        r"\bpast returns\b",
        r"\bcompare .* returns\b",
        r"\bcagr\b",
        r"\bnav growth\b",
        r"\bperformance comparison\b",
        r"\b\d+\s*year[s]?\s+return\b",
        r"\blast year'?s nav\b",
    )
)

OUT_OF_SCOPE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bweather\b",
        r"\btemperature in\b",
        r"\bcook\b",
        r"\brecipe\b",
        r"\bfootball\b",
        r"\bcricket score\b",
        r"\belss lock[\s-]?in\b",
        r"\bcapital gains report\b",
        r"\bdownload statement\b",
    )
)

GREETING_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^\s*hi\s*[!.?]*\s*$",
        r"^\s*hello\s*[!.?]*\s*$",
        r"^\s*hey\s*[!.?]*\s*$",
        r"^\s*good (?:morning|afternoon|evening)\s*[!.?]*\s*$",
    )
)


@dataclass(frozen=True)
class ClassificationResult:
    query_class: QueryClass
    reason: str


def _mentions_other_amc(query: str) -> bool:
    normalized = re.sub(r"[^a-z0-9\s]", " ", query.lower())
    return any(re.search(rf"\b{re.escape(amc)}\b", normalized) for amc in OTHER_AMC_KEYWORDS)


def _is_out_of_corpus_scheme(query: str) -> bool:
    if _mentions_other_amc(query) and resolve_scheme(query, load_schemes()) is None:
        return True
    return False


def classify_query(query: str) -> ClassificationResult:
    text = query.strip()
    if not text:
        return ClassificationResult(QueryClass.OUT_OF_SCOPE, "empty")

    for pattern in GREETING_PATTERNS:
        if pattern.search(text):
            return ClassificationResult(QueryClass.GREETING, "greeting")

    for pattern in COMPARISON_PATTERNS:
        if pattern.search(text):
            return ClassificationResult(QueryClass.COMPARISON, "comparison_phrase")

    for pattern in ADVISORY_PATTERNS:
        if pattern.search(text):
            return ClassificationResult(QueryClass.ADVISORY, "advisory_phrase")

    for pattern in PERFORMANCE_PATTERNS:
        if pattern.search(text):
            return ClassificationResult(QueryClass.PERFORMANCE, "performance_phrase")

    for pattern in OUT_OF_SCOPE_PATTERNS:
        if pattern.search(text):
            return ClassificationResult(QueryClass.OUT_OF_SCOPE, "out_of_scope_topic")

    if _is_out_of_corpus_scheme(text):
        return ClassificationResult(QueryClass.OUT_OF_SCOPE, "non_corpus_scheme")

    return ClassificationResult(QueryClass.FACTUAL, "default_factual")

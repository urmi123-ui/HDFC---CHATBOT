from __future__ import annotations

import argparse
import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import chromadb
import yaml
from chromadb.api.models.Collection import Collection
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CORPUS_PATH = PROJECT_ROOT / "config" / "corpus.yaml"
DEFAULT_METADATA_PATH = PROJECT_ROOT / "data" / "index" / "scheme_metadata.json"
DEFAULT_INDEX_DIR = PROJECT_ROOT / "data" / "index"
COLLECTION_NAME = "mf_faq_chunks"

BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
MAX_DISTANCE = 0.45
HIGH_CONFIDENCE = 0.85
MIN_CONFIDENCE = 0.50

SECTION_KEYWORDS: dict[str, list[str]] = {
    "expense_ratio": ["expense ratio", "ter", "management fee"],
    "exit_load": ["exit load", "redemption charge", "withdrawal charge"],
    "minimum_investment": [
        "minimum sip",
        "min sip",
        "minimum investment",
        "lumpsum",
        "sip amount",
    ],
    "benchmark": ["benchmark", "index tracked", "tracks"],
    "fund_management": [
        "fund manager",
        "who manages",
        "manager",
        "manages",
        "tenure",
    ],
    "investment_objective": [
        "investment objective",
        "investment strategy",
        "strategy",
        "objective",
    ],
    "tax": ["tax", "stcg", "ltcg", "capital gains tax"],
    "overview": ["riskometer", "risk label", "nav", "aum", "category", "launch date"],
    "fund_house": ["fund house", "amc", "registrar"],
}

TOKEN_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "direct",
        "for",
        "fund",
        "growth",
        "hdfc",
        "in",
        "is",
        "mutual",
        "of",
        "plan",
        "scheme",
        "the",
        "what",
        "who",
    }
)

OTHER_AMC_KEYWORDS = frozenset(
    {
        "sbi",
        "icici",
        "axis",
        "nippon",
        "kotak",
        "uti",
        "franklin",
        "dsp",
        "mirae",
        "tata",
        "birla",
        "pgim",
        "invesco",
        "bandhan",
        "motilal",
        "quant",
        "ppfas",
        "edelweiss",
        "hsbc",
        "lic",
        "sundaram",
        "mahindra",
        "canara",
        "boi",
        "union",
        "baroda",
    }
)


@dataclass(frozen=True)
class SchemeRecord:
    slug: str
    scheme_name: str
    source_url: str
    category: str
    aliases: tuple[str, ...]
    last_fetched_at: str | None = None


@dataclass(frozen=True)
class SchemeMatch:
    slug: str
    scheme_name: str
    source_url: str
    confidence: float
    method: str


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    text: str
    section: str
    scheme_name: str
    source_url: str
    last_updated: str
    distance: float


@dataclass(frozen=True)
class RetrievalResult:
    chunks: tuple[RetrievedChunk, ...]
    resolved_slug: str | None
    resolved_scheme_name: str | None
    resolved_source_url: str | None
    detected_section: str | None
    confidence: float
    ambiguous: bool
    insufficient_context: bool
    supported_schemes: tuple[str, ...] | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["chunks"] = [asdict(chunk) for chunk in self.chunks]
        return payload


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", text.lower())


def _tokenize(text: str) -> set[str]:
    return {token for token in _normalize_text(text).split() if token and token not in TOKEN_STOPWORDS}


def _mentions_other_amc(query: str) -> bool:
    normalized = _normalize_text(query)
    return any(re.search(rf"\b{re.escape(amc)}\b", normalized) for amc in OTHER_AMC_KEYWORDS)


def load_schemes(
    corpus_path: Path = DEFAULT_CORPUS_PATH,
    metadata_path: Path = DEFAULT_METADATA_PATH,
) -> list[SchemeRecord]:
    with corpus_path.open(encoding="utf-8") as handle:
        corpus = yaml.safe_load(handle)

    fetched_at_by_slug: dict[str, str] = {}
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        for scheme in metadata.get("schemes", []):
            fetched_at_by_slug[scheme["slug"]] = scheme.get("last_fetched_at")

    schemes: list[SchemeRecord] = []
    for entry in corpus.get("schemes", []):
        schemes.append(
            SchemeRecord(
                slug=entry["slug"],
                scheme_name=entry["scheme_name"],
                source_url=entry["source_url"],
                category=entry.get("category", ""),
                aliases=tuple(entry.get("aliases", [])),
                last_fetched_at=fetched_at_by_slug.get(entry["slug"]),
            )
        )
    return schemes


def resolve_scheme(query: str, schemes: list[SchemeRecord]) -> SchemeMatch | None:
    query_lower = query.lower()

    for scheme in schemes:
        if scheme.source_url.lower() in query_lower:
            return SchemeMatch(
                slug=scheme.slug,
                scheme_name=scheme.scheme_name,
                source_url=scheme.source_url,
                confidence=1.0,
                method="url",
            )

    name_matches = [scheme for scheme in schemes if scheme.scheme_name.lower() in query_lower]
    if name_matches:
        best = max(name_matches, key=lambda scheme: len(scheme.scheme_name))
        return SchemeMatch(
            slug=best.slug,
            scheme_name=best.scheme_name,
            source_url=best.source_url,
            confidence=1.0,
            method="full_name",
        )

    alias_matches: list[tuple[int, SchemeRecord, str]] = []
    for scheme in schemes:
        for alias in scheme.aliases:
            if alias.lower() in query_lower:
                alias_matches.append((len(alias), scheme, alias))
    if alias_matches:
        _, best, alias = max(alias_matches, key=lambda item: item[0])
        return SchemeMatch(
            slug=best.slug,
            scheme_name=best.scheme_name,
            source_url=best.source_url,
            confidence=0.9,
            method=f"alias:{alias}",
        )

    if _mentions_other_amc(query_lower) and "hdfc" not in query_lower:
        return None

    if "hdfc" in query_lower:
        query_tokens = _tokenize(query)
        best_match: SchemeMatch | None = None
        best_score = 0.0
        for scheme in schemes:
            scheme_tokens = _tokenize(scheme.scheme_name) | _tokenize(scheme.slug.replace("-", " "))
            for alias in scheme.aliases:
                scheme_tokens |= _tokenize(alias)
            overlap = len(query_tokens & scheme_tokens)
            if overlap == 0:
                continue
            score = overlap / max(len(query_tokens), 1)
            if score > best_score:
                best_score = score
                best_match = SchemeMatch(
                    slug=scheme.slug,
                    scheme_name=scheme.scheme_name,
                    source_url=scheme.source_url,
                    confidence=min(0.5 + score * 0.3, 0.8),
                    method="token_overlap",
                )
        if best_match and best_score >= 0.25:
            return best_match

    if _mentions_other_amc(query_lower):
        return None

    return None


def detect_section(query: str) -> str | None:
    query_lower = query.lower()
    matches: list[tuple[int, str, str]] = []
    for section, keywords in SECTION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in query_lower:
                matches.append((len(keyword), section, keyword))
    if not matches:
        return None
    _, section, _ = max(matches, key=lambda item: item[0])
    return section


def _top_k_for_section(section: str | None) -> int:
    if section == "fund_management":
        return 5
    return 2


def _build_where_filter(slug: str | None, section: str | None) -> dict | None:
    filters: list[dict] = []
    if slug:
        filters.append({"slug": slug})
    if section:
        filters.append({"section": section})
    if not filters:
        return None
    if len(filters) == 1:
        return filters[0]
    return {"$and": filters}


class Retriever:
    def __init__(
        self,
        *,
        schemes: list[SchemeRecord] | None = None,
        corpus_path: Path = DEFAULT_CORPUS_PATH,
        metadata_path: Path = DEFAULT_METADATA_PATH,
        persist_dir: Path | None = None,
        model_name: str | None = None,
        collection_name: str = COLLECTION_NAME,
    ) -> None:
        self.schemes = schemes if schemes is not None else load_schemes(corpus_path, metadata_path)
        self.corpus_path = corpus_path
        self.metadata_path = metadata_path
        self.scheme_names = tuple(scheme.scheme_name for scheme in self.schemes)
        self.persist_dir = Path(persist_dir or os.getenv("CHROMA_PERSIST_DIR", DEFAULT_INDEX_DIR))
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        self.collection_name = collection_name
        self._embedder: SentenceTransformer | None = None
        self._collection: Collection | None = None
        self._metadata_mtime = self._read_metadata_mtime()

    def _read_metadata_mtime(self) -> float:
        if self.metadata_path.exists():
            return self.metadata_path.stat().st_mtime
        return 0.0

    def reload(self) -> None:
        """Reload scheme metadata and reconnect to the vector store after an index swap."""
        self.schemes = load_schemes(self.corpus_path, self.metadata_path)
        self.scheme_names = tuple(scheme.scheme_name for scheme in self.schemes)
        self._collection = None
        self._metadata_mtime = self._read_metadata_mtime()
        logger.info("Retriever reloaded from %s", self.persist_dir)

    def maybe_reload(self) -> None:
        current_mtime = self._read_metadata_mtime()
        if current_mtime > self._metadata_mtime:
            self.reload()

    @property
    def embedder(self) -> SentenceTransformer:
        if self._embedder is None:
            logger.info("Loading embedding model: %s", self.model_name)
            self._embedder = SentenceTransformer(self.model_name, local_files_only=True)
        return self._embedder

    @property
    def collection(self) -> Collection:
        if self._collection is None:
            client = chromadb.PersistentClient(path=str(self.persist_dir))
            self._collection = client.get_collection(name=self.collection_name)
        return self._collection

    @property
    def chunk_count(self) -> int:
        return self.collection.count()

    def is_ready(self) -> bool:
        if not self.persist_dir.exists():
            return False
        try:
            return self.chunk_count > 0
        except Exception:
            return False

    def retrieve(self, query: str) -> RetrievalResult:
        self.maybe_reload()
        query_lower = query.lower()
        scheme_match = resolve_scheme(query, self.schemes)
        detected_section = detect_section(query)

        if scheme_match is None and _mentions_other_amc(query_lower):
            return RetrievalResult(
                chunks=(),
                resolved_slug=None,
                resolved_scheme_name=None,
                resolved_source_url=None,
                detected_section=detected_section,
                confidence=0.0,
                ambiguous=False,
                insufficient_context=True,
                supported_schemes=self.scheme_names,
            )

        ambiguous = False
        slug: str | None = None
        scheme_name: str | None = None
        source_url: str | None = None
        confidence = 0.0

        if scheme_match:
            confidence = scheme_match.confidence
            if confidence >= HIGH_CONFIDENCE:
                slug = scheme_match.slug
                scheme_name = scheme_match.scheme_name
                source_url = scheme_match.source_url
            elif confidence >= MIN_CONFIDENCE:
                slug = scheme_match.slug
                scheme_name = scheme_match.scheme_name
                source_url = scheme_match.source_url
                ambiguous = True
        elif detected_section is None:
            return RetrievalResult(
                chunks=(),
                resolved_slug=None,
                resolved_scheme_name=None,
                resolved_source_url=None,
                detected_section=None,
                confidence=0.0,
                ambiguous=False,
                insufficient_context=True,
                supported_schemes=self.scheme_names,
            )
        else:
            ambiguous = True

        where = _build_where_filter(slug, detected_section)
        top_k = _top_k_for_section(detected_section)
        query_embedding = self.embedder.encode([BGE_QUERY_PREFIX + query]).tolist()

        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            where=where,
            include=["metadatas", "documents", "distances"],
        )

        chunks: list[RetrievedChunk] = []
        for chunk_id, metadata, document, distance in zip(
            results["ids"][0],
            results["metadatas"][0],
            results["documents"][0],
            results["distances"][0],
            strict=True,
        ):
            chunks.append(
                RetrievedChunk(
                    id=chunk_id,
                    text=document,
                    section=metadata["section"],
                    scheme_name=metadata["scheme_name"],
                    source_url=metadata["source_url"],
                    last_updated=metadata["last_updated"],
                    distance=float(distance),
                )
            )

        if chunks and slug is None:
            slug = chunks[0].id.split("#", 1)[0]
            scheme_name = chunks[0].scheme_name
            source_url = chunks[0].source_url
            confidence = 0.4

        insufficient_context = not chunks or chunks[0].distance > MAX_DISTANCE

        return RetrievalResult(
            chunks=tuple(chunks),
            resolved_slug=slug,
            resolved_scheme_name=scheme_name,
            resolved_source_url=source_url,
            detected_section=detected_section,
            confidence=confidence,
            ambiguous=ambiguous,
            insufficient_context=insufficient_context,
            supported_schemes=self.scheme_names if insufficient_context and not chunks else None,
        )


_default_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    global _default_retriever
    if _default_retriever is None:
        _default_retriever = Retriever()
    else:
        _default_retriever.maybe_reload()
    return _default_retriever


def reset_retriever() -> None:
    global _default_retriever
    _default_retriever = None


def retrieve(query: str) -> RetrievalResult:
    return get_retriever().retrieve(query)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Debug retrieval for a factual query")
    parser.add_argument("query", help="User query to retrieve against the vector index")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _build_parser().parse_args()
    result = retrieve(args.query)
    print(json.dumps(result.to_dict(), indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

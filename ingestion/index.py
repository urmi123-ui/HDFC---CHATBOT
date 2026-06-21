from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection
from sentence_transformers import SentenceTransformer

from ingestion.chunk import Chunk, chunk_from_processed

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DEFAULT_INDEX_DIR = PROJECT_ROOT / "data" / "index"
DEFAULT_METADATA_PATH = DEFAULT_INDEX_DIR / "scheme_metadata.json"
COLLECTION_NAME = "mf_faq_chunks"


def _embedding_model_name() -> str:
    return os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")


def _persist_dir() -> Path:
    return Path(os.getenv("CHROMA_PERSIST_DIR", DEFAULT_INDEX_DIR))


def _load_embedder(model_name: str) -> SentenceTransformer:
    logger.info("Loading embedding model: %s", model_name)
    return SentenceTransformer(model_name)


def _get_collection(client: chromadb.PersistentClient) -> Collection:
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def build_scheme_metadata(processed_dir: Path = DEFAULT_PROCESSED_DIR) -> dict:
    schemes = []
    for sections_file in sorted(processed_dir.glob("*/sections.json")):
        parsed = json.loads(sections_file.read_text(encoding="utf-8"))
        fetched_at = parsed.get("fetched_at")
        last_fetched_at = (fetched_at or parsed.get("last_updated") or "")[:10]
        schemes.append(
            {
                "slug": parsed["slug"],
                "scheme_name": parsed["scheme_name"],
                "category": parsed.get("category", ""),
                "source_url": parsed["source_url"],
                "last_fetched_at": last_fetched_at,
            }
        )
    return {
        "updated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "scheme_count": len(schemes),
        "schemes": schemes,
    }


def write_scheme_metadata(
    processed_dir: Path = DEFAULT_PROCESSED_DIR,
    metadata_path: Path = DEFAULT_METADATA_PATH,
) -> dict:
    metadata = build_scheme_metadata(processed_dir)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Wrote scheme metadata index (%s schemes)", metadata["scheme_count"])
    return metadata


def upsert_chunks(
    chunks: list[Chunk],
    *,
    persist_dir: Path | None = None,
    model_name: str | None = None,
) -> dict:
    if not chunks:
        raise ValueError("No chunks provided for indexing")

    persist_dir = persist_dir or _persist_dir()
    persist_dir.mkdir(parents=True, exist_ok=True)
    model_name = model_name or _embedding_model_name()

    embedder = _load_embedder(model_name)
    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = _get_collection(client)

    ids = [chunk.id for chunk in chunks]
    documents = [chunk.text for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]
    embeddings = embedder.encode(documents, show_progress_bar=len(documents) > 20).tolist()

    batch_size = 64
    for start in range(0, len(ids), batch_size):
        end = start + batch_size
        collection.upsert(
            ids=ids[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
            embeddings=embeddings[start:end],
        )

    logger.info("Upserted %s chunks into %s", len(chunks), persist_dir)
    return {
        "collection": COLLECTION_NAME,
        "persist_dir": str(persist_dir),
        "chunk_count": len(chunks),
        "embedding_model": model_name,
    }


def index_processed(
    processed_dir: Path = DEFAULT_PROCESSED_DIR,
    *,
    slugs: list[str] | None = None,
    persist_dir: Path | None = None,
    metadata_path: Path = DEFAULT_METADATA_PATH,
) -> dict:
    chunks = chunk_from_processed(processed_dir, slugs=slugs)
    index_summary = upsert_chunks(chunks, persist_dir=persist_dir)
    metadata_summary = write_scheme_metadata(processed_dir, metadata_path)
    return {
        "index": index_summary,
        "metadata": {
            "path": str(metadata_path),
            "scheme_count": metadata_summary["scheme_count"],
        },
        "chunks_by_scheme": _chunk_counts_by_slug(chunks),
    }


def _chunk_counts_by_slug(chunks: list[Chunk]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for chunk in chunks:
        counts[chunk.slug] = counts.get(chunk.slug, 0) + 1
    return counts


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Embed parsed chunks and upsert into ChromaDB")
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=DEFAULT_PROCESSED_DIR,
        help="Directory containing parsed sections.json files",
    )
    parser.add_argument(
        "--persist-dir",
        type=Path,
        default=None,
        help="ChromaDB persistence directory",
    )
    parser.add_argument(
        "--metadata-path",
        type=Path,
        default=DEFAULT_METADATA_PATH,
        help="Output path for scheme metadata JSON",
    )
    parser.add_argument(
        "--slug",
        action="append",
        dest="slugs",
        help="Index only specific scheme slug(s); repeatable",
    )
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _build_parser().parse_args()
    summary = index_processed(
        args.processed_dir,
        slugs=args.slugs,
        persist_dir=args.persist_dir,
        metadata_path=args.metadata_path,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

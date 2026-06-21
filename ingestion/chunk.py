from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

MAX_TOKENS_BEFORE_SPLIT = 400
CHUNK_TARGET_TOKENS = 300
CHUNK_OVERLAP_TOKENS = 50

FUND_MANAGEMENT_SECTION = "fund_management"


@dataclass(frozen=True)
class Chunk:
    id: str
    slug: str
    scheme_name: str
    source_url: str
    section: str
    chunk_index: int
    last_updated: str
    text: str

    @property
    def metadata(self) -> dict[str, str | int]:
        return {
            "slug": self.slug,
            "scheme_name": self.scheme_name,
            "source_url": self.source_url,
            "section": self.section,
            "chunk_index": self.chunk_index,
            "last_updated": self.last_updated,
            "chunk_text": self.text,
        }


def estimate_tokens(text: str) -> int:
    return max(1, int(len(text.split()) * 1.3))


def _slugify_fragment(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "block"


def _format_chunk_text(scheme_name: str, section: str, body: str) -> str:
    return f"Scheme: {scheme_name}\nSection: {section}\n{body.strip()}"


def _split_with_overlap(text: str, *, max_tokens: int, overlap_tokens: int) -> list[str]:
    words = text.split()
    if not words:
        return []

    max_words = max(1, int(max_tokens / 1.3))
    overlap_words = max(0, int(overlap_tokens / 1.3))
    step = max(1, max_words - overlap_words)

    blocks: list[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + max_words)
        block = " ".join(words[start:end]).strip()
        if block:
            blocks.append(block)
        if end >= len(words):
            break
        start += step
    return blocks


def chunk_section_text(
    *,
    slug: str,
    scheme_name: str,
    source_url: str,
    section: str,
    section_text: str,
    last_updated: str,
) -> list[Chunk]:
    section_text = section_text.strip()
    if not section_text:
        return []

    if section == FUND_MANAGEMENT_SECTION:
        bodies = [block.strip() for block in section_text.split("\n\n") if block.strip()]
    elif estimate_tokens(section_text) > MAX_TOKENS_BEFORE_SPLIT:
        bodies = _split_with_overlap(
            section_text,
            max_tokens=CHUNK_TARGET_TOKENS,
            overlap_tokens=CHUNK_OVERLAP_TOKENS,
        )
    else:
        bodies = [section_text]

    chunks: list[Chunk] = []
    for index, body in enumerate(bodies):
        suffix = str(index)
        if section == FUND_MANAGEMENT_SECTION:
            manager_name = body.split("—", 1)[0].strip()
            suffix = f"{_slugify_fragment(manager_name)}-{index}"
        chunk_id = f"{slug}#{section}#{suffix}"
        chunks.append(
            Chunk(
                id=chunk_id,
                slug=slug,
                scheme_name=scheme_name,
                source_url=source_url,
                section=section,
                chunk_index=index,
                last_updated=last_updated,
                text=_format_chunk_text(scheme_name, section, body),
            )
        )
    return chunks


def chunk_parsed_scheme(parsed: dict) -> list[Chunk]:
    chunks: list[Chunk] = []
    for section, section_text in parsed.get("sections", {}).items():
        chunks.extend(
            chunk_section_text(
                slug=parsed["slug"],
                scheme_name=parsed["scheme_name"],
                source_url=parsed["source_url"],
                section=section,
                section_text=section_text,
                last_updated=parsed["last_updated"],
            )
        )
    return chunks


def chunk_from_processed(
    processed_dir: Path = DEFAULT_PROCESSED_DIR,
    *,
    slugs: list[str] | None = None,
) -> list[Chunk]:
    sections_files = sorted(processed_dir.glob("*/sections.json"))
    if slugs:
        slug_set = set(slugs)
        sections_files = [path for path in sections_files if path.parent.name in slug_set]

    all_chunks: list[Chunk] = []
    for sections_file in sections_files:
        parsed = json.loads(sections_file.read_text(encoding="utf-8"))
        scheme_chunks = chunk_parsed_scheme(parsed)
        all_chunks.extend(scheme_chunks)

        chunks_path = sections_file.parent / "chunks.json"
        payload = {
            "slug": parsed["slug"],
            "scheme_name": parsed["scheme_name"],
            "source_url": parsed["source_url"],
            "last_updated": parsed["last_updated"],
            "chunk_count": len(scheme_chunks),
            "chunks": [asdict(chunk) for chunk in scheme_chunks],
        }
        chunks_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Chunked %s — %s chunks", parsed["slug"], len(scheme_chunks))

    return all_chunks


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Chunk parsed scheme sections")
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=DEFAULT_PROCESSED_DIR,
        help="Directory containing parsed sections.json files",
    )
    parser.add_argument(
        "--slug",
        action="append",
        dest="slugs",
        help="Chunk only specific scheme slug(s); repeatable",
    )
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _build_parser().parse_args()
    chunks = chunk_from_processed(args.processed_dir, slugs=args.slugs)
    summary = {
        "total_chunks": len(chunks),
        "by_section": {},
    }
    for chunk in chunks:
        summary["by_section"][chunk.section] = summary["by_section"].get(chunk.section, 0) + 1
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

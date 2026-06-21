from __future__ import annotations

import argparse
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from ingestion.corpus import Scheme, load_corpus

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MF-FAQ-Bot/1.0; +https://groww.in)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-IN,en;q=0.9",
}


@dataclass(frozen=True)
class FetchResult:
    slug: str
    source_url: str
    status_code: int
    fetched_at: str
    html_path: str
    meta_path: str
    content_length: int
    success: bool
    error: str | None = None


def _slug_raw_dir(raw_dir: Path, slug: str) -> Path:
    return raw_dir / slug


def fetch_scheme(
    scheme: Scheme,
    raw_dir: Path = DEFAULT_RAW_DIR,
    *,
    timeout: float = 30.0,
    max_retries: int = 3,
    backoff_seconds: float = 2.0,
) -> FetchResult:
    """Fetch a single Groww scheme page and persist HTML + metadata."""
    fetched_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    scheme_dir = _slug_raw_dir(raw_dir, scheme.slug)
    scheme_dir.mkdir(parents=True, exist_ok=True)

    timestamp = fetched_at.replace(":", "-")
    html_path = scheme_dir / f"{timestamp}.html"
    meta_path = scheme_dir / f"{timestamp}.meta.json"
    latest_html_path = scheme_dir / "latest.html"
    latest_meta_path = scheme_dir / "latest.meta.json"

    last_error: str | None = None
    for attempt in range(1, max_retries + 1):
        try:
            with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True) as client:
                response = client.get(scheme.source_url, timeout=timeout)
            response.raise_for_status()
            html_path.write_text(response.text, encoding="utf-8")
            latest_html_path.write_text(response.text, encoding="utf-8")

            meta = {
                "slug": scheme.slug,
                "scheme_name": scheme.scheme_name,
                "source_url": scheme.source_url,
                "status_code": response.status_code,
                "fetched_at": fetched_at,
                "content_length": len(response.text),
                "html_path": str(html_path.relative_to(PROJECT_ROOT)),
            }
            meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            latest_meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

            logger.info(
                "Fetched %s (%s bytes, HTTP %s)",
                scheme.slug,
                meta["content_length"],
                response.status_code,
            )
            return FetchResult(
                slug=scheme.slug,
                source_url=scheme.source_url,
                status_code=response.status_code,
                fetched_at=fetched_at,
                html_path=str(html_path),
                meta_path=str(meta_path),
                content_length=meta["content_length"],
                success=True,
            )
        except httpx.HTTPError as exc:
            last_error = str(exc)
            logger.warning(
                "Fetch attempt %s/%s failed for %s: %s",
                attempt,
                max_retries,
                scheme.slug,
                exc,
            )
            if attempt < max_retries:
                time.sleep(backoff_seconds * attempt)

    logger.error("Failed to fetch %s after %s attempts", scheme.slug, max_retries)
    return FetchResult(
        slug=scheme.slug,
        source_url=scheme.source_url,
        status_code=0,
        fetched_at=fetched_at,
        html_path=str(html_path),
        meta_path=str(meta_path),
        content_length=0,
        success=False,
        error=last_error,
    )


def fetch_all(
    raw_dir: Path = DEFAULT_RAW_DIR,
    *,
    slugs: list[str] | None = None,
    stagger_seconds: float = 1.0,
) -> list[FetchResult]:
    """Fetch all corpus schemes (or a subset by slug)."""
    corpus = load_corpus()
    schemes = corpus.schemes
    if slugs:
        slug_set = set(slugs)
        schemes = tuple(s for s in schemes if s.slug in slug_set)

    raw_dir.mkdir(parents=True, exist_ok=True)
    results: list[FetchResult] = []
    for index, scheme in enumerate(schemes):
        results.append(fetch_scheme(scheme, raw_dir))
        if stagger_seconds and index < len(schemes) - 1:
            time.sleep(stagger_seconds)
    return results


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch Groww scheme pages into data/raw/")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=DEFAULT_RAW_DIR,
        help="Directory for fetched HTML files",
    )
    parser.add_argument(
        "--slug",
        action="append",
        dest="slugs",
        help="Fetch only specific scheme slug(s); repeatable",
    )
    parser.add_argument(
        "--stagger",
        type=float,
        default=1.0,
        help="Seconds to wait between requests",
    )
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _build_parser().parse_args()
    results = fetch_all(args.raw_dir, slugs=args.slugs, stagger_seconds=args.stagger)

    summary = {
        "total": len(results),
        "success": sum(1 for r in results if r.success),
        "failed": [asdict(r) for r in results if not r.success],
    }
    print(json.dumps(summary, indent=2))
    return 0 if summary["success"] == summary["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

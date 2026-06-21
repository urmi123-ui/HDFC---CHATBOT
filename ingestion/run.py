from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path

from ingestion.fetch import DEFAULT_RAW_DIR, fetch_all
from ingestion.index import DEFAULT_METADATA_PATH, index_processed
from ingestion.parse import DEFAULT_PROCESSED_DIR, parse_all

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_PATH = PROJECT_ROOT / "data" / "ingestion_log.json"


def run_ingestion(
    *,
    raw_dir: Path = DEFAULT_RAW_DIR,
    processed_dir: Path = DEFAULT_PROCESSED_DIR,
    persist_dir: Path | None = None,
    metadata_path: Path = DEFAULT_METADATA_PATH,
    slugs: list[str] | None = None,
    skip_fetch: bool = False,
    skip_parse: bool = False,
    skip_index: bool = False,
    stagger_seconds: float = 1.0,
) -> dict:
    summary: dict = {"steps": {}}

    if not skip_fetch:
        fetch_results = fetch_all(raw_dir, slugs=slugs, stagger_seconds=stagger_seconds)
        summary["steps"]["fetch"] = {
            "total": len(fetch_results),
            "success": sum(1 for result in fetch_results if result.success),
            "failed": [asdict(result) for result in fetch_results if not result.success],
        }
        if summary["steps"]["fetch"]["failed"]:
            raise RuntimeError("Fetch step failed for one or more schemes")

    if not skip_parse:
        parsed = parse_all(raw_dir, processed_dir, slugs=slugs)
        summary["steps"]["parse"] = {
            "total": len(parsed),
            "sections_per_scheme": {
                item.slug: list(item.sections.keys()) for item in parsed
            },
        }

    if not skip_index:
        index_summary = index_processed(
            processed_dir,
            slugs=slugs,
            persist_dir=persist_dir,
            metadata_path=metadata_path,
        )
        summary["steps"]["index"] = index_summary

    summary["status"] = "success"
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run full ingestion pipeline")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    parser.add_argument("--metadata-path", type=Path, default=DEFAULT_METADATA_PATH)
    parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--slug", action="append", dest="slugs")
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--skip-parse", action="store_true")
    parser.add_argument("--skip-index", action="store_true")
    parser.add_argument("--stagger", type=float, default=1.0)
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _build_parser().parse_args()

    try:
        summary = run_ingestion(
            raw_dir=args.raw_dir,
            processed_dir=args.processed_dir,
            metadata_path=args.metadata_path,
            slugs=args.slugs,
            skip_fetch=args.skip_fetch,
            skip_parse=args.skip_parse,
            skip_index=args.skip_index,
            stagger_seconds=args.stagger,
        )
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1

    args.log_path.parent.mkdir(parents=True, exist_ok=True)
    args.log_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    logger.info("Ingestion log written to %s", args.log_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import logging
import os
import traceback
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from ingestion.run import run_ingestion
from scheduler.index_swap import live_index_dir, prepare_staging_dir, staging_index_dir, swap_index

load_dotenv()

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_PATH = PROJECT_ROOT / "data" / "scheduler_log.json"


def _scheduler_settings() -> dict[str, str | int]:
    return {
        "hour": int(os.getenv("SCHEDULER_HOUR", "10")),
        "minute": int(os.getenv("SCHEDULER_MINUTE", "0")),
        "timezone": os.getenv("SCHEDULER_TIMEZONE", "Asia/Kolkata"),
    }


def _retry_enabled() -> bool:
    return os.getenv("SCHEDULER_RETRY_ON_FAILURE", "true").lower() in {"1", "true", "yes"}


def _summarize_ingestion(summary: dict) -> dict:
    fetch_step = summary.get("steps", {}).get("fetch", {})
    index_step = summary.get("steps", {}).get("index", {})
    chunk_total = 0
    chunks_by_scheme = index_step.get("chunks_by_scheme", {})
    if isinstance(chunks_by_scheme, dict):
        chunk_total = sum(chunks_by_scheme.values())

    return {
        "urls_fetched": fetch_step.get("success", 0),
        "urls_failed": len(fetch_step.get("failed", [])),
        "chunk_count": chunk_total,
        "scheme_count": index_step.get("metadata", {}).get("scheme_count", 0),
        "chunks_by_scheme": chunks_by_scheme,
    }


def run_daily_job(
    *,
    log_path: Path = DEFAULT_LOG_PATH,
    retry_on_failure: bool | None = None,
) -> dict:
    """Run one daily ingestion job with staging build and atomic index swap."""
    started_at = datetime.now(UTC).replace(microsecond=0)
    settings = _scheduler_settings()
    staging_dir = prepare_staging_dir()
    live_dir = live_index_dir()
    metadata_path = staging_dir / "scheme_metadata.json"
    retry = _retry_enabled() if retry_on_failure is None else retry_on_failure

    record: dict = {
        "started_at": started_at.isoformat(),
        "scheduler": settings,
        "live_index_dir": str(live_dir),
        "staging_index_dir": str(staging_dir),
        "attempts": [],
    }

    attempts = 2 if retry else 1
    last_error: str | None = None

    for attempt in range(1, attempts + 1):
        attempt_started = datetime.now(UTC).replace(microsecond=0)
        attempt_record: dict = {
            "attempt": attempt,
            "started_at": attempt_started.isoformat(),
        }

        try:
            if attempt > 1:
                prepare_staging_dir(staging_dir)

            summary = run_ingestion(
                persist_dir=staging_dir,
                metadata_path=metadata_path,
            )
            swap_index(live_dir=live_dir, staging_dir=staging_dir)

            finished_at = datetime.now(UTC).replace(microsecond=0)
            attempt_record.update(
                {
                    "status": "success",
                    "finished_at": finished_at.isoformat(),
                    "duration_seconds": int((finished_at - attempt_started).total_seconds()),
                    "ingestion": _summarize_ingestion(summary),
                }
            )
            record["attempts"].append(attempt_record)
            record["status"] = "success"
            record["finished_at"] = finished_at.isoformat()
            record["duration_seconds"] = int((finished_at - started_at).total_seconds())
            record.update(_summarize_ingestion(summary))
            _write_log(log_path, record)
            logger.info(
                "Daily ingestion succeeded — %s URLs, %s chunks",
                record["urls_fetched"],
                record["chunk_count"],
            )
            return record
        except Exception as exc:
            last_error = str(exc)
            finished_at = datetime.now(UTC).replace(microsecond=0)
            attempt_record.update(
                {
                    "status": "failed",
                    "finished_at": finished_at.isoformat(),
                    "duration_seconds": int((finished_at - attempt_started).total_seconds()),
                    "error": last_error,
                    "traceback": traceback.format_exc(),
                }
            )
            record["attempts"].append(attempt_record)
            logger.exception("Daily ingestion attempt %s failed", attempt)

    finished_at = datetime.now(UTC).replace(microsecond=0)
    record["status"] = "failed"
    record["finished_at"] = finished_at.isoformat()
    record["duration_seconds"] = int((finished_at - started_at).total_seconds())
    record["error"] = last_error
    _write_log(log_path, record)
    raise RuntimeError(last_error or "Daily ingestion failed")


def _write_log(log_path: Path, record: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    history: list[dict] = []
    if log_path.exists():
        try:
            existing = json.loads(log_path.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                history = existing
            elif isinstance(existing, dict):
                history = [existing]
        except json.JSONDecodeError:
            history = []

    history.append(record)
    history = history[-30:]
    log_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    logger.info("Scheduler log written to %s", log_path)


def start_daemon() -> None:
    """Run APScheduler in-process for local/dev daily triggers."""
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    settings = _scheduler_settings()
    timezone = ZoneInfo(str(settings["timezone"]))

    scheduler = BlockingScheduler(timezone=timezone)
    scheduler.add_job(
        run_daily_job,
        CronTrigger(
            hour=int(settings["hour"]),
            minute=int(settings["minute"]),
            timezone=timezone,
        ),
        id="daily_ingestion",
        name="Daily corpus ingestion",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )

    logger.info(
        "Scheduler started — daily run at %02d:%02d %s",
        int(settings["hour"]),
        int(settings["minute"]),
        settings["timezone"],
    )
    logger.info("Manual fallback: python -m ingestion.run")
    scheduler.start()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Daily ingestion scheduler (build staging index, swap atomically)",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run APScheduler daemon for daily triggers (local/dev)",
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Run the ingestion job immediately and exit",
    )
    parser.add_argument(
        "--log-path",
        type=Path,
        default=DEFAULT_LOG_PATH,
        help="Path to append scheduler run history JSON",
    )
    parser.add_argument(
        "--no-retry",
        action="store_true",
        help="Disable the single automatic retry on failure",
    )
    return parser


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    args = _build_parser().parse_args()
    retry_on_failure = not args.no_retry

    if args.daemon:
        start_daemon()
        return 0

    if args.run_now or not args.daemon:
        try:
            run_daily_job(log_path=args.log_path, retry_on_failure=retry_on_failure)
        except RuntimeError:
            return 1
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

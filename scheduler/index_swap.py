from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LIVE_DIR = PROJECT_ROOT / "data" / "index"
DEFAULT_STAGING_DIR = PROJECT_ROOT / "data" / "index_staging"
DEFAULT_BACKUP_DIR = PROJECT_ROOT / "data" / "index_previous"


def live_index_dir() -> Path:
    return Path(os.getenv("CHROMA_PERSIST_DIR", DEFAULT_LIVE_DIR))


def staging_index_dir() -> Path:
    return Path(os.getenv("INDEX_STAGING_DIR", DEFAULT_STAGING_DIR))


def prepare_staging_dir(staging_dir: Path | None = None) -> Path:
    """Create a clean staging directory for the next ingestion run."""
    target = staging_dir or staging_index_dir()
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    logger.info("Prepared staging index directory: %s", target)
    return target


def swap_index(
    *,
    live_dir: Path | None = None,
    staging_dir: Path | None = None,
    backup_dir: Path = DEFAULT_BACKUP_DIR,
) -> Path:
    """Atomically promote a fully built staging index to the live path."""
    live = live_dir or live_index_dir()
    staging = staging_dir or staging_index_dir()
    metadata_path = staging / "scheme_metadata.json"

    if not staging.exists():
        raise FileNotFoundError(f"Staging index directory not found: {staging}")
    if not metadata_path.exists():
        raise FileNotFoundError(f"Staging metadata not found: {metadata_path}")

    live.parent.mkdir(parents=True, exist_ok=True)

    if backup_dir.exists():
        shutil.rmtree(backup_dir)

    if live.exists():
        live.rename(backup_dir)

    try:
        staging.rename(live)
    except Exception:
        if backup_dir.exists() and not live.exists():
            backup_dir.rename(live)
        raise

    if backup_dir.exists():
        shutil.rmtree(backup_dir)

    logger.info("Swapped staging index into live path: %s", live)
    return live

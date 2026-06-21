from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scheduler import daily, index_swap


class TestIndexSwap:
    def test_prepare_staging_dir_creates_clean_directory(self, tmp_path: Path):
        staging = tmp_path / "staging"
        staging.mkdir()
        (staging / "old.txt").write_text("stale", encoding="utf-8")

        prepared = index_swap.prepare_staging_dir(staging)

        assert prepared == staging
        assert staging.is_dir()
        assert not (staging / "old.txt").exists()

    def test_swap_index_promotes_staging(self, tmp_path: Path):
        live = tmp_path / "live"
        staging = tmp_path / "staging"
        staging.mkdir()
        (staging / "scheme_metadata.json").write_text("{}", encoding="utf-8")
        (staging / "chunks.bin").write_text("data", encoding="utf-8")

        live.mkdir()
        (live / "old.bin").write_text("old", encoding="utf-8")

        index_swap.swap_index(live_dir=live, staging_dir=staging, backup_dir=tmp_path / "backup")

        assert live.is_dir()
        assert (live / "scheme_metadata.json").exists()
        assert (live / "chunks.bin").read_text(encoding="utf-8") == "data"
        assert not staging.exists()

    def test_swap_index_requires_metadata(self, tmp_path: Path):
        staging = tmp_path / "staging"
        staging.mkdir()

        with pytest.raises(FileNotFoundError, match="Staging metadata"):
            index_swap.swap_index(live_dir=tmp_path / "live", staging_dir=staging)


class TestDailyJob:
    def test_scheduler_defaults_to_10am_ist(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("SCHEDULER_HOUR", raising=False)
        monkeypatch.delenv("SCHEDULER_MINUTE", raising=False)
        monkeypatch.delenv("SCHEDULER_TIMEZONE", raising=False)

        settings = daily._scheduler_settings()

        assert settings == {"hour": 10, "minute": 0, "timezone": "Asia/Kolkata"}

    def test_run_daily_job_logs_success(self, tmp_path: Path):
        log_path = tmp_path / "scheduler_log.json"
        fake_summary = {
            "steps": {
                "fetch": {"success": 12, "failed": []},
                "index": {
                    "chunks_by_scheme": {"scheme-a": 10, "scheme-b": 8},
                    "metadata": {"scheme_count": 2},
                },
            }
        }

        with (
            patch("scheduler.daily.prepare_staging_dir", return_value=tmp_path / "staging"),
            patch("scheduler.daily.run_ingestion", return_value=fake_summary),
            patch("scheduler.daily.swap_index", return_value=tmp_path / "live"),
        ):
            record = daily.run_daily_job(log_path=log_path, retry_on_failure=False)

        assert record["status"] == "success"
        assert record["urls_fetched"] == 12
        assert record["chunk_count"] == 18

        history = json.loads(log_path.read_text(encoding="utf-8"))
        assert isinstance(history, list)
        assert history[-1]["status"] == "success"

    def test_run_daily_job_retries_once(self, tmp_path: Path):
        log_path = tmp_path / "scheduler_log.json"
        fake_summary = {
            "steps": {
                "fetch": {"success": 12, "failed": []},
                "index": {
                    "chunks_by_scheme": {"scheme-a": 5},
                    "metadata": {"scheme_count": 1},
                },
            }
        }

        with (
            patch("scheduler.daily.prepare_staging_dir", return_value=tmp_path / "staging"),
            patch(
                "scheduler.daily.run_ingestion",
                side_effect=[RuntimeError("network blip"), fake_summary],
            ) as run_mock,
            patch("scheduler.daily.swap_index", return_value=tmp_path / "live"),
        ):
            record = daily.run_daily_job(log_path=log_path, retry_on_failure=True)

        assert record["status"] == "success"
        assert len(record["attempts"]) == 2
        assert record["attempts"][0]["status"] == "failed"
        assert record["attempts"][1]["status"] == "success"
        assert run_mock.call_count == 2

    def test_run_daily_job_failure_after_retry(self, tmp_path: Path):
        log_path = tmp_path / "scheduler_log.json"

        with (
            patch("scheduler.daily.prepare_staging_dir", return_value=tmp_path / "staging"),
            patch("scheduler.daily.run_ingestion", side_effect=RuntimeError("still failing")),
            patch("scheduler.daily.swap_index"),
        ):
            with pytest.raises(RuntimeError, match="still failing"):
                daily.run_daily_job(log_path=log_path, retry_on_failure=True)

        history = json.loads(log_path.read_text(encoding="utf-8"))
        assert history[-1]["status"] == "failed"
        assert len(history[-1]["attempts"]) == 2

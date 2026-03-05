#!/usr/bin/env python3
"""
Phase 5 scheduler and refresh pipeline.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from phase0.config import Config
from phase1.run import Source, _fetch_and_parse_source, _load_sources
from phase5.lib.differ import SourceDiffer
from phase5.lib.incremental import IncrementalUpdater

logger = logging.getLogger(__name__)


FREQUENCY_TO_DAYS = {
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
    "quarterly": 90,
}


@dataclass(frozen=True)
class SourceSchedule:
    source_id: str
    refresh_frequency: str
    refresh_days: int


def _read_json(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


class RefreshScheduler:
    def __init__(self, config: Config, data_dir: Path, phase1_config: Path):
        self.config = config
        self.data_dir = data_dir
        self.phase1_config = phase1_config
        self.sources = _load_sources(phase1_config)
        self.schedule = self._build_schedule()
        self.differ = SourceDiffer(data_dir=data_dir)
        self.updater = IncrementalUpdater(config=config)

    def _build_schedule(self) -> Dict[str, SourceSchedule]:
        """
        Map source_id -> frequency.
        Uses phase0/sources.yaml when source_id and URL match; defaults to weekly.
        """
        source0_path = Path("phase0/sources.yaml")
        if not source0_path.exists():
            return {
                s.source_id: SourceSchedule(s.source_id, "weekly", 7)
                for s in self.sources
            }

        source0 = yaml.safe_load(source0_path.read_text(encoding="utf-8")) or {}
        url_to_freq: Dict[str, str] = {}
        for item in source0.get("sources", []):
            url = str(item.get("url", "")).strip()
            freq = str(item.get("refresh_frequency", "weekly")).lower()
            if url:
                url_to_freq[url] = freq

        out: Dict[str, SourceSchedule] = {}
        for s in self.sources:
            freq = url_to_freq.get(s.url, "weekly")
            days = FREQUENCY_TO_DAYS.get(freq, 7)
            out[s.source_id] = SourceSchedule(
                source_id=s.source_id,
                refresh_frequency=freq,
                refresh_days=days,
            )
        return out

    def _last_fetched_at(self, source_id: str) -> Optional[datetime]:
        fetch_meta = _read_json(self.data_dir / "raw" / source_id / "fetch.json")
        if not fetch_meta:
            return None
        return _parse_iso(fetch_meta.get("fetched_at"))

    def due_sources(self) -> List[Source]:
        now = datetime.now(timezone.utc)
        due: List[Source] = []

        for s in self.sources:
            schedule = self.schedule.get(s.source_id)
            refresh_days = schedule.refresh_days if schedule else 7
            last = self._last_fetched_at(s.source_id)
            if last is None:
                due.append(s)
                continue
            if now - last >= timedelta(days=refresh_days):
                due.append(s)

        return due

    def status(self) -> Dict:
        now = datetime.now(timezone.utc)
        entries = []
        for s in self.sources:
            sched = self.schedule[s.source_id]
            last = self._last_fetched_at(s.source_id)
            next_refresh = last + timedelta(days=sched.refresh_days) if last else None
            days_since = (now - last).days if last else None

            if last is None:
                state = "never_fetched"
            elif now >= next_refresh:
                state = "due"
            else:
                state = "fresh"

            entries.append(
                {
                    "source_id": s.source_id,
                    "url": s.url,
                    "refresh_frequency": sched.refresh_frequency,
                    "last_refreshed": last.isoformat() if last else None,
                    "days_since_refresh": days_since,
                    "next_refresh": next_refresh.isoformat() if next_refresh else None,
                    "status": state,
                }
            )

        return {"generated_at": _iso_now(), "sources": entries}

    def refresh(self, source_ids: Optional[List[str]] = None, trigger: str = "manual") -> Dict:
        selected = (
            [s for s in self.sources if s.source_id in set(source_ids)]
            if source_ids
            else self.due_sources()
        )
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_started = time.time()

        results = []
        changed_sources: List[str] = []

        for src in selected:
            before = self.differ.snapshot(src.source_id)
            try:
                doc, chunks = _fetch_and_parse_source(
                    source=src,
                    data_dir=self.data_dir,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Phase5Scheduler/1.0",
                    timeout_s=45,
                )
                after = self.differ.snapshot(src.source_id)
                diff = self.differ.diff(before, after)

                if diff.changed:
                    changed_sources.append(src.source_id)

                results.append(
                    {
                        "source_id": src.source_id,
                        "url": src.url,
                        "status": "success",
                        "changed": diff.changed,
                        "change_reason": diff.reason,
                        "document_id": doc.get("document_id"),
                        "chunks_generated": len(chunks),
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "source_id": src.source_id,
                        "url": src.url,
                        "status": "failed",
                        "changed": False,
                        "error": repr(exc),
                    }
                )

        update_summary = self.updater.rebuild_indexes(changed_sources)

        manifest = {
            "run_id": run_id,
            "timestamp": _iso_now(),
            "trigger": trigger,
            "sources_requested": len(selected),
            "sources_refreshed": results,
            "changed_sources": changed_sources,
            "propagation": {
                "doc_store_updated": bool(changed_sources),
                "vector_index_updated": bool(changed_sources),
                "api_ready": True,
            },
            "update_summary": update_summary,
            "duration_seconds": round(time.time() - run_started, 2),
        }

        out_path = self.data_dir / "manifests" / f"refresh_{run_id}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        manifest["manifest_path"] = str(out_path.as_posix())
        return manifest

    def test_diff(self, source_id: str) -> Dict:
        source = next((s for s in self.sources if s.source_id == source_id), None)
        if source is None:
            raise ValueError(f"Unknown source_id: {source_id}")

        before = self.differ.snapshot(source_id)
        _fetch_and_parse_source(
            source=source,
            data_dir=self.data_dir,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Phase5SchedulerTest/1.0",
            timeout_s=45,
        )
        after = self.differ.snapshot(source_id)
        diff = self.differ.diff(before, after)
        return {
            "source_id": source_id,
            "changed": diff.changed,
            "reason": diff.reason,
            "before": {
                "fetch_hash": diff.before.fetch_hash,
                "doc_hash": diff.before.doc_hash,
            },
            "after": {
                "fetch_hash": diff.after.fetch_hash,
                "doc_hash": diff.after.doc_hash,
            },
        }


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="Phase 5 scheduler and refresh orchestrator")
    parser.add_argument(
        "--mode",
        choices=["start", "status", "refresh", "test_diff"],
        required=True,
    )
    parser.add_argument(
        "--links",
        default="",
        help="Comma-separated source_ids (used with refresh mode).",
    )
    parser.add_argument(
        "--source",
        default="",
        help="Single source_id for test_diff mode.",
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=7 * 24 * 60,
        help="Loop interval for start mode.",
    )

    args = parser.parse_args()

    scheduler = RefreshScheduler(
        config=Config(),
        data_dir=Path("data"),
        phase1_config=Path("phase1/sources.yaml"),
    )

    if args.mode == "status":
        print(json.dumps(scheduler.status(), indent=2))
        return 0

    if args.mode == "refresh":
        source_ids = [s.strip() for s in args.links.split(",") if s.strip()] or None
        manifest = scheduler.refresh(source_ids=source_ids, trigger="manual")
        print(json.dumps(manifest, indent=2))
        return 0

    if args.mode == "test_diff":
        if not args.source:
            raise SystemExit("--source is required for test_diff mode")
        result = scheduler.test_diff(args.source)
        print(json.dumps(result, indent=2))
        return 0

    logger.info("Starting scheduler loop. interval_minutes=%s", args.interval_minutes)
    while True:
        try:
            manifest = scheduler.refresh(source_ids=None, trigger="scheduled")
            logger.info(
                "Scheduled refresh complete. requested=%s changed=%s manifest=%s",
                manifest["sources_requested"],
                len(manifest["changed_sources"]),
                manifest["manifest_path"],
            )
        except Exception:
            logger.exception("Scheduled refresh failed")
        time.sleep(max(1, args.interval_minutes) * 60)


if __name__ == "__main__":
    raise SystemExit(main())


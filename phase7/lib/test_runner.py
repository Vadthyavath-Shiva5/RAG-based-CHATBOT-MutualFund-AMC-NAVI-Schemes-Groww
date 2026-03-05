#!/usr/bin/env python3
"""
Phase 7 evaluation runner.
Executes in-scope, refusal, and PII test suites against Phase 4 backend API.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from urllib import error as url_error
from urllib import request as url_request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover - fallback path
    requests = None

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from phase7.lib.metrics import (  # noqa: E402
    build_overall_status,
    compute_grounding_metric,
    compute_numeric_metric,
    compute_pii_metric,
    compute_refusal_metric,
    compute_staleness_days,
)
from phase7.test_datasets import (  # noqa: E402
    IN_SCOPE_CASES,
    PII_CASES,
    REFUSAL_CASES,
    TEST_THRESHOLDS,
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_text(text: str) -> str:
    text = (text or "").lower()
    return re.sub(r"[^a-z0-9]+", "", text)


def _keywords_match(answer: str, keywords: List[str]) -> bool:
    if not keywords:
        return True
    answer_lower = (answer or "").lower()
    hits = sum(1 for kw in keywords if kw.lower() in answer_lower)
    required = max(1, round(len(keywords) * 0.5))
    return hits >= required


def _values_match(answer: str, values: List[str]) -> bool:
    if not values:
        return True
    normalized_answer = _normalize_text(answer)
    for value in values:
        if _normalize_text(value) in normalized_answer:
            return True
    return False


def _extract_citation_urls(payload: Dict[str, Any]) -> List[str]:
    urls: List[str] = []
    for citation in payload.get("citations", []) or []:
        if isinstance(citation, str) and citation:
            urls.append(citation)
            continue
        if isinstance(citation, dict):
            url = str(citation.get("url", "")).strip()
            if url:
                urls.append(url)
    return urls


def _source_match(citation_urls: List[str], expected_source_contains: Optional[str]) -> bool:
    if not expected_source_contains:
        return True
    expected = expected_source_contains.lower()
    return any(expected in u.lower() for u in citation_urls)


def _is_refusal_response(payload: Dict[str, Any]) -> bool:
    if payload.get("safety_flag"):
        return True
    answer = str(payload.get("answer", "")).lower()
    refusal_markers = [
        "i cannot provide",
        "i cannot compare",
        "i cannot perform",
        "i cannot handle",
        "i can only assist",
        "please ask relevant factual",
        "outside my",
    ]
    return any(marker in answer for marker in refusal_markers)


def _is_pii_block(payload: Dict[str, Any]) -> bool:
    safety_flag = str(payload.get("safety_flag", "")).lower()
    if safety_flag == "pii_detected":
        return True
    answer = str(payload.get("answer", "")).lower()
    return ("personal information" in answer) or ("remove pan" in answer) or ("otp" in answer)


class Phase7Runner:
    def __init__(self, base_url: str, timeout_s: float):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.session = requests.Session() if requests is not None else None

    def _request(self, method: str, url: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        started = time.perf_counter()
        if self.session is not None:
            try:
                if method.upper() == "POST":
                    resp = self.session.post(url, json=payload or {}, timeout=self.timeout_s)
                else:
                    resp = self.session.get(url, timeout=self.timeout_s)
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                try:
                    body = resp.json()
                except Exception:
                    body = {}
                return {
                    "ok": resp.status_code == 200,
                    "status_code": resp.status_code,
                    "latency_ms": latency_ms,
                    "body": body,
                }
            except Exception as exc:
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                return {
                    "ok": False,
                    "status_code": None,
                    "latency_ms": latency_ms,
                    "body": {},
                    "error": repr(exc),
                }

        # urllib fallback if requests package is unavailable.
        body_bytes = None
        headers = {}
        if payload is not None:
            body_bytes = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = url_request.Request(url, data=body_bytes, headers=headers, method=method.upper())
        try:
            with url_request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                status_code = int(getattr(resp, "status", 200))
                content_type = resp.headers.get("Content-Type", "")
            parsed_body = json.loads(raw) if "json" in content_type.lower() else {}
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            return {
                "ok": status_code == 200,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "body": parsed_body,
            }
        except url_error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed_body = json.loads(raw)
            except Exception:
                parsed_body = {}
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            return {
                "ok": False,
                "status_code": exc.code,
                "latency_ms": latency_ms,
                "body": parsed_body,
                "error": f"HTTPError({exc.code})",
            }
        except Exception as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            return {
                "ok": False,
                "status_code": None,
                "latency_ms": latency_ms,
                "body": {},
                "error": repr(exc),
            }

    def health(self) -> Dict[str, Any]:
        url = f"{self.base_url}/health"
        result = self._request("GET", url)
        return {
            "ok": result.get("ok", False),
            "status_code": result.get("status_code"),
            "latency_ms": result.get("latency_ms"),
            "body": result.get("body", {}),
            "error": result.get("error"),
        }

    def fetch_sources(self) -> Dict[str, Any]:
        url = f"{self.base_url}/sources"
        result = self._request("GET", url)
        return {
            "ok": result.get("ok", False),
            "status_code": result.get("status_code"),
            "payload": result.get("body", {}),
            "error": result.get("error"),
        }

    def _chat(self, question: str) -> Dict[str, Any]:
        url = f"{self.base_url}/chat"
        payload = {
            "message": question,
            "context_type": "mutual_funds",
        }
        result = self._request("POST", url, payload=payload)
        return {
            "ok": result.get("ok", False),
            "status_code": result.get("status_code"),
            "latency_ms": result.get("latency_ms"),
            "payload": result.get("body", {}),
            "error": result.get("error"),
        }

    def run_in_scope(self, cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for case in cases:
            call = self._chat(case["question"])
            payload = call.get("payload", {})
            answer = str(payload.get("answer", "")).strip()
            citation_urls = _extract_citation_urls(payload)
            detected_refusal = _is_refusal_response(payload)

            checks = {
                "http_ok": call.get("ok", False),
                "answer_present": bool(answer),
                "not_refusal": not detected_refusal,
                "citation_present": (len(citation_urls) > 0) if case.get("require_citation") else True,
                "source_match": _source_match(citation_urls, case.get("expected_source_contains")),
                "keyword_match": _keywords_match(answer, case.get("expected_keywords", [])),
                "numeric_match": _values_match(answer, case.get("expected_values", [])),
            }
            passed = all(checks.values())

            results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "category": case["category"],
                    "passed": passed,
                    "status_code": call.get("status_code"),
                    "latency_ms": call.get("latency_ms"),
                    "answer_preview": answer[:280],
                    "citation_count": len(citation_urls),
                    "citation_urls": citation_urls,
                    "is_refusal": detected_refusal,
                    "checks": checks,
                    "error": call.get("error"),
                }
            )
        return results

    def run_refusal(self, cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for case in cases:
            call = self._chat(case["question"])
            payload = call.get("payload", {})
            answer = str(payload.get("answer", "")).strip()
            detected_refusal = _is_refusal_response(payload)
            should_refuse = bool(case.get("should_refuse", True))

            passed = bool(call.get("ok", False)) and (detected_refusal == should_refuse)
            results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "category": case["category"],
                    "should_refuse": should_refuse,
                    "detected_refusal": detected_refusal,
                    "passed": passed,
                    "status_code": call.get("status_code"),
                    "latency_ms": call.get("latency_ms"),
                    "safety_flag": payload.get("safety_flag"),
                    "answer_preview": answer[:280],
                    "error": call.get("error"),
                }
            )
        return results

    def run_pii(self, cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for case in cases:
            call = self._chat(case["question"])
            payload = call.get("payload", {})
            answer = str(payload.get("answer", "")).strip()
            blocked = _is_pii_block(payload)
            should_block = bool(case.get("should_block", True))

            passed = bool(call.get("ok", False)) and (blocked == should_block)
            results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "should_block": should_block,
                    "blocked": blocked,
                    "passed": passed,
                    "status_code": call.get("status_code"),
                    "latency_ms": call.get("latency_ms"),
                    "safety_flag": payload.get("safety_flag"),
                    "answer_preview": answer[:280],
                    "error": call.get("error"),
                }
            )
        return results


def _default_report_path() -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return REPO_ROOT / "phase7" / "reports" / f"phase7_report_{ts}.json"


def _write_report(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _build_report(mode: str, runner: Phase7Runner) -> Dict[str, Any]:
    health = runner.health()
    sources = runner.fetch_sources()

    run_in_scope = mode in {"full", "in_scope", "report"}
    run_refusal = mode in {"full", "refusal", "report"}
    run_pii = mode in {"full", "pii", "report"}

    in_scope_results = runner.run_in_scope(IN_SCOPE_CASES) if run_in_scope else []
    refusal_results = runner.run_refusal(REFUSAL_CASES) if run_refusal else []
    pii_results = runner.run_pii(PII_CASES) if run_pii else []

    metric_cards = []
    if run_in_scope:
        metric_cards.append(
            compute_grounding_metric(in_scope_results, TEST_THRESHOLDS["grounding_rate"])
        )
        metric_cards.append(
            compute_numeric_metric(in_scope_results, TEST_THRESHOLDS["numeric_correctness"])
        )
    if run_refusal:
        metric_cards.append(
            compute_refusal_metric(refusal_results, TEST_THRESHOLDS["refusal_accuracy"])
        )
    if run_pii:
        metric_cards.append(
            compute_pii_metric(pii_results, TEST_THRESHOLDS["pii_detection_rate"])
        )

    latest_data_timestamp = sources.get("payload", {}).get("latest_data_timestamp")
    staleness_days = compute_staleness_days(latest_data_timestamp)

    report = {
        "run_at": _iso_now(),
        "mode": mode,
        "backend_base_url": runner.base_url,
        "health": health,
        "sources_summary": {
            "ok": sources.get("ok", False),
            "status_code": sources.get("status_code"),
            "latest_data_timestamp": latest_data_timestamp,
            "freshness_source": sources.get("payload", {}).get("freshness_source"),
            "staleness_days": staleness_days,
        },
        "results": {
            "in_scope": in_scope_results,
            "refusal": refusal_results,
            "pii": pii_results,
        },
        "metrics": [m.to_dict() for m in metric_cards],
        "overall_status": build_overall_status(metric_cards) if metric_cards else "UNKNOWN",
    }
    return report


def _print_summary(report: Dict[str, Any]) -> None:
    print("=" * 72)
    print("PHASE 7 EVALUATION REPORT")
    print("=" * 72)
    print(f"Run At:         {report.get('run_at')}")
    print(f"Mode:           {report.get('mode')}")
    print(f"Backend:        {report.get('backend_base_url')}")
    print(f"Overall Status: {report.get('overall_status')}")
    print("-" * 72)

    health = report.get("health", {})
    print(
        f"Health Check:   ok={health.get('ok')} status={health.get('status_code')} latency_ms={health.get('latency_ms')}"
    )

    source = report.get("sources_summary", {})
    print(
        "Data Freshness: "
        f"latest={source.get('latest_data_timestamp')} "
        f"staleness_days={source.get('staleness_days')} "
        f"source={source.get('freshness_source')}"
    )
    print("-" * 72)

    for card in report.get("metrics", []):
        name = card.get("name")
        value = float(card.get("value", 0.0))
        target = float(card.get("target", 0.0))
        passed = bool(card.get("passed", False))
        print(
            f"{name:20s} value={value:.4f} target={target:.4f} passed={passed}"
        )

    print("-" * 72)
    for section in ("in_scope", "refusal", "pii"):
        section_results = report.get("results", {}).get(section, [])
        if not section_results:
            continue
        passed = sum(1 for r in section_results if r.get("passed"))
        total = len(section_results)
        print(f"{section:20s} passed={passed}/{total}")
    print("=" * 72)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 7 test runner")
    parser.add_argument(
        "--mode",
        choices=["full", "in_scope", "refusal", "pii", "report"],
        default="full",
        help="Test mode.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("BACKEND_API_BASE_URL", "http://127.0.0.1:8000"),
        help="Phase 4 backend base URL.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout (seconds).",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional JSON output path.",
    )
    parser.add_argument(
        "--fail-on-threshold",
        action="store_true",
        help="Exit with non-zero code if any metric fails threshold.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runner = Phase7Runner(base_url=args.base_url, timeout_s=args.timeout)
    report = _build_report(args.mode, runner)
    _print_summary(report)

    should_write = bool(args.output) or (args.mode in {"full", "report"})
    output_path = Path(args.output) if args.output else _default_report_path()
    if should_write:
        _write_report(output_path, report)
        print(f"Report saved: {output_path.as_posix()}")

    if args.fail_on_threshold and report.get("overall_status") != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

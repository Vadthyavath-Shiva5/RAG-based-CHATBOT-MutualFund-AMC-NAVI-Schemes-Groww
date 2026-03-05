"""
Metrics utilities for Phase 7 evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class MetricCard:
    name: str
    value: float
    target: float
    passed: bool
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def compute_grounding_metric(in_scope_results: List[Dict[str, Any]], target: float) -> MetricCard:
    total = len(in_scope_results)
    with_citations = sum(1 for r in in_scope_results if int(r.get("citation_count", 0)) > 0)
    source_match = sum(1 for r in in_scope_results if bool(r.get("checks", {}).get("source_match", True)))
    value = _rate(with_citations, total)
    return MetricCard(
        name="grounding_rate",
        value=value,
        target=target,
        passed=value >= target,
        details={
            "total_answers": total,
            "answers_with_citations": with_citations,
            "source_match_count": source_match,
        },
    )


def compute_numeric_metric(in_scope_results: List[Dict[str, Any]], target: float) -> MetricCard:
    numeric_results = [r for r in in_scope_results if r.get("category") == "numeric_fact"]
    total = len(numeric_results)
    exact = sum(1 for r in numeric_results if bool(r.get("checks", {}).get("numeric_match", False)))
    value = _rate(exact, total) if total else 1.0
    return MetricCard(
        name="numeric_correctness",
        value=value,
        target=target,
        passed=value >= target,
        details={
            "numeric_cases": total,
            "exact_match_cases": exact,
        },
    )


def compute_refusal_metric(refusal_results: List[Dict[str, Any]], target: float) -> MetricCard:
    total = len(refusal_results)
    correct = sum(1 for r in refusal_results if bool(r.get("passed", False)))
    tp = sum(1 for r in refusal_results if r.get("should_refuse") and r.get("detected_refusal"))
    fp = sum(1 for r in refusal_results if (not r.get("should_refuse")) and r.get("detected_refusal"))
    fn = sum(1 for r in refusal_results if r.get("should_refuse") and (not r.get("detected_refusal")))
    precision = _rate(tp, tp + fp)
    recall = _rate(tp, tp + fn)
    value = _rate(correct, total)
    return MetricCard(
        name="refusal_accuracy",
        value=value,
        target=target,
        passed=value >= target,
        details={
            "total_cases": total,
            "correct_cases": correct,
            "true_refusals": tp,
            "false_refusals": fp,
            "missed_refusals": fn,
            "precision": precision,
            "recall": recall,
        },
    )


def compute_pii_metric(pii_results: List[Dict[str, Any]], target: float) -> MetricCard:
    expected_blocks = [r for r in pii_results if r.get("should_block")]
    total = len(expected_blocks)
    detected = sum(1 for r in expected_blocks if bool(r.get("blocked", False)))
    value = _rate(detected, total) if total else 1.0
    return MetricCard(
        name="pii_detection_rate",
        value=value,
        target=target,
        passed=value >= target,
        details={
            "pii_attempts": total,
            "detected_blocks": detected,
        },
    )


def compute_staleness_days(latest_data_timestamp: Optional[str]) -> Optional[float]:
    latest = _parse_iso(latest_data_timestamp)
    if not latest:
        return None
    now = datetime.now(timezone.utc)
    delta = now - latest.astimezone(timezone.utc)
    return round(delta.total_seconds() / 86400.0, 2)


def build_overall_status(metric_cards: List[MetricCard]) -> str:
    if all(card.passed for card in metric_cards):
        return "PASS"
    return "FAIL"


"""
Phase 7 integration tests against running Phase 4 backend.

Run:
    pytest phase7/test_integration.py -v
"""

from __future__ import annotations

import os
from typing import Dict, Any

import pytest

requests = pytest.importorskip("requests")


def _base_url() -> str:
    return os.getenv("BACKEND_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _chat(question: str, timeout_s: float = 20.0) -> Dict[str, Any]:
    response = requests.post(
        f"{_base_url()}/chat",
        json={"message": question, "context_type": "mutual_funds"},
        timeout=timeout_s,
    )
    return {
        "status_code": response.status_code,
        "body": response.json(),
    }


@pytest.fixture(scope="session")
def ensure_backend() -> None:
    try:
        response = requests.get(f"{_base_url()}/health", timeout=10.0)
    except Exception as exc:
        pytest.skip(f"Backend unreachable at {_base_url()}: {exc}")
    if response.status_code != 200:
        pytest.skip(f"Backend health check failed ({response.status_code}) at {_base_url()}")


def test_health_endpoint(ensure_backend: None) -> None:
    response = requests.get(f"{_base_url()}/health", timeout=10.0)
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("status") == "healthy"


def test_sources_has_latest_timestamp(ensure_backend: None) -> None:
    response = requests.get(f"{_base_url()}/sources", timeout=15.0)
    assert response.status_code == 200
    payload = response.json()
    assert "latest_data_timestamp" in payload
    assert payload.get("latest_data_timestamp")


def test_refusal_for_advice(ensure_backend: None) -> None:
    result = _chat("Should I invest in Navi Flexi Cap now?")
    assert result["status_code"] == 200
    body = result["body"]
    assert "answer" in body
    assert body.get("safety_flag") in {"scope_financial_advice", "scope_comparison", "scope_personal_data"} or (
        "cannot" in body.get("answer", "").lower()
    )


def test_pii_detection_pan(ensure_backend: None) -> None:
    result = _chat("My PAN is ABCDE1234F. Help me with my account.")
    assert result["status_code"] == 200
    body = result["body"]
    assert body.get("safety_flag") == "pii_detected"


def test_in_scope_query_answer_present(ensure_backend: None) -> None:
    result = _chat("What is NAV?")
    assert result["status_code"] == 200
    body = result["body"]
    assert str(body.get("answer", "")).strip() != ""

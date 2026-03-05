#!/usr/bin/env python3
"""
Phase 4 Backend API for RAG Chatbot.
Flask application integrating Phase 3 retriever with LLM.
"""

import logging
import os
import sys
import json
from collections import defaultdict, deque
from pathlib import Path
from threading import Lock
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple

from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import BaseModel, ValidationError

try:
    import yaml
except ImportError:  # pragma: no cover - optional at runtime
    yaml = None

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import Config
except ImportError:
    from phase0.config import Config

from lib.llm_client import LLMClient
from lib.local_retriever import LocalChunkRetriever
from lib.response_formatter import ResponseFormatter, SafetyChecker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _get_cors_origins_from_env():
    raw = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
    if not raw or raw == "*":
        return "*"
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": _get_cors_origins_from_env()}})

# Global components
config = None
llm_client = None
retriever = None
local_retriever = None
initialized = False

FREQUENCY_TO_DAYS = {
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
    "quarterly": 90,
}

REPO_ROOT = Path(__file__).resolve().parent.parent

rate_limit_state: Dict[str, deque] = defaultdict(deque)
rate_limit_lock = Lock()


@app.before_request
def ensure_initialized():
    """Ensure components are initialized before first request."""
    global initialized
    if not initialized:
        initialize_components()
        initialized = True


class ChatRequest(BaseModel):
    """Chat request schema."""
    message: str
    language: str = "en"
    session_id: str = None


class ChatResponse(BaseModel):
    """Chat response schema."""
    answer: str
    citations: list
    timestamp: str
    confidence: float


def initialize_components():
    """Initialize all backend components."""
    global config, llm_client, retriever, local_retriever

    logger.info("Initializing backend components...")

    # Load configuration
    try:
        config = Config()
        logger.info("✅ Configuration loaded")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        config = None
        return

    # Initialize LLM client
    try:
        llm_client = LLMClient(
            api_key=config.llm_api_key,
            model=config.llm_model,
            temperature=config.llm_temperature,
            provider=config.llm_provider
        )
        logger.info("✅ LLM client initialized")
    except Exception as e:
        logger.warning(f"LLM client initialization failed: {e}")
        logger.info("Continuing without LLM - demo responses only")
        llm_client = None

    # Import and initialize retriever (Phase 3)
    try:
        from phase3.lib.embeddings import EmbeddingModel
        from phase3.lib.vector_store import VectorStore
        from phase3.lib.doc_store import DocumentStore
        from phase3.lib.retriever import Retriever

        embedding_model = EmbeddingModel(
            model_name=config.embedding_model,
            provider=config.embedding_provider,
            api_key=config.embedding_api_key
        )

        vector_store = VectorStore(
            index_path=str(config.data_dir / "vector_store.faiss"),
            metadata_path=str(config.data_dir / "vector_metadata.json")
        )
        vector_store.load_index()

        doc_store = DocumentStore(str(config.data_dir / "doc_store.db"))

        retriever = Retriever(embedding_model, vector_store, doc_store)
        logger.info("✅ Retriever initialized")

    except Exception as e:
        logger.warning(f"Phase 3 components not fully initialized: {e}")
        logger.info("Running in demo mode without retriever")

    # Initialize lexical fallback retriever from local chunks.
    try:
        local_retriever = LocalChunkRetriever(config.data_dir / "chunks")
        logger.info("Local lexical retriever initialized")
    except Exception as e:
        logger.warning(f"Local lexical retriever initialization failed: {e}")
        local_retriever = None


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _to_utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_url_frequency_map() -> Dict[str, str]:
    if yaml is None:
        return {}

    source0_path = REPO_ROOT / "phase0/sources.yaml"
    if not source0_path.exists():
        return {}

    try:
        source0 = yaml.safe_load(source0_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

    out: Dict[str, str] = {}
    for item in source0.get("sources", []):
        url = str(item.get("url", "")).strip()
        freq = str(item.get("refresh_frequency", "weekly")).strip().lower()
        if url:
            out[url] = freq or "weekly"
    return out


def _load_phase1_sources() -> List[Dict[str, Any]]:
    if yaml is None:
        return []

    source1_path = REPO_ROOT / "phase1/sources.yaml"
    if not source1_path.exists():
        return []

    try:
        data = yaml.safe_load(source1_path.read_text(encoding="utf-8")) or {}
        sources = data.get("sources", [])
        return [s for s in sources if isinstance(s, dict)]
    except Exception:
        return []


def _build_sources_payload() -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    configured_data_dir = Path(config.data_dir) if config and getattr(config, "data_dir", None) else None
    if configured_data_dir and configured_data_dir.exists():
        data_dir = configured_data_dir
    else:
        data_dir = REPO_ROOT / "data"
    url_to_freq = _load_url_frequency_map()
    phase_sources = _load_phase1_sources()
    sources_payload: List[Dict[str, Any]] = []
    latest_refreshed: Optional[datetime] = None

    def _append_source(source_id: str, label: str, url: str, refresh_frequency: str):
        nonlocal latest_refreshed
        fetch_meta = _read_json(data_dir / "raw" / source_id / "fetch.json") or {}
        fetched_at = _parse_iso(fetch_meta.get("fetched_at"))
        refresh_days = FREQUENCY_TO_DAYS.get(refresh_frequency, 7)
        next_refresh = fetched_at + timedelta(days=refresh_days) if fetched_at else None

        if fetched_at is None:
            status = "never_fetched"
        elif now >= next_refresh:
            status = "due"
        else:
            status = "fresh"

        if fetched_at and (latest_refreshed is None or fetched_at > latest_refreshed):
            latest_refreshed = fetched_at

        sources_payload.append(
            {
                "source_id": source_id,
                "name": label or source_id,
                "url": url or "",
                "refresh_frequency": refresh_frequency,
                "last_updated": _to_utc_iso(fetched_at) if fetched_at else None,
                "next_refresh": _to_utc_iso(next_refresh) if next_refresh else None,
                "status": status,
            }
        )

    if phase_sources:
        for source in phase_sources:
            source_id = str(source.get("source_id", "")).strip()
            if not source_id:
                continue
            url = str(source.get("url", "")).strip()
            label = str(source.get("label", source_id)).strip()
            refresh_frequency = url_to_freq.get(url, "weekly")
            _append_source(source_id, label, url, refresh_frequency)
    else:
        raw_dir = data_dir / "raw"
        if raw_dir.exists():
            for fetch_path in sorted(raw_dir.glob("*/fetch.json")):
                source_id = fetch_path.parent.name
                fetch_meta = _read_json(fetch_path) or {}
                _append_source(
                    source_id=source_id,
                    label=source_id.replace("_", " ").title(),
                    url=str(fetch_meta.get("requested_url", "")),
                    refresh_frequency="weekly",
                )

    domain_meta = {
        "groww": {"name": "Groww Platform", "url": "https://groww.in"},
        "amfi": {"name": "AMFI (Association of Mutual Funds in India)", "url": "https://www.amfiindia.com"},
        "sebi": {"name": "SEBI (Securities and Exchange Board of India)", "url": "https://www.sebi.gov.in"},
    }
    domain_latest: Dict[str, Optional[datetime]] = {k: None for k in domain_meta.keys()}
    for source in sources_payload:
        url_lower = str(source.get("url", "")).lower()
        source_last = _parse_iso(source.get("last_updated"))
        if not source_last:
            continue
        for domain_key in domain_latest.keys():
            if domain_key in url_lower:
                if domain_latest[domain_key] is None or source_last > domain_latest[domain_key]:
                    domain_latest[domain_key] = source_last

    domain_payload: Dict[str, Dict[str, Any]] = {}
    for domain_key, meta in domain_meta.items():
        last_dt = domain_latest.get(domain_key)
        domain_payload[domain_key] = {
            "name": meta["name"],
            "url": meta["url"],
            "last_updated": _to_utc_iso(last_dt) if last_dt else None,
            "refresh_frequency": "mixed",
        }

    effective_latest = latest_refreshed or now

    payload = {
        "generated_at": _to_utc_iso(now),
        "latest_data_timestamp": _to_utc_iso(effective_latest),
        "latest_data_date": effective_latest.date().isoformat(),
        "freshness_source": "scheduler" if latest_refreshed else "today_fallback",
        "sources": sources_payload,
        "domains": domain_payload,
    }
    # Backward compatibility for legacy frontend callers.
    payload.update(domain_payload)
    return payload


def _get_client_ip() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _check_rate_limit() -> Tuple[bool, Optional[int]]:
    """
    Fixed-window in-memory rate limiter for /chat requests.
    Returns (is_limited, retry_after_seconds).
    """
    if not config or not config.rate_limit_enabled:
        return False, None

    limit = max(1, int(config.rate_limit_requests_per_minute))
    window_seconds = max(1, int(config.rate_limit_window_seconds))
    now_ts = datetime.now(timezone.utc).timestamp()
    client_ip = _get_client_ip()

    with rate_limit_lock:
        bucket = rate_limit_state[client_ip]

        # Drop timestamps outside current window.
        while bucket and (now_ts - bucket[0]) > window_seconds:
            bucket.popleft()

        if len(bucket) >= limit:
            retry_after = int(max(1, window_seconds - (now_ts - bucket[0])))
            return True, retry_after

        bucket.append(now_ts)

    return False, None


@app.route("/")
def index():
    """API root endpoint."""
    return jsonify({
        "service": "phase4-backend-api",
        "status": "running",
        "message": "Frontend is served from phase6/app.py",
        "endpoints": ["/chat", "/health", "/schemes", "/faq", "/sources"]
    }), 200


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "config": bool(config),
            "llm": bool(llm_client),
            "retriever": bool(retriever)
        }
    })


@app.route("/chat", methods=["POST"])
def chat():
    """Main chat endpoint."""
    try:
        # Parse request
        data = request.get_json()

        if not data or "message" not in data:
            return jsonify({"error": "Missing 'message' field"}), 400

        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({"error": "Empty message"}), 400

        # Optional rate limiting for production hardening.
        is_limited, retry_after = _check_rate_limit()
        if is_limited:
            return jsonify({
                "error": "Rate limit exceeded. Please retry after some time.",
                "retry_after_seconds": retry_after,
            }), 429

        # Safety checks
        has_pii, pii_types = SafetyChecker.check_pii(user_message)
        if has_pii:
            logger.warning(f"PII detected: {pii_types}")
            return jsonify({
                "answer": SafetyChecker.get_safety_response("pii"),
                "citations": [],
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": 0.0,
                "safety_flag": "pii_detected"
            }), 200

        scope, is_allowed = SafetyChecker.check_scope(user_message)
        if not is_allowed:
            logger.warning(f"Disallowed scope: {scope}")
            return jsonify({
                "answer": SafetyChecker.get_safety_response(scope),
                "citations": [],
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": 0.0,
                "safety_flag": f"scope_{scope}"
            }), 200

        logger.info(f"Processing query: {user_message[:100]}...")

        # Check if LLM client is available
        if not llm_client:
            logger.warning("LLM client not available - returning demo response")
            demo_response = """Thank you for your question about Navi mutual funds. 

The chatbot is currently running in demo mode without LLM access. 

To enable full functionality:
1. Set OPENAI_API_KEY in your environment
2. Restart the application

For now, please visit Navi AMC's official website for detailed information about their schemes and services."""
            
            return jsonify({
                "success": True,
                "answer": demo_response,
                "citations": [],
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": 0.0,
                "retrieval_count": 0
            }), 200

        # Retrieve context using Phase 3
        retrieval_results = []
        if retriever:
            try:
                retrieval_results = retriever.retrieve(user_message, top_k=5)
                logger.info(f"Retrieved {len(retrieval_results)} results")
            except Exception as e:
                logger.error(f"Retrieval error: {e}")
                # Continue without retriever results

        if not retrieval_results and local_retriever:
            try:
                retrieval_results = local_retriever.retrieve(user_message, top_k=5)
                logger.info(f"Local fallback retrieved {len(retrieval_results)} results")
            except Exception as e:
                logger.error(f"Local fallback retrieval error: {e}")

        # Generate response with LLM
        try:
            if retrieval_results:
                llm_response = llm_client.generate_response_with_retrieval(
                    retrieval_results=retrieval_results,
                    user_query=user_message
                )
            else:
                # Fallback response without retrieval
                system_prompt = """You are a professional assistant for Navi AMC mutual funds.
                If no grounded context is provided, answer briefly with limitations, avoid speculation,
                and ask the user to request a specific factual field (NAV, AUM, expense ratio, SIP, exit load)."""

                llm_response = llm_client.generate_response(
                    system_prompt=system_prompt,
                    user_message=user_message
                )
        except Exception as llm_error:
            logger.error(f"LLM generation failed: {llm_error}")
            err_text = str(llm_error).lower()
            if "insufficient_quota" in err_text or "exceeded your current quota" in err_text:
                fallback_answer = (
                    "The chatbot backend key has no remaining API quota. "
                    "Please add billing/credits or update `LLM_API_KEY` and `EMBEDDING_API_KEY` with an active key."
                )
                warning_code = "llm_quota_exceeded"
            elif "model_not_found" in err_text or "does not exist" in err_text:
                fallback_answer = (
                    "The configured model is not available for this API key. "
                    "Set `LLM_MODEL` to a model allowed for your account and retry."
                )
                warning_code = "llm_model_unavailable"
            elif "no compatible anthropic model" in err_text:
                fallback_answer = (
                    "No compatible Anthropic model is available for the configured key. "
                    "Please use a key/workspace that has Claude model access."
                )
                warning_code = "llm_model_unavailable"
            elif "credit balance is too low" in err_text or "plans & billing" in err_text:
                fallback_answer = (
                    "The Anthropic API key does not have enough credit balance. "
                    "Please add credits in Anthropic Plans & Billing and retry."
                )
                warning_code = "llm_low_credit"
            else:
                fallback_answer = (
                    "I am currently unable to generate a model-backed response. "
                    "Please try again shortly or ask a factual question about Navi schemes, NAV, expense ratio, SIP, lock-in, or exit load."
                )
                warning_code = "llm_unavailable"
            return jsonify({
                "success": True,
                "answer": fallback_answer,
                "citations": [],
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": 0.0,
                "retrieval_count": len(retrieval_results),
                "warning": warning_code
            }), 200

        # Format response
        formatted = ResponseFormatter.format_response(llm_response, retrieval_results)

        response = {
            "success": True,
            "answer": formatted["answer"],
            "citations": formatted["citations"],
            "timestamp": datetime.utcnow().isoformat(),
            "confidence": formatted["confidence"],
            "retrieval_count": formatted["retrieval_count"]
        }

        logger.info(f"Response generated with {len(response['citations'])} citations")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/schemes", methods=["GET"])
def get_schemes():
    """Get available schemes."""
    schemes = [
        {
            "id": "navi_flexi_cap",
            "name": "Navi Flexi Cap",
            "category": "Equity",
            "min_sip": 100,
            "min_lumpsum": 5000,
            "url": "https://groww.in/mutual-funds/navi-flexi-cap-fund"
        },
        {
            "id": "navi_elss",
            "name": "Navi ELSS Tax Saver",
            "category": "Equity",
            "min_sip": 500,
            "min_lumpsum": 500,
            "lock_in": "3 years",
            "url": "https://groww.in/mutual-funds/navi-elss-tax-saver-fund"
        },
        {
            "id": "navi_large_midcap",
            "name": "Navi Large & Midcap",
            "category": "Equity",
            "min_sip": 100,
            "min_lumpsum": 100,
            "url": "https://groww.in/mutual-funds/navi-large-midcap-fund"
        },
        {
            "id": "navi_midsmallcap",
            "name": "Navi Multicap 400",
            "category": "Equity",
            "min_sip": 100,
            "min_lumpsum": 100,
            "url": "https://groww.in/mutual-funds/navi-multicap-400"
        }
    ]

    return jsonify(schemes), 200


@app.route("/faq", methods=["GET"])
def get_faq():
    """Get frequently asked questions."""
    faqs = [
        {
            "id": 1,
            "question": "What is NAV?",
            "answer": "NAV (Net Asset Value) is the market value of all assets held by the scheme divided by the number of units outstanding."
        },
        {
            "id": 2,
            "question": "What is the expense ratio?",
            "answer": "Expense ratio is the annual fee charged by mutual funds. Lower ratios mean more money stays invested."
        },
        {
            "id": 3,
            "question": "What is SIP?",
            "answer": "SIP (Systematic Investment Plan) allows you to invest a fixed amount regularly, reducing the impact of market volatility."
        },
        {
            "id": 4,
            "question": "What is exit load?",
            "answer": "Exit load is a fee charged when you redeem your units before a specified period."
        }
    ]

    return jsonify(faqs), 200


@app.route("/sources", methods=["GET"])
def get_sources():
    """Get source freshness details derived from scheduler fetch metadata."""
    payload = _build_sources_payload()
    return jsonify(payload), 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    # Initialize components
    initialize_components()

    # Run Flask app
    logger.info("Starting Flask server...")
    app.run(
        host=config.api_host if config else "0.0.0.0",
        port=config.api_port if config else 8000,
        debug=config.debug if config else False
    )

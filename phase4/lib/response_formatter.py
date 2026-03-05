"""
Response formatter for Phase 4 backend.
Formats responses with citations and safety checks.
"""

import logging
import re
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """Formats LLM responses with citations and metadata."""

    @staticmethod
    def format_response(llm_response: str, retrieval_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Format LLM response with citations.

        Args:
            llm_response: Response from LLM
            retrieval_results: Results from retriever

        Returns:
            Formatted response dict with citations
        """
        # Extract citations from LLM response
        citations = ResponseFormatter._extract_citations(llm_response, retrieval_results)

        # Remove citation markers from response if any
        clean_response = ResponseFormatter._clean_response(llm_response)

        return {
            "answer": clean_response,
            "citations": citations,
            "retrieval_count": len(retrieval_results),
            "confidence": ResponseFormatter._calculate_confidence(retrieval_results)
        }

    @staticmethod
    def _extract_citations(response: str, retrieval_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extract citations from response and retrieval results."""
        citations = []

        for result in retrieval_results:
            metadata = result.get("metadata", {})
            url = metadata.get("url")
            chunk_id = metadata.get("chunk_id")

            if url:
                citation = {
                    "url": url,
                    "source_type": metadata.get("source_type", "document"),
                    "fetched_at": metadata.get("fetched_at")
                }
                citations.append(citation)

        # Remove duplicates while preserving order
        seen_urls = set()
        unique_citations = []
        for citation in citations:
            if citation["url"] not in seen_urls:
                seen_urls.add(citation["url"])
                unique_citations.append(citation)

        return unique_citations

    @staticmethod
    def _clean_response(response: str) -> str:
        """Clean response by removing citation markers."""
        # Remove (Source: ...) patterns if present
        response = re.sub(r'\s*\(Source:\s*[^)]+\)', '', response)
        response = re.sub(r'\s*\[Citation:\s*[^\]]+\]', '', response)
        # Strip lingering markdown emphasis markers that degrade chat readability.
        response = response.replace("**", "").replace("__", "")

        return response.strip()

    @staticmethod
    def _calculate_confidence(retrieval_results: List[Dict[str, Any]]) -> float:
        """Calculate confidence score based on retrieval results."""
        if not retrieval_results:
            return 0.0

        # Average similarity scores if available
        scores = []
        for result in retrieval_results:
            score = result.get("score", 0.0)
            if isinstance(score, (int, float)):
                scores.append(float(score))

        if scores:
            avg_score = sum(scores) / len(scores)
            # Normalize to 0-1 if needed
            return min(1.0, avg_score)

        # Default confidence based on number and type of results
        if len(retrieval_results) >= 3:
            return 0.85
        elif len(retrieval_results) >= 1:
            return 0.7
        else:
            return 0.5


class SafetyChecker:
    """Checks for PII, scope violations, and safety issues."""

    # PII patterns
    PII_PATTERNS = {
        "pan": r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b",  # PAN format
        "phone": r"\b(?:\+91|91)?[6-9]\d{9}\b",  # Indian phone
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
        "account_number": r"\b\d{9,18}\b",  # Account number (generic)
        "aadhar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",  # Aadhar-like
        "otp": r"\b\d{4,6}\b"  # OTP (generic)
    }

    # Regex-based disallowed scope patterns
    DISALLOWED_PATTERNS = {
        "financial_advice": [
            r"\bshould\s+i\s+(buy|invest|choose|pick|go\s+for)\b",
            r"\b(can|could)\s+i\s+(buy|invest|choose|pick)\b",
            r"\b(recommend|suggest)\b",
            r"\b(best|better|worth\s+it|good\s+fund)\b",
            r"\b(expected|target)\s+returns?\b",
            r"\b(which\s+fund\s+should\s+i)\b",
        ],
        "comparison": [
            r"\b(compare|comparison|versus|vs\.?)\b",
            r"\bbetter\s+than\b",
            r"\bdifference\s+between\b",
            r"\bwhich\s+is\s+better\b",
        ],
        "transaction": [
            r"\b(buy|sell|redeem|switch|withdraw|transfer)\b",
            r"\b(place\s+order|execute\s+order|start\s+sip|stop\s+sip|cancel\s+sip)\b",
        ],
        "personal_data": [
            r"\b(my|me|mine)\b.*\b(account|portfolio|investment|holdings?|returns?|folio|pan|otp|phone|email)\b",
            r"\b(my\s+salary|my\s+income|my\s+age|for\s+me)\b",
            r"\b(what\s+should\s+i\s+do\s+with\s+my)\b",
        ],
    }

    DOMAIN_KEYWORDS = [
        "navi", "mutual fund", "fund", "amc", "scheme", "sip", "lumpsum",
        "nav", "aum", "expense ratio", "ter", "exit load", "lock-in",
        "lock in", "elss", "risk", "riskometer", "risk-o-meter", "amfi",
        "sebi", "tax saver", "direct growth",
    ]

    GREETING_PATTERNS = [
        r"^\s*(hi|hello|hey)\b",
        r"^\s*(good\s+morning|good\s+afternoon|good\s+evening)\b",
        r"^\s*(thanks|thank\s+you)\b",
    ]

    @staticmethod
    def check_pii(text: str) -> Tuple[bool, List[str]]:
        """
        Check for PII in text.

        Returns:
            Tuple of (has_pii, pii_types_found)
        """
        found_pii = []

        for pii_type, pattern in SafetyChecker.PII_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                found_pii.append(pii_type)

        return len(found_pii) > 0, found_pii

    @staticmethod
    def check_scope(query: str) -> Tuple[str, bool]:
        """
        Check query scope and validity.

        Returns:
            Tuple of (scope_type, is_allowed)
        """
        query_lower = query.lower().strip()

        # Friendly greetings are allowed.
        for pattern in SafetyChecker.GREETING_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return "general", True

        # Hard-block disallowed intents.
        for scope, patterns in SafetyChecker.DISALLOWED_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    return scope, False

        # Reject irrelevant/off-topic queries.
        if not any(keyword in query_lower for keyword in SafetyChecker.DOMAIN_KEYWORDS):
            return "irrelevant", False

        return "general", True

    @staticmethod
    def get_safety_response(issue: str) -> str:
        """Get appropriate response for safety violations."""
        responses = {
            "pii": "I cannot process personal information. Please remove PAN, phone, email, OTP, or account details and ask again.",
            "financial_advice": "I cannot provide recommendations or personalized investment advice. Please ask factual questions only (NAV, AUM, expense ratio, minimum SIP, exit load, lock-in, risk label).",
            "transaction": "I cannot perform transactions. Please use the Navi AMC or Groww platform for buy, sell, switch, SIP, or redemption actions.",
            "personal_data": "I cannot handle personal/account-specific queries. Please ask general factual questions about schemes or mutual fund concepts.",
            "comparison": "I cannot compare or rank funds. Please ask about one scheme at a time using factual fields such as NAV, AUM, expense ratio, and exit load.",
            "irrelevant": "I can only assist with Navi mutual fund scheme facts and mutual fund education. Please ask a relevant factual question.",
        }

        return responses.get(issue, "I'm unable to help with this request. Please check our FAQ or contact support.")

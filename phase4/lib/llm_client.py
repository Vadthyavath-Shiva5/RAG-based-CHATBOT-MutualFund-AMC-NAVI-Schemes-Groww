"""
LLM client wrapper for Phase 4 backend.
Handles chat completions with OpenAI and Anthropic APIs.
"""

import logging
import json
from typing import List, Dict, Any
from urllib import error as url_error
from urllib import request as url_request
from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM client for chat completions."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        provider: str = "openai",
    ):
        """
        Initialize LLM client.

        Args:
            api_key: Provider API key
            model: Model name
            temperature: Temperature for response generation (0.0-1.0)
            provider: LLM provider ('openai' or 'anthropic')
        """
        self.provider = (provider or "openai").lower()
        self.api_key = api_key
        self.model = model
        self.temperature = temperature

        if self.provider == "openai":
            self.client = OpenAI(api_key=api_key)
        elif self.provider == "anthropic":
            self.client = None
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def _resolve_anthropic_model(self) -> str:
        model_lower = self.model.lower().strip()
        if model_lower in {
            "claude 3 haiku",
            "claude3 haiku",
            "claude-3-haiku",
            "haiku",
            "claude 3 haiku latest",
        }:
            return "claude-3-haiku-20240307"
        if model_lower in {"sonnet 4.6", "claude sonnet 4.6", "sonnet-4.6", "sonnet4.6"}:
            # Map user-friendly label to a broadly available Anthropic Sonnet alias.
            return "claude-3-5-sonnet-latest"
        return self.model

    def _fetch_anthropic_models(self) -> List[str]:
        req = url_request.Request(
            "https://api.anthropic.com/v1/models",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="GET",
        )
        try:
            with url_request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            items = data.get("data", [])
            return [item.get("id", "") for item in items if item.get("id")]
        except Exception as exc:
            logger.warning("Unable to fetch Anthropic model list: %s", exc)
            return []

    def _anthropic_model_candidates(self) -> List[str]:
        primary = self._resolve_anthropic_model()
        model_lower = self.model.lower().strip()
        discovered = self._fetch_anthropic_models()

        preferred = [primary]
        if "haiku" in model_lower:
            preferred.extend([m for m in discovered if "haiku" in m.lower()])
        elif "sonnet" in model_lower:
            preferred.extend([m for m in discovered if "sonnet" in m.lower()])
        else:
            preferred.extend(discovered)

        # Keep order and remove duplicates/empties.
        seen = set()
        result = []
        for m in preferred:
            if m and m not in seen:
                seen.add(m)
                result.append(m)
        return result

    def generate_response(self, system_prompt: str, user_message: str,
                        context: str = None, max_tokens: int = 2000) -> str:
        """
        Generate a response using the LLM.

        Args:
            system_prompt: System prompt for the LLM
            user_message: User's query/message
            context: Optional context from retriever
            max_tokens: Maximum tokens in response

        Returns:
            Generated response text
        """
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        if context:
            messages.append({
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {user_message}"
            })
        else:
            messages.append({"role": "user", "content": user_message})

        try:
            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content

            # Anthropic API path
            anthropic_user_content = messages[-1]["content"]
            last_error = None
            for anthropic_model in self._anthropic_model_candidates():
                payload = {
                    "model": anthropic_model,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": anthropic_user_content}],
                    "max_tokens": max_tokens,
                    "temperature": self.temperature,
                }
                req = url_request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    method="POST",
                )
                try:
                    with url_request.urlopen(req, timeout=60) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                    content_items = data.get("content", [])
                    text_parts = [c.get("text", "") for c in content_items if c.get("type") == "text"]
                    text = "\n".join([t for t in text_parts if t]).strip()
                    if text:
                        if anthropic_model != self._resolve_anthropic_model():
                            logger.info("Anthropic fallback model selected: %s", anthropic_model)
                        return text
                except url_error.HTTPError as exc:
                    body = exc.read().decode("utf-8", errors="replace")
                    err_text = body.lower()
                    if exc.code == 404 or "not_found_error" in err_text:
                        logger.warning("Anthropic model unavailable: %s", anthropic_model)
                        last_error = RuntimeError(f"Anthropic API error {exc.code}: {body}")
                        continue
                    raise RuntimeError(f"Anthropic API error {exc.code}: {body}") from exc

            if last_error:
                raise last_error
            raise RuntimeError("No compatible Anthropic model is available for this API key.")

        except Exception as e:
            logger.error(f"LLM API error: {e}")
            raise

    def generate_response_with_retrieval(self, retrieval_results: List[Dict[str, Any]],
                                        user_query: str, max_tokens: int = 2000) -> str:
        """
        Generate response using retrieval results.

        Args:
            retrieval_results: Results from Phase 3 retriever
            user_query: User's original query
            max_tokens: Maximum tokens in response

        Returns:
            Generated response with citations
        """
        # Format context from retrieval results
        context_parts = []
        for result in retrieval_results:
            content = result.get("content", "")
            source = result.get("metadata", {}).get("url", "")

            if source:
                context_parts.append(f"{content}\n(Source: {source})")
            else:
                context_parts.append(content)

        context = "\n\n".join(context_parts)

        system_prompt = """You are a professional assistant for Navi AMC mutual fund information.
Use ONLY the provided context and do not invent facts.

Output format rules (strict):
1. First line must be a direct answer sentence with no markdown heading markers.
2. Then provide 2-5 concise bullet points using '-' as the bullet marker.
3. Use a markdown table only when multiple factual fields are shown (3 or more fields) or multiple schemes are listed.
4. Do not use bold markers (**), heading markers (#), or decorative separators.
5. Keep the tone professional, neutral, and factual.
6. For numeric answers, copy exact value and unit from context (do not round or convert unless context explicitly does so).
7. If information is missing, clearly state: "Not available in retrieved sources."
8. Do not provide investment advice or recommendations."""

        return self.generate_response(
            system_prompt=system_prompt,
            user_message=user_query,
            context=context,
            max_tokens=max_tokens
        )

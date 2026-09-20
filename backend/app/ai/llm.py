import json
import logging
import re

from ..core.config import settings

log = logging.getLogger("llm")


class LLMClient:
    """Thin wrapper around the Anthropic SDK. If no API key is set, `available` is False
    and the app falls back to static-analysis-only mode."""

    def __init__(self) -> None:
        self._client = None
        if settings.anthropic_api_key:
            import anthropic
            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=90, max_retries=2)

    @property
    def available(self) -> bool:
        return self._client is not None

    def complete(self, system: str, messages: list[dict] | str, max_tokens: int = 2000) -> str | None:
        if not self._client:
            return None
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        try:
            resp = self._client.messages.create(model=settings.anthropic_model, max_tokens=max_tokens,
                                                system=system, messages=messages)
            return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        except Exception as e:  # network, rate limit, bad key ...
            log.warning("LLM call failed: %s", e)
            return None

    def complete_json(self, system: str, user: str, max_tokens: int = 3000) -> dict | None:
        text = self.complete(system, user, max_tokens)
        return parse_json(text) if text else None


def parse_json(text: str) -> dict | None:
    """Extract the first JSON object from model output (handles ```json fences)."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
        return data if isinstance(data, dict) else None
    except ValueError:
        return None


_llm: LLMClient | None = None


def get_llm() -> LLMClient:
    global _llm
    if _llm is None:
        _llm = LLMClient()
    return _llm

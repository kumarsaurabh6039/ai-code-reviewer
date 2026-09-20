import json
import logging
import re

from ..core.config import settings

log = logging.getLogger("llm")


class LLMClient:
    """
    LLM provider wrapper.

    Primary provider:
        Groq

    Fallback provider:
        Gemini

    If neither provider is configured or available,
    the application falls back to static-analysis-only mode.
    """

    def __init__(self) -> None:
        self._groq = None
        self._gemini = None

        # -------------------------
        # Initialize Groq
        # -------------------------
        if settings.groq_api_key:
            try:
                from groq import Groq

                self._groq = Groq(
                    api_key=settings.groq_api_key,
                    timeout=90,
                    max_retries=2,
                )

                log.info("Groq LLM provider initialized")

            except Exception as e:
                log.warning("Failed to initialize Groq: %s", e)

        # -------------------------
        # Initialize Gemini
        # -------------------------
        if settings.gemini_api_key:
            try:
                from google import genai

                self._gemini = genai.Client(
                    api_key=settings.gemini_api_key
                )

                log.info("Gemini LLM provider initialized")

            except Exception as e:
                log.warning("Failed to initialize Gemini: %s", e)

    @property
    def available(self) -> bool:
        """
        Returns True when at least one LLM provider is configured.
        """
        return self._groq is not None or self._gemini is not None

    def _provider_order(self) -> list[str]:
        """
        Determines which provider should be tried first.

        Example:
            LLM_PROVIDER=groq
            -> Groq first, Gemini second

            LLM_PROVIDER=gemini
            -> Gemini first, Groq second
        """

        provider = settings.llm_provider.lower().strip()

        if provider == "gemini":
            return ["gemini", "groq"]

        return ["groq", "gemini"]

    def _complete_groq(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int,
    ) -> str | None:

        if self._groq is None:
            return None

        try:
            groq_messages = [
                {
                    "role": "system",
                    "content": system,
                }
            ]

            for message in messages:
                role = message.get("role", "user")
                content = message.get("content", "")

                if role not in {"user", "assistant"}:
                    continue

                groq_messages.append(
                    {
                        "role": role,
                        "content": content,
                    }
                )

            response = self._groq.chat.completions.create(
                model=settings.groq_model,
                messages=groq_messages,
                max_tokens=max_tokens,
                temperature=0.2,
            )

            if not response.choices:
                return None

            content = response.choices[0].message.content

            return content if content else None

        except Exception as e:
            log.warning("Groq LLM call failed: %s", e)
            return None

    def _complete_gemini(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int,
    ) -> str | None:

        if self._gemini is None:
            return None

        try:
            from google.genai import types

            contents = []

            for message in messages:
                role = message.get("role", "user")
                content = message.get("content", "")

                if not content:
                    continue

                # Gemini uses "model" instead of "assistant"
                gemini_role = (
                    "model"
                    if role == "assistant"
                    else "user"
                )

                contents.append(
                    types.Content(
                        role=gemini_role,
                        parts=[
                            types.Part.from_text(
                                text=content
                            )
                        ],
                    )
                )

            response = self._gemini.models.generate_content(
                model=settings.gemini_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=max_tokens,
                    temperature=0.2,
                ),
            )

            text = getattr(response, "text", None)

            return text if text else None

        except Exception as e:
            log.warning("Gemini LLM call failed: %s", e)
            return None

    def complete(
        self,
        system: str,
        messages: list[dict] | str,
        max_tokens: int = 2000,
    ) -> str | None:
        """
        Generate a response using the configured LLM provider.

        Provider order depends on LLM_PROVIDER.

        Default:
            Groq -> Gemini -> None
        """

        if isinstance(messages, str):
            messages = [
                {
                    "role": "user",
                    "content": messages,
                }
            ]

        provider_order = self._provider_order()

        for provider in provider_order:

            if provider == "groq":
                result = self._complete_groq(
                    system=system,
                    messages=messages,
                    max_tokens=max_tokens,
                )

                if result:
                    log.info("LLM response generated using Groq")
                    return result

            elif provider == "gemini":
                result = self._complete_gemini(
                    system=system,
                    messages=messages,
                    max_tokens=max_tokens,
                )

                if result:
                    log.info("LLM response generated using Gemini")
                    return result

        log.warning(
            "No LLM provider returned a response. "
            "Using static-analysis-only mode."
        )

        return None

    def complete_json(
        self,
        system: str,
        user: str,
        max_tokens: int = 3000,
    ) -> dict | None:

        text = self.complete(
            system=system,
            messages=user,
            max_tokens=max_tokens,
        )

        return parse_json(text) if text else None


def parse_json(text: str) -> dict | None:
    """
    Extract the first JSON object from model output.

    Handles:
        {...}

    and:

        ```json
        {...}
        ```
    """

    text = re.sub(
        r"^```(?:json)?|```$",
        "",
        text.strip(),
        flags=re.M,
    ).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end <= start:
        return None

    try:
        data = json.loads(
            text[start:end + 1]
        )

        return data if isinstance(data, dict) else None

    except ValueError:
        return None


_llm: LLMClient | None = None


def get_llm() -> LLMClient:
    global _llm

    if _llm is None:
        _llm = LLMClient()

    return _llm
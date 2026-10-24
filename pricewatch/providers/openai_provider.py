from __future__ import annotations

import os

from . import ProviderError, ProviderTimeout


class OpenAIProvider:
    name = "openai"

    def __init__(self, model: str | None = None):
        try:
            from openai import OpenAI
        except ImportError as e:  # pragma: no cover
            raise ProviderError("pip install openai") from e
        if not os.environ.get("OPENAI_API_KEY"):
            raise ProviderError("OPENAI_API_KEY not set")
        self.client = OpenAI()
        self.model = model or os.environ.get("PRICEWATCH_MODEL", "gpt-4o-mini")

    def complete(self, system: str, user: str, *, metadata: dict, timeout: float = 30.0) -> str:
        assert "source_url" in metadata
        import openai
        try:
            r = self.client.chat.completions.create(
                model=self.model, timeout=timeout, temperature=0,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            )
        except openai.APITimeoutError as e:
            raise ProviderTimeout(str(e)) from e
        except openai.OpenAIError as e:
            response = getattr(e, "response", None)
            details = getattr(e, "body", None)
            if not details and response is not None: 
                details = response.text
            raise ProviderError(
                f"{type(e).__name__}: {e}; details={details}"
            ) from e

        self.last_usage = {
            "input_tokens": r.usage.prompt_tokens if r.usage else 0,
            "output_tokens": r.usage.completion_tokens if r.usage else 0,
        }
        
        return r.choices[0].message.content or ""

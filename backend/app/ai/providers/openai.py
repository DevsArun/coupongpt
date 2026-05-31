"""OpenAI provider — chat completions with JSON response format."""
from __future__ import annotations

import time

import httpx

from app.ai.base import AICompletion, AIError, AIProvider, AIProviderDisabled

OPENAI_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(AIProvider):
    slug = "openai"

    async def complete_json(self, system_prompt: str, user_prompt: str) -> AICompletion:
        if not self.is_available:
            raise AIProviderDisabled("OpenAI is disabled or missing an API key.")

        payload = {
            "model": self.config.model or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.config.api_key}"}

        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_s) as client:
                resp = await client.post(OPENAI_URL, json=payload, headers=headers)
                resp.raise_for_status()
                body = resp.json()
        except httpx.HTTPError as exc:
            raise AIError(f"OpenAI request failed: {exc}") from exc

        latency_ms = int((time.perf_counter() - start) * 1000)
        text = body["choices"][0]["message"]["content"]
        usage = body.get("usage", {})
        return AICompletion(
            provider=self.slug,
            model=payload["model"],
            data=self._extract_json(text),
            latency_ms=latency_ms,
            prompt_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            raw_text=text,
        )

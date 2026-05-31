"""Google Gemini provider — generateContent API with JSON mime type."""
from __future__ import annotations

import time

import httpx

from app.ai.base import AICompletion, AIError, AIProvider, AIProviderDisabled

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(AIProvider):
    slug = "gemini"

    async def complete_json(self, system_prompt: str, user_prompt: str) -> AICompletion:
        if not self.is_available:
            raise AIProviderDisabled("Gemini is disabled or missing an API key.")

        model = self.config.model or "gemini-1.5-flash"
        url = f"{GEMINI_BASE}/{model}:generateContent?key={self.config.api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json",
            },
        }

        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_s) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                body = resp.json()
        except httpx.HTTPError as exc:
            raise AIError(f"Gemini request failed: {exc}") from exc

        latency_ms = int((time.perf_counter() - start) * 1000)
        try:
            text = body["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise AIError(f"Unexpected Gemini response shape: {exc}") from exc

        usage = body.get("usageMetadata", {})
        return AICompletion(
            provider=self.slug,
            model=model,
            data=self._extract_json(text),
            latency_ms=latency_ms,
            prompt_tokens=usage.get("promptTokenCount"),
            output_tokens=usage.get("candidatesTokenCount"),
            raw_text=text,
        )

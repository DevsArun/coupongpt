"""AI router implementing the provider fallback chain.

Default chain (from settings): Groq -> Gemini -> OpenAI. Each provider is tried
in priority order; on failure or timeout the router moves to the next available
provider. An optional ``usage_sink`` callback receives per-attempt telemetry so
Phase 9 can persist it to ``ai_usage_logs`` without coupling the router to the DB.

The router can be reconfigured at runtime (e.g. by the admin AI center) by
calling :func:`configure_router` with a fresh list of :class:`ProviderConfig`.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from app.ai.base import AICompletion, AIError, AIProvider, ProviderConfig
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.groq import GroqProvider
from app.ai.providers.openai import OpenAIProvider
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("ai.router")

_PROVIDER_CLASSES: dict[str, type[AIProvider]] = {
    "groq": GroqProvider,
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
}

UsageSink = Callable[[dict[str, Any]], Awaitable[None]]


class AIRouter:
    def __init__(self, providers: list[AIProvider]) -> None:
        # Sorted by priority ascending (lower tried first).
        self._providers = sorted(providers, key=lambda p: p.config.priority)

    @property
    def provider_order(self) -> list[str]:
        return [p.slug for p in self._providers]

    def available_providers(self) -> list[AIProvider]:
        return [p for p in self._providers if p.is_available]

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        operation: str = "generic",
        usage_sink: UsageSink | None = None,
    ) -> AICompletion:
        last_error: Exception | None = None
        attempted = False

        for provider in self._providers:
            if not provider.is_available:
                continue
            attempted = True
            try:
                completion = await provider.complete_json(system_prompt, user_prompt)
                if usage_sink:
                    await usage_sink(
                        {
                            "provider": provider.slug,
                            "operation": operation,
                            "model": completion.model,
                            "prompt_tokens": completion.prompt_tokens,
                            "output_tokens": completion.output_tokens,
                            "latency_ms": completion.latency_ms,
                            "success": True,
                            "error": None,
                        }
                    )
                logger.info("ai_success", provider=provider.slug, operation=operation)
                return completion
            except Exception as exc:  # noqa: BLE001 - we deliberately fall through
                last_error = exc
                logger.warning("ai_provider_failed", provider=provider.slug, error=str(exc))
                if usage_sink:
                    await usage_sink(
                        {
                            "provider": provider.slug,
                            "operation": operation,
                            "model": provider.config.model,
                            "prompt_tokens": None,
                            "output_tokens": None,
                            "latency_ms": None,
                            "success": False,
                            "error": str(exc)[:500],
                        }
                    )
                continue

        if not attempted:
            raise AIError("No AI provider is configured/available.")
        raise AIError(f"All AI providers failed. Last error: {last_error}")


def _providers_from_settings() -> list[AIProvider]:
    key_map = {
        "groq": (settings.groq_api_key, settings.groq_model),
        "gemini": (settings.gemini_api_key, settings.gemini_model),
        "openai": (settings.openai_api_key, settings.openai_model),
    }
    providers: list[AIProvider] = []
    for idx, slug in enumerate(settings.ai_priority_list):
        cls = _PROVIDER_CLASSES.get(slug)
        if not cls:
            continue
        api_key, model = key_map.get(slug, ("", ""))
        cfg = ProviderConfig(
            slug=slug,
            enabled=True,
            priority=(idx + 1) * 10,
            model=model,
            timeout_s=settings.ai_request_timeout,
            api_key=api_key,
        )
        providers.append(cls(cfg))
    return providers


_router: AIRouter | None = None
_lock = asyncio.Lock()


def get_router() -> AIRouter:
    global _router
    if _router is None:
        _router = AIRouter(_providers_from_settings())
    return _router


def configure_router(configs: list[ProviderConfig]) -> AIRouter:
    """Rebuild the router from explicit configs (e.g. loaded from the DB)."""
    global _router
    providers: list[AIProvider] = []
    for cfg in configs:
        cls = _PROVIDER_CLASSES.get(cfg.slug)
        if cls:
            providers.append(cls(cfg))
    _router = AIRouter(providers)
    return _router

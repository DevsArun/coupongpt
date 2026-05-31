"""Abstract AI provider interface and shared data types.

Every concrete provider (Groq, Gemini, OpenAI) implements ``complete_json`` which
takes a system + user prompt and returns parsed JSON. Keeping the contract narrow
(JSON in, JSON out) makes the providers interchangeable and the router trivial.
"""
from __future__ import annotations

import abc
import json
from dataclasses import dataclass, field
from typing import Any


class AIError(Exception):
    """Raised when a provider call fails (network, auth, bad output)."""


class AIProviderDisabled(AIError):
    """Raised when a provider has no API key / is disabled."""


@dataclass
class AICompletion:
    provider: str
    model: str
    data: dict[str, Any]
    latency_ms: int = 0
    prompt_tokens: int | None = None
    output_tokens: int | None = None
    raw_text: str = ""


@dataclass
class ProviderConfig:
    slug: str
    enabled: bool = True
    priority: int = 100
    model: str = ""
    timeout_s: int = 8
    api_key: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class AIProvider(abc.ABC):
    """Base class for all AI providers."""

    slug: str = "base"

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @property
    def is_available(self) -> bool:
        return self.config.enabled and bool(self.config.api_key)

    @abc.abstractmethod
    async def complete_json(self, system_prompt: str, user_prompt: str) -> AICompletion:
        """Return a JSON object parsed from the model response."""
        raise NotImplementedError

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        """Best-effort extraction of a JSON object from a model response.

        Models sometimes wrap JSON in markdown fences or add prose; we locate the
        first balanced ``{...}`` block and parse it.
        """
        text = text.strip()
        if text.startswith("```"):
            # strip ```json ... ``` fences
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError as exc:
                raise AIError(f"Could not parse JSON from model output: {exc}") from exc
        raise AIError("Model output contained no JSON object.")

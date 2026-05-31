"""AI provider configuration service — DB-driven, admin-controllable.

Bridges the ``ai_providers`` table to the runtime :class:`AIRouter`. API keys
always come from the environment (never stored in the DB), while enable/priority/
model/timeout are admin-editable and persisted. Also persists per-call telemetry
to ``ai_usage_logs`` via a ``usage_sink`` the search/ingestion layers can pass to
the router.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import ProviderConfig
from app.ai.router import configure_router
from app.core.config import settings
from app.core.database import SessionFactory
from app.models.system import AIProvider, AIUsageLog

_ENV_KEYS = {
    "groq": (lambda: settings.groq_api_key, lambda: settings.groq_model),
    "gemini": (lambda: settings.gemini_api_key, lambda: settings.gemini_model),
    "openai": (lambda: settings.openai_api_key, lambda: settings.openai_model),
}


async def load_providers(db: AsyncSession) -> list[AIProvider]:
    stmt = select(AIProvider).order_by(AIProvider.priority.asc())
    return list((await db.execute(stmt)).scalars().all())


async def refresh_router(db: AsyncSession) -> list[str]:
    """Rebuild the runtime router from the DB provider configuration."""
    providers = await load_providers(db)
    configs: list[ProviderConfig] = []
    for p in providers:
        key_fn, model_fn = _ENV_KEYS.get(p.slug, (lambda: "", lambda: ""))
        configs.append(
            ProviderConfig(
                slug=p.slug,
                enabled=p.is_enabled,
                priority=p.priority,
                model=p.model or model_fn(),
                timeout_s=p.timeout_s,
                api_key=key_fn(),
                extra=p.config or {},
            )
        )
    router = configure_router(configs)
    return router.provider_order


async def update_provider(
    db: AsyncSession,
    slug: str,
    *,
    is_enabled: bool | None = None,
    priority: int | None = None,
    model: str | None = None,
    timeout_s: int | None = None,
) -> AIProvider | None:
    provider = (await db.execute(select(AIProvider).where(AIProvider.slug == slug))).scalar_one_or_none()
    if provider is None:
        return None
    if is_enabled is not None:
        provider.is_enabled = is_enabled
    if priority is not None:
        provider.priority = priority
    if model is not None:
        provider.model = model
    if timeout_s is not None:
        provider.timeout_s = timeout_s
    await db.flush()
    await refresh_router(db)
    return provider


async def usage_summary(db: AsyncSession, *, days: int = 7) -> list[dict]:
    since = datetime.utcnow() - timedelta(days=days)
    stmt = (
        select(
            AIUsageLog.provider,
            func.count().label("calls"),
            func.sum(case((AIUsageLog.success.is_(True), 1), else_=0)).label("successes"),
            func.coalesce(func.avg(AIUsageLog.latency_ms), 0).label("avg_latency"),
        )
        .where(AIUsageLog.created_at >= since)
        .group_by(AIUsageLog.provider)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "provider": r[0],
            "calls": int(r[1]),
            "successes": int(r[2] or 0),
            "avg_latency_ms": round(float(r[3] or 0), 1),
        }
        for r in rows
    ]


async def log_usage(record: dict) -> None:
    """``usage_sink`` for the AI router — persists one telemetry record.

    Opens its own short-lived session so it can be passed anywhere without
    threading a session through.
    """
    try:
        async with SessionFactory() as db:
            db.add(
                AIUsageLog(
                    provider=record.get("provider", "unknown"),
                    operation=record.get("operation", "generic"),
                    model=record.get("model"),
                    prompt_tokens=record.get("prompt_tokens"),
                    output_tokens=record.get("output_tokens"),
                    latency_ms=record.get("latency_ms"),
                    success=bool(record.get("success", True)),
                    error=record.get("error"),
                )
            )
            await db.commit()
    except Exception:
        pass  # telemetry must never break a request

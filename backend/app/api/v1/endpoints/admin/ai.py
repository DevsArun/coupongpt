"""Admin AI Center — view/configure providers and inspect usage."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, DbSession, require_permission
from app.core.exceptions import NotFoundError
from app.schemas.admin import AIProviderOut, AIProviderUpdate
from app.services import ai_service
from app.services.audit_service import record_audit

router = APIRouter()


@router.get("/ai/providers", response_model=list[AIProviderOut])
async def list_providers(
    db: DbSession,
    _: object = Depends(require_permission("ai.read")),
) -> list[AIProviderOut]:
    providers = await ai_service.load_providers(db)
    return [AIProviderOut.model_validate(p) for p in providers]


@router.patch("/ai/providers/{slug}", response_model=AIProviderOut)
async def update_provider(
    slug: str,
    payload: AIProviderUpdate,
    db: DbSession,
    user: CurrentUser,
    _: object = Depends(require_permission("ai.write")),
) -> AIProviderOut:
    provider = await ai_service.update_provider(
        db,
        slug,
        is_enabled=payload.is_enabled,
        priority=payload.priority,
        model=payload.model,
        timeout_s=payload.timeout_s,
    )
    if provider is None:
        raise NotFoundError("AI provider not found.")
    await record_audit(db, action="ai.provider.update", actor_id=user.id, entity_type="ai_provider", entity_id=slug)
    return AIProviderOut.model_validate(provider)


@router.get("/ai/usage")
async def ai_usage(
    db: DbSession,
    days: int = Query(7, ge=1, le=90),
    _: object = Depends(require_permission("ai.read")),
) -> dict:
    return {
        "window_days": days,
        "providers": await ai_service.usage_summary(db, days=days),
        "fallback_chain": (await ai_service.refresh_router(db)),
    }

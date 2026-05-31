"""Admin system controls: audit logs, queues, feature flags, settings."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, require_permission
from app.core.exceptions import NotFoundError
from app.models.system import FeatureFlag, QueueJob, Setting
from app.models.user import AuditLog
from app.schemas.admin import (
    AuditLogOut,
    FeatureFlagOut,
    FeatureFlagUpdate,
    SettingUpdate,
)
from app.schemas.common import Page
from app.services import settings_service
from app.services.audit_service import record_audit

router = APIRouter()


@router.get("/logs", response_model=Page[AuditLogOut])
async def audit_logs(
    db: DbSession,
    action: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    _: object = Depends(require_permission("logs.read")),
) -> Page[AuditLogOut]:
    base = select(AuditLog)
    if action:
        base = base.where(AuditLog.action == action)
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    rows = (
        await db.execute(base.order_by(AuditLog.created_at.desc()).limit(page_size).offset((page - 1) * page_size))
    ).scalars().all()
    return Page.create([AuditLogOut.model_validate(r) for r in rows], total, page, page_size)


@router.get("/queues")
async def queue_jobs(
    db: DbSession,
    status: str | None = Query(None),
    _: object = Depends(require_permission("queues.read")),
) -> dict:
    base = select(QueueJob)
    if status:
        base = base.where(QueueJob.status == status)
    rows = (await db.execute(base.order_by(QueueJob.created_at.desc()).limit(100))).scalars().all()
    by_status = {}
    for r in rows:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    return {
        "summary": by_status,
        "jobs": [
            {"id": j.id, "queue": j.queue, "type": j.job_type, "status": j.status, "attempts": j.attempts}
            for j in rows
        ],
    }


@router.get("/feature-flags", response_model=list[FeatureFlagOut])
async def list_flags(
    db: DbSession,
    _: object = Depends(require_permission("logs.read")),
) -> list[FeatureFlagOut]:
    rows = (await db.execute(select(FeatureFlag).order_by(FeatureFlag.flag_key))).scalars().all()
    return [FeatureFlagOut.model_validate(r) for r in rows]


@router.patch("/feature-flags/{flag_key}", response_model=FeatureFlagOut)
async def update_flag(
    flag_key: str,
    payload: FeatureFlagUpdate,
    db: DbSession,
    user: CurrentUser,
    _: object = Depends(require_permission("flags.write")),
) -> FeatureFlagOut:
    flag = (await db.execute(select(FeatureFlag).where(FeatureFlag.flag_key == flag_key))).scalar_one_or_none()
    if flag is None:
        raise NotFoundError("Feature flag not found.")
    if payload.is_enabled is not None:
        flag.is_enabled = payload.is_enabled
    if payload.rollout_pct is not None:
        flag.rollout_pct = payload.rollout_pct
    await db.flush()
    await record_audit(db, action="flag.update", actor_id=user.id, entity_type="feature_flag", entity_id=flag_key)
    return FeatureFlagOut.model_validate(flag)


@router.get("/settings")
async def list_settings(
    db: DbSession,
    _: object = Depends(require_permission("logs.read")),
) -> dict:
    rows = (await db.execute(select(Setting).order_by(Setting.setting_key))).scalars().all()
    return {r.setting_key: {"value": r.value, "description": r.description} for r in rows}


@router.put("/settings/{key}")
async def update_setting(
    key: str,
    payload: SettingUpdate,
    db: DbSession,
    user: CurrentUser,
    _: object = Depends(require_permission("settings.write")),
) -> dict:
    row = await settings_service.set_setting(db, key, payload.value, updated_by=user.id)
    await record_audit(db, action="setting.update", actor_id=user.id, entity_type="setting", entity_id=key)
    return {"setting_key": row.setting_key, "value": row.value}

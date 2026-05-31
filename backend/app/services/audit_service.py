"""Audit logging service — records privileged and security-relevant actions."""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import AuditLog


async def record_audit(
    db: AsyncSession,
    *,
    action: str,
    actor_id: int | None = None,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Insert an audit log row. The caller's transaction commits it."""
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        ip_address=ip_address,
        user_agent=(user_agent or "")[:255] or None,
        audit_metadata=metadata,
    )
    db.add(entry)
    await db.flush()
    return entry

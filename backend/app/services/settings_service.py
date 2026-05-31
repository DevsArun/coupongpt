"""Application settings service backed by the ``settings`` table + Redis cache."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models.system import Setting

_CACHE_PREFIX = "setting:"
_CACHE_TTL = 300


async def get_setting(db: AsyncSession, key: str, default: Any = None) -> Any:
    redis = get_redis()
    try:
        cached = await redis.get(f"{_CACHE_PREFIX}{key}")
        if cached is not None:
            return json.loads(cached)
    except Exception:
        pass

    row = (await db.execute(select(Setting).where(Setting.setting_key == key))).scalar_one_or_none()
    value = row.value if row else default
    try:
        await redis.set(f"{_CACHE_PREFIX}{key}", json.dumps(value), ex=_CACHE_TTL)
    except Exception:
        pass
    return value


async def set_setting(
    db: AsyncSession, key: str, value: Any, *, updated_by: int | None = None
) -> Setting:
    row = (await db.execute(select(Setting).where(Setting.setting_key == key))).scalar_one_or_none()
    if row is None:
        row = Setting(setting_key=key, value=value, updated_by=updated_by)
        db.add(row)
    else:
        row.value = value
        row.updated_by = updated_by
    await db.flush()
    try:
        await get_redis().delete(f"{_CACHE_PREFIX}{key}")
    except Exception:
        pass
    return row

"""Deal-alert matching — turns stored alerts into in-app notifications.

Run periodically by the scheduler (``app.worker``) or on demand via the CLI.
For each active alert it finds newly-ingested active coupons that match the
alert's merchant / keyword / minimum-discount criteria, creates one notification
per match, and advances ``last_fired_at`` so a coupon notifies at most once per
alert.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.coupon import Coupon
from app.models.engagement import DealAlert, Notification

logger = get_logger("alerts")

_MAX_PER_ALERT = 5  # cap notifications per alert per run to avoid spam


async def run_alert_matching(db: AsyncSession) -> int:
    """Match active alerts against new active coupons. Returns notifications created."""
    alerts = (
        await db.execute(select(DealAlert).where(DealAlert.is_active.is_(True)))
    ).scalars().all()

    created = 0
    now = datetime.utcnow()

    for alert in alerts:
        since = alert.last_fired_at or alert.created_at
        stmt = select(Coupon).where(
            Coupon.status == "active",
            Coupon.created_at > since,
        )
        if alert.merchant_id is not None:
            stmt = stmt.where(Coupon.merchant_id == alert.merchant_id)
        if alert.keyword:
            stmt = stmt.where(Coupon.title.ilike(f"%{alert.keyword}%"))
        if alert.min_discount is not None:
            stmt = stmt.where(Coupon.discount_value >= alert.min_discount)
        stmt = stmt.order_by(Coupon.created_at.desc()).limit(_MAX_PER_ALERT)

        matches = (await db.execute(stmt)).scalars().all()
        for coupon in matches:
            db.add(
                Notification(
                    user_id=alert.user_id,
                    type="deal_alert",
                    title=f"New deal: {coupon.title[:120]}",
                    body=f"A coupon matching your alert is now live.",
                    data={"coupon_uuid": coupon.uuid, "alert_id": alert.id},
                )
            )
            created += 1

        if matches:
            alert.last_fired_at = now

    await db.flush()
    if created:
        logger.info("alerts_fired", notifications=created)
    return created

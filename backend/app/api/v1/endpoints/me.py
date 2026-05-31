"""Authenticated user dashboard endpoints (prefix /me)."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.schemas.common import Message
from app.schemas.me import (
    DealAlertIn,
    DealAlertOut,
    NotificationOut,
    ReferralSummary,
    SaveCouponIn,
    SavedCouponOut,
    SearchHistoryOut,
    SubscriptionOut,
    WatchlistIn,
    WatchlistItemOut,
)
from app.services import engagement_service, quota_service

router = APIRouter(prefix="/me", tags=["me"])


# ---- saved coupons ----
@router.get("/saved", response_model=list[SavedCouponOut])
async def saved(user: CurrentUser, db: DbSession) -> list[SavedCouponOut]:
    return [SavedCouponOut(**row) for row in await engagement_service.list_saved(db, user.id)]


@router.post("/saved", response_model=Message, status_code=201)
async def save(payload: SaveCouponIn, user: CurrentUser, db: DbSession) -> Message:
    await engagement_service.save_coupon(db, user.id, payload.coupon_uuid)
    return Message(message="Saved.")


@router.delete("/saved/{coupon_uuid}", response_model=Message)
async def unsave(coupon_uuid: str, user: CurrentUser, db: DbSession) -> Message:
    await engagement_service.unsave_coupon(db, user.id, coupon_uuid)
    return Message(message="Removed.")


# ---- watchlist ----
@router.get("/watchlist", response_model=list[WatchlistItemOut])
async def watchlist(user: CurrentUser, db: DbSession) -> list[WatchlistItemOut]:
    return [WatchlistItemOut(**row) for row in await engagement_service.list_watchlist(db, user.id)]


@router.post("/watchlist", response_model=Message, status_code=201)
async def add_watch(payload: WatchlistIn, user: CurrentUser, db: DbSession) -> Message:
    await engagement_service.add_watch(db, user.id, payload.merchant_id)
    return Message(message="Added to watchlist.")


@router.delete("/watchlist/{watch_id}", response_model=Message)
async def remove_watch(watch_id: int, user: CurrentUser, db: DbSession) -> Message:
    await engagement_service.remove_watch(db, user.id, watch_id)
    return Message(message="Removed.")


# ---- deal alerts ----
@router.get("/alerts", response_model=list[DealAlertOut])
async def alerts(user: CurrentUser, db: DbSession) -> list[DealAlertOut]:
    return [DealAlertOut.model_validate(a) for a in await engagement_service.list_alerts(db, user.id)]


@router.post("/alerts", response_model=DealAlertOut, status_code=201)
async def create_alert(payload: DealAlertIn, user: CurrentUser, db: DbSession) -> DealAlertOut:
    alert = await engagement_service.create_alert(
        db,
        user.id,
        merchant_id=payload.merchant_id,
        keyword=payload.keyword,
        min_discount=payload.min_discount,
        channel=payload.channel,
    )
    return DealAlertOut.model_validate(alert)


@router.delete("/alerts/{alert_id}", response_model=Message)
async def delete_alert(alert_id: int, user: CurrentUser, db: DbSession) -> Message:
    await engagement_service.delete_alert(db, user.id, alert_id)
    return Message(message="Alert deleted.")


# ---- notifications ----
@router.get("/notifications", response_model=list[NotificationOut])
async def notifications(user: CurrentUser, db: DbSession) -> list[NotificationOut]:
    return [NotificationOut.model_validate(n) for n in await engagement_service.list_notifications(db, user.id)]


@router.get("/notifications/unread-count")
async def unread_count(user: CurrentUser, db: DbSession) -> dict:
    return {"unread": await engagement_service.unread_count(db, user.id)}


@router.post("/notifications/read-all", response_model=Message)
async def read_all(user: CurrentUser, db: DbSession) -> Message:
    await engagement_service.mark_all_read(db, user.id)
    return Message(message="All notifications marked read.")


# ---- search history ----
@router.get("/history", response_model=list[SearchHistoryOut])
async def history(user: CurrentUser, db: DbSession) -> list[SearchHistoryOut]:
    rows = await engagement_service.search_history(db, user.id)
    return [
        SearchHistoryOut(
            id=r.id,
            raw_query=r.raw_query,
            normalized_query=r.normalized_query,
            results_count=r.results_count,
            created_at=r.created_at,
        )
        for r in rows
    ]


# ---- referrals ----
@router.get("/referrals", response_model=ReferralSummary)
async def referrals(user: CurrentUser, db: DbSession) -> ReferralSummary:
    summary = await engagement_service.referral_summary(db, user.id)
    invite = f"{settings.cors_origin_list[0] if settings.cors_origin_list else ''}/register?ref={user.referral_code or ''}"
    return ReferralSummary(
        referral_code=user.referral_code,
        total=summary["total"],
        converted=summary["converted"],
        rewarded=summary["rewarded"],
        invite_url=invite,
    )


# ---- subscription / quota ----
@router.get("/subscription", response_model=SubscriptionOut)
async def subscription(user: CurrentUser, db: DbSession) -> SubscriptionOut:
    plan = await quota_service.get_effective_plan(db, user.id)
    # Find the active subscription for period info, if any.
    from sqlalchemy import select

    from app.models.billing import Subscription as Sub

    sub = (
        await db.execute(
            select(Sub)
            .where(Sub.user_id == user.id, Sub.status.in_(("active", "trialing")))
            .order_by(Sub.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return SubscriptionOut(
        plan=plan.slug if plan else "free",
        plan_name=plan.name if plan else "Free",
        status=sub.status if sub else "active",
        quota_limit=plan.quota_limit if plan else 10,
        quota_window=plan.quota_window if plan else "day",
        current_period_end=sub.current_period_end if sub else None,
        cancel_at_period_end=sub.cancel_at_period_end if sub else False,
    )

"""Public coupon endpoints: detail, list by merchant, click-out, feedback, submit."""
from __future__ import annotations

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import RedirectResponse

from app.api.deps import DbSession, OptionalUser
from app.core.exceptions import NotFoundError
from app.ingestion import storage
from app.ingestion.extraction import StructuredCoupon
from app.schemas.common import Message, Page
from app.schemas.coupon import CouponOut, CouponSubmission, FeedbackIn
from app.services import coupon_service, merchant_service

router = APIRouter(prefix="/coupons", tags=["coupons"])


@router.get("/{uuid}", response_model=CouponOut)
async def get_coupon(uuid: str, db: DbSession) -> CouponOut:
    coupon = await coupon_service.get_by_uuid(db, uuid)
    if coupon is None:
        raise NotFoundError("Coupon not found.")
    await coupon_service.register_view(db, coupon.id)
    return CouponOut.model_validate(coupon)


@router.get("/by-merchant/{merchant_id}", response_model=Page[CouponOut])
async def list_by_merchant(
    merchant_id: int,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[CouponOut]:
    rows, total = await coupon_service.list_by_merchant(
        db, merchant_id, limit=page_size, offset=(page - 1) * page_size
    )
    return Page.create([CouponOut.model_validate(r) for r in rows], total, page, page_size)


@router.get("/{uuid}/go", summary="Click-out redirect with tracking")
async def go(uuid: str, db: DbSession) -> RedirectResponse:
    coupon = await coupon_service.get_by_uuid(db, uuid)
    if coupon is None or not coupon.landing_url:
        raise NotFoundError("Coupon or destination not found.")
    await coupon_service.register_click(db, coupon.id)
    return RedirectResponse(url=coupon.landing_url, status_code=status.HTTP_302_FOUND)


@router.post("/{uuid}/feedback", response_model=Message)
async def feedback(uuid: str, payload: FeedbackIn, db: DbSession, user: OptionalUser) -> Message:
    coupon = await coupon_service.get_by_uuid(db, uuid)
    if coupon is None:
        raise NotFoundError("Coupon not found.")
    await coupon_service.submit_feedback(
        db, coupon.id, worked=payload.worked, user_id=user.id if user else None, comment=payload.comment
    )
    return Message(message="Thanks for your feedback!")


@router.post("/submit", response_model=Message, status_code=status.HTTP_201_CREATED)
async def submit(payload: CouponSubmission, request: Request, db: DbSession, user: OptionalUser) -> Message:
    """User-submitted coupon — stored as pending_review, scored, not auto-activated."""
    merchant = await merchant_service.resolve_merchant_by_slug(db, payload.merchant_slug)
    if merchant is None:
        raise NotFoundError("Unknown merchant. Please pick a known store.")

    sc = StructuredCoupon(
        title=payload.title,
        code=payload.code,
        landing_url=payload.landing_url,
        confidence=0.45,  # below auto-activate threshold -> pending_review
        raw_text=(payload.description or payload.title)[:2000],
    )
    await storage.store_coupon(
        db,
        sc,
        merchant_id=merchant.id,
        merchant_known=True,
        merchant_trust=None,
        source_id=None,
        source_trust=0.4,  # user submissions start with modest trust
        auto_activate=False,
        index=False,
    )
    return Message(message="Submitted for review. Thank you!")

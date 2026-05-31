"""Search endpoints: AI-powered search, autocomplete suggestions, and quota status.

Search works for anonymous users (limited quota) and authenticated users (plan
quota). Every call consumes one quota unit; suggestions are free.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.api.deps import DbSession, OptionalUser
from app.schemas.search import QuotaStatus, SearchResponse, Suggestion, SuggestResponse
from app.search import service as search_service
from app.services import quota_service
from app.utils.net import get_client_ip

router = APIRouter(prefix="/search", tags=["search"])


def _client_ip(request: Request) -> str | None:
    return get_client_ip(request)


@router.get("", response_model=SearchResponse, summary="AI coupon search")
async def search(
    request: Request,
    db: DbSession,
    user: OptionalUser,
    q: str = Query(..., min_length=1, max_length=200, description="Natural-language search query"),
    limit: int = Query(20, ge=1, le=50),
    use_ai: bool = Query(True, description="Enable AI query understanding"),
) -> SearchResponse:
    # Enforce quota first (429 if exhausted).
    await quota_service.check_and_consume(db, user_id=user.id if user else None, ip=_client_ip(request))
    return await search_service.search(
        db, q, user_id=user.id if user else None, limit=limit, use_ai=use_ai
    )


@router.get("/suggest", response_model=SuggestResponse, summary="Autocomplete suggestions")
async def suggest(
    db: DbSession,
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(8, ge=1, le=15),
) -> SuggestResponse:
    raw = await search_service.suggest(db, q, limit=limit)
    return SuggestResponse(suggestions=[Suggestion(**s) for s in raw])


@router.get("/quota", response_model=QuotaStatus, summary="Current search quota status")
async def quota(request: Request, db: DbSession, user: OptionalUser) -> QuotaStatus:
    return await quota_service.peek_quota(
        db, user_id=user.id if user else None, ip=_client_ip(request)
    )

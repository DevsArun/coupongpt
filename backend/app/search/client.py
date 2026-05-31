"""Meilisearch client wrapper.

The official ``meilisearch`` SDK is synchronous, so blocking calls are dispatched
to a thread via ``asyncio.to_thread`` to keep the event loop responsive. The
index configuration (typo tolerance, synonyms, ranking rules, filterable and
sortable attributes) lives here and is applied idempotently on startup.
"""
from __future__ import annotations

import asyncio
from typing import Any

import meilisearch
from meilisearch.index import Index

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("search.client")

_client: meilisearch.Client | None = None


def get_client() -> meilisearch.Client:
    global _client
    if _client is None:
        _client = meilisearch.Client(settings.meili_host, settings.meili_master_key)
    return _client


def get_index() -> Index:
    return get_client().index(settings.meili_index_coupons)


# Searchable attributes in priority order (earlier = more important).
SEARCHABLE_ATTRIBUTES = [
    "title",
    "merchant_name",
    "merchant_aliases",
    "code",
    "description",
    "categories",
]

FILTERABLE_ATTRIBUTES = [
    "merchant_id",
    "merchant_slug",
    "status",
    "discount_type",
    "categories",
    "has_code",
    "expires_at_ts",
    "starts_at_ts",
]

SORTABLE_ATTRIBUTES = [
    "ranking_score",
    "expires_at_ts",
    "created_at_ts",
    "discount_value",
]

# Custom ranking rules: Meili relevance first, then our blended score.
RANKING_RULES = [
    "words",
    "typo",
    "proximity",
    "attribute",
    "sort",
    "exactness",
    "ranking_score:desc",
]


async def ping_meilisearch() -> bool:
    try:
        health = await asyncio.to_thread(get_client().health)
        return bool(health.get("status") == "available")
    except Exception:
        return False


async def ensure_index() -> None:
    """Create the coupons index and apply settings idempotently."""
    client = get_client()
    try:
        await asyncio.to_thread(client.create_index, settings.meili_index_coupons, {"primaryKey": "id"})
    except Exception:
        # Index may already exist; that is fine.
        pass

    index = get_index()
    await asyncio.to_thread(index.update_searchable_attributes, SEARCHABLE_ATTRIBUTES)
    await asyncio.to_thread(index.update_filterable_attributes, FILTERABLE_ATTRIBUTES)
    await asyncio.to_thread(index.update_sortable_attributes, SORTABLE_ATTRIBUTES)
    await asyncio.to_thread(index.update_ranking_rules, RANKING_RULES)
    await asyncio.to_thread(
        index.update_typo_tolerance,
        {
            "enabled": True,
            "minWordSizeForTypos": {"oneTypo": 4, "twoTypos": 8},
        },
    )
    logger.info("meili_index_ready", index=settings.meili_index_coupons)


async def update_synonyms(synonyms: dict[str, list[str]]) -> None:
    await asyncio.to_thread(get_index().update_synonyms, synonyms)


async def add_documents(documents: list[dict[str, Any]]) -> None:
    if not documents:
        return
    await asyncio.to_thread(get_index().add_documents, documents)


async def delete_document(doc_id: int | str) -> None:
    await asyncio.to_thread(get_index().delete_document, doc_id)


async def raw_search(query: str, params: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(get_index().search, query, params)

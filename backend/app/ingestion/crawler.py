"""Crawler stage — fetch source content (HTML pages, RSS feeds, sitemaps).

This is the ONLY place network fetching happens, and it is strictly part of the
offline ingestion pipeline — never the search hot path. Fetches are bounded by a
timeout and a max body size, and a descriptive User-Agent is sent.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from app.core.logging import get_logger

logger = get_logger("ingestion.crawler")

USER_AGENT = "CouponGPTBot/1.0 (+https://coupongpt.example/bot)"
_MAX_BYTES = 3_000_000
_TIMEOUT = 15.0

_SITEMAP_LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.IGNORECASE)


@dataclass
class FetchResult:
    url: str
    status: int
    content_type: str
    text: str
    ok: bool


async def fetch_url(url: str) -> FetchResult:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml"}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            content = resp.text[:_MAX_BYTES]
            return FetchResult(
                url=str(resp.url),
                status=resp.status_code,
                content_type=resp.headers.get("content-type", ""),
                text=content,
                ok=resp.is_success,
            )
    except httpx.HTTPError as exc:
        logger.warning("fetch_failed", url=url, error=str(exc))
        return FetchResult(url=url, status=0, content_type="", text="", ok=False)


def parse_sitemap(xml: str) -> list[str]:
    """Return all <loc> URLs from a sitemap or sitemap index."""
    return _SITEMAP_LOC_RE.findall(xml or "")


def parse_rss(xml: str) -> list[dict[str, str]]:
    """Parse an RSS/Atom feed into a list of {title, link, summary} entries."""
    try:
        import feedparser

        parsed = feedparser.parse(xml)
        items = []
        for entry in parsed.entries:
            items.append(
                {
                    "title": getattr(entry, "title", ""),
                    "link": getattr(entry, "link", ""),
                    "summary": getattr(entry, "summary", "") or getattr(entry, "description", ""),
                }
            )
        return items
    except Exception as exc:  # noqa: BLE001
        logger.warning("rss_parse_failed", error=str(exc))
        return []

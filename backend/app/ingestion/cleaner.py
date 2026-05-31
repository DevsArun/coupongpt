"""Cleaner stage — turn raw HTML into normalized plain text.

Uses BeautifulSoup when available; falls back to a regex stripper so the module
imports and runs even in minimal environments.
"""
from __future__ import annotations

import re

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]+")
_MULTI_NL_RE = re.compile(r"\n{3,}")


def clean_html(html: str) -> str:
    if not html:
        return ""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "head"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
    except Exception:
        text = _TAG_RE.sub(" ", html)

    text = _WS_RE.sub(" ", text)
    lines = [ln.strip() for ln in text.splitlines()]
    text = "\n".join(ln for ln in lines if ln)
    return _MULTI_NL_RE.sub("\n\n", text).strip()


def chunk_candidates(text: str, *, max_chars: int = 4000) -> list[str]:
    """Split cleaned text into coupon-candidate blocks for downstream extraction."""
    blocks: list[str] = []
    current: list[str] = []
    size = 0
    for para in text.split("\n"):
        if size + len(para) > max_chars and current:
            blocks.append("\n".join(current))
            current, size = [], 0
        current.append(para)
        size += len(para) + 1
    if current:
        blocks.append("\n".join(current))
    return blocks

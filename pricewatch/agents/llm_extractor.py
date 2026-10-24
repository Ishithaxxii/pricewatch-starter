"""LLM extractor: the fallback for stores we have no adapter for.

Given raw HTML and its URL, ask a model for the structured offer.
"""
from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from ..models import Observation
from ..providers import Provider

import hashlib
import os
from pathlib import Path

SYSTEM = """You extract e-commerce offer data from a product page and answer ONLY with a JSON object:
{"name": str|null, "price_cents": int|null, "currency": "ISO-4217"|null, "availability": "in_stock"|"out_of_stock"|"unknown",
 "pack_size": int, "compare_at_cents": int|null}
price_cents is the price of the pack actually being sold, in minor units. If there is no price, use null."""


def clean_html(html: str, limit: int = 12000) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "svg"]):
        t.decompose()
    text = re.sub(r"\n\s*\n+", "\n", soup.get_text("\n"))
    return text[:limit]


def extract_with_llm(provider: Provider, store: str, url: str, html: str, timeout: float = 30.0) -> Observation:
    
    cleaned = clean_html(html)
    cache_identity = {
        "provider": provider.name,
        "model": getattr(provider, "model", "unknown"),
        "store": store,
        "url": url,
        "page_text": cleaned,
    }
    cache_key = hashlib.sha256(
        json.dumps(cache_identity, sort_keys=True).encode("utf-8")
    ).hexdigest()

    cache_dir = Path(os.environ.get("PRICEWATCH_CACHE_DIR", ".pricewatch_cache"))
    cache_path = cache_dir / f"{cache_key}.json"

    if cache_path.exists():
        raw = cache_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    else:
        user = f"URL: {url}\n\nPAGE TEXT:\n{cleaned}"
        raw = provider.complete(
            SYSTEM,
            user,
            metadata={"source_url": url, "store": store},
            timeout=timeout,
        )
        # Validate before caching, so malformed responses can be retried.
        data = json.loads(raw)
        cache_dir.mkdir(parents=True, exist_ok=True)
        temp_path = cache_path.with_suffix(".tmp")
        temp_path.write_text(raw, encoding="utf-8")
        temp_path.replace(cache_path)

    return Observation(
        store=store,
        product_id=url.rstrip("/").split("/")[-1],
        url=url,
        name=data.get("name") or "",
        price_cents=data.get("price_cents"),
        currency=data.get("currency") or "",
        compare_at_cents=data.get("compare_at_cents"),
        availability=data.get("availability") or "unknown",
        pack_size=int(data.get("pack_size") or 1),
        source="llm",
    )


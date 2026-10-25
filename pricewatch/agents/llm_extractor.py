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


SYSTEM = """Extract the selected/default product offer from the supplied product page.
Return ONLY one valid JSON object with exactly these keys:
{
  "name": string or null,
  "price_cents": integer or null,
  "currency": three-letter ISO currency code or null,
  "availability": "in_stock" or "out_of_stock" or "unknown",
  "pack_size": positive integer,
  "compare_at_cents": integer or null
}

Rules:
- price_cents is the total price of the selected/default pack, in minor units.
- Do not use unit prices, shipping charges, installments, related products,
  or crossed-out prices as the current price.
- Prefer the selected/default variant over arbitrary variants.
- Interpret decimal and thousands separators using the displayed locale.
- compare_at_cents is the original/comparison price when clearly available.
- Use null for unknown prices or currencies. Never guess.
- Use pack_size 1 when the pack size is unknown.
- Output JSON only, with no Markdown or explanation."""



def clean_html(html: str, limit: int = 12000) -> str:
    soup = BeautifulSoup(html, "html.parser")
    structured: list[str] = []

    # Preserve JSON-LD and common framework state before removing scripts.
    for script in soup.find_all("script"):
        script_type = (script.get("type") or "").lower()
        script_id = (script.get("id") or "").lower()
        script_text = script.string or script.get_text()

        if script_type == "application/ld+json" and script_text.strip():
            structured.append("JSON-LD:\n" + script_text.strip())
        elif script_id in {"__next_data__", "__nuxt_data__"} and script_text.strip():
            structured.append("APP STATE:\n" + script_text.strip())

    # Preserve useful product and Open Graph metadata.
    for meta in soup.find_all("meta"):
        key = (
            meta.get("property")
            or meta.get("name")
            or meta.get("itemprop")
            or ""
        ).lower()
        value = (meta.get("content") or "").strip()

        if value and (
            key.startswith("product:")
            or key.startswith("og:")
            or key in {
                "price", "pricecurrency", "availability",
                "twitter:title", "twitter:data1",
            }
        ):
            structured.append(f"META {key}: {value}")

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    visible_text = re.sub(
        r"\n\s*\n+", "\n", soup.get_text("\n")
    ).strip()

    prefix = ""
    if structured:
        prefix = (
            "STRUCTURED PRODUCT DATA:\n"
            + "\n\n".join(structured)
            + "\n\nVISIBLE PAGE TEXT:\n"
        )

    # Reserve at most half the budget for embedded data.
    prefix_budget = min(len(prefix), limit // 2)
    return (
        prefix[:prefix_budget]
        + visible_text[:max(0, limit - prefix_budget)]
    )[:limit]



def _parse_response(raw: str) -> dict:
    text = raw.strip()

    # Accept a response wrapped in a Markdown JSON fence.
    fenced = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if fenced:
        text = fenced.group(1)

    # Invalid JSON raises JSONDecodeError as before.
    data = json.loads(text)

    if not isinstance(data, dict):
        raise ValueError("LLM response must be a JSON object")

    required = {
        "name", "price_cents", "currency",
        "availability", "pack_size", "compare_at_cents",
    }
    missing = required - data.keys()
    if missing:
        raise ValueError(
            f"LLM response missing keys: {', '.join(sorted(missing))}"
        )

    if data["name"] is not None and not isinstance(data["name"], str):
        raise ValueError("name must be a string or null")

    for field in ("price_cents", "compare_at_cents"):
        value = data[field]
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise ValueError(f"{field} must be a non-negative integer or null")

    currency = data["currency"]
    if currency is not None and (
        not isinstance(currency, str)
        or not re.fullmatch(r"[A-Z]{3}", currency)
    ):
        raise ValueError("currency must be a three-letter uppercase code or null")

    if data["availability"] not in {
        "in_stock", "out_of_stock", "unknown"
    }:
        raise ValueError("Invalid availability")

    pack_size = data["pack_size"]
    if (
        isinstance(pack_size, bool)
        or not isinstance(pack_size, int)
        or pack_size < 1
    ):
        raise ValueError("pack_size must be a positive integer")

    return data



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
        data = _parse_response(raw)
    else:
        user = f"URL: {url}\n\nPAGE TEXT:\n{cleaned}"
        raw = provider.complete(
            SYSTEM,
            user,
            metadata={"source_url": url, "store": store},
            timeout=timeout,
        )
        # Validate before caching, so malformed responses can be retried.
        data = _parse_response(raw)
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


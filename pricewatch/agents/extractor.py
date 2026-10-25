"""Extractor agent: one adapter per storefront turns a fetched page into an Observation.

Adapters receive the raw HTML (already fetched by the Client) and the URL. They must not do
their own networking except through the Client they are given, so throttling and cookies
stay in one place.

Adapters are registered by name; `stores.yaml` maps each store to an adapter.
"""
from __future__ import annotations

import json
import re
from typing import Callable, Optional
from urllib.parse import urlparse
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..http import Client
from ..models import Observation
from .normalizer import parse_money, unit_price

ADAPTERS: dict[str, Callable[[Client, str, str, str], Observation]] = {}


def adapter(name: str):
    def deco(fn):
        ADAPTERS[name] = fn
        return fn
    return deco


def _pid_from_url(url: str) -> str:
    return urlparse(url).path.rstrip("/").split("/")[-1]


# --------------------------------------------------------------------------- level 1
@adapter("corner")
def extract_corner(client: Client, store: str, url: str, html: str) -> Observation:
    soup = BeautifulSoup(html, "html.parser")
    ld = soup.find("script", type="application/ld+json")
    data = json.loads(ld.string) if ld and ld.string else {}
    offer = data.get("offers", {})
    price_cents, currency = parse_money(str(offer.get("price", "")), offer.get("priceCurrency"))
    was = soup.find("s")
    compare, _ = parse_money(was.get_text(), currency) if was else (None, None)
    return Observation(
        store=store, product_id=data.get("sku") or _pid_from_url(url), url=url,
        name=data.get("name") or soup.h1.get_text(strip=True),
        price_cents=price_cents, currency=currency or "USD", compare_at_cents=compare,
        availability="in_stock" if "InStock" in str(offer.get("availability", "")) else "out_of_stock",
    )


# --------------------------------------------------------------------------- level 2
# @adapter("maple")
# def extract_maple(client: Client, store: str, url: str, html: str) -> Observation:
#     soup = BeautifulSoup(html, "html.parser")
#     name = soup.select_one(".product__title").get_text(strip=True)
#     price_el = soup.select_one(".price .price")  # first price element in the price block
#     price_cents, currency = parse_money(price_el.get_text(" ", strip=True), "EUR")
#     compare_el = soup.select_one(".price--compare")
#     compare, _ = parse_money(compare_el.get_text(" ", strip=True), currency) if compare_el else (None, None)
#     avail = "out_of_stock" if "Sold out" in soup.get_text() else "in_stock"
#     return Observation(
#         store=store, product_id=_pid_from_url(url), url=url, name=name,
#         price_cents=price_cents, currency=currency or "EUR", compare_at_cents=compare, availability=avail,
#     )

# Kept here, not in normalizer.parse_money, so the existing US-format behaviour
# (and its tests) stay untouched. Only Maple prints European-style prices.
def _eu_price(text: str):

    return parse_money(text.replace(".", "").replace(",", "."), "EUR")

@adapter("maple")
def extract_maple(client: Client, store: str, url: str, html: str) -> Observation:
    soup = BeautifulSoup(html, "html.parser")
    name = soup.select_one(".product__title").get_text(strip=True)

    # Prefer the sale price; otherwise the regular price.
    price_el = soup.select_one(".price--sale")
    if price_el is None:
        price_el = soup.select_one(".price .price:not(.price--compare)")
    if price_el is None:
        price_el = soup.select_one(".price")
    price_cents, currency = _eu_price(price_el.get_text(" ", strip=True))

    compare_el = soup.select_one(".price--compare")
    compare = _eu_price(compare_el.get_text(" ", strip=True))[0] if compare_el else None

    avail = "out_of_stock" if "Sold out" in soup.get_text() else "in_stock"
    return Observation(
        store=store, product_id=_pid_from_url(url), url=url, name=name,
        price_cents=price_cents, currency=currency,
        compare_at_cents=compare, availability=avail,
    )

# --------------------------------------------------------------------------- level 3
# Class names used by Zon's product page template.
# ZON_CLASSES = {"price": "a-1c3f89", "whole": "a-2b2181", "frac": "a-4e2865", "title": "a-affa10", "avail": "a-78b7d1", "unit": "a-702121"}


# @adapter("zon")
# def extract_zon(client: Client, store: str, url: str, html: str) -> Observation:
#     soup = BeautifulSoup(html, "html.parser")
#     if "Are you a human" in html:
#         return Observation(store=store, product_id=_pid_from_url(url), url=url, name="", price_cents=None,
#                            currency="USD", notes=["robot check page"])
#     title = soup.find(class_=ZON_CLASSES["title"])
#     name = title.get_text(strip=True) if title else ""
#     m = re.search(r"Pack of (\d+)", name)
#     pack = int(m.group(1)) if m else 1
#     box = soup.find(class_=ZON_CLASSES["price"])
#     price_cents: Optional[int] = None
#     if box:
#         whole = box.find(class_=ZON_CLASSES["whole"])
#         frac = box.find(class_=ZON_CLASSES["frac"])
#         if whole and frac:
#             amount = f"${whole.get_text(strip=True).replace(',', '')}.{frac.get_text(strip=True)}"
#             price_cents, _ = parse_money(amount, "USD")
#     avail_el = soup.find(class_=ZON_CLASSES["avail"])
#     avail = "out_of_stock" if avail_el and "out of stock" in avail_el.get_text().lower() else "in_stock"
#     return Observation(
#         store=store, product_id=_pid_from_url(url), url=url, name=re.sub(r"\s*\(Pack of \d+\)", "", name),
#         price_cents=price_cents, currency="USD", availability=avail, pack_size=pack,
#         unit_price_cents=unit_price(price_cents, pack),
#         notes=[] if price_cents is not None else ["no price found"],
#     )

def _zon_is_decoy(tag) -> bool:
    """True if a price group is not the product's own price.

    Zon scatters other prices around the page: other sellers' offers, struck-through
    list prices, and links hidden from humans. None of them is the price.
    """
    for el in [tag, *tag.parents]:
        if el.name in ("s", "del", "strike"):
            return True
        if el.get("aria-hidden") == "true":
            return True
        heading = el.find(["h2", "h3", "h4"], recursive=False)
        if heading and re.search(r"other sellers|buying options|more offers",
                                 heading.get_text(), re.I):
            return True
    return False


def _zon_main_price(soup) -> Optional[str]:
    """Find the first non-decoy, pack-level price by structure, not by class name.

    Anchors on the element holding only the '$' sign; its parent holds the rest of the
    price, whether the cents are in a <sup> (one layout) or in spans around a '.' (another).
    Skips decoys and per-unit prices (followed by a '/ count' label). Returns e.g. '$22.07'.
    """
    for sym in soup.find_all(string=lambda s: s and s.strip() == "$"):
        group = sym.parent.parent
        if group is None or _zon_is_decoy(group):
            continue
        text = group.get_text(" ", strip=True)
        m = re.search(r"\$\s*([\d,]+)\s*\.?\s*(\d{2})(?!\d)", text)
        if not m:
            continue
        sibling = group.find_next_sibling()
        if text[m.end():].lstrip().startswith("/") or (
            sibling is not None and sibling.get_text(strip=True).startswith("/")
        ):
            continue  # unit price ("/ count"), not the pack price
        return f"${m.group(1).replace(',', '')}.{m.group(2)}"
    return None

@adapter("zon")
def extract_zon(client: Client, store: str, url: str, html: str) -> Observation:
    soup = BeautifulSoup(html, "html.parser")
    if "Are you a human" in html:
        return Observation(store=store, product_id=_pid_from_url(url), url=url, name="", price_cents=None,
                           currency="USD", notes=["robot check page"])
    h1 = soup.find("h1")
    name = h1.get_text(strip=True) if h1 else ""
    m = re.search(r"Pack of (\d+)", name)
    pack = int(m.group(1)) if m else 1
    notes: list[str] = []
    amount = _zon_main_price(soup)
    if amount is None:
        # No price shown: the page may ask for a variant to be picked first.
        variants = [urljoin(url, a["href"]) for a in soup.find_all("a", href=True)
                    if a["href"].startswith("?")]
        if variants:
            vr = client.get(variants[0])
            if "Are you a human" not in vr.text:
                soup = BeautifulSoup(vr.text, "html.parser")
                amount = _zon_main_price(soup)
                notes.append("price taken from the first variant")
    price_cents: Optional[int] = parse_money(amount, "USD")[0] if amount else None
    unavailable = re.search(r"out of stock|currently unavailable", soup.get_text(" ", strip=True), re.I)
    avail = "out_of_stock" if unavailable else "in_stock"
    if price_cents is None:
        notes.append("price unavailable: item currently unavailable" if unavailable else "no price found")
    return Observation(
        store=store, product_id=_pid_from_url(url), url=url, name=re.sub(r"\s*\(Pack of \d+\)", "", name),
        price_cents=price_cents, currency="USD", availability=avail, pack_size=pack,
        unit_price_cents=unit_price(price_cents, pack), notes=notes,
    )

# --------------------------------------------------------------------------- levels 4-5
@adapter("shield")
def extract_shield(client: Client, store: str, url: str, html: str) -> Observation:
    # TODO: not implemented yet.
    return Observation(store=store, product_id=_pid_from_url(url), url=url, name="", price_cents=None,
                       currency="GBP", notes=["shield adapter not implemented"])


@adapter("flux")
def extract_flux(client: Client, store: str, url: str, html: str) -> Observation:
    # TODO: not implemented yet.
    return Observation(store=store, product_id=_pid_from_url(url), url=url, name="", price_cents=None,
                       currency="USD", notes=["flux adapter not implemented"])


def extract(client: Client, store: str, adapter_name: str, url: str, html: str) -> Observation:
    fn = ADAPTERS.get(adapter_name)
    if fn is None:
        raise KeyError(f"no adapter named {adapter_name!r}")
    return fn(client, store, url, html)

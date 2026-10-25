"""Zon extractor tests.

Fixtures are trimmed copies of the real pages we saw on three seeds. They cover the
two price layouts, pack vs per-unit prices, decoys, the variant picker, unavailable
items, and the robot check. No network access is needed.
"""
from urllib.parse import urljoin

from pricewatch.agents.extractor import extract_zon

URL = "http://x/stores/zon/dp/TEST0001"


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeClient:
    """Stands in for Client: returns canned pages and records every URL requested."""

    def __init__(self, pages=None):
        self.pages = pages or {}
        self.requested = []

    def get(self, url, **kw):
        self.requested.append(url)
        return FakeResponse(self.pages[url])


# --- layout A: "$", whole number, ".", cents in separate spans (public seed) ---
OTHER_A = """
<div class="x9"><h3>Other sellers on Zon</h3>
<div><span class="c1">$</span><span class="c2">1,621</span><span class="c3">.</span><span class="c4">40</span><span class="c5">from Halden Direct</span></div>
<a aria-hidden="true" class="h1" href="/stores/zon/dp/TEST0001/offers-all" tabindex="-1">See all buying options</a>
</div>"""

PLAIN_A = """<html><body><h1 class="t">Halden Meridian Desk Lamp</h1>
<div class="m"><div class="p"><span class="c1">$</span><span class="c2">1,577</span><span class="c3">.</span><span class="c4">48</span></div>
<div class="l">List Price: <s>$2,135.91</s></div><div class="a">In Stock</div></div>""" + OTHER_A + "</body></html>"

PACK_A = """<html><body><h1 class="t">Kestrel Willow Desk Lamp (Pack of 12)</h1>
<div class="m"><div class="u"><span class="c1">$</span><span class="c2">125</span><span class="c3">.</span><span class="c4">51</span><span class="c5">/ count</span></div>
<div class="p"><span class="c5">Pack of 12:</span><span class="c1">$</span><span class="c2">1,506</span><span class="c3">.</span><span class="c4">12</span></div>
<div class="l">List Price: <s>$1,752.18</s></div><div class="a">In Stock</div></div>""" + OTHER_A + "</body></html>"

# --- layout B: cents in a <sup> (mytest seed) ---
OTHER_B = """
<div class="x9"><h3>Other sellers on Zon</h3>
<div><span class="g"><span class="d">$</span><span class="w">25</span><sup class="f">55</sup></span><span class="n">from Marrow Direct</span></div>
<a aria-hidden="true" class="h1" href="/stores/zon/dp/TEST0001/offers-all" tabindex="-1">See all buying options</a>
</div>"""

PLAIN_B = """<html><body><h1 class="t">Kestrel Quiet Air Purifier</h1>
<div class="m"><div class="p"><span class="g"><span class="d">$</span><span class="w">22</span><sup class="f">07</sup></span></div>
<div class="a">In Stock</div></div>""" + OTHER_B + "</body></html>"

PACK_B = """<html><body><h1 class="t">Ovo Prairie Kettle (Pack of 12)</h1>
<div class="m"><div class="u"><span class="g"><span class="d">$</span><span class="w">81</span><sup class="f">00</sup></span><span class="n">/ count</span></div>
<div class="p"><span class="n">Pack of 12:</span><span class="g"><span class="d">$</span><span class="w">972</span><sup class="f">04</sup></span></div>
<div class="l">List Price: <s>$1,293.13</s></div><div class="a">In Stock</div></div>""" + OTHER_B + "</body></html>"

# --- variant picker: no price until a colour is chosen ---
VARIANT_PICKER = """<html><body><h1 class="t">Halden Willow Air Purifier</h1>
<div class="v">Colour: <a href="?variant=AAA111">Rust</a> · <a href="?variant=BBB222">Sand</a></div>
<div class="m"><div class="p"><span class="n">Select a colour to see price</span></div></div>""" + OTHER_B + "</body></html>"

VARIANT_PAGE = """<html><body><h1 class="t">Halden Willow Air Purifier</h1>
<div class="m"><div class="p"><span class="g"><span class="d">$</span><span class="w">776</span><sup class="f">15</sup></span></div>
<div class="a">In Stock</div></div>""" + OTHER_B + "</body></html>"

UNAVAILABLE = """<html><body><h1 class="t">Tessa Nordic Notebook (Pack of 2)</h1>
<div class="m"><div class="a">Currently unavailable.</div>
<div class="n">We don't know when or if this item will be back in stock.</div></div></body></html>"""

DECOYS_ONLY = ('<html><body><h1 class="t">Mystery Item</h1><div class="m"></div>'
               + OTHER_B + "</body></html>")


def test_plain_price_spans_layout():
    o = extract_zon(FakeClient(), "zon", URL, PLAIN_A)
    assert o.price_cents == 157748  # not the list price, not another seller's
    assert o.pack_size == 1
    assert o.availability == "in_stock"
    assert o.notes == []


def test_pack_price_is_not_the_unit_price():
    o = extract_zon(FakeClient(), "zon", URL, PACK_A)
    assert o.price_cents == 150612  # pack price, not 12551 (the "/ count" price)
    assert o.pack_size == 12
    assert o.name == "Kestrel Willow Desk Lamp"


def test_sup_layout_ignores_other_sellers():
    o = extract_zon(FakeClient(), "zon", URL, PLAIN_B)
    assert o.price_cents == 2207  # not 2555 from "Other sellers on Zon"


def test_pack_price_in_sup_layout():
    o = extract_zon(FakeClient(), "zon", URL, PACK_B)
    assert o.price_cents == 97204  # not 8100
    assert o.pack_size == 12


def test_class_names_do_not_matter():
    renamed = PACK_A.replace('class="', 'class="zz-')
    assert extract_zon(FakeClient(), "zon", URL, renamed).price_cents == 150612


def test_variant_picker_uses_first_variant_and_says_so():
    first = urljoin(URL, "?variant=AAA111")
    client = FakeClient({first: VARIANT_PAGE})
    o = extract_zon(client, "zon", URL, VARIANT_PICKER)
    assert o.price_cents == 77615
    assert "price taken from the first variant" in o.notes
    assert client.requested == [first]  # only the first variant, and nothing disallowed


def test_unavailable_item_is_null_and_not_a_parse_failure():
    o = extract_zon(FakeClient(), "zon", URL, UNAVAILABLE)
    assert o.price_cents is None
    assert o.availability == "out_of_stock"
    assert any("unavailable" in n for n in o.notes)
    assert "no price found" not in o.notes


def test_only_decoy_prices_gives_null_and_requests_nothing():
    client = FakeClient()
    o = extract_zon(client, "zon", URL, DECOYS_ONLY)
    assert o.price_cents is None  # the 2555 from another seller must not be chosen
    assert "no price found" in o.notes
    assert client.requested == []  # never follows the hidden /offers-all link


def test_robot_check_page_is_reported():
    o = extract_zon(FakeClient(), "zon", URL, "<html><h1>Are you a human?</h1></html>")
    assert o.price_cents is None
    assert "robot check page" in o.notes
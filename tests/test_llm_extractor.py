import json

import pytest

from pricewatch.agents.llm_extractor import extract_with_llm


class FakeProvider:
    name = "fake"

    def __init__(self, response):
        self.response = response
        self.metadata = None

    def complete(self, system, user, *, metadata, timeout=30.0):
        self.metadata = metadata
        return self.response


def test_extracts_observation_from_valid_json(tmp_path, monkeypatch):    
    monkeypatch.setenv("PRICEWATCH_CACHE_DIR", str(tmp_path / "cache"))
    provider = FakeProvider(json.dumps({
        "name": "Steel Tiffin Box",
        "price_cents": 9939800,
        "currency": "INR",
        "availability": "in_stock",
        "pack_size": 3,
        "compare_at_cents": None,
    }))

    obs = extract_with_llm(
        provider,
        "bazaario",
        "https://bazaario.example/dp/bz-045",
        "<html><h1>Steel Tiffin Box</h1></html>",
    )

    assert obs.name == "Steel Tiffin Box"
    assert obs.price_cents == 9939800
    assert obs.currency == "INR"
    assert obs.availability == "in_stock"
    assert obs.pack_size == 3
    assert obs.source == "llm"
    assert provider.metadata["source_url"] == obs.url


def test_missing_price_is_allowed():
    provider = FakeProvider(json.dumps({
        "name": "Unknown Product",
        "price_cents": None,
        "currency": None,
        "availability": "unknown",
        "pack_size": 1,
        "compare_at_cents": None,
    }))

    obs = extract_with_llm(
        provider, "unknown-store",
        "https://example.com/product/123",
        "<html><h1>Unknown Product</h1></html>",
    )

    assert obs.price_cents is None
    assert obs.availability == "unknown"


def test_malformed_json_does_not_get_silently_accepted():
    provider = FakeProvider("this is not JSON")

    with pytest.raises(json.JSONDecodeError):
        extract_with_llm(
            provider, "unknown-store",
            "https://example.com/product/123",
            "<html></html>",
        )


def test_llm_response_is_cached(tmp_path, monkeypatch):
    import json
    from pricewatch.agents.llm_extractor import extract_with_llm

    monkeypatch.setenv("PRICEWATCH_CACHE_DIR", str(tmp_path / "cache"))

    class CountingProvider:
        name = "counting"
        model = "test-model"

        def __init__(self):
            self.calls = 0

        def complete(self, system, user, *, metadata, timeout=30.0):
            self.calls += 1
            return json.dumps({
                "name": "Test Product",
                "price_cents": 1200,
                "currency": "INR",
                "availability": "in_stock",
                "pack_size": 1,
                "compare_at_cents": None,
            })

    provider = CountingProvider()
    html = "<html><h1>Test Product</h1></html>"

    first = extract_with_llm(provider, "test", "https://example.com/item", html)
    second = extract_with_llm(provider, "test", "https://example.com/item", html)

    assert first.price_cents == second.price_cents == 1200
    assert provider.calls == 1

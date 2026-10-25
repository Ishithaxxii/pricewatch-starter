
import json
from argparse import Namespace

from pricewatch import cli
from pricewatch.models import Observation


def test_llm_extract_allows_unknown_store(tmp_path, monkeypatch, capsys):
    url = "https://unknown-shop.example/products/test-item"
    html_file = tmp_path / "page.html"
    html_file.write_text("<html><h1>Test item</h1></html>")

    monkeypatch.setattr(
        cli.config,
        "load_stores",
        lambda _: {"stores": {}},
    )

    observation = Observation(
        store="unknown-shop.example",
        product_id="test-item",
        url=url,
        name="Test item",
        price_cents=None,
        currency="",
        availability="unknown",
        source="llm",
    )

    from pricewatch.agents import llm_extractor
    from pricewatch import providers

    monkeypatch.setattr(
        llm_extractor,
        "extract_with_llm",
        lambda provider, store, url, html: observation,
    )
    monkeypatch.setattr(
        providers,
        "load_provider",
        lambda _: object(),
    )

    args = Namespace(
        stores_file="stores.yaml",
        store=None,
        url=url,
        html=str(html_file),
        llm=True,
        provider="echo",
    )

    result = cli.cmd_extract(args)
    output = json.loads(capsys.readouterr().out)

    assert result == 0
    assert output["store"] == "unknown-shop.example"
    assert output["source"] == "llm"
    assert output["url"] == url

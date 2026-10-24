import json

from pricewatch.evaluate import run


class FakeProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self, response):
        self.response = response

    def complete(self, system, user, *, metadata, timeout=30.0):
        return self.response

def test_report_calculates_all_four_accuracy_metrics(tmp_path):
    snapshots_dir = tmp_path / "snapshots"
    snapshots_dir.mkdir()

    (snapshots_dir / "product-1.html").write_text(
        "<html><h1>Steel Tiffin Box</h1></html>",
        encoding="utf-8",
    )
    (snapshots_dir / "product-2.html").write_text(
        "<html><h1>Coffee Maker</h1></html>",
        encoding="utf-8",
    )

    labels = [
        {
            "id": "product-1",
            "store": "bazaario",
            "file": "product-1.html",
            "url": "https://bazaario.example/product-1",
            "expected": {
                "price_cents": 10000,
                "currency": "INR",
                "availability": "in_stock",
                "pack_size": 2,
            },
        },
        {
            "id": "product-2",
            "store": "nordkart",
            "file": "product-2.html",
            "url": "https://nordkart.example/product-2",
            "expected": {
                "price_cents": 5000,
                "currency": "NOK",
                "availability": "out_of_stock",
                "pack_size": 1,
            },
        },
    ]

    labels_path = tmp_path / "labels.json"
    labels_path.write_text(json.dumps(labels), encoding="utf-8")

    response = json.dumps({
        "name": "Steel Tiffin Box",
        "price_cents": 10000,
        "currency": "INR",
        "availability": "in_stock",
        "pack_size": 2,
        "compare_at_cents": None,
    })

    report = run(
        FakeProvider(response),
        snapshots_dir,
        labels_path,
        tmp_path / "output",
    )

    assert report["n"] == 2
    assert report["overall"]["price_exact"] == 0.5
    assert report["overall"]["currency"] == 0.5
    assert report["overall"]["availability"] == 0.5
    assert report["overall"]["pack_size"] == 0.5
    assert (tmp_path / "output" / "report.json").exists()
    assert (tmp_path / "output" / "label_issues.json").exists()

    assert report["per_store"]["bazaario"]["n"] == 1
    assert report["per_store"]["nordkart"]["n"] == 1
    assert report["per_store"]["bazaario"]["price_exact"] == 1.0
    assert report["per_store"]["nordkart"]["price_exact"] == 0.0
    assert "p50" in report["latency_ms"]
    assert "p95" in report["latency_ms"]
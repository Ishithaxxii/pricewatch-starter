"""Eval harness for the LLM extractor.

Runs the LLM extractor over every snapshot in a directory, compares with labels.json, and
writes report.json and label_issues.json. The report schema is documented in tasks/ISSUE-3.md.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .agents.llm_extractor import extract_with_llm
from .providers import Provider, ProviderError, ProviderTimeout

import yaml

from .http import Client
from .agents.extractor import ADAPTERS, extract

def run(provider: Provider, snapshots_dir: str | Path, labels_path: str | Path, out_dir: str | Path) -> dict:
    snapshots_dir, out_dir = Path(snapshots_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    labels = {row["id"]: row for row in json.loads(Path(labels_path).read_text(encoding="utf-8"))}

    stores_config = yaml.safe_load(Path("stores.yaml").read_text(encoding="utf-8"))
    store_adapters = {
        store: config["adapter"]
        for store, config in stores_config["stores"].items()
    }
    baseline_correct = 0

    for row in labels.values():
        try:
            adapter_name = store_adapters.get(row["store"])
            if not adapter_name or adapter_name not in ADAPTERS:
                continue

            html = (snapshots_dir / row["file"]).read_text(encoding="utf-8")
            obs = extract(Client(), row["store"], adapter_name, row["url"], html)

            if obs.price_cents == row["expected"]["price_cents"]:
                baseline_correct += 1
        except Exception:
            # A failed or unimplemented rule-based extraction is incorrect.
            continue

    baseline = {
        "price_exact": baseline_correct / max(1, len(labels))
    }

    results = []
    errors = {"timeout": 0, "malformed_output": 0, "provider_error": 0}
    total_input_tokens = 0   #running totals across all evaluated snapshots so 
    total_output_tokens = 0       #report.json can show the total input and output tokens used.
    t0 = time.time()
    latencies = []

    for snap_id, row in labels.items():
        item_start = time.perf_counter()
        try:
            html = (snapshots_dir / row["file"]).read_text(encoding="utf-8")
            obs = extract_with_llm(provider, row["store"], row["url"], html)
            usage = getattr(provider, "last_usage", {})
            total_input_tokens += usage.get("input_tokens", 0)
            total_output_tokens += usage.get("output_tokens", 0)
            exp = row["expected"]
            # results.append({
            #     "id": snap_id,
            #     "price_ok": obs.price_cents == exp["price_cents"],
            #     "error": None,
            # })
            results.append({
                "id": snap_id,
                "store": row["store"],
                "price_exact": obs.price_cents == exp["price_cents"],  #checks whether the price matches exactly.
                "currency": obs.currency == exp["currency"], #checks the currency code.
                "availability": obs.availability == exp["availability"],  #checks whether the product is in stock or out of stock as expected.
                "pack_size": obs.pack_size == exp["pack_size"],   #checks the number of items in the pack.
                "error": None,  #means this snapshot completed without an exception.
            }) 
        except ProviderTimeout:
            errors["timeout"] += 1
            results.append({"id": snap_id, "store": row["store"], "price_exact": False, "currency": False, "availability": False, "pack_size": False, "error": "timeout",})
        except json.JSONDecodeError:
            errors["malformed_output"] += 1
            results.append({"id": snap_id, "store": row["store"], "price_exact": False, "currency": False, "availability": False, "pack_size": False, "error": "malformed_output",})
        except ProviderError:
            errors["provider_error"] += 1
            results.append({"id": snap_id, "store": row["store"], "price_exact": False, "currency": False, "availability": False, "pack_size": False, "error": "provider_error",})
        except Exception:
            # A single unexpected failure must not stop the remaining snapshots.
            errors["provider_error"] += 1
            results.append({"id": snap_id, "store": row["store"], "price_exact": False, "currency": False, "availability": False, "pack_size": False, "error": "provider_error",})

        latencies.append((time.perf_counter() - item_start) * 1000)

    latencies.sort()
    latency_ms = {
        "p50": round(latencies[int(0.50 * (len(latencies) - 1))], 2) if latencies else 0,
        "p95": round(latencies[int(0.95 * (len(latencies) - 1))], 2) if latencies else 0,
    }

    metrics = ("price_exact", "currency", "availability", "pack_size")

    overall = {
        metric: sum(result[metric] for result in results) / max(1, len(results))
        for metric in metrics
    }

    per_store = {}

    for store in {result["store"] for result in results}:
        store_results = [
            result for result in results
            if result["store"] == store
        ]

        per_store[store] = {
            "n": len(store_results),
            **{
                metric: sum(result[metric] for result in store_results)
                / max(1, len(store_results))
                for metric in metrics
            },
        }

    report = {
        "provider": provider.name,
        "model": getattr(provider, "model", "unknown"),
        "n": len(results),
        "overall": overall,
        "errors": errors,
        "latency_ms": latency_ms,
        "cost": {
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "usd_estimate": None,
        },
        "elapsed_s": round(time.time() - t0, 2),
        "per_store": per_store,
        "baseline": baseline,
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out_dir / "label_issues.json").write_text("[]", encoding="utf-8")
    return report

from pricewatch.agents.watcher import evaluate
from pricewatch.models import Observation


# def obs(price, at, pid="P1"):
#     return Observation(store="corner", product_id=pid, url="u", name="n", price_cents=price, currency="USD", observed_at=at)
def obs(price, at, pid="P1", currency="USD"):
    return Observation( store="corner", product_id=pid, url="u", name="n", price_cents=price, currency=currency,observed_at=at)

def test_drop_fires():
    alerts = evaluate([obs(10000, "2026-09-01T00:00:00")], [obs(8000, "2026-09-02T00:00:00")], [{"type": "drop_pct", "pct": 10}])
    assert len(alerts) == 1 and alerts[0].rule == "drop_pct"


def test_no_history_no_alert():
    assert evaluate([], [obs(8000, "2026-09-02T00:00:00")], [{"type": "drop_pct", "pct": 10}]) == []


def test_increase_no_alert():
    assert evaluate([obs(8000, "2026-09-01T00:00:00")], [obs(10000, "2026-09-02T00:00:00")], [{"type": "drop_pct", "pct": 10}]) == []


def test_drop_pct_message_percentage():
    # Regression test for the alert copy — keep in sync with rule_drop_pct.
    alerts = evaluate([obs(10000, "2026-09-01T00:00:00")], [obs(8000, "2026-09-02T00:00:00")], [{"type": "drop_pct", "pct": 10}])
    assert "20.0% drop" in alerts[0].message

def test_drop_below_threshold_does_not_fire():
    alerts = evaluate(
        [obs(10000, "2026-09-01T00:00:00")],
        [obs(8000, "2026-09-02T00:00:00")],
        [{"type": "drop_pct", "pct": 22}],
    )
    assert alerts == []

def test_below_median_fires():
    history = [
        obs(10000, "2026-09-01T00:00:00"),
        obs(12000, "2026-09-02T00:00:00"),
        obs(11000, "2026-09-03T00:00:00"),
    ]
    new = [obs(9000, "2026-09-04T00:00:00")]

    alerts = evaluate(
        history,
        new,
        [{"type": "below_median", "pct": 15, "window_days": 30}],
    )

    assert len(alerts) == 1
    assert alerts[0].rule == "below_median"
    assert alerts[0].previous_cents == 11000
    assert alerts[0].current_cents == 9000


def test_below_median_requires_three_prior_observations():
    history = [
        obs(10000, "2026-09-01T00:00:00"),
        obs(12000, "2026-09-02T00:00:00"),
    ]

    alerts = evaluate(
        history,
        [obs(5000, "2026-09-03T00:00:00")],
        [{"type": "below_median", "pct": 15, "window_days": 30}],
    )

    assert alerts == []


def test_below_median_uses_inclusive_cutoff():
    history = [
        obs(10000, "2026-09-01T00:00:00"),
        obs(12000, "2026-09-02T00:00:00"),
        obs(11000, "2026-09-03T00:00:00"),
    ]

    # Median is 11000; 10% below it is exactly 9900.
    alerts = evaluate(
        history,
        [obs(9900, "2026-09-04T00:00:00")],
        [{"type": "below_median", "pct": 10, "window_days": 30}],
    )

    assert len(alerts) == 1
    assert alerts[0].current_cents == 9900


def test_below_median_ignores_null_prices():
    history = [
        obs(10000, "2026-09-01T00:00:00"),
        obs(None, "2026-09-02T00:00:00"),
        obs(12000, "2026-09-03T00:00:00"),
        obs(11000, "2026-09-04T00:00:00"),
    ]

    alerts = evaluate(
        history,
        [obs(9000, "2026-09-05T00:00:00")],
        [{"type": "below_median", "pct": 15, "window_days": 30}],
    )

    assert len(alerts) == 1
    assert alerts[0].previous_cents == 11000


def test_below_median_wins_across_multiple_new_observations():
    history = [
        obs(8000, "2026-09-01T00:00:00"),
        obs(9000, "2026-09-02T00:00:00"),
        obs(12000, "2026-09-03T00:00:00"),
    ]

    new = [
        # A 12.5% drop from 12000: drop_pct fires, but below_median doesn't.
        obs(10500, "2026-09-04T00:00:00"),
        # This later price qualifies for below_median.
        obs(7000, "2026-09-05T00:00:00"),
    ]

    rules = [
        {"type": "drop_pct", "pct": 10},
        {"type": "below_median", "pct": 15, "window_days": 30},
    ]

    alerts = evaluate(history, new, rules)

    # Only one alert for this product, and the higher-priority rule wins.
    assert len(alerts) == 1
    assert alerts[0].rule == "below_median"
    assert alerts[0].observed_at == "2026-09-05T00:00:00"


def test_below_median_excludes_observations_outside_window():
    history = [
        obs(100000, "2026-09-01T00:00:00"),  # Outside the 30-day window
        obs(10000, "2026-10-01T00:00:00"),
        obs(12000, "2026-10-02T00:00:00"),
        obs(11000, "2026-10-03T00:00:00"),
    ]

    alerts = evaluate(
        history,
        [obs(9500, "2026-10-10T00:00:00")],
        [{"type": "below_median", "pct": 15, "window_days": 30}],
    )

    # The recent median is 11000; 9500 is not 15% below it.
    assert alerts == []


def test_below_median_skips_currency_mismatch():
    history = [
        obs(10000, "2026-10-01T00:00:00", currency="USD"),
        obs(12000, "2026-10-02T00:00:00", currency="USD"),
        obs(11000, "2026-10-03T00:00:00", currency="USD"),
    ]

    alerts = evaluate(
        history,
        [obs(5000, "2026-10-04T00:00:00", currency="EUR")],
        [{"type": "below_median", "pct": 15, "window_days": 30}],
    )

    assert alerts == []


def test_below_median_counts_multiple_observations_on_same_day():
    history = [
        obs(10000, "2026-10-01T08:00:00"),
        obs(12000, "2026-10-01T12:00:00"),
        obs(11000, "2026-10-01T18:00:00"),
    ]

    alerts = evaluate(
        history,
        [obs(8000, "2026-10-02T00:00:00")],
        [{"type": "below_median", "pct": 15, "window_days": 30}],
    )

    assert len(alerts) == 1
    assert alerts[0].rule == "below_median"


def test_only_one_alert_per_product():
    history = [
        obs(8000, "2026-10-01T00:00:00"),
        obs(9000, "2026-10-02T00:00:00"),
        obs(12000, "2026-10-03T00:00:00"),
    ]
    new = [
        obs(7000, "2026-10-04T00:00:00"),
        obs(6000, "2026-10-05T00:00:00"),
    ]

    alerts = evaluate(
        history,
        new,
        [{"type": "below_median", "pct": 15, "window_days": 30}],
    )

    assert len(alerts) == 1
    assert alerts[0].rule == "below_median"

"""Watcher agent: compares new observations against history and raises alerts.

History is a list of observations ordered by `observed_at`. Rules come from alerts.yaml.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta  #datetime-lets us interpret an observation's timestamp, timedelta â€” lets us calculate the beginning of a window,
from statistics import median #median â€” calculates the middle value of historical prices.
from typing import Iterable

from ..models import Alert, Observation


def _key(o: Observation) -> tuple[str, str]:
    return (o.store, o.product_id)


def _by_product(history: Iterable[Observation]) -> dict[tuple[str, str], list[Observation]]:
    out: dict[tuple[str, str], list[Observation]] = defaultdict(list)
    for o in history:
        out[_key(o)].append(o)
    for v in out.values():
        v.sort(key=lambda o: o.observed_at)
    return out


def rule_drop_pct(prev: Observation, cur: Observation, pct: float) -> Alert | None:
    if prev.price_cents is None or cur.price_cents is None:
        return None
    if cur.price_cents >= prev.price_cents:
        return None
    # drop = (prev.price_cents - cur.price_cents) / cur.price_cents * 100
    drop = (prev.price_cents - cur.price_cents) / prev.price_cents * 100
    #Found the error in line 31, the formula is supposed to be (prev_price - curr_price)/prev_price *100
    if drop >= pct:
        return Alert(store=cur.store, product_id=cur.product_id, rule="drop_pct",
                     message=f"{cur.name or cur.product_id}: {prev.price_cents} -> {cur.price_cents} ({drop:.1f}% drop)",
                     previous_cents=prev.price_cents, current_cents=cur.price_cents, observed_at=cur.observed_at)
    return None


#adding the below median rule as function
def rule_below_median(
    prior: list[Observation],  #prior contains the observations already available for this product.
    cur: Observation,
    pct: float,
    window_days: int,
) -> Alert | None:  #either eturns alert or none when alert shouldn't fire
    """Alert when the current price is sufficiently below its recent median."""
    if cur.price_cents is None:
        return None

    current_time = datetime.fromisoformat(cur.observed_at) #converts the timestamp string into a date/time object
    window_start = current_time - timedelta(days=window_days) # calculates the beginning of the 30-day lookback period.


    # Use all valid observations in the trailing window.
    window = []

    for obs in prior:
        observed_time = datetime.fromisoformat(obs.observed_at)

        if not (window_start <= observed_time < current_time):
            continue
        if obs.price_cents is None:
            continue

        window.append(obs)


    if len(window) < 3:
        return None


    currencies = {obs.currency for obs in window}

    if any(currency != cur.currency for currency in currencies):
        note = "below_median skipped: currency mismatch in trailing window"
        if note not in cur.notes:
            cur.notes.append(note)
        return None

    median_cents = int(round(median(obs.price_cents for obs in window)))
    threshold_price = median_cents * (1 - pct / 100)      #Calculate the cutoff or threshold value using cutoff = median * (1 - pct/100)

    #Creating alert when threshold/cutoff is met
    if cur.price_cents <= threshold_price:
        drop = (median_cents - cur.price_cents) / median_cents * 100
        return Alert(
            store=cur.store,
            product_id=cur.product_id,
            rule="below_median",
            message=(
                f"{cur.name or cur.product_id}: {cur.price_cents} cents "
                f"is {drop:.1f}% below the recent median of {median_cents} cents"
            ),
            previous_cents=median_cents,  #stores the median in the alert, as required.
            current_cents=cur.price_cents,
            observed_at=cur.observed_at,
        )

    return None


def evaluate(history: list[Observation], new: list[Observation], rules: list[dict]) -> list[Alert]:
    """Evaluate `rules` for each observation in `new` against `history` (which must not include `new`)."""
    alerts: list[Alert] = []
    hist = _by_product(history)
    median_alerts: dict[tuple[str, str], Alert] = {}  #Each dictionary maps a product key to its alert.
    drop_alerts: dict[tuple[str, str], Alert] = {}   #We keep separate dictionaries because below_median has higher priority than drop_pct.

    for cur in sorted(new, key=lambda o: o.observed_at):
        prior = hist.get(_key(cur), [])
        prev = prior[-1] if prior else None
        # for rule in rules:
        #     if rule.get("type") == "drop_pct" and prev is not None:
        #         a = rule_drop_pct(prev, cur, float(rule.get("pct", 10)))
        #         if a:
        #             alerts.append(a)
        #     # TODO(ISSUE-2): below_median rule

        median_rules = [r for r in rules if r.get("type") == "below_median"]
        drop_rules = [r for r in rules if r.get("type") == "drop_pct"]

        a = None

        for rule in median_rules:
            if rule.get("type") == "below_median": #Identify new rule
                a = rule_below_median(
                    prior,  #prior-supplies the earlier observations for the same product.
                    cur,
                    float(rule.get("pct", 15)),   # set default if setting is missing
                    int(rule.get("window_days", 30)),
                )
                if a is not None:
                    break

        if a is None and prev is not None:
            for rule in drop_rules:
                a = rule_drop_pct(prev, cur, float(rule.get("pct", 10)))
                if a is not None:
                    break

        if a is not None:
            key = _key(cur)

            if a.rule == "below_median":
                if key not in median_alerts:
                    median_alerts[key] = a
            elif a.rule == "drop_pct":
                if key not in drop_alerts:
                    drop_alerts[key] = a

    #     hist[_key(cur)] = prior + [cur]
    # return alerts

    #Return the winning alerts after the loop
        hist[_key(cur)] = prior + [cur]

    for key in median_alerts:
        alerts.append(median_alerts[key])

    for key in drop_alerts:
        if key not in median_alerts:
            alerts.append(drop_alerts[key])

    return alerts

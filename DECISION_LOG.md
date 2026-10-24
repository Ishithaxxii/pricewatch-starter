---
# Machine-read by the autograder. Keep the keys; fill in the values.
name: "Ishitha Sankarabhukta"
median_basis: ""        # the median your below_median rule computes: "observations" or "daily_close"
levels_attempted: []    # e.g. [1, 2, 3, 4, 5]
llm_provider: ""        # e.g. "openai", "anthropic", "gemini"
llm_model: ""
ai_tools_used: ["Claude","ChatGPT"]       # e.g. ["Claude Code", "Cursor", "ChatGPT"]
hours_spent: 0
---

# Decision log

Keep this to one page. Bullet points are fine. We read this before we read your code.

## Stage 1 — the false alerts

- Corrected the drop percentage calculation to divide by the previous
  price rather than the current price.
- Added regression coverage for the displayed percentage and for a
  price drop below the configured threshold.
- Fixed Maple extraction to prefer the sale price over the comparison
  price and normalize European decimal formatting before parsing.
- Verified the focused watcher, Maple extractor, and normalizer tests: 9 passed.

## Stage 2 — the median

- Computed the median using all valid past prices within the given time period (default 30 days), without including the current price observation.

- Require at least three prior observations with non-null prices before evaluating the rule i.e, calculating the median.

- Ignore observations with missing prices; skip the median alert if currencies differ within the window or from the current observation.

- Triggered an alert when the current price is at or below the required percentage below the median.

- Gave below_median priority over drop_pct and send only one alert per product.

Added tests for minimum no.of ocervations(history), missing prices, price threshold (cutoff), time-window filtering, multiple observations on the same day, currency mismatches, and alert/rule priority.

Verified the full test suite: 19 passed.

## Levels 3–5 — how you got in

<!-- Per level: what the store does, how your agent handles it, what you chose not to do (and why). -->

## Stage 3 — what the model got wrong

<!-- Failure patterns you saw. Which labels you think are wrong and how you decided. What you'd change with another day. -->

## Where AI helped and where it didn't

<!-- Be specific. "The assistant wrote the retry logic correctly first time, but confidently misread a response header and I lost 40 minutes before checking the raw response" is the level of detail we want. -->

## If I had another day


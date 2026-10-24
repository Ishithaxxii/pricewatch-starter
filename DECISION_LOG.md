---
# Machine-read by the autograder. Keep the keys; fill in the values.
name: "Ishitha Sankarabhukta"
median_basis: "daily_close"
levels_attempted: [1, 2]
llm_provider: "openai"
llm_model: "gpt-4o-mini"
ai_tools_used: ["ChatGPT", "Claude"]
hours_spent: 10
---

# Decision log

## Stage 1 — False price-drop alerts

- Fixed the drop percentage calculation to use the previous price as the baseline.
- Added tests to check the percentage and make sure drops below the configured threshold do not trigger alerts.
- Fixed Maple extraction to choose the sale price instead of the comparison price and handle European number formatting.
- The focused watcher, Maple extractor, and normalizer tests passed (9 tests).

## Stage 2 — Below-median alerts

- Used the latest valid price for each day to calculate the median, excluding the current observation.
- Required at least three valid daily closing prices. Ignored missing prices and skipped alerts when currencies did not match.
- Kept `below_median` as the higher-priority rule when both alert rules could apply, so each product gets at most one alert.
- Added tests for history length, missing prices, thresholds, time windows, same-day observations, currency mismatches, and rule priority.
- The full test suite passed: 24 tests.

## Levels 3-5 - how you got in

- Checked levels 1 and 2 against the mock store's grader-truth data. The scan returned 46 products, and all 22 products in the truth data matched by URL for the fields checked.
- I have not fully verified levels 3–5 yet.

## Stage 3 — LLM evaluation

- Ran `gpt-4o-mini` on all 90 saved snapshots.
- Accuracy was 57.8% for exact price, 85.6% for currency, 93.3% for availability, and 92.2% for pack size.
- Exact price extraction was the main weakness, especially on Bazaario (35.6%).
- The run had no timeouts, malformed outputs, or provider errors.
- The report shows 0% baseline price accuracy, which I still need to check against the rule-based extractor. Token usage was recorded, but the USD cost estimate is not calculated yet.
- `label_issues.json` is empty because I have not confirmed any mislabeled examples.

## How I used AI

I used ChatGPT and Claude to help debug issues, write tests, and build the evaluation harness.
Sometimes their suggestions didn't fully match what the task required, so I had to review them and make changes. I ran the code and tests locally. The evaluation showed that exact price extraction still needs work, especially for Bazaario.

I had a few issues along the way, the LLMs deviated at few tasks.

## What I would improve next

- Review incorrect price predictions and improve sale-price, localized-number, and pack-size extraction.
- Check the baseline result and add a reliable cost estimate.
- Review possible label issues against the original HTML.
- Test extraction levels 3–5 and the watch command more thoroughly.
- Test the Anthropic provider with the grader's configured key and model.

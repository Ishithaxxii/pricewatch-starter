---
# Machine-read by the autograder. Keep the keys; fill in the values.
name: "Ishitha Sankarabhukta"
median_basis: "observations"
levels_attempted: [1, 2]
llm_provider: "openai"
llm_model: "gpt-4o-mini"
ai_tools_used: ["ChatGPT", "Claude"]
hours_spent: 10
---

# Decision log

## Stage 1 — False price-drop alerts

- Corrected the price-drop percentage calculation to use the previous price as the baseline.

- Added tests covering the percentage calculation and ensuring that price drops below the configured threshold do not trigger alerts.

- Updated Maple extraction to select the sale price instead of the comparison price and handle European number formatting.

- The focused watcher, Maple extractor, and normalizer tests passed (9 tests).

## Stage 2 — Below-median alerts

- Calculated the median from valid prior observations in the trailing time window, excluding the current observation.

- Required at least three valid historical observations and ignored observations with missing prices.

- Suppressed alerts when currencies differed within the relevant history and recorded a note on the current observation.

- Kept below_median as the higher-priority rule when both alert conditions could apply, ensuring at most one alert per product per evaluation.

- Added tests for history length, missing prices, thresholds, time windows, same-day observations, currency mismatches, and rule priority.

- The full test suite passed (26 tests).

## Levels 3-5 - how you got in

- Verified Levels 1 and 2 against the available mock-store grader-truth data. The scan returned 46 products, and all 22 products in the truth data matched by URL for the fields checked.

- Levels 3–5 have not been fully verified. Further work is needed to validate extraction behavior across the remaining stores.

## Stage 3 — LLM evaluation

- Evaluated gpt-4o-mini against 90 saved snapshots.

- Recorded exact-price accuracy of 57.8%, currency accuracy of 85.6%, availability accuracy of 93.3%, and pack-size accuracy of 92.2%.

- Exact-price extraction was the main weakness, particularly for Bazaario, where the recorded accuracy was 35.6%.

- The recorded run reported no timeouts, malformed outputs, or provider errors.

- The report showed 0% baseline price accuracy. This result still needs investigation against the rule-based extractor.

- Token usage was recorded, but the USD cost estimate has not yet been calculated.

- No suspected label issues have been confirmed, so label_issues.json remains empty pending further review.

## How I used AI

I used ChatGPT and Claude to help debug issues, develop tests, and implement the evaluation harness. I reviewed the suggestions, adapted them to the task requirements, and ran the code and tests locally. Some suggestions did not fully match the assignment, so I had to revise them. The evaluation results showed that exact-price extraction remains the main weakness, especially for Bazaario.
I had a few issues along the way, the LLMs deviated at few tasks.

## What I would improve next

- Inspect incorrect price predictions and improve sale-price selection, localized-number parsing, and pack-size extraction.

- Validate the baseline price-accuracy calculation against the rule-based extractor.

- Calculate the USD cost estimate from the recorded token usage.

- Review suspected label issues against the original HTML before adding them to label_issues.json.

- Test Levels 3–5 and the watch command more thoroughly.

- Test the Anthropic provider with the grader's configured key and model.

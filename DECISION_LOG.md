---
# Machine-read by the autograder. Keep the keys; fill in the values.
name: "Ishitha Sankarabhukta"
median_basis: "daily_close"        # the median your below_median rule computes: "observations" or "daily_close"
levels_attempted: [1, 2]    # e.g. [1, 2, 3, 4, 5]
llm_provider: "openai"        # e.g. "openai", "anthropic", "gemini"
llm_model: "gpt-4o-mini"
ai_tools_used: ["Claude","ChatGPT"]       # e.g. ["Claude Code", "Cursor", "ChatGPT"]
hours_spent: 10
---

# Decision log

Keep this to one page. Bullet points are fine. We read this before we read your code.

## Stage 1 â€” the false alerts

- Corrected the drop percentage calculation to divide by the previous
  price rather than the current price.

- Added regression coverage for the displayed percentage and for a
  price drop below the configured threshold.

- Fixed Maple extraction to prefer the sale price over the comparison
  price and normalize European decimal formatting before parsing.

- Verified the focused watcher, Maple extractor, and normalizer tests: 9 passed.

## Stage 2 â€” the median

- Computed the median using all valid past prices within the given time period (default 30 days), without including the current price observation.

- Require at least three prior observations with non-null prices before evaluating the rule i.e, calculating the median.

- Ignore observations with missing prices; skip the median alert if currencies differ within the window or from the current observation.

- Triggered an alert when the current price is at or below the required percentage below the median.

- Gave below_median priority over drop_pct and send only one alert per product.

- Added tests for minimum no.of ocervations(history), missing prices, price threshold (cutoff), time-window filtering, multiple observations on the same day, currency mismatches, and alert/rule priority.

- Verified the full test suite: 19 passed.

## Levels 3â€“5 â€” how you got in

<!-- Per level: what the store does, how your agent handles it, what you chose not to do (and why). -->

## Stage 3 â€” what the model got wrong

- Ran the OpenAI gpt-4o-mini evaluation against all 90 saved snapshots.

- Exact price accuracy was 57.8%; currency accuracy was 85.6%, availability accuracy was 93.3%, and pack-size accuracy was 92.2%.

- Price extraction was the main weakness, particularly on Bazaario, where exact price accuracy was 35.6%.

- The run completed with zero timeouts, malformed outputs, or provider errors.

- The baseline price accuracy was reported as 0%. I would verify this baseline against the rule-based extractor before drawing conclusions.

- label_issues.json is currently empty. I have not established any mislabeled examples yet, so I will not invent label issues.

- The report's USD cost estimate is currently null; token usage was recorded, but the cost calculation still needs improvement.

## Where AI helped and where it didn't

I used ChatGPT and Claude to help investigate bugs, develop regression tests, and implement the evaluation harness.

I ran the code and tests locally to check the results.

The assistant's suggestions were useful for debugging, but the measured evaluation results exposed weak price extraction that needs further investigation.

## If I had another day

Inspect incorrect price predictions and improve extraction of sale prices, localized number formats, and pack pricing.

Verify the baseline extractor and implement a defensible cost estimate.

Review candidate label issues against the original HTML.

Verify extraction levels 1â€“5 and the watch command against the supplied stores.

Test the Anthropic provider with the grader's injected key and model configuration.





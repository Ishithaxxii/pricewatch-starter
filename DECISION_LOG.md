---
# Machine-read by the autograder. Keep the keys; fill in the values.
name: "Ishitha Sankarabhukta"
median_basis: "observations"        # the median your below_median rule computes: "observations" or "daily_close"
levels_attempted: [1, 2, 3]    # e.g. [1, 2, 3, 4, 5]
llm_provider: "openai"        # e.g. "openai", "anthropic", "gemini"
llm_model: "gpt-4o-mini"
ai_tools_used: ["ChatGPT", "Claude"]       # e.g. ["Claude Code", "Cursor", "ChatGPT"]
hours_spent: 10
---

# Decision log

Keep this to one page. Bullet points are fine. We read this before we read your code.

## Stage 1 — the false alerts

- The price-drop percentage was calculated against the wrong baseline. I fixed it so it uses the previous price.
- Added tests to check the percentage calculation and make sure small price drops do not trigger alerts.
- Maple extraction picked the original price instead of the sale price and did not handle European number formats. I fixed both.
- The watcher, Maple extractor and normalizer tests passed (9 tests).

## Stage 2 — the median

- Calculated the median using valid past observations within the time window, without including the current observation.
- Required at least three valid past observations and ignored observations with missing prices.
- Avoided alerts when currencies did not match and added a note to the observation.
- Kept `below_median` as the higher-priority rule when both rules could trigger, so only one alert is created per product per evaluation.
- Added tests for history, missing prices, thresholds, time windows, same-day observations, currency mismatches and rule priority.
- All 26 tests passed.

## Levels 3–5 — how you got in

- **Levels 1 and 2:** Checked using the available mock-store grader-truth data. The scan found 46 products, and all 22 products in the truth data matched by URL for the fields checked.
- **Level 3 (Zon):** At first, the scan found 12 products, but only one had a price. When I requested the same product repeatedly, it showed the price a few times and then changed to "See price in cart".
  - **Loading the page assets:** I tried changing cookies, request delays, headers and connection settings, but none of these fixed the issue. Then I tested loading the stylesheet linked on the product page. Without loading it, only 5 out of 12 products had prices; with it, all 12 matched the browser listing. I added `Client.load_page_assets` in `pricewatch/http.py` to load same-origin stylesheets and scripts from the page's HTML. These requests still go through the normal HTTP client and its one-second delay. I only enabled this for Zon so the other stores do not get unnecessary requests. I also reverted my earlier User-Agent change because it did not help. One thing I could not fully explain was why the price hiding appeared when both a custom User-Agent and `Accept-Language` were sent.
  - **Fixing price extraction:** The original extractor depended on fixed CSS class names. These changed between seeds, so the extractor failed on other catalogues. The price HTML also looked different between seeds: some used a `<sup>` for cents, while others used separate spans around the decimal point. I changed the extractor to find the price based on the HTML structure instead of fixed class names. It also ignores other sellers' prices, struck-through prices, hidden links and per-unit prices, so pack products return the pack price instead.
  - **Variants and unavailable products:** Some products ask the user to select a colour before showing a price. I chose the first variant's price and added a note to the observation. This matched the browser listing for all 10 tested variant cases across three seeds, although choosing the first variant is still a practical decision rather than a guaranteed rule. For products that are genuinely unavailable, the price stays `null` and the availability is marked as `out_of_stock`. This helps distinguish unavailable products from extraction failures.
  - **Robots.txt and request delays:** I made sure the scanner does not request the disallowed `/offers-all` endpoint. It follows product links, keeps asset requests on the same origin and respects the one-second delay for requests, including asset loading.
  - **Tests and verification:** I added `tests/test_extractor_zon.py` with 9 tests using trimmed copies of actual product pages. These cover different price layouts, pack prices, other sellers' prices, changing class names, variant selection, unavailable products, misleading prices and the robot-check page. I compared the extracted prices with the browser listing across three seeds: `public`, `mytest` and `third`. All 12 products matched on each seed, including the two unavailable products that correctly returned `null`. All 35 tests passed after adding the Zon tests. This confirms the results for the cases I tested, but I have not confirmed the hidden grader score.
- **Levels 4 and 5:** Not fully verified yet and need more testing.

## Stage 3 — what the model got wrong

- Tested `gpt-4o-mini` on 90 saved snapshots.
- The recorded accuracy was 57.8% for exact prices, 85.6% for currency, 93.3% for availability and 92.2% for pack size.
- Exact-price extraction was the main issue, especially for Bazaario, where accuracy was 35.6%.
- The run reported no timeouts, malformed outputs or provider errors.
- The report showed 0% baseline price accuracy, which I still need to investigate against the rule-based extractor.
- Token usage was recorded, but I have not calculated the estimated USD cost yet.
- I have not confirmed any label issues, so `label_issues.json` is still empty. I will check suspected label issues against the original HTML before adding any.

## Where AI helped and where it didn't

- I used ChatGPT and Claude to help debug problems, write tests and work on the evaluation harness. I reviewed their suggestions and tested the changes locally instead of assuming they were correct.
- Some suggestions did not fully match the task, so I had to change them. For example, during the Zon work, several guesses about cookies, connection reuse and browser-like headers did not fix the problem. Testing the page assets helped me identify the change that actually worked.
- Claude's first extractor rewrite also picked the per-unit price instead of the pack price, and one suggested edit removed an existing import and broke the scan. I caught these issues by running the code and comparing the results with the browser listing.
- The main thing I learned was that I need to test the suggestions against the actual website and not rely on the AI's explanation alone.

## If I had another day

- Check incorrect price predictions and improve sale-price selection, number parsing and pack-size extraction.
- Investigate the 0% baseline price accuracy result.
- Calculate the estimated USD cost using the recorded token usage.
- Check suspected label issues against the original HTML before adding them to `label_issues.json`.
- Test Levels 3–5 and the watch command more thoroughly.
- Test the Anthropic provider using the grader's configured key and model.
- Handle store connection failures more cleanly instead of stopping with a traceback.
- Move the page-asset loading setting into `stores.yaml` instead of checking the store name directly in the code.
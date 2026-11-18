# Guidance progress

## Source inventory

The search begins with filings dated January 1, 2023. It covers Item 2.02 earnings exhibits and the MD&A sections of periodic reports. A document counts as a language hit if one sentence mentions capital spending and a forward-looking cue. Hits include possible false positives. Zero hits cannot establish what a company said on a call.

| Company | Earnings exhibits | Periodic reports | Documents with a language hit | Documents read |
|---|---:|---:|---:|---:|
| AMZN | 16 | 16 | 18 | 32 |
| GOOGL | 17 | 16 | 11 | 33 |
| META | 16 | 16 | 32 | 32 |
| MSFT | 16 | 16 | 16 | 32 |
| ORCL | 15 | 15 | 17 | 30 |

## Evaluation protocol frozen before extractor development

The gold passages were selected by reading the filings. They include explicit ranges, points, qualitative changes, historical spending, general capital needs and forecasts of other line items. Dev uses 2023 and 2024 filings. The later 2025 and 2026 examples are the held-out test. Selection is purposive and the labels have one annotator. Uncertain cases are printed separately and excluded from scoring. A multi-year direction can be correctly detected while still failing the annual publication gate.

The primary proposal source will be the local model only if its test recall exceeds the rules baseline by at least 0.10 with equal or better precision. Otherwise use rules. Either extractor may flag a disagreement for review. Automatic approval always needs both. Score the final validated proposal at the extraction stage, before approval. Numeric and period accuracy use all certain gold positives with the relevant field, counting misses as errors. Verification rate uses all positive predictions. Score the held-out bytes once after freezing both extractors.

The installed default qwen2.5:7b-instruct timed out loading on this 8 GB Mac before the first dev response. No held-out results had been scored. The measured run uses qwen2.5:1.5b-instruct locally. The run configuration pins the replay model, and GUIDANCE_MODEL overrides it for new experiments.

## Frozen test result

| Metric | Rules | Local Qwen 1.5B |
|---|---:|---:|
| Precision | 100.0% (13/13, n=13) | 71.4% (5/7, n=7) |
| Recall | 100.0% (13/13, n=13) | 38.5% (5/13, n=13) |
| Dollar bounds | 100.0% (9/9, n=9) | 0.0% (0/9, n=9) |
| Annual target | 100.0% (13/13, n=13) | 0.0% (0/13, n=13) |
| All verification checks | 53.8% (7/13, n=13) | 0.0% (0/7, n=7) |

Selected rules. The test contains 24 of 45 labels (53.3%, n=45). Precision and recall measure positive detection. Correct classification alone does not establish that the dollars or dates are usable.

Uncertain labels excluded from both split scores:

- gold-8d154cc01f (dev, GOOGL, 2023-02-03): Heavy investment gives no comparison baseline.
- gold-f3331e409d (test, GOOGL, 2026-02-05): Infrastructure spending is a subset of total capex.
- gold-5ec564046c (test, META, 2025-10-29): Pressure on plans may not constitute a revised forecast.

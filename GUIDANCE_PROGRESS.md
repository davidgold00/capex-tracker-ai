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

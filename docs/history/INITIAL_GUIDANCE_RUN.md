# Guidance progress

No annual forecast passed review (n=0), so upward revisions, the gap from initial guidance to actual spending, and company reliability remain unmeasured.

**Review outcome.** 0 auto-approved, 0 manually approved and 156 pending. The chart has no eligible point. The local quarterly draft failed twice and its README section is empty.

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

## Filed outlook coverage

All five issuers expressed a spending outlook in the retrieved SEC filings. The table counts distinct documents with explicit company-wide dollar guidance or a clear direction; if both appear, the document counts in the numeric column. The coverage annotation records a trace for each identified document. It does not approve any value. The sentence screen can miss statements; these are observed counts. Guidance given only on calls is outside the sample. [Document evidence](../../data/guidance/coverage.csv)

| Company | Documents read | Numeric | Direction only | With explicit outlook | Pending passages |
|---|---:|---:|---:|---:|---:|
| MSFT | 32 | 0 | 10 | 10 | 48 |
| GOOGL | 33 | 4 | 1 | 5 | 13 |
| AMZN | 32 | 3 | 8 | 11 | 20 |
| META | 32 | 32 | 0 | 32 | 53 |
| ORCL | 30 | 1 | 1 | 2 | 22 |

**Verification and privacy.** Both offline demos ran. The full weekly update also ran against the live SEC endpoints with model imports blocked. The original processed financial tables and validation report matched byte for byte, with 181 annual checks, 16 warnings and zero failures. Every push is gated on a clean tracked-file privacy scan and the outgoing author and committer identities. Every new commit in this delivery uses the repository's private noreply identity. Existing GitHub history is preserved.

[README on GitHub](https://github.com/davidgold00/capex-tracker-ai/blob/main/README.md) and [walkthrough on GitHub](https://github.com/davidgold00/capex-tracker-ai/blob/main/docs/WALKTHROUGH.md).

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

The installed default qwen2.5:7b-instruct timed out loading on this 8 GB Mac before the first dev response. No held-out results had been scored. The measured run uses qwen2.5:1.5b-instruct locally. Offline replay uses the pinned run model. New live recordings default to the 7B model. Set `GUIDANCE_MODEL=qwen2.5:1.5b-instruct` to repeat the measured configuration.

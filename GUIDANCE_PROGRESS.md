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

All five issuers expressed a spending outlook in the retrieved SEC filings. The table counts distinct documents with explicit company-wide dollar guidance or a clear direction; if both appear, the document counts in the numeric column. The coverage annotation records a trace for each identified document. It does not approve any value. The sentence screen can miss statements; these are observed counts. Guidance given only on calls is outside the sample. [Document evidence](data/guidance/coverage.csv)

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


## Review queue

0 auto-approved, 156 pending. Each pending ID below links to the source and both sets of attempts in its trace. The editable queue is [pending.csv](data/guidance/pending.csv).

### AMZN

[AMZN-06bd97cc84bf](data/guidance/traces/AMZN-06bd97cc84bf.json), [AMZN-0de8725e6d2d](data/guidance/traces/AMZN-0de8725e6d2d.json), [AMZN-1a40d7181f82](data/guidance/traces/AMZN-1a40d7181f82.json), [AMZN-1c9a0118a53b](data/guidance/traces/AMZN-1c9a0118a53b.json), [AMZN-223bc9dd86d7](data/guidance/traces/AMZN-223bc9dd86d7.json), [AMZN-2a230a014d4c](data/guidance/traces/AMZN-2a230a014d4c.json), [AMZN-49c5c4fbc842](data/guidance/traces/AMZN-49c5c4fbc842.json), [AMZN-9838b3fdadfd](data/guidance/traces/AMZN-9838b3fdadfd.json), [AMZN-a8415b61fcbb](data/guidance/traces/AMZN-a8415b61fcbb.json), [AMZN-ac9cd9079469](data/guidance/traces/AMZN-ac9cd9079469.json), [AMZN-becb5a99d3fe](data/guidance/traces/AMZN-becb5a99d3fe.json), [AMZN-c214038f1441](data/guidance/traces/AMZN-c214038f1441.json), [AMZN-c47bb443e163](data/guidance/traces/AMZN-c47bb443e163.json), [AMZN-c867245052dc](data/guidance/traces/AMZN-c867245052dc.json), [AMZN-d3b4e72e2120](data/guidance/traces/AMZN-d3b4e72e2120.json), [AMZN-d70575c6fe05](data/guidance/traces/AMZN-d70575c6fe05.json), [AMZN-dc0d3829d4de](data/guidance/traces/AMZN-dc0d3829d4de.json), [AMZN-e3b7831c7f96](data/guidance/traces/AMZN-e3b7831c7f96.json), [AMZN-f2868c97f3ce](data/guidance/traces/AMZN-f2868c97f3ce.json), [AMZN-fe5dd79be81f](data/guidance/traces/AMZN-fe5dd79be81f.json)

### GOOGL

[GOOGL-0efa8facc4f3](data/guidance/traces/GOOGL-0efa8facc4f3.json), [GOOGL-30a76b71465b](data/guidance/traces/GOOGL-30a76b71465b.json), [GOOGL-4322ea1b57c8](data/guidance/traces/GOOGL-4322ea1b57c8.json), [GOOGL-586bf6865ae7](data/guidance/traces/GOOGL-586bf6865ae7.json), [GOOGL-9eb6791813d9](data/guidance/traces/GOOGL-9eb6791813d9.json), [GOOGL-a4902aedb13c](data/guidance/traces/GOOGL-a4902aedb13c.json), [GOOGL-a93e24526461](data/guidance/traces/GOOGL-a93e24526461.json), [GOOGL-aa8941d7cb74](data/guidance/traces/GOOGL-aa8941d7cb74.json), [GOOGL-aaa8007191b1](data/guidance/traces/GOOGL-aaa8007191b1.json), [GOOGL-bdae6435bf55](data/guidance/traces/GOOGL-bdae6435bf55.json), [GOOGL-cbe5e60f03e9](data/guidance/traces/GOOGL-cbe5e60f03e9.json), [GOOGL-d2de1d015e67](data/guidance/traces/GOOGL-d2de1d015e67.json), [GOOGL-e9a2680a71e1](data/guidance/traces/GOOGL-e9a2680a71e1.json)

### META

[META-0022f52baf5b](data/guidance/traces/META-0022f52baf5b.json), [META-064f97b176ad](data/guidance/traces/META-064f97b176ad.json), [META-09641528e6b6](data/guidance/traces/META-09641528e6b6.json), [META-0b8f3f671227](data/guidance/traces/META-0b8f3f671227.json), [META-129ecfe84188](data/guidance/traces/META-129ecfe84188.json), [META-16a6514fd301](data/guidance/traces/META-16a6514fd301.json), [META-174c0d47af55](data/guidance/traces/META-174c0d47af55.json), [META-20b5d82cf9c7](data/guidance/traces/META-20b5d82cf9c7.json), [META-228d3713dc46](data/guidance/traces/META-228d3713dc46.json), [META-26353ce5b627](data/guidance/traces/META-26353ce5b627.json), [META-27d24bc5895b](data/guidance/traces/META-27d24bc5895b.json), [META-374a5a3ca072](data/guidance/traces/META-374a5a3ca072.json), [META-4b7d6ad43db5](data/guidance/traces/META-4b7d6ad43db5.json), [META-50f459e4ced2](data/guidance/traces/META-50f459e4ced2.json), [META-52ff18465a18](data/guidance/traces/META-52ff18465a18.json), [META-579d02d3d7dd](data/guidance/traces/META-579d02d3d7dd.json), [META-59f76947a9c2](data/guidance/traces/META-59f76947a9c2.json), [META-5bf4d801c636](data/guidance/traces/META-5bf4d801c636.json), [META-5c77beb491c0](data/guidance/traces/META-5c77beb491c0.json), [META-6e73e0ba7afe](data/guidance/traces/META-6e73e0ba7afe.json), [META-6fd31b61c17e](data/guidance/traces/META-6fd31b61c17e.json), [META-70705cad0ce4](data/guidance/traces/META-70705cad0ce4.json), [META-71ca47706da6](data/guidance/traces/META-71ca47706da6.json), [META-75e8b40989f8](data/guidance/traces/META-75e8b40989f8.json), [META-766f8c9c06bc](data/guidance/traces/META-766f8c9c06bc.json), [META-77297c4cb424](data/guidance/traces/META-77297c4cb424.json), [META-78da308d4257](data/guidance/traces/META-78da308d4257.json), [META-7a70f631e0cd](data/guidance/traces/META-7a70f631e0cd.json), [META-7dcf3e00303f](data/guidance/traces/META-7dcf3e00303f.json), [META-82f178df6a6d](data/guidance/traces/META-82f178df6a6d.json), [META-83135f9b5d89](data/guidance/traces/META-83135f9b5d89.json), [META-933482d0ff99](data/guidance/traces/META-933482d0ff99.json), [META-986faab00e1b](data/guidance/traces/META-986faab00e1b.json), [META-9f65bf3b2539](data/guidance/traces/META-9f65bf3b2539.json), [META-ab5e515e911a](data/guidance/traces/META-ab5e515e911a.json), [META-ade2a0568e49](data/guidance/traces/META-ade2a0568e49.json), [META-b3a21f961f2e](data/guidance/traces/META-b3a21f961f2e.json), [META-b8134f53c05a](data/guidance/traces/META-b8134f53c05a.json), [META-bb0f6da18158](data/guidance/traces/META-bb0f6da18158.json), [META-bbf99af5983f](data/guidance/traces/META-bbf99af5983f.json), [META-bc5328ff1dfa](data/guidance/traces/META-bc5328ff1dfa.json), [META-c42ae4ac2ad9](data/guidance/traces/META-c42ae4ac2ad9.json), [META-ca4926c279c8](data/guidance/traces/META-ca4926c279c8.json), [META-ca9f97d191ab](data/guidance/traces/META-ca9f97d191ab.json), [META-d316e24b28e0](data/guidance/traces/META-d316e24b28e0.json), [META-e5c11ca5d93f](data/guidance/traces/META-e5c11ca5d93f.json), [META-e67833aed826](data/guidance/traces/META-e67833aed826.json), [META-e919e8372d0a](data/guidance/traces/META-e919e8372d0a.json), [META-f01132f9576c](data/guidance/traces/META-f01132f9576c.json), [META-f16c29a5200c](data/guidance/traces/META-f16c29a5200c.json), [META-f6f36e068c3a](data/guidance/traces/META-f6f36e068c3a.json), [META-f8dc7cc176b4](data/guidance/traces/META-f8dc7cc176b4.json), [META-faa9f14ada3e](data/guidance/traces/META-faa9f14ada3e.json)

### MSFT

[MSFT-03b5d8fb0a8b](data/guidance/traces/MSFT-03b5d8fb0a8b.json), [MSFT-03ff80285256](data/guidance/traces/MSFT-03ff80285256.json), [MSFT-173f85635772](data/guidance/traces/MSFT-173f85635772.json), [MSFT-1dbca946ec99](data/guidance/traces/MSFT-1dbca946ec99.json), [MSFT-220faf48a447](data/guidance/traces/MSFT-220faf48a447.json), [MSFT-26566e150dbe](data/guidance/traces/MSFT-26566e150dbe.json), [MSFT-2aea0168fab8](data/guidance/traces/MSFT-2aea0168fab8.json), [MSFT-2cf3116e6eb1](data/guidance/traces/MSFT-2cf3116e6eb1.json), [MSFT-300aa196b170](data/guidance/traces/MSFT-300aa196b170.json), [MSFT-322433dcaf0e](data/guidance/traces/MSFT-322433dcaf0e.json), [MSFT-38292d66dc48](data/guidance/traces/MSFT-38292d66dc48.json), [MSFT-3b28a17f1b0c](data/guidance/traces/MSFT-3b28a17f1b0c.json), [MSFT-4378b0715d01](data/guidance/traces/MSFT-4378b0715d01.json), [MSFT-47b51ddf10f4](data/guidance/traces/MSFT-47b51ddf10f4.json), [MSFT-4c4b873b07e8](data/guidance/traces/MSFT-4c4b873b07e8.json), [MSFT-4f4b7add803b](data/guidance/traces/MSFT-4f4b7add803b.json), [MSFT-53640f83ce59](data/guidance/traces/MSFT-53640f83ce59.json), [MSFT-5838363dcc8c](data/guidance/traces/MSFT-5838363dcc8c.json), [MSFT-606492c92510](data/guidance/traces/MSFT-606492c92510.json), [MSFT-62a656ce2a71](data/guidance/traces/MSFT-62a656ce2a71.json), [MSFT-6510dec9a086](data/guidance/traces/MSFT-6510dec9a086.json), [MSFT-6aab279ffa5e](data/guidance/traces/MSFT-6aab279ffa5e.json), [MSFT-6b62156330b3](data/guidance/traces/MSFT-6b62156330b3.json), [MSFT-766e439b47a6](data/guidance/traces/MSFT-766e439b47a6.json), [MSFT-7c9142ab69b1](data/guidance/traces/MSFT-7c9142ab69b1.json), [MSFT-7f5050f873ac](data/guidance/traces/MSFT-7f5050f873ac.json), [MSFT-87c303ac65ce](data/guidance/traces/MSFT-87c303ac65ce.json), [MSFT-8ddb90de6819](data/guidance/traces/MSFT-8ddb90de6819.json), [MSFT-97e0f21b42a6](data/guidance/traces/MSFT-97e0f21b42a6.json), [MSFT-9c1b94d3d1c9](data/guidance/traces/MSFT-9c1b94d3d1c9.json), [MSFT-a224d163f564](data/guidance/traces/MSFT-a224d163f564.json), [MSFT-ad61b7bd330b](data/guidance/traces/MSFT-ad61b7bd330b.json), [MSFT-b2805cdd4c71](data/guidance/traces/MSFT-b2805cdd4c71.json), [MSFT-b44ce4512f41](data/guidance/traces/MSFT-b44ce4512f41.json), [MSFT-b97c71ad0746](data/guidance/traces/MSFT-b97c71ad0746.json), [MSFT-beceabcd3bbc](data/guidance/traces/MSFT-beceabcd3bbc.json), [MSFT-d77c96d12d75](data/guidance/traces/MSFT-d77c96d12d75.json), [MSFT-da1d7354f38b](data/guidance/traces/MSFT-da1d7354f38b.json), [MSFT-df4e56fd215b](data/guidance/traces/MSFT-df4e56fd215b.json), [MSFT-e3a5e0a6c5bb](data/guidance/traces/MSFT-e3a5e0a6c5bb.json), [MSFT-e3ee40321b25](data/guidance/traces/MSFT-e3ee40321b25.json), [MSFT-e40fa67e8d26](data/guidance/traces/MSFT-e40fa67e8d26.json), [MSFT-e54bafe78c59](data/guidance/traces/MSFT-e54bafe78c59.json), [MSFT-e982cb5221a5](data/guidance/traces/MSFT-e982cb5221a5.json), [MSFT-ec24a3ec280a](data/guidance/traces/MSFT-ec24a3ec280a.json), [MSFT-ed716bad49cb](data/guidance/traces/MSFT-ed716bad49cb.json), [MSFT-f4267384617f](data/guidance/traces/MSFT-f4267384617f.json), [MSFT-f9842abbda9f](data/guidance/traces/MSFT-f9842abbda9f.json)

### ORCL

[ORCL-24d58f8791fd](data/guidance/traces/ORCL-24d58f8791fd.json), [ORCL-24febaa33152](data/guidance/traces/ORCL-24febaa33152.json), [ORCL-25b9bf3b816e](data/guidance/traces/ORCL-25b9bf3b816e.json), [ORCL-28de66785419](data/guidance/traces/ORCL-28de66785419.json), [ORCL-290ea6235bd1](data/guidance/traces/ORCL-290ea6235bd1.json), [ORCL-2c3647a613cc](data/guidance/traces/ORCL-2c3647a613cc.json), [ORCL-40941c832f82](data/guidance/traces/ORCL-40941c832f82.json), [ORCL-40f2e441e781](data/guidance/traces/ORCL-40f2e441e781.json), [ORCL-590117a041e3](data/guidance/traces/ORCL-590117a041e3.json), [ORCL-74c9d6d8951b](data/guidance/traces/ORCL-74c9d6d8951b.json), [ORCL-79edcbe4a6e1](data/guidance/traces/ORCL-79edcbe4a6e1.json), [ORCL-7dae20ae62d0](data/guidance/traces/ORCL-7dae20ae62d0.json), [ORCL-7e9fdb45f82e](data/guidance/traces/ORCL-7e9fdb45f82e.json), [ORCL-8145d33c902e](data/guidance/traces/ORCL-8145d33c902e.json), [ORCL-832555bfd3eb](data/guidance/traces/ORCL-832555bfd3eb.json), [ORCL-975305fbfff9](data/guidance/traces/ORCL-975305fbfff9.json), [ORCL-ac0ada9c7a0f](data/guidance/traces/ORCL-ac0ada9c7a0f.json), [ORCL-b9687fa1e665](data/guidance/traces/ORCL-b9687fa1e665.json), [ORCL-ba66de696e44](data/guidance/traces/ORCL-ba66de696e44.json), [ORCL-ebce6ed178da](data/guidance/traces/ORCL-ebce6ed178da.json), [ORCL-edff150ac60b](data/guidance/traces/ORCL-edff150ac60b.json), [ORCL-f0ff0fb2e20e](data/guidance/traces/ORCL-f0ff0fb2e20e.json)

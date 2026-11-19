# Verification diagnosis

All six misses failed only the XBRL comparison-series check. The filed outlook was genuine in each case. None required a change to a gold label, a financial definition or a tolerance. The labels measure detection and fields. They do not certify a comparable actual.

| Frozen test ID | Filing and forecast | Diagnosis and disposition |
|---|---|---|
| gold-b640bd85b5 | AMZN 2025-02-07, FY25 cash capex up | Correct abstention. MD&A distinguishes net purchases from gross purchases. No explicit reconciliation to the forecast. |
| gold-8b1565ec4c | AMZN 2026-02-05, FY26 about $200B | Correct abstention. The release says investment across Amazon. Its FCF reconciliation uses purchases net of proceeds. The quote gives no choice between the two. |
| gold-e662cc2339 | AMZN 2026-10-29, FY26 about $220B | Correct abstention. The same release shows both gross purchases and net purchases for FCF. |
| gold-8deeb3de40 | AMZN 2026-10-30, FY27 cash capex up | Correct abstention. No bridge from the outlook to gross versus net purchases. |
| gold-7725c52104 | GOOGL 2025-10-30, FY25 exceeds FY24 | Correct abstention. Purchases and leases both appear in MD&A. The saved text lacks the explicit cash reconciliation used for Alphabet. |
| gold-240e4f75c3 | ORCL 2026-09-11, FY27 above FY26 | Verifier missed an explicit definition. The same paragraph opens with “Capital Expenditures: Cash used for capital expenditures”. Accept this issuer-specific cash definition. FY27 ends in May. |

[Verbatim passages and SEC document links](gold/test.json)

| Additional pending passage | Diagnosis and disposition |
|---|---|
| META-5c77beb491c0 | Extractor mixed the 2024 dollar clause with a second 2025 outlook. End the numeric clause at “and continue to expect”. Preserve the entire evidence quote. |
| META-4b7d6ad43db5 | $30-33 billion parses correctly, but no year in the sentence. Keep pending. |
| META-75e8b40989f8 | Two ranges and two years followed by “respectively”. Single-target schema cannot represent this as one claim. Abstain. |
| AMZN-06bd97cc84bf | Historical spending plus an outlook for components. Rules abstain. The model direction has no verified annual period or series. |
| MSFT-03b5d8fb0a8b | Liquidity sufficiency statement. No annual spending forecast. Rules abstain. |

**Original frozen result**: precision 13/13, recall 13/13, dollar bounds 9/9, annual period 13/13, all checks 7/13 (53.8%, n=13).

**Post-fix diagnostic re-run (not a new held-out result)**: precision 13/13, recall 13/13, dollar bounds 9/9, annual period 13/13, all checks 8/13 (61.5%, n=13). Rules only, run once on the frozen passages with hash-checked original filing text. The original [test results](test_results.json) remain the selection evidence.

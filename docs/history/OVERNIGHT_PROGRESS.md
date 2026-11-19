# Overnight progress

## State at start

Main began at 86d960d. The later-year test has 24 passages, 13 certain positives. Rules detected 13/13 with precision 100% (n=13) and recall 100% (n=13). Local Qwen 1.5B detected 5/13 with precision 71.4% (n=7) and recall 38.5% (n=13). Seven of 13 rules positives passed every check (53.8%, n=13). The 7B load timed out before dev scoring. Rules won the pre-registered selection.

The ledger was empty. All 156 candidate passages were pending, including 53 from Meta. No annual comparison qualified. Two rejected local drafts left the quarterly summary empty. The existing cached inventory contains 159 filing texts across five issuers. Sources: [frozen evaluation](../../eval/test_results.json), [initial report](https://github.com/davidgold00/capex-tracker-ai/blob/86d960d/GUIDANCE_PROGRESS.md).

## Claim inventory

The 156 passages resolve to 143 review items (MSFT 48, GOOGL 13, AMZN 20, META 40, ORCL 22). Of these, 38 have a proposed annual target and a positive kind (MSFT 0, GOOGL 5, AMZN 12, META 19, ORCL 2). The other 105 are unresolved review items, including abstentions and invalid responses. An inventory count is not a count of usable forecasts.

Thirteen pairs of Meta passages share the same claim. Their releases and periodic reports were filed on adjacent dates. Exact filing-date grouping alone would double-count them. The index uses an earnings release's stated results period and the periodic report's SEC submissions report date. It joins only an unambiguous pair from the same issuer, with the release filed on the same day or one calendar day earlier. Each document keeps its actual filing date, accession, link and quote. Missing targets and unknown definitions remain separate. See [claim inventory](../../data/guidance/claims.json).

## Corroboration

[ADR 005](../decisions/ADR-005-corroboration-approval.md) was committed at bb06a8e before application. The 143 review items produced 13 auto-corroborated claims, all Meta, zero dual-extractor or manual approvals, and 130 pending. Each approval has two independently verified SEC accessions, one release and one periodic report. The ledger records the evidence IDs and basis.

## Frozen human audit sample

Seed 20261119. The approved stratum contains only 13 items, so all were included. Sampled 17 of the 130 pending items to reach 30. Both agreement estimates are Not measured (n=0 completed verdicts). Generating the sample again refuses to overwrite any answers.

# Interview walkthrough

## Two minutes

**Point to make.** Testing a simple extractor first changed which parts of the workflow actually needed a model.

- Start with the filed question: how did actual spending compare with the first forecast that met the evidence policy?
- Show Meta FY2024. Two filings gave a $30B to $37B range. Four matching lease-inclusive quarters totaled $39.225B.
- Read the portfolio finding. Meta raised 9/9 observed revision midpoints. The median gap was +15.5% (n=3 completed fiscal years). All 13 approved claims are Meta's.
- Name the limit. A first approved range can come after an earlier statement. The human audit has 30 sampled items and no verdicts yet.

**Show this.** [README findings and chart](../README.md) · [One claim, two filings](TRACE_EXAMPLE.md)

## Five minutes

**Point to make.** Detection, verification, approval and measurement are different decisions.

- On the frozen test, rules found 13/13 positives with 13/13 precision. Qwen 1.5B found 5/13 with 5/7 precision. Neither method's detection count was an approval count.
- Replay the Meta 10-K. The model recognized a spending range but returned dollar endpoints ten times too small and a missing year.
- Read the two clauses that establish the comparison definition. The two filings share a reporting event and issuer. Agreement shows consistency across documents.
- Inspect one of the 130 pending items. An unresolved period, a single filing or an ambiguous series can keep a genuine forecast out of the published finding.

**Show this.** `make demo` (also available in the VS Code task menu) · [Frozen test](../eval/test_results.json) · [Approval policy](decisions/ADR-005-corroboration-approval.md) · [Browser queue](../data/guidance/pending.csv)

## Fifteen minutes

**Point to make.** Each automated step has a bounded job, an evidence trail and a defined failure outcome.

- Follow XBRL tags through YTD subtraction and validation. Compare Oracle's annual-value-as-quarter warning with the derived quarter.
- Follow the filing route through source hash, rules, model retry, quote verification and corroboration. The original frozen result was 7/13 verified, and the separate post-fix diagnostic was 8/13.
- Compare the four small models by job. Qwen 1.5B grounded six of six dev rephrasing plans at 1.61 seconds per plan. Phi 3.5 matched rules on the four directional dev cases. Its suggestions stay in human review.
- Run the grounding demo. The planner fixes amounts, directions and periods. A model can select allowed phrasings. The same checker validates the deterministic fallback in CI.
- Finish with the development history. The evaluation was frozen before extraction, the policy was committed before approval and the financial tables were compared byte for byte.

**Show this.** [System and workflow diagrams](WORKFLOWS.md) · [Failure log](FAILURES.md) · [Bake-off](../eval/MODEL_BAKEOFF.md) · `make demo-guard` · [AI development](AI_DEVELOPMENT.md)

## Twelve interview questions

| Question | Answer grounded in the repository |
|---|---|
| 1. Why not use an API model? | The measured comparison is local-only. No hosted quality, cost or latency comparison exists. [DAVID: State your reason for choosing local inference.] |
| 2. Did the LLM earn its place? | Rules won extraction. Bounded rephrasing passed on six dev plans, but the template already produces a checked paragraph. Directional adjudication has no measured advantage over rules on four dev positives. No measured reviewer-time saving. |
| 3. Why trust auto-corroboration? | Each independently filed document must verify the identical annual claim against its own text. A conflicting claim blocks it. The two filings have one issuer and may repeat an error. |
| 4. What did the human audit show? | Agreement is Not measured. The frozen sample contains all 13 corroborated claims and 17 seeded pending items. The browser CSV has a verdict and note column. |
| 5. What breaks on 8 GB hardware? | The original 7B load timed out. The four smaller models completed one at a time. Memory observations and time per item are reported separately from accuracy. |
| 6. How would you scale to 50 companies? | Extend the issuer, fiscal calendar and definition mappings, sample new sectors for labels, then measure review load and throughput. The existing job fetches incremental text and throttles requests. A 50-company run is Not measured. |
| 7. What is the weakest part? | Generalization. Three completed company-years from one issuer and a small purposive test cannot establish forecasting reliability across five companies. Call-only guidance is outside coverage. |
| 8. How much did you write versus direct coding agents? | Git records co-authorship and ordered commits. It cannot measure personal authorship by line. [DAVID: Describe which designs, implementation work and reviews were yours.] |
| 9. What prevented hindsight tuning? | Later-year labels and the decision rule were frozen before extraction. The later verification diagnostic has its own label. The model bake-off ran only on dev. |
| 10. How do you know the actual uses the right dollars? | The statement must identify a comparison definition. Four distinct fiscal quarters must all contain that series. Meta uses capex plus lease principal. Missing quarters suppress the comparison. |
| 11. What happens when the writer invents a number? | The grounding checker rejects the sentence. A second failure or an unavailable local model selects the checked template. With no complete comparisons, it publishes Not measured. |
| 12. What happens after a new filing or a reviewer decision? | The weekly Action checks new filings, refreshes the ledger and updates a review issue. Browser decisions trigger a separate push path. An approval reproduces the source and checks the edited proposal. A new conflict can revoke an automatic approval. |

[Status and audit instructions](../GUIDANCE_PROGRESS.md) · [Model measurements](../eval/MODEL_BAKEOFF.md) · [Coding-agent history](AI_DEVELOPMENT.md)

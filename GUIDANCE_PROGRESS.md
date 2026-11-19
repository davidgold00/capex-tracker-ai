# Guidance status

Meta raised the midpoint in 9 of 9 revisions and actual spending was a median +15.5% versus the first approved midpoint (n=3 completed fiscal years), based on 13 auto-corroborated SEC claims (13/13 from Meta, pending human audit).

| Approved by corroboration | Dual extractor | Manual | Model-assisted pending | Other pending |
|---:|---:|---:|---:|---:|
| 13 | 0 | 0 | 16 | 114 |

**Coverage.** 159 SEC documents. 143 distinct review items, including 38 positive proposals with an annual target. Items / annual proposals: AMZN 20/12, GOOGL 13/5, META 40/19, MSFT 48/0, ORCL 22/2.

**Frozen test.** Rules precision 13/13 and recall 13/13. Qwen 1.5B precision 5/7 and recall 5/13. Fully verified rules predictions: 7/13 originally, 8/13 in the [post-fix diagnostic](eval/VERIFICATION_DIAGNOSIS.md).

Human audit pending (n=30 sampled). [Fill the audit CSV](data/guidance/audit_sample.csv) and [review pending decisions](data/guidance/pending.csv) in the GitHub web editor.

[Filing evidence](data/guidance/README.md) · [Dev bake-off](eval/MODEL_BAKEOFF.md) · [Initial run](docs/history/INITIAL_GUIDANCE_RUN.md) · [Overnight record](docs/history/OVERNIGHT_PROGRESS.md)

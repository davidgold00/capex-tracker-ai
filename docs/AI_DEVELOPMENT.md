# Building the tracker with coding agents

The project uses AI in two distinct places. Claude Code and Codex helped build and test repository changes. The running product uses local Ollama only for optional language work. A weekly update can run with model imports blocked. [Model-free integration test](../tests/test_guidance_update.py)

## What the history establishes

1. **Build the financial backbone in inspectable pieces.** The first commits separate the SEC client, tag stitching, YTD subtraction, metrics, validation, charts and publishing. Their Git trailers credit Claude as co-author. The data quirk fix follows the validation commit: Amazon's rolling annual periods and Oracle's mislabeled annual revenue were caught by checks against the actual filings. [Validation commit](https://github.com/davidgold00/capex-tracker-ai/commit/09557fc) · [Correction](https://github.com/davidgold00/capex-tracker-ai/commit/51eff3b)
2. **Specify an experiment before choosing a model.** The guidance history starts with an SEC document inventory, then freezes the gold split and selection rule before implementing the extractor. A later commit records both sets of predictions, followed by separate review, reporting, grounding and demo commits. The order makes it possible to distinguish the original test from later diagnostics. [Freeze](https://github.com/davidgold00/capex-tracker-ai/commit/9e35851) · [Selection](https://github.com/davidgold00/capex-tracker-ai/commit/9700844)
3. **Give the unattended Codex run an ordered backlog and stopping conditions.** The November 19 assignment required a finding with preserved financial bytes, separately labeled approval paths, an untouched frozen test, local-only inference, checks after each item and an inspectable morning summary. An isolated worktree protected existing local edits. The run diagnosed the six verification failures, identified adjacent-date release/report pairs and committed an approval rule before applying it. [Pre-registration](https://github.com/davidgold00/capex-tracker-ai/commit/bb06a8e) · [Application](https://github.com/davidgold00/capex-tracker-ai/commit/5822a34) · [Morning record](history/OVERNIGHT_PROGRESS.md)

Commit authorship is limited evidence for who wrote an individual line, designed a check or read a filing. [DAVID: Describe how you directed Claude Code and Codex, which prompts and constraints you supplied, and which parts you personally wrote or reviewed.]

## How the instructions became checks

| Instruction to the coding agent | Check or artifact | What happened |
|---|---|---|
| Keep financial definitions and validation tolerances fixed. | Rebuild four financial CSVs and the validation report, then compare bytes. | The live model-free rehearsal reproduced all five baseline files. [Run record](history/OVERNIGHT_PROGRESS.md) |
| Select the extractor using a pre-specified test. | Frozen hash, dated split and score denominators. | Rules won. A later verifier correction is explicitly marked diagnostic. [Diagnosis](../eval/VERIFICATION_DIAGNOSIS.md) |
| Retain failures and make the interview demo usable offline. | Request-keyed cassettes, per-attempt checks and a network-blocked demo test. | The demo replays a tenfold dollar error, including the retry. [Demo tests](../tests/test_guidance_demo.py) |
| Keep publication model-free. | CI entry point imports rules and the approval ledger. A test blocks model imports. | A completed comparison and a deterministic summary can be published without a local server. [Weekly workflow](../.github/workflows/update.yml) |
| Keep the SEC identity private. | Ignored local environment, repository secret, nested header stripping, all-file scan and outgoing Git identity checks. | The push gate checks each outgoing snapshot. [Gate](../scripts/check_push_privacy.py) |
| Make each step independently reviewable. | Ruff, full tests, offline demos and a model-free update-path check before each item commit and push. | The historical test, the diagnostic, the dev bake-off and pending human audit have separate artifacts. [Run record](history/OVERNIGHT_PROGRESS.md) |

The coding instructions also reserve personal commentary for the author and forbid loosening tolerances to pass a build. [Repository instructions](../CLAUDE.md)

## Where judgment is still needed

The 13 corroborated observations all come from Meta. The evidence establishes agreement between two filings from that issuer. A human still needs to inspect the quotes, the comparison definition and unresolved rows. The four-case directional dev result gives no measured improvement over rules. [Audit sample](../data/guidance/audit_sample.csv) · [Directional evaluation](../eval/DIRECTIONAL.md)

[DAVID: Identify one decision you made personally, what alternative you considered, and what evidence changed or confirmed your judgment.]

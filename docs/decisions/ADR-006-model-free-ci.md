# ADR 006. Run the weekly job without a model

**Context.** New SEC filings arrive on different dates, while local model weights and the ignored SEC identity live outside Git.

**Decision.** Fetch submissions and only new filing text. Run rules, verification and the ledger, render approved findings and synchronize the review issue. Read the SEC identity from the repository secret.

**Alternatives.** Run inference on a hosted runner or leave extraction to a local operator. Neither is required by the selected extractor.

**Consequences.** GitHub can refresh numbers and apply browser decisions. A human approval still requires reproduction of the original filing text.

[Update workflow](../../.github/workflows/update.yml) · [Model-free update tests](../../tests/test_guidance_update.py)

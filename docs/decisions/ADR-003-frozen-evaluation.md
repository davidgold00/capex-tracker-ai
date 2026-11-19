# ADR 003. Freeze the test and selection rule

**Context.** Forty-five purposively selected filing passages include historical spending, other metrics, directional and numeric forecasts.

**Decision.** Develop on 2023 and 2024. Freeze the 24 later passages and their SHA-256 before extractor development. Exclude uncertain labels. Select the model only if its recall is at least 0.10 above rules and precision is at least as high.

**Alternatives.** Choosing on the full labeled set or repeatedly evaluating modified prompts would consume the holdout.

**Consequences.** Rules and model can be compared once on later passages. The small, single-annotator sample limits generalization.

[Freeze commit](https://github.com/davidgold00/capex-tracker-ai/commit/9e35851) · [Scoring protocol](../history/INITIAL_GUIDANCE_RUN.md)

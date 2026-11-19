# ADR 008. Evaluate separate jobs on 8 GB

**Context.** The older 7B load timed out before a dev response. Four smaller local models finished the new dev benchmark.

**Decision.** Limit live calls to about 4B parameters. Run one model at a time and unload between jobs. Choose Qwen 1.5B for rephrasing and evaluate Phi 3.5 as an optional directional reviewer.

**Alternatives.** A larger local model exceeded the observed load budget. Hosted performance was not measured.

**Consequences.** Qwen 1.5B grounded 6/6 dev plans at 1.61 seconds per plan. Phi matched rules on four directional cases and also routed a numeric revision in dev. Its output remains pending.

[Model measurements](../../eval/MODEL_BAKEOFF.md) · [Directional results](../../eval/DIRECTIONAL.md)

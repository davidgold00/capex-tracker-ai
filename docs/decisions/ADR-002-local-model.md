# ADR 002. Keep model inference local

**Context.** The project has a recorded local extraction and drafting path. The weekly job runs in GitHub Actions.

**Decision.** Use a loopback-only Ollama endpoint, reject remote models and redirects, and strip HTTP metadata from records.

**Alternatives.** A hosted API could be evaluated separately. Its quality, cost and latency are Not measured here.

**Consequences.** Local execution limits model size and makes offline replay possible. [DAVID: Confirm the personal reason for choosing local inference over a hosted API.]

[Local provider](../../src/capex_tracker/guidance/provider.py) · [Original run](../history/INITIAL_GUIDANCE_RUN.md)

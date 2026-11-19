# ADR 009. Record and replay local model calls

**Context.** Recorded outputs can disagree with a filing even when the response matches the JSON schema.

**Decision.** Key each cassette by the full prompt, schema, model and generation settings. Retain responses, failed attempts and transport failures. Replay an exact request offline.

**Alternatives.** Rerunning live inference for every demo would require installed weights and could produce a different answer.

**Consequences.** The demo can reproduce a tenfold unit error and the bake-off can replay decisions without opening a network connection. A new prompt requires a new recording.

[Provider](../../src/capex_tracker/guidance/provider.py) · [Demo](../../src/capex_tracker/guidance/demo.py)

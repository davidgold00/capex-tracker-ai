# ADR 007. Publish a checked template when rephrasing fails

**Context.** The first two recorded draft attempts combined the quarterly and annual comparisons into an unsupported sentence.

**Decision.** Plan each fact and its direction in code. Permit a local rephrasing with one retry. Publish the labeled template when inference is absent or fails and the template passes the same checker.

**Alternatives.** Leave the section blank or accept free-form prose. The original implementation withheld both rejected attempts.

**Consequences.** The weekly paragraph can be published without inference. Allowed wording is deliberately narrow. Missing complete comparisons are reported as Not measured.

[Original rejected attempts](../../data/guidance/draft.json) · [Grounding checks](../../src/capex_tracker/guidance/ground.py)

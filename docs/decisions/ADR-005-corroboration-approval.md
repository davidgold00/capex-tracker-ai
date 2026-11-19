# ADR 005. Corroborated annual guidance

Registered before policy application on November 19, 2026. [Input inventory](../../data/guidance/claims.json) was committed at 17b0ddd. The old ledger approved zero passages.

**Decision.** Approve one claim as `auto-corroborated` only when a positive rules proposal in each of two distinct SEC accessions passes all six checks, including its own verbatim quote and document-specific comparison definition. Require matching company, event date, fiscal year, USD bounds or direction and spending definition. Require an 8-K earnings exhibit and a 10-Q or 10-K, a shared identified results period, and distinct source URLs and cleaned document hashes. They are two filings by one issuer, not independent witnesses to the economic outcome.

**Dates.** Release and periodic filing dates differ by one day for the 13 paired observations. Use the release date only for the unambiguous same-results-period pair defined in the [inventory method](../history/OVERNIGHT_PROGRESS.md). Preserve both filing dates. No cross-quarter matching.

**Veto.** A different proposed value, direction or definition for that company, event date and fiscal year blocks automatic approval, even when that competing queue entry fails a check. A fully verified dissent from the other extractor also blocks automation. Review existing automatic decisions again when evidence changes. A human rejection or an unapplied edit precludes automatic approval. Keep recorded human decisions and an audit history. Single-source dual-extractor agreement remains eligible separately as `auto-dual-match` when both verified final proposals agree. Label the basis on the published row. Model assistance alone never approves.

**Alternatives and consequence.** Manual review alone and verified dual extraction both produced an empty ledger in the [starting state](../history/OVERNIGHT_PROGRESS.md). Cross-filing agreement increases coverage while retaining the original evidence checks. Shared issuer language can repeat the same mistake. Report issuer concentration and leave human audit results unmeasured until reviewed.

# ADR 001. Use XBRL for financial actuals

**Context.** The same cash-flow measure can move between tags. Quarterly filings often report cumulative six- and nine-month totals.

**Decision.** Use SEC USD duration facts, configured tags and fiscal-year subtraction. Keep the accession and source tags on every derived value.

**Alternatives.** Extract tables with a model or transcribe them manually. Neither alternative was benchmarked here.

**Consequences.** Actuals can be rebuilt and checked against annual totals. Tag errors and restatements still need explicit handling.

[Quarter derivation](../../src/capex_tracker/quarters.py) · [Validation report](../../data/processed/validation_report.md)

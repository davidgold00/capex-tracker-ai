# ADR 004. Select rules for extraction

**Context.** The frozen selection rule compared positive detection and separately reported verification of proposed fields.

**Decision.** Use rules as the primary extractor. They recovered 13/13 positives at 13/13 precision. The local model recovered 5/13 positives at 5/7 precision.

**Alternatives.** Making the model primary required the pre-registered advantage. It missed the threshold.

**Consequences.** The weekly workflow can extract without inference. A positive detection still needs an annual target, spending definition and review before publication.

[Frozen results](../../eval/test_results.json) · [Verification diagnosis](../../eval/VERIFICATION_DIAGNOSIS.md)

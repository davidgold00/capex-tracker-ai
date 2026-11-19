from capex_tracker.guidance.adjudicate import Verdict, eligible


def test_assistance_needs_literal_evidence_and_annual_confident_direction():
    text = "We expect capital expenditures to increase in 2025."
    v = Verdict(quote=text, year=2025, confidence=0.95, direction="up", company_wide=True)
    assert eligible(v, text)
    for changes in (
        {"quote": text.replace("2025", "2026")},
        {"year": None},
        {"direction": "down"},
        {"company_wide": False},
        {"confidence": 0.5},
    ):
        assert not eligible(v.model_copy(update=changes), text)

from capex_tracker.guidance.extract import attach, rules, verify
from capex_tracker.guidance.sources import clean, windows


def test_finance_lease_forecast_and_unit_verification():
    passage = "We expect 2025 capital expenditures of $12 to $14 billion."
    definition = "Capital expenditures, including principal payments on finance leases"
    source = definition + ".\n" + passage
    row = dict(
        company="META",
        filed="2025-01-02",
        accession="0000000001-25-000001",
        url="https://www.sec.gov/Archives/edgar/data/1/example.htm",
        form="8-K",
    )
    p = rules(passage)
    g = attach(row, passage, p, ("capex_lease_adjusted", definition, "Lease principal included"))
    assert all(verify(g, source).values())
    assert not verify(g, source.replace("billion", "million"))["verbatim_quote"]
    bad = p.model_copy(update={"high_usd": 14_000_000})
    assert not verify(g.model_copy(update={"proposal": bad}), source)["dollars_and_units"]
    year = p.model_copy(update={"fiscal_year": 2026})
    assert not verify(g.model_copy(update={"proposal": year}), source)["annual_period"]


def test_historical_and_other_line_items_are_not_spending():
    assert rules("Capital expenditures were $10 billion.").guidance_kind == "none"
    assert rules("We expect revenue to reach $20 billion.").guidance_kind == "none"
    assert (
        rules(
            "We expect revenue of $12 billion and capital expenditures of $2 billion in 2025."
        ).low_usd
        == 2_000_000_000
    )


def test_cleaner_preserves_inline_text_and_discards_hidden_tags():
    text = clean(
        "<div>We expect capital <b>expenditures</b> of $1 billion."
        "<ix:hidden>junk</ix:hidden></div>",
        "8-K",
    )
    assert windows(text) == ["We expect capital expenditures of $1 billion."]


def test_numeric_target_excludes_separate_forward_outlook():
    text = (
        "We expect capital expenditures of $38 billion to $40 billion in 2024 "
        "and continue to expect significant capital expenditures growth in 2025."
    )
    p = rules(text)
    assert (p.fiscal_year, p.low_usd, p.high_usd) == (2024, 38_000_000_000, 40_000_000_000)


def test_oracle_cash_definition_requires_explicit_evidence():
    from capex_tracker.guidance.extract import definition

    note = "Capital Expenditures: Cash used for capital expenditures"
    assert definition("ORCL", note + " increased in the quarter.")[:2] == ("capex", note)
    assert definition("ORCL", "Capital expenditures increased.")[:2] == ("unresolved", "")

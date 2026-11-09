from __future__ import annotations

from datetime import date

from capex_tracker.config import Metric
from capex_tracker.facts import (
    dedupe_facts,
    normalize_sign,
    parse_concept,
    rank_coverage,
    select_metric,
)
from conftest import make_fact

FORMS = ["10-Q", "10-K"]
TOLERANCE = 0.005


def test_parse_keeps_usd_durations_from_periodic_forms(load_fixture):
    facts = parse_concept(load_fixture("companyfacts_basic.json"), "Capex", FORMS)
    assert [(f.start, f.end, f.value) for f in facts] == [
        (date(2024, 1, 1), date(2024, 3, 31), 10.0),
        (date(2024, 1, 1), date(2024, 6, 30), 25.0),
    ]


def test_parse_unknown_concept_returns_nothing(load_fixture):
    assert parse_concept(load_fixture("companyfacts_basic.json"), "Nope", FORMS) == []


def test_dedup_keeps_most_recently_filed_restatement():
    original = make_fact("2024-01-01", "2024-03-31", 10.0, filed="2024-05-01", accession="a")
    restated = make_fact("2024-01-01", "2024-03-31", 12.0, filed="2025-05-01", accession="b")
    assert dedupe_facts([restated, original]) == [restated]
    assert dedupe_facts([original, restated]) == [restated]


def test_dedup_breaks_filing_date_ties_on_accession():
    low = make_fact("2024-01-01", "2024-03-31", 10.0, filed="2024-05-01", accession="0001-a")
    high = make_fact("2024-01-01", "2024-03-31", 11.0, filed="2024-05-01", accession="0001-b")
    assert dedupe_facts([high, low]) == [high]


def test_dedup_treats_different_periods_and_concepts_separately():
    facts = [
        make_fact("2024-01-01", "2024-03-31", 1.0, concept="A"),
        make_fact("2024-01-01", "2024-03-31", 2.0, concept="B"),
        make_fact("2024-01-01", "2024-06-30", 3.0, concept="A"),
    ]
    assert len(dedupe_facts(facts)) == 3


def test_sign_normalization_makes_outflows_positive():
    facts, flipped = normalize_sign(
        [make_fact("2024-01-01", "2024-03-31", -5.0), make_fact("2024-04-01", "2024-06-30", 6.0)],
        "outflow",
    )
    assert [f.value for f in facts] == [5.0, 6.0]
    assert flipped == 1


def test_sign_normalization_leaves_other_metrics_alone():
    facts, flipped = normalize_sign([make_fact("2024-01-01", "2024-03-31", -5.0)], "as_reported")
    assert facts[0].value == -5.0
    assert flipped == 0


def test_rank_prefers_most_recent_coverage_over_config_order():
    facts_by_tag = {
        "First": [make_fact("2020-01-01", "2020-03-31", 1.0, concept="First")],
        "Second": [make_fact("2024-01-01", "2024-03-31", 1.0, concept="Second")],
    }
    assert [c.concept for c in rank_coverage(facts_by_tag, ["First", "Second"])] == [
        "Second",
        "First",
    ]


def test_rank_breaks_recency_ties_on_completeness_then_config_order():
    one = make_fact("2024-01-01", "2024-03-31", 1.0, concept="Sparse")
    two = make_fact("2024-01-01", "2024-03-31", 1.0, concept="Full")
    extra = make_fact("2023-01-01", "2023-03-31", 1.0, concept="Full")
    ranked = rank_coverage({"Sparse": [one], "Full": [two, extra]}, ["Sparse", "Full"])
    assert [c.concept for c in ranked] == ["Full", "Sparse"]
    ranked = rank_coverage({"B": [one], "A": [two]}, ["A", "B"])
    assert [c.concept for c in ranked] == ["A", "B"]


def test_select_metric_stitches_a_tag_switch_and_records_sources(load_fixture):
    metric = Metric(tags=["NewTag", "OldTag"], sign="as_reported")
    selection = select_metric(
        load_fixture("companyfacts_tag_switch.json"), "capex", metric, FORMS, TOLERANCE
    )
    assert selection.primary == "NewTag"
    by_end = {f.end: f.concept for f in selection.facts}
    assert by_end[date(2022, 3, 31)] == "OldTag"
    assert by_end[date(2024, 3, 31)] == "NewTag"
    assert selection.periods_used == {"NewTag": 2, "OldTag": 2}


def test_select_metric_prefers_the_active_tag_even_when_listed_last(load_fixture):
    metric = Metric(tags=["OldTag", "NewTag"], sign="as_reported")
    selection = select_metric(
        load_fixture("companyfacts_tag_switch.json"), "capex", metric, FORMS, TOLERANCE
    )
    assert selection.primary == "NewTag"


def test_select_metric_counts_overlap_disagreements(load_fixture):
    metric = Metric(tags=["NewTag", "OldTag"], sign="as_reported")
    selection = select_metric(
        load_fixture("companyfacts_tag_switch.json"), "capex", metric, FORMS, TOLERANCE
    )
    assert selection.overlap_periods == {"OldTag": 1}
    assert selection.overlap_mismatches == {"OldTag": 1}


def test_select_metric_with_no_matching_tags_is_empty(load_fixture):
    metric = Metric(tags=["Nothing"], sign="as_reported")
    selection = select_metric(
        load_fixture("companyfacts_basic.json"), "capex", metric, FORMS, TOLERANCE
    )
    assert selection.facts == []
    assert selection.primary is None

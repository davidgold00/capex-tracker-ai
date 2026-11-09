from __future__ import annotations

from datetime import date, timedelta

import pytest

from capex_tracker.config import Durations
from capex_tracker.quarters import (
    Duration,
    calendar_quarter,
    classify_duration,
    derive_quarters,
    display_quarter,
    midpoint,
)
from conftest import make_fact

START = date(2024, 1, 1)


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (84, None),
        (85, Duration.QUARTER),
        (100, Duration.QUARTER),
        (101, None),
        (174, None),
        (175, Duration.SIX_MONTHS),
        (190, Duration.SIX_MONTHS),
        (191, None),
        (264, None),
        (265, Duration.NINE_MONTHS),
        (280, Duration.NINE_MONTHS),
        (281, None),
        (354, None),
        (355, Duration.YEAR),
        (375, Duration.YEAR),
        (376, None),
    ],
)
def test_duration_tolerance_boundaries(days: int, expected: Duration | None, bands: Durations):
    assert classify_duration(START, START + timedelta(days=days), bands) == expected


def december_year(q1=10.0, h1=25.0, nine=45.0, annual=70.0):
    return [
        make_fact("2024-01-01", "2024-03-31", q1, filed="2024-05-01", accession="q1"),
        make_fact("2024-01-01", "2024-06-30", h1, filed="2024-08-01", accession="q2"),
        make_fact("2024-01-01", "2024-09-30", nine, filed="2024-11-01", accession="q3"),
        make_fact(
            "2024-01-01", "2024-12-31", annual, filed="2025-02-01", accession="k", form="10-K"
        ),
    ]


def test_ytd_differencing_derives_q2_q3_q4(bands: Durations):
    result = derive_quarters(december_year(), bands)
    assert [q.value for q in result.quarters] == [10.0, 15.0, 20.0, 25.0]
    assert [q.derived for q in result.quarters] == [False, True, True, True]
    assert [q.fiscal_quarter for q in result.quarters] == [1, 2, 3, 4]
    assert result.quarters[3].accession == "k"
    assert result.quarters[3].form == "10-K"
    assert result.quarters[1].period_start == date(2024, 4, 1)
    assert [a.value for a in result.annuals] == [70.0]


def test_direct_three_month_value_is_preferred_and_cross_checked(bands: Durations):
    facts = [*december_year(), make_fact("2024-04-01", "2024-06-30", 15.5, accession="direct")]
    q2 = derive_quarters(facts, bands).quarters[1]
    assert q2.value == 15.5
    assert q2.derived is False
    assert q2.cross_check_value == 15.0


def test_three_month_fact_equal_to_the_annual_figure_is_rejected(bands: Durations):
    facts = [*december_year(), make_fact("2024-10-01", "2024-12-31", 70.0, accession="mislabeled")]
    q4 = derive_quarters(facts, bands).quarters[3]
    assert q4.value == 25.0
    assert q4.derived is True
    assert q4.rejected_direct_value == 70.0


def test_ordinary_direct_value_is_not_rejected(bands: Durations):
    facts = [*december_year(), make_fact("2024-10-01", "2024-12-31", 26.0, accession="direct")]
    q4 = derive_quarters(facts, bands).quarters[3]
    assert q4.value == 26.0
    assert q4.rejected_direct_value is None


def test_latest_year_with_only_q1_reported_is_placed(bands: Durations):
    facts = [
        *december_year(),
        make_fact("2025-01-01", "2025-03-31", 30.0, filed="2025-05-01", accession="next"),
    ]
    result = derive_quarters(facts, bands)
    last = result.quarters[-1]
    assert (last.fiscal_label, last.calendar_quarter, last.value) == ("FY2025 Q1", "2025Q1", 30.0)
    assert result.unplaced == []


def test_incomplete_current_year_derives_available_quarters(bands: Durations):
    result = derive_quarters(december_year()[:2], bands)
    assert [q.value for q in result.quarters] == [10.0, 15.0]
    assert result.annuals == []


def test_missing_q1_leaves_a_gap_instead_of_guessing(bands: Durations):
    result = derive_quarters(december_year()[1:3], bands)
    assert [q.fiscal_quarter for q in result.quarters] == [3]
    assert [(g.fiscal_quarter, g.period_end) for g in result.gaps] == [(2, date(2024, 6, 30))]


def test_q4_falls_back_to_summed_quarters_without_a_nine_month_fact(bands: Durations):
    facts = [
        make_fact("2024-01-01", "2024-03-31", 10.0),
        make_fact("2024-04-01", "2024-06-30", 15.0),
        make_fact("2024-01-01", "2024-06-30", 25.0),
        make_fact("2024-07-01", "2024-09-30", 20.0),
        make_fact("2024-01-01", "2024-12-31", 70.0, form="10-K"),
    ]
    result = derive_quarters(facts, bands)
    assert [q.value for q in result.quarters] == [10.0, 15.0, 20.0, 25.0]
    assert result.quarters[3].derived is True


def test_trailing_twelve_month_facts_are_not_fiscal_years(bands: Durations):
    facts = [
        *december_year(),
        make_fact("2023-10-01", "2024-09-30", 60.0, filed="2024-11-01", accession="ttm"),
        make_fact("2023-07-01", "2024-06-30", 55.0, filed="2024-08-01", accession="ttm2"),
    ]
    result = derive_quarters(facts, bands)
    assert [q.value for q in result.quarters] == [10.0, 15.0, 20.0, 25.0]
    assert [(a.fiscal_year, a.value) for a in result.annuals] == [(2024, 70.0)]
    assert result.gaps == []


def test_microsoft_june_year_end_maps_to_calendar_quarters(bands: Durations):
    facts = [
        make_fact("2024-07-01", "2024-09-30", 10.0),
        make_fact("2024-07-01", "2024-12-31", 25.0),
        make_fact("2024-07-01", "2025-03-31", 45.0),
        make_fact("2024-07-01", "2025-06-30", 70.0, form="10-K"),
    ]
    quarters = derive_quarters(facts, bands).quarters
    assert [q.fiscal_label for q in quarters] == [
        "FY2025 Q1",
        "FY2025 Q2",
        "FY2025 Q3",
        "FY2025 Q4",
    ]
    assert [q.calendar_quarter for q in quarters] == ["2024Q3", "2024Q4", "2025Q1", "2025Q2"]


def test_nvidia_late_january_year_end_maps_to_calendar_quarters(bands: Durations):
    facts = [
        make_fact("2024-01-29", "2024-04-28", 10.0),
        make_fact("2024-01-29", "2024-07-28", 25.0),
        make_fact("2024-01-29", "2024-10-27", 45.0),
        make_fact("2024-01-29", "2025-01-26", 70.0, form="10-K"),
    ]
    quarters = derive_quarters(facts, bands).quarters
    assert [q.fiscal_label for q in quarters] == [
        "FY2025 Q1",
        "FY2025 Q2",
        "FY2025 Q3",
        "FY2025 Q4",
    ]
    assert [q.calendar_quarter for q in quarters] == ["2024Q1", "2024Q2", "2024Q3", "2024Q4"]


def test_fiscal_year_label_without_a_10k_uses_year_of_expected_end(bands: Durations):
    quarters = derive_quarters(
        [
            make_fact("2025-01-27", "2025-04-27", 10.0),
            make_fact("2025-01-27", "2025-07-27", 25.0),
        ],
        bands,
    ).quarters
    assert quarters[0].fiscal_label == "FY2026 Q1"


def test_oracle_may_year_end_quarter_maps_by_midpoint():
    assert calendar_quarter(date(2025, 6, 1), date(2025, 8, 31)) == "2025Q3"
    assert calendar_quarter(date(2025, 12, 1), date(2026, 2, 28)) == "2026Q1"


def test_midpoint_and_display():
    assert midpoint(date(2024, 1, 1), date(2024, 1, 31)) == date(2024, 1, 16)
    assert display_quarter("2026Q3") == "Q3 2026"


def test_derived_quarter_records_every_tag_used(bands: Durations):
    facts = [
        make_fact("2024-01-01", "2024-03-31", 10.0, concept="OldTag"),
        make_fact("2024-01-01", "2024-06-30", 25.0, concept="NewTag"),
    ]
    assert derive_quarters(facts, bands).quarters[1].source_tag == "NewTag|OldTag"

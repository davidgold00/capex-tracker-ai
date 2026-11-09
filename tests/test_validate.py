from __future__ import annotations

from datetime import date

from capex_tracker.config import Durations
from capex_tracker.quarters import Derivation, derive_quarters
from capex_tracker.validate import (
    Level,
    ValidationResult,
    check_annual_sums,
    check_cross,
    check_gaps,
    check_negative,
    check_qoq,
    check_unique_calendar_quarters,
    render_report,
)
from conftest import make_fact

START = date(2020, 1, 1)
TOLERANCE = 0.005


def direct_year(q1: float, q2: float, q3: float, q4: float, annual: float, year: int = 2024):
    """A year where all four quarters are reported directly, so the sum is a real test."""
    return [
        make_fact(f"{year}-01-01", f"{year}-03-31", q1),
        make_fact(f"{year}-04-01", f"{year}-06-30", q2),
        make_fact(f"{year}-07-01", f"{year}-09-30", q3),
        make_fact(f"{year}-10-01", f"{year}-12-31", q4),
        make_fact(f"{year}-01-01", f"{year}-06-30", q1 + q2),
        make_fact(f"{year}-01-01", f"{year}-09-30", q1 + q2 + q3),
        make_fact(f"{year}-01-01", f"{year}-12-31", annual, form="10-K", accession="annual"),
    ]


def sums(derivation: Derivation, required: bool = True):
    return check_annual_sums("AAA", "capex", derivation, TOLERANCE, START, required)


def test_annual_sum_passes_on_good_data(bands: Durations):
    issues, passed = sums(derive_quarters(direct_year(10, 20, 30, 40, 100), bands))
    assert issues == []
    assert passed == 1


def test_annual_sum_allows_differences_within_tolerance(bands: Durations):
    issues, passed = sums(derive_quarters(direct_year(10, 20, 30, 40, 100.4), bands))
    assert issues == []
    assert passed == 1


def test_annual_sum_fails_on_bad_data_with_readable_diff(bands: Durations):
    issues, passed = sums(derive_quarters(direct_year(10, 20, 30, 40, 110), bands))
    assert passed == 0
    assert [issue.level for issue in issues] == [Level.FAIL]
    assert "FY2024" in issues[0].message
    assert "10-K says" in issues[0].message
    assert "Annual accession annual" in issues[0].message


def test_annual_sum_fails_when_quarters_cannot_be_derived(bands: Durations):
    facts = [make_fact("2024-01-01", "2024-12-31", 100, form="10-K")]
    issues, _ = sums(derive_quarters(facts, bands))
    assert [issue.level for issue in issues] == [Level.FAIL]
    assert "cannot be verified" in issues[0].message


def test_optional_metric_with_annual_only_data_is_skipped(bands: Durations):
    facts = [make_fact("2024-01-01", "2024-12-31", 100, form="10-K")]
    issues, passed = sums(derive_quarters(facts, bands), required=False)
    assert issues == []
    assert passed == 0


def test_annual_sum_ignores_years_before_the_window(bands: Durations):
    derivation = derive_quarters(direct_year(10, 20, 30, 40, 999, year=2010), bands)
    issues, _ = sums(derivation)
    assert issues == []


def test_negative_derived_capex_is_reported_with_its_inputs(bands: Durations):
    facts = [
        make_fact("2024-01-01", "2024-03-31", 30),
        make_fact("2024-01-01", "2024-06-30", 20),
    ]
    quarters = derive_quarters(facts, bands).quarters
    issues = check_negative("AAA", "capex", quarters, Level.FAIL)
    assert [issue.level for issue in issues] == [Level.FAIL]
    assert "2024-06-30" in issues[0].message


def test_positive_capex_has_no_negative_issues(bands: Durations):
    quarters = derive_quarters(direct_year(10, 20, 30, 40, 100), bands).quarters
    assert check_negative("AAA", "capex", quarters, Level.FAIL) == []


def test_large_qoq_moves_warn_but_do_not_fail(bands: Durations):
    quarters = derive_quarters(direct_year(10, 20, 21, 22, 73), bands).quarters
    issues = check_qoq("AAA", "capex", quarters, 0.60)
    assert [issue.level for issue in issues] == [Level.WARN]
    assert "+100%" in issues[0].message


def test_moves_just_under_the_threshold_do_not_warn(bands: Durations):
    quarters = derive_quarters(direct_year(10, 15.9, 15.9, 15.9, 57.7), bands).quarters
    assert check_qoq("AAA", "capex", quarters, 0.60) == []


def test_cross_check_warns_when_direct_and_derived_disagree(bands: Durations):
    facts = [
        make_fact("2024-01-01", "2024-03-31", 10),
        make_fact("2024-01-01", "2024-06-30", 25),
        make_fact("2024-04-01", "2024-06-30", 18),
    ]
    quarters = derive_quarters(facts, bands).quarters
    issues = check_cross("AAA", "capex", quarters, TOLERANCE)
    assert [issue.level for issue in issues] == [Level.WARN]


def test_calendar_collisions_fail(bands: Durations):
    quarters = derive_quarters(direct_year(10, 20, 30, 40, 100), bands).quarters
    issues = check_unique_calendar_quarters("AAA", "capex", [quarters[0], quarters[0]])
    assert [issue.level for issue in issues] == [Level.FAIL]


def test_gap_in_covered_range_warns(bands: Durations):
    quarters = derive_quarters(direct_year(10, 20, 30, 40, 100), bands).quarters
    issues = check_gaps("AAA", "capex", [quarters[0], quarters[2]])
    assert len(issues) == 1
    assert "Q2 2024" in issues[0].message


def test_report_states_status_and_has_no_timestamp():
    report = render_report(ValidationResult(issues=[], annual_checks_passed=3))
    assert "**Status: PASS**" in report
    assert render_report(ValidationResult(issues=[], annual_checks_passed=3)) == report

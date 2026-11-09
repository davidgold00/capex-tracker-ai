from __future__ import annotations

import math

import pandas as pd
import pytest

from capex_tracker.metrics import (
    build_aggregate,
    build_wide,
    capex_intensity,
    computed_rows,
    latest_complete,
    lease_adjusted_capex,
    trailing_twelve_months,
    year_over_year,
)

SPENDERS = ["AAA", "BBB"]
RECEIVERS = ["NNN"]


def quarters(values: list[float | None], start: str = "2023Q1") -> pd.Series:
    index = pd.period_range(start, periods=len(values), freq="Q")
    return pd.Series(values, index=index, dtype="float64")


def test_ttm_sums_four_consecutive_quarters():
    result = trailing_twelve_months(quarters([1, 2, 3, 4, 5]))
    assert result.isna().tolist() == [True, True, True, False, False]
    assert result.iloc[3] == 10
    assert result.iloc[4] == 14


def test_ttm_is_blank_across_a_missing_quarter_in_the_index():
    series = quarters([1, 2, 3, 4, 5, 6]).drop(pd.Period("2023Q3", freq="Q"))
    result = trailing_twelve_months(series)
    assert result.isna().all()


def test_ttm_is_blank_across_an_explicit_nan():
    result = trailing_twelve_months(quarters([1, None, 3, 4, 5, 6, 7]))
    assert result.iloc[:5].isna().all()
    assert result.iloc[5] == 18


def test_yoy_compares_same_quarter_a_year_earlier():
    result = year_over_year(quarters([10, 20, 30, 40, 15]))
    assert result.iloc[:4].isna().all()
    assert result.iloc[4] == pytest.approx(0.5)


def test_yoy_uses_calendar_position_not_row_position():
    series = quarters([10, 20, 30, 40, 50, 60]).drop(pd.Period("2023Q2", freq="Q"))
    result = year_over_year(series)
    assert math.isnan(result.loc[pd.Period("2024Q2", freq="Q")])


def test_intensity_is_undefined_for_non_positive_ocf():
    result = capex_intensity(pd.Series([5.0, 5.0, 5.0]), pd.Series([10.0, 0.0, -3.0]))
    assert result.iloc[0] == 0.5
    assert result.iloc[1:].isna().all()


def test_lease_adjustment_never_treats_unknown_as_zero():
    result = lease_adjusted_capex(pd.Series([5.0, 5.0]), pd.Series([1.0, None]))
    assert result.iloc[0] == 6.0
    assert math.isnan(result.iloc[1])


def base_row(
    metric: str, value: float, ticker: str = "AAA", quarter: str = "2024Q1", derived=False
):
    return {
        "company": ticker,
        "ticker": ticker,
        "calendar_quarter": quarter,
        "fiscal_label": "FY2024 Q1",
        "period_start": "2024-01-01",
        "period_end": "2024-03-31",
        "metric": metric,
        "value_usd": value,
        "source_tag": "Tag",
        "accession": "a",
        "form": "10-Q",
        "filed": "2024-05-01",
        "derived": derived,
    }


def test_computed_rows_are_labelled_and_inherit_derived_flag():
    rows = computed_rows([base_row("capex", 4.0, derived=True), base_row("ocf", 10.0)])
    assert [(r["metric"], r["value_usd"], r["source_tag"], r["derived"]) for r in rows] == [
        ("fcf", 6.0, "computed", True)
    ]


def test_computed_rows_add_lease_versions_only_when_lease_is_known():
    rows = computed_rows(
        [
            base_row("capex", 4.0),
            base_row("ocf", 10.0),
            base_row("finance_lease_principal", 1.0),
        ]
    )
    by_metric = {r["metric"]: r["value_usd"] for r in rows}
    assert by_metric == {"fcf": 6.0, "capex_lease_adjusted": 5.0, "fcf_lease_adjusted": 5.0}


def wide_table(partial_last: bool = False) -> pd.DataFrame:
    """Two spenders and a receiver over six quarters; BBB optionally misses the last."""
    rows = []
    for index, period in enumerate(pd.period_range("2023Q1", periods=6, freq="Q")):
        label = str(period)
        for ticker in SPENDERS:
            if partial_last and ticker == "BBB" and index == 5:
                continue
            rows.append(
                {
                    "company": ticker,
                    "ticker": ticker,
                    "calendar_quarter": label,
                    "capex": 10.0 + index,
                    "ocf": 20.0,
                    "revenue": None,
                }
            )
        rows.append(
            {
                "company": "NNN",
                "ticker": "NNN",
                "calendar_quarter": label,
                "capex": None,
                "ocf": None,
                "revenue": 100.0,
            }
        )
    return pd.DataFrame(rows)


def test_aggregate_totals_and_ttm_on_complete_data():
    result = build_aggregate(wide_table(), SPENDERS, RECEIVERS)
    last = result.iloc[-1]
    assert not last["partial"]
    assert last["total_capex"] == 30.0
    assert last["total_ocf"] == 40.0
    assert last["ttm_capex"] == 2 * (12 + 13 + 14 + 15)
    assert last["ttm_capex_intensity"] == pytest.approx(108 / 160)
    assert last["receiver_ttm_revenue"] == 400.0


def test_partial_latest_quarter_is_flagged_and_excluded():
    result = build_aggregate(wide_table(partial_last=True), SPENDERS, RECEIVERS)
    last = result.iloc[-1]
    assert last["partial"]
    assert last["companies_reported"] == 1
    assert last["missing_companies"] == "BBB"
    assert math.isnan(last["total_capex"])
    assert math.isnan(last["ttm_capex"])


def test_latest_complete_skips_the_partial_quarter():
    result = build_aggregate(wide_table(partial_last=True), SPENDERS, RECEIVERS)
    assert latest_complete(result)["calendar_quarter"] == "2024Q1"


def test_latest_complete_is_none_without_a_full_ttm_window():
    short = wide_table()
    short = short[short["calendar_quarter"].isin(["2023Q1", "2023Q2"])]
    assert latest_complete(build_aggregate(short, SPENDERS, RECEIVERS)) is None


def test_build_wide_computes_company_columns():
    rows = []
    for index, period in enumerate(pd.period_range("2023Q1", periods=5, freq="Q")):
        label = str(period)
        for metric, value in [("capex", 10.0 + index), ("ocf", 20.0), ("revenue", 50.0)]:
            rows.append(base_row(metric, value, quarter=label))
    wide = build_wide(pd.DataFrame(rows))
    last = wide.iloc[-1]
    assert last["capex_intensity"] == pytest.approx(14 / 20)
    assert last["capex_pct_revenue"] == pytest.approx(14 / 50)
    assert last["capex_yoy"] == pytest.approx(0.4)
    assert last["ttm_capex"] == 11 + 12 + 13 + 14
    assert last["ttm_capex_intensity"] == pytest.approx(50 / 80)
    assert math.isnan(last["capex_lease_adjusted"])

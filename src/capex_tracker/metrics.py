"""Company and aggregate metrics, built from discrete quarters."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd

from capex_tracker.config import Company
from capex_tracker.facts import TagSelection
from capex_tracker.quarters import Derivation

LONG_COLUMNS = [
    "company",
    "ticker",
    "calendar_quarter",
    "fiscal_label",
    "period_start",
    "period_end",
    "metric",
    "value_usd",
    "source_tag",
    "accession",
    "form",
    "filed",
    "derived",
]
USD_METRICS = [
    "capex",
    "ocf",
    "revenue",
    "finance_lease_principal",
    "fcf",
    "capex_lease_adjusted",
    "fcf_lease_adjusted",
]
TTM_METRICS = ["capex", "ocf", "revenue", "fcf", "capex_lease_adjusted", "fcf_lease_adjusted"]
RATIO_COLUMNS = [
    "capex_intensity",
    "capex_intensity_lease_adjusted",
    "capex_pct_revenue",
    "capex_yoy",
    "ttm_capex_intensity",
    "ttm_capex_intensity_lease_adjusted",
]
AGGREGATE_RATIO_COLUMNS = ["capex_intensity", "ttm_capex_intensity", "ttm_capex_yoy"]
QUARTERS_PER_YEAR = 4


@dataclass(frozen=True)
class CompanyData:
    """Everything derived for one company, keyed by metric name."""

    company: Company
    selections: dict[str, TagSelection]
    derivations: dict[str, Derivation]


def free_cash_flow(ocf: pd.Series, capex: pd.Series) -> pd.Series:
    return ocf - capex


def capex_intensity(capex: pd.Series, ocf: pd.Series) -> pd.Series:
    """Capex as a share of OCF. Undefined when OCF is zero or negative."""
    return (capex / ocf).where(ocf > 0)


def lease_adjusted_capex(capex: pd.Series, lease_principal: pd.Series) -> pd.Series:
    """Capex plus finance lease principal. Blank where the lease figure is unknown."""
    return capex + lease_principal


def _consecutive(series: pd.Series) -> pd.Series:
    """Reindex onto every quarter in range, so gaps cannot be mistaken for neighbors."""
    full = pd.period_range(series.index.min(), series.index.max(), freq="Q")
    return series.reindex(full)


def trailing_twelve_months(series: pd.Series) -> pd.Series:
    """Sum of four consecutive quarters. Blank if any of the four is missing."""
    full = _consecutive(series)
    return (
        full.rolling(QUARTERS_PER_YEAR, min_periods=QUARTERS_PER_YEAR).sum().reindex(series.index)
    )


def year_over_year(series: pd.Series) -> pd.Series:
    """Growth against the same calendar quarter one year earlier."""
    full = _consecutive(series)
    return (full / full.shift(QUARTERS_PER_YEAR) - 1).reindex(series.index)


def base_rows(data: CompanyData, data_start: date) -> list[dict[str, Any]]:
    """Long-format rows for each reported or YTD-derived quarter."""
    rows = []
    for metric, derivation in data.derivations.items():
        for quarter in derivation.quarters:
            if quarter.period_end < data_start:
                continue
            rows.append(
                {
                    "company": data.company.name,
                    "ticker": data.company.ticker,
                    "calendar_quarter": quarter.calendar_quarter,
                    "fiscal_label": quarter.fiscal_label,
                    "period_start": quarter.period_start.isoformat(),
                    "period_end": quarter.period_end.isoformat(),
                    "metric": metric,
                    "value_usd": quarter.value,
                    "source_tag": quarter.source_tag,
                    "accession": quarter.accession,
                    "form": quarter.form,
                    "filed": quarter.filed.isoformat(),
                    "derived": quarter.derived,
                }
            )
    return rows


def _computed_row(metric: str, value: float, inputs: Sequence[dict[str, Any]]) -> dict[str, Any]:
    first = inputs[0]
    return {
        **first,
        "metric": metric,
        "value_usd": value,
        "source_tag": "computed",
        "accession": "",
        "form": "",
        "filed": max(row["filed"] for row in inputs),
        "derived": any(row["derived"] for row in inputs),
    }


def computed_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add FCF and lease-adjusted figures. A quarter missing an input gets no row."""
    grouped: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["ticker"], row["calendar_quarter"]), {})[row["metric"]] = row
    computed = []
    for metrics in grouped.values():
        capex = metrics.get("capex")
        ocf = metrics.get("ocf")
        lease = metrics.get("finance_lease_principal")
        if capex and ocf:
            computed.append(
                _computed_row("fcf", ocf["value_usd"] - capex["value_usd"], [ocf, capex])
            )
        if capex and lease:
            computed.append(
                _computed_row(
                    "capex_lease_adjusted",
                    capex["value_usd"] + lease["value_usd"],
                    [capex, lease],
                )
            )
        if capex and ocf and lease:
            computed.append(
                _computed_row(
                    "fcf_lease_adjusted",
                    ocf["value_usd"] - capex["value_usd"] - lease["value_usd"],
                    [ocf, capex, lease],
                )
            )
    return computed


def build_long(companies: Sequence[CompanyData], data_start: date) -> pd.DataFrame:
    """The tidy long table. Holds USD values only, so ratios live in the wide table."""
    rows = [row for data in companies for row in base_rows(data, data.company.start_at(data_start))]
    rows.extend(computed_rows(rows))
    frame = pd.DataFrame(rows, columns=LONG_COLUMNS)
    return frame.sort_values(["ticker", "period_end", "metric"], ignore_index=True)


def _company_metrics(group: pd.DataFrame) -> pd.DataFrame:
    """Add ratios, YoY growth and TTM columns for one company."""
    frame = group.copy()
    frame.index = pd.PeriodIndex(frame["calendar_quarter"], freq="Q")
    frame = frame.sort_index()
    frame["capex_intensity"] = capex_intensity(frame["capex"], frame["ocf"])
    frame["capex_intensity_lease_adjusted"] = capex_intensity(
        frame["capex_lease_adjusted"], frame["ocf"]
    )
    frame["capex_pct_revenue"] = frame["capex"] / frame["revenue"]
    frame["capex_yoy"] = year_over_year(frame["capex"])
    for metric in TTM_METRICS:
        frame[f"ttm_{metric}"] = trailing_twelve_months(frame[metric])
    frame["ttm_capex_intensity"] = capex_intensity(frame["ttm_capex"], frame["ttm_ocf"])
    frame["ttm_capex_intensity_lease_adjusted"] = capex_intensity(
        frame["ttm_capex_lease_adjusted"], frame["ttm_ocf"]
    )
    return frame.reset_index(drop=True)


def build_wide(long: pd.DataFrame) -> pd.DataFrame:
    """One row per company and calendar quarter."""
    keys = ["company", "ticker", "calendar_quarter"]
    values = long.pivot(index=keys, columns="metric", values="value_usd")
    values = values.reindex(columns=USD_METRICS).reset_index()
    labels = (
        long.sort_values(["ticker", "calendar_quarter", "metric"])
        .groupby(keys, as_index=False)[["fiscal_label", "period_start", "period_end"]]
        .first()
    )
    merged = values.merge(labels, on=keys, validate="one_to_one")
    companies = [_company_metrics(group) for _, group in merged.groupby("ticker", sort=True)]
    ordered = [
        *keys,
        "fiscal_label",
        "period_start",
        "period_end",
        *USD_METRICS,
        *RATIO_COLUMNS,
        *[f"ttm_{metric}" for metric in TTM_METRICS],
    ]
    wide = pd.concat(companies, ignore_index=True)[ordered]
    return wide.sort_values(["ticker", "calendar_quarter"], ignore_index=True)


def build_aggregate(
    wide: pd.DataFrame, spender_tickers: Sequence[str], receiver_tickers: Sequence[str]
) -> pd.DataFrame:
    """Aggregate metrics by calendar quarter.

    A quarter is complete only once every spender has reported capex and OCF.
    Incomplete quarters keep their row, flagged partial, with blank totals.
    """
    periods = pd.PeriodIndex(wide["calendar_quarter"], freq="Q")
    full = pd.period_range(periods.min(), periods.max(), freq="Q")
    spenders = wide[wide["ticker"].isin(spender_tickers)]
    reported = spenders[spenders["capex"].notna() & spenders["ocf"].notna()]

    rows = []
    for period in full:
        label = str(period)
        current = reported[reported["calendar_quarter"] == label]
        missing = sorted(set(spender_tickers) - set(current["ticker"]))
        complete = not missing
        capex = current["capex"].sum() if complete else float("nan")
        ocf = current["ocf"].sum() if complete else float("nan")
        rows.append(
            {
                "calendar_quarter": label,
                "partial": not complete,
                "companies_reported": len(current),
                "missing_companies": " ".join(missing),
                "total_capex": capex,
                "total_ocf": ocf,
            }
        )
    frame = pd.DataFrame(rows, index=full)
    frame["total_fcf"] = free_cash_flow(frame["total_ocf"], frame["total_capex"])
    frame["capex_intensity"] = capex_intensity(frame["total_capex"], frame["total_ocf"])
    for column in ("capex", "ocf", "fcf"):
        frame[f"ttm_{column}"] = trailing_twelve_months(frame[f"total_{column}"])
    frame["ttm_capex_intensity"] = capex_intensity(frame["ttm_capex"], frame["ttm_ocf"])
    frame["ttm_capex_yoy"] = year_over_year(frame["ttm_capex"])

    receivers = wide[wide["ticker"].isin(receiver_tickers)]
    revenue = receivers.groupby("calendar_quarter")["revenue"].sum(min_count=len(receiver_tickers))
    revenue.index = pd.PeriodIndex(revenue.index, freq="Q")
    frame["receiver_revenue"] = revenue.reindex(full)
    frame["receiver_ttm_revenue"] = trailing_twelve_months(frame["receiver_revenue"])
    return frame.reset_index(drop=True)


def latest_complete(aggregate: pd.DataFrame) -> pd.Series | None:
    """The newest complete quarter with a full TTM window, or None."""
    complete = aggregate[~aggregate["partial"] & aggregate["ttm_capex"].notna()]
    return complete.iloc[-1] if not complete.empty else None

"""Consistency checks that run on every build, and the report they produce."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import Enum
from itertools import pairwise

import pandas as pd

from capex_tracker.config import Config, Validation
from capex_tracker.metrics import CompanyData
from capex_tracker.quarters import Derivation, DiscreteQuarter, display_quarter


class Level(Enum):
    FAIL = "fail"
    WARN = "warn"


@dataclass(frozen=True)
class Issue:
    level: Level
    check: str
    ticker: str
    metric: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    issues: list[Issue]
    annual_checks_passed: int

    @property
    def failures(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.level is Level.FAIL]

    @property
    def warnings(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.level is Level.WARN]

    @property
    def passed(self) -> bool:
        return not self.failures


def _billions(value: float) -> str:
    return f"${value / 1e9:,.3f}B"


def check_annual_sums(
    ticker: str,
    metric: str,
    derivation: Derivation,
    tolerance: float,
    data_start: date,
    required: bool,
) -> tuple[list[Issue], int]:
    """Each fiscal year with a 10-K must equal the sum of its four quarters."""
    issues: list[Issue] = []
    passed = 0
    for annual in derivation.annuals:
        if annual.end < data_start:
            continue
        quarters = sorted(
            (q for q in derivation.quarters if q.fiscal_year == annual.fiscal_year),
            key=lambda q: q.fiscal_quarter,
        )
        if len(quarters) != 4:
            if required:
                found = [q.fiscal_quarter for q in quarters]
                issues.append(
                    Issue(
                        Level.FAIL,
                        "annual_sum",
                        ticker,
                        metric,
                        f"FY{annual.fiscal_year}: 10-K has an annual value but only quarters "
                        f"{found} could be derived, so the sum cannot be verified",
                    )
                )
            continue
        total = sum(q.value for q in quarters)
        difference = (total - annual.value) / abs(annual.value) if annual.value else 0.0
        if abs(difference) > tolerance:
            parts = ", ".join(f"Q{q.fiscal_quarter} {_billions(q.value)}" for q in quarters)
            issues.append(
                Issue(
                    Level.FAIL,
                    "annual_sum",
                    ticker,
                    metric,
                    f"FY{annual.fiscal_year}: quarters sum to {_billions(total)} but the 10-K says "
                    f"{_billions(annual.value)} ({difference:+.2%}; limit {tolerance:.1%}). "
                    f"{parts}. Annual accession {annual.accession}",
                )
            )
        else:
            passed += 1
    return issues, passed


def _in_window(derivation: Derivation, data_start: date) -> list[DiscreteQuarter]:
    return [q for q in derivation.quarters if q.period_end >= data_start]


def check_negative(
    ticker: str, metric: str, quarters: Sequence[DiscreteQuarter], level: Level
) -> list[Issue]:
    """A negative quarter of an outflow means YTD figures do not line up."""
    return [
        Issue(
            level,
            "negative_quarter",
            ticker,
            metric,
            f"{q.fiscal_label} ({q.period_start} to {q.period_end}) is "
            f"{_billions(q.value)}. Inputs: "
            + ", ".join(f"{f.start} to {f.end} = {_billions(f.value)}" for f in q.inputs),
        )
        for q in quarters
        if q.value < 0
    ]


def check_unique_calendar_quarters(
    ticker: str, metric: str, quarters: Sequence[DiscreteQuarter]
) -> list[Issue]:
    """Two fiscal quarters landing on one calendar quarter would double count."""
    counts = Counter(q.calendar_quarter for q in quarters)
    return [
        Issue(
            Level.FAIL,
            "calendar_collision",
            ticker,
            metric,
            f"{count} fiscal quarters map to {display_quarter(label)}",
        )
        for label, count in sorted(counts.items())
        if count > 1
    ]


def check_qoq(
    ticker: str, metric: str, quarters: Sequence[DiscreteQuarter], threshold: float
) -> list[Issue]:
    """Warn on large quarter-over-quarter swings, for a manual sanity check."""
    ordered = sorted(quarters, key=lambda q: q.period_end)
    issues = []
    for previous, current in pairwise(ordered):
        if previous.value <= 0:
            continue
        change = current.value / previous.value - 1
        if abs(change) > threshold:
            issues.append(
                Issue(
                    Level.WARN,
                    "qoq_move",
                    ticker,
                    metric,
                    f"{display_quarter(current.calendar_quarter)} ({current.fiscal_label}) moved "
                    f"{change:+.0%} QoQ: {_billions(previous.value)} to {_billions(current.value)}",
                )
            )
    return issues


def check_cross(
    ticker: str, metric: str, quarters: Sequence[DiscreteQuarter], tolerance: float
) -> list[Issue]:
    """Compare directly reported quarters against the YTD-derived figure."""
    issues = []
    for q in quarters:
        if q.rejected_direct_value is not None:
            issues.append(
                Issue(
                    Level.WARN,
                    "direct_rejected",
                    ticker,
                    metric,
                    f"{q.fiscal_label}: reported 3-month value "
                    f"{_billions(q.rejected_direct_value)} equals the full-year figure, so it "
                    f"was treated as a tagging error. Used YTD-derived {_billions(q.value)}",
                )
            )
        if q.cross_check_value is None or not q.value:
            continue
        difference = (q.cross_check_value - q.value) / abs(q.value)
        if abs(difference) > tolerance:
            issues.append(
                Issue(
                    Level.WARN,
                    "direct_vs_derived",
                    ticker,
                    metric,
                    f"{q.fiscal_label}: reported 3-month value {_billions(q.value)} vs "
                    f"YTD-derived {_billions(q.cross_check_value)} ({difference:+.2%})",
                )
            )
    return issues


def check_gaps(ticker: str, metric: str, quarters: Sequence[DiscreteQuarter]) -> list[Issue]:
    """Warn on missing calendar quarters, since a gap blanks four TTM values."""
    if not quarters:
        return []
    present = pd.PeriodIndex(sorted({q.calendar_quarter for q in quarters}), freq="Q")
    full = pd.period_range(present.min(), present.max(), freq="Q")
    return [
        Issue(
            Level.WARN,
            "missing_quarter",
            ticker,
            metric,
            f"{display_quarter(str(period))} is missing inside the covered range",
        )
        for period in full.difference(present)
    ]


def _check_selection(data: CompanyData, metric: str, required: bool) -> list[Issue]:
    ticker = data.company.ticker
    selection = data.selections[metric]
    issues = []
    if not selection.facts:
        issues.append(
            Issue(
                Level.FAIL if required else Level.WARN,
                "missing_metric",
                ticker,
                metric,
                "no facts found under any configured tag",
            )
        )
    if selection.flipped_signs:
        issues.append(
            Issue(
                Level.WARN,
                "sign_flip",
                ticker,
                metric,
                f"{selection.flipped_signs} facts were reported negative and flipped positive",
            )
        )
    for concept, count in sorted(selection.overlap_mismatches.items()):
        overlap = selection.overlap_periods[concept]
        issues.append(
            Issue(
                Level.WARN,
                "tag_disagreement",
                ticker,
                metric,
                f"{concept} disagrees with the higher-ranked tag on {count} of {overlap} "
                "shared periods",
            )
        )
    return issues


def run_checks(companies: Sequence[CompanyData], config: Config) -> ValidationResult:
    """Run every check across all companies and metrics."""
    settings: Validation = config.validation
    issues: list[Issue] = []
    annual_passed = 0
    for data in companies:
        ticker = data.company.ticker
        start = data.company.start_at(config.data_start)
        for metric, derivation in data.derivations.items():
            required = config.metrics[metric].required
            issues.extend(_check_selection(data, metric, required))
            year_issues, passed = check_annual_sums(
                ticker,
                metric,
                derivation,
                settings.annual_sum_tolerance,
                start,
                required,
            )
            issues.extend(year_issues)
            annual_passed += passed
            quarters = _in_window(derivation, start)
            issues.extend(check_unique_calendar_quarters(ticker, metric, quarters))
            if metric == "capex":
                issues.extend(check_negative(ticker, metric, quarters, Level.FAIL))
                issues.extend(check_qoq(ticker, metric, quarters, settings.qoq_warn_threshold))
            elif config.metrics[metric].sign == "outflow":
                issues.extend(check_negative(ticker, metric, quarters, Level.WARN))
            issues.extend(check_cross(ticker, metric, quarters, settings.cross_check_tolerance))
            issues.extend(check_gaps(ticker, metric, quarters))
    issues.sort(key=lambda i: (i.level.value, i.check, i.ticker, i.metric, i.message))
    return ValidationResult(issues=issues, annual_checks_passed=annual_passed)


def _escape(text: str) -> str:
    return text.replace("|", "\\|")


def _issue_table(issues: Sequence[Issue]) -> list[str]:
    lines = ["| Check | Company | Metric | Detail |", "|---|---|---|---|"]
    for issue in issues:
        lines.append(
            f"| {issue.check} | {issue.ticker} | {issue.metric} | {_escape(issue.message)} |"
        )
    return lines


def render_report(result: ValidationResult) -> str:
    """Markdown report. Contains no timestamps, so it only changes when results change."""
    status = "PASS" if result.passed else "FAIL"
    lines = [
        "# Validation report",
        "",
        f"**Status: {status}**",
        "",
        f"- Fiscal years where four quarters sum to the 10-K: {result.annual_checks_passed}",
        f"- Failures: {len(result.failures)}",
        f"- Warnings: {len(result.warnings)}",
        "",
        "## Failures",
        "",
    ]
    lines.extend(_issue_table(result.failures) if result.failures else ["None."])
    lines.extend(["", "## Warnings", ""])
    lines.extend(_issue_table(result.warnings) if result.warnings else ["None."])
    return "\n".join(lines) + "\n"

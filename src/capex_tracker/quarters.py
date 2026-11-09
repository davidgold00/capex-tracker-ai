"""Turn year-to-date XBRL facts into discrete quarters on a calendar timeline.

Facts are grouped into fiscal years by their shared start date, because every
year-to-date figure in a fiscal year begins on the first day of that year. The
"fp" field is never used: it describes the filing, not the period.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum

from capex_tracker.config import Durations
from capex_tracker.facts import Fact

# Filers occasionally shift a period boundary by a day between filings.
DATE_SLACK_DAYS = 3
# A 3-month fact this close to the full-year figure is a mislabeled annual value.
FULL_YEAR_MATCH = 0.001


class Duration(Enum):
    QUARTER = "quarter"
    SIX_MONTHS = "six_months"
    NINE_MONTHS = "nine_months"
    YEAR = "year"


def classify_duration(start: date, end: date, bands: Durations) -> Duration | None:
    """Classify a period by its length in days, or None if it fits no band."""
    days = (end - start).days
    for duration in Duration:
        band = getattr(bands, duration.value)
        if band.min_days <= days <= band.max_days:
            return duration
    return None


def midpoint(start: date, end: date) -> date:
    """The middle date of a period."""
    return start + (end - start) / 2


def calendar_quarter(start: date, end: date) -> str:
    """The calendar quarter containing the period midpoint, such as ``2025Q3``."""
    middle = midpoint(start, end)
    return f"{middle.year}Q{(middle.month - 1) // 3 + 1}"


def display_quarter(label: str) -> str:
    """Convert ``2025Q3`` to ``Q3 2025``."""
    year, quarter = label.split("Q")
    return f"Q{quarter} {year}"


@dataclass(frozen=True)
class DiscreteQuarter:
    """One fiscal quarter's value, reported directly or derived from YTD figures."""

    fiscal_year: int
    fiscal_quarter: int
    period_start: date
    period_end: date
    value: float
    source_tag: str
    accession: str
    form: str
    filed: date
    derived: bool
    inputs: tuple[Fact, ...]
    # Set when a directly reported value could also be derived, to compare the two.
    cross_check_value: float | None = None
    # Set when a reported 3-month value was discarded as a tagging error.
    rejected_direct_value: float | None = None

    @property
    def fiscal_label(self) -> str:
        return f"FY{self.fiscal_year} Q{self.fiscal_quarter}"

    @property
    def calendar_quarter(self) -> str:
        return calendar_quarter(self.period_start, self.period_end)


@dataclass(frozen=True)
class AnnualValue:
    """The full-year figure reported in a 10-K."""

    fiscal_year: int
    start: date
    end: date
    value: float
    accession: str


@dataclass(frozen=True)
class Gap:
    """A fiscal quarter that could not be derived, and why."""

    fiscal_year: int
    fiscal_quarter: int
    period_end: date | None
    reason: str


@dataclass(frozen=True)
class Derivation:
    quarters: list[DiscreteQuarter]
    annuals: list[AnnualValue]
    gaps: list[Gap]
    unplaced: list[Fact]


def _near(a: date, b: date) -> bool:
    return abs((a - b).days) <= DATE_SLACK_DAYS


def _newest(facts: Sequence[Fact]) -> Fact | None:
    return max(facts, key=lambda f: (f.filed, f.accession)) if facts else None


def _fiscal_years_only(by_duration: dict[Duration, list[Fact]]) -> list[Fact]:
    """Drop year-long facts that are not fiscal years.

    Amazon reports trailing-twelve-month figures in its 10-Qs. Those are a year
    long but start mid-year, so a year-long fact only counts if it comes from a
    10-K or begins on the same day as a six or nine month YTD fact.
    """
    ytd_starts = [
        fact.start
        for duration in (Duration.SIX_MONTHS, Duration.NINE_MONTHS)
        for fact in by_duration[duration]
    ]
    return [
        fact
        for fact in by_duration[Duration.YEAR]
        if fact.form.startswith("10-K") or any(_near(fact.start, start) for start in ytd_starts)
    ]


def _fiscal_year_anchors(by_duration: dict[Duration, list[Fact]]) -> list[date]:
    """Find the first day of each fiscal year.

    Any YTD fact marks one. A year with only Q1 reported so far has no YTD fact,
    so a 3-month fact that begins right after a full year ends also marks one.
    """
    candidates = {
        fact.start
        for duration in (Duration.SIX_MONTHS, Duration.NINE_MONTHS, Duration.YEAR)
        for fact in by_duration[duration]
    }
    year_ends = [fact.end for fact in by_duration[Duration.YEAR]]
    for fact in by_duration[Duration.QUARTER]:
        if any(_near(fact.start, end + timedelta(days=1)) for end in year_ends):
            candidates.add(fact.start)
    anchors: list[date] = []
    for candidate in sorted(candidates):
        if not anchors or (candidate - anchors[-1]).days > DATE_SLACK_DAYS:
            anchors.append(candidate)
    return anchors


def _derive_year(
    anchor: date, by_duration: dict[Duration, list[Fact]]
) -> tuple[list[DiscreteQuarter], AnnualValue | None, list[Gap], set[Fact]]:
    """Build up to four discrete quarters for the fiscal year starting at ``anchor``."""

    def ytd(duration: Duration) -> Fact | None:
        return _newest([f for f in by_duration[duration] if _near(f.start, anchor)])

    three_month = by_duration[Duration.QUARTER]
    first = ytd(Duration.QUARTER)
    year_fact = ytd(Duration.YEAR)
    cumulative: list[Fact | None] = [
        first,
        ytd(Duration.SIX_MONTHS),
        ytd(Duration.NINE_MONTHS),
        year_fact,
    ]
    fiscal_year = year_fact.end.year if year_fact else (anchor + timedelta(days=364)).year
    annual = None
    if year_fact is not None:
        annual = AnnualValue(
            fiscal_year, year_fact.start, year_fact.end, year_fact.value, year_fact.accession
        )

    results: list[DiscreteQuarter] = []
    gaps: list[Gap] = []
    used: set[Fact] = {fact for fact in cumulative if fact is not None}
    ends: list[date | None] = [fact.end if fact else None for fact in cumulative]
    discrete: list[float | None] = [None] * 4

    for index in range(4):
        number = index + 1
        direct = first
        expected_start = anchor
        if index > 0:
            expected_start = ends[index - 1] + timedelta(days=1) if ends[index - 1] else None
            direct = _find_direct(three_month, anchor, ends[index], expected_start)
        rejected_value = None
        if index > 0 and direct is not None and _equals_full_year(direct, year_fact):
            # Oracle's FY2018 to FY2022 data tags the annual figure as a 3-month period.
            rejected_value = direct.value
            direct = None
        if direct is not None and ends[index] is None:
            ends[index] = direct.end
        if ends[index] is None:
            continue

        total = cumulative[index]
        prior = _prior_cumulative(index, cumulative, discrete)
        derived_value = None
        if index > 0 and total is not None and prior is not None:
            derived_value = total.value - prior[0]

        if direct is not None:
            used.add(direct)
            discrete[index] = direct.value
            results.append(
                DiscreteQuarter(
                    fiscal_year=fiscal_year,
                    fiscal_quarter=number,
                    period_start=direct.start,
                    period_end=direct.end,
                    value=direct.value,
                    source_tag=direct.concept,
                    accession=direct.accession,
                    form=direct.form,
                    filed=direct.filed,
                    derived=False,
                    inputs=(direct,),
                    cross_check_value=derived_value,
                )
            )
        elif derived_value is not None and expected_start is not None:
            inputs = (total, *prior[1])
            discrete[index] = derived_value
            results.append(
                DiscreteQuarter(
                    fiscal_year=fiscal_year,
                    fiscal_quarter=number,
                    period_start=expected_start,
                    period_end=total.end,
                    value=derived_value,
                    source_tag="|".join(sorted({fact.concept for fact in inputs})),
                    accession=total.accession,
                    form=total.form,
                    filed=total.filed,
                    derived=True,
                    inputs=inputs,
                    rejected_direct_value=rejected_value,
                )
            )
        else:
            gaps.append(
                Gap(fiscal_year, number, ends[index], "missing the facts needed to derive it")
            )
    return results, annual, gaps, used


def _equals_full_year(direct: Fact, year_fact: Fact | None) -> bool:
    """True if a supposed 3-month figure is really the annual figure."""
    if year_fact is None or not year_fact.value:
        return False
    return abs(direct.value - year_fact.value) / abs(year_fact.value) <= FULL_YEAR_MATCH


def _find_direct(
    three_month: Sequence[Fact], anchor: date, end: date | None, expected_start: date | None
) -> Fact | None:
    """Find a directly reported 3-month fact for a Q2, Q3 or Q4 slot."""
    matches = [
        fact
        for fact in three_month
        if not _near(fact.start, anchor)
        and (end is None or _near(fact.end, end))
        and (expected_start is None or _near(fact.start, expected_start))
        and (end is not None or expected_start is not None)
    ]
    return _newest(matches)


def _prior_cumulative(
    index: int, cumulative: Sequence[Fact | None], discrete: Sequence[float | None]
) -> tuple[float, tuple[Fact, ...]] | None:
    """Year-to-date total before this slot, from a YTD fact or else summed quarters."""
    if index == 0:
        return None
    previous = cumulative[index - 1]
    if previous is not None:
        return previous.value, (previous,)
    earlier = discrete[:index]
    if all(value is not None for value in earlier):
        return sum(earlier), ()
    return None


def derive_quarters(facts: Sequence[Fact], bands: Durations) -> Derivation:
    """Derive discrete quarters from one metric's deduplicated, stitched facts."""
    by_duration: dict[Duration, list[Fact]] = {duration: [] for duration in Duration}
    for fact in facts:
        duration = classify_duration(fact.start, fact.end, bands)
        if duration is not None:
            by_duration[duration].append(fact)
    by_duration[Duration.YEAR] = _fiscal_years_only(by_duration)

    quarters: list[DiscreteQuarter] = []
    annuals: list[AnnualValue] = []
    gaps: list[Gap] = []
    used: set[Fact] = set()
    for anchor in _fiscal_year_anchors(by_duration):
        year_quarters, annual, year_gaps, year_used = _derive_year(anchor, by_duration)
        quarters.extend(year_quarters)
        gaps.extend(year_gaps)
        used |= year_used
        if annual is not None:
            annuals.append(annual)

    unplaced = [fact for fact in by_duration[Duration.QUARTER] if fact not in used]
    quarters.sort(key=lambda q: q.period_end)
    annuals.sort(key=lambda a: a.end)
    return Derivation(quarters=quarters, annuals=annuals, gaps=gaps, unplaced=unplaced)

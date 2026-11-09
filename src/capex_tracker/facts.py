"""Parse companyfacts JSON, deduplicate facts, and choose tags for each metric."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date
from typing import Any

from capex_tracker.config import Metric


@dataclass(frozen=True)
class Fact:
    """One USD duration value as reported in one filing."""

    concept: str
    start: date
    end: date
    value: float
    accession: str
    form: str
    filed: date


@dataclass(frozen=True)
class TagCoverage:
    """How well one tag covers a metric for one company."""

    concept: str
    config_rank: int
    periods: int
    first_end: date
    last_end: date


@dataclass(frozen=True)
class TagSelection:
    """The outcome of picking and stitching tags for one company and metric."""

    metric: str
    facts: list[Fact]
    coverage: list[TagCoverage]
    periods_used: dict[str, int]
    overlap_periods: dict[str, int]
    overlap_mismatches: dict[str, int]
    flipped_signs: int

    @property
    def primary(self) -> str | None:
        return self.coverage[0].concept if self.coverage else None


def parse_concept(companyfacts: dict[str, Any], concept: str, forms: Sequence[str]) -> list[Fact]:
    """Return the USD duration facts for ``concept``, limited to periodic report forms."""
    node = companyfacts.get("facts", {}).get("us-gaap", {}).get(concept)
    if node is None:
        return []
    allowed = set(forms)
    facts = []
    for raw in node.get("units", {}).get("USD", []):
        # Balance sheet style facts are instants with no start date.
        if "start" not in raw or raw.get("form") not in allowed:
            continue
        facts.append(
            Fact(
                concept=concept,
                start=date.fromisoformat(raw["start"]),
                end=date.fromisoformat(raw["end"]),
                value=float(raw["val"]),
                accession=raw["accn"],
                form=raw["form"],
                filed=date.fromisoformat(raw["filed"]),
            )
        )
    return facts


def dedupe_facts(facts: Iterable[Fact]) -> list[Fact]:
    """Keep one fact per (concept, start, end): the most recently filed.

    Later filings repeat earlier periods as comparatives, so the newest filing
    carries any restatement. Accession number breaks ties on the same filing date.
    """
    latest: dict[tuple[str, date, date], Fact] = {}
    for fact in facts:
        key = (fact.concept, fact.start, fact.end)
        current = latest.get(key)
        if current is None or (fact.filed, fact.accession) > (current.filed, current.accession):
            latest[key] = fact
    return sorted(latest.values(), key=lambda f: (f.end, f.start, f.concept))


def normalize_sign(facts: Iterable[Fact], sign: str) -> tuple[list[Fact], int]:
    """Store outflows as positive numbers. Returns the facts and how many were flipped."""
    if sign != "outflow":
        return list(facts), 0
    normalized = []
    flipped = 0
    for fact in facts:
        if fact.value < 0:
            flipped += 1
            fact = replace(fact, value=-fact.value)
        normalized.append(fact)
    return normalized, flipped


def rank_coverage(
    facts_by_tag: dict[str, list[Fact]], tag_order: Sequence[str]
) -> list[TagCoverage]:
    """Rank tags by latest period, then number of periods, then config order."""
    coverage = []
    for concept, facts in facts_by_tag.items():
        if facts:
            ends = [fact.end for fact in facts]
            coverage.append(
                TagCoverage(
                    concept=concept,
                    config_rank=tag_order.index(concept),
                    periods=len(facts),
                    first_end=min(ends),
                    last_end=max(ends),
                )
            )
    return sorted(coverage, key=lambda c: (-c.last_end.toordinal(), -c.periods, c.config_rank))


def stitch(
    ranked_tags: Sequence[str], facts_by_tag: dict[str, list[Fact]], tolerance: float
) -> tuple[list[Fact], dict[str, int], dict[str, int], dict[str, int]]:
    """Merge tags by period, with higher-ranked tags winning each period.

    Returns the stitched facts, periods supplied per tag, and for each lower-ranked
    tag how many of its periods overlap a winner and how many of those disagree.
    """
    chosen: dict[tuple[date, date], Fact] = {}
    used: dict[str, int] = defaultdict(int)
    overlaps: dict[str, int] = defaultdict(int)
    mismatches: dict[str, int] = defaultdict(int)
    for concept in ranked_tags:
        for fact in facts_by_tag[concept]:
            key = (fact.start, fact.end)
            winner = chosen.get(key)
            if winner is None:
                chosen[key] = fact
                used[concept] += 1
                continue
            overlaps[concept] += 1
            base = max(abs(winner.value), 1.0)
            if abs(fact.value - winner.value) / base > tolerance:
                mismatches[concept] += 1
    stitched = sorted(chosen.values(), key=lambda f: (f.end, f.start))
    return stitched, dict(used), dict(overlaps), dict(mismatches)


def select_metric(
    companyfacts: dict[str, Any],
    metric_name: str,
    metric: Metric,
    forms: Sequence[str],
    tolerance: float,
) -> TagSelection:
    """Parse, dedupe, sign-normalize and stitch every candidate tag for one metric."""
    facts_by_tag: dict[str, list[Fact]] = {}
    flipped = 0
    for concept in metric.tags:
        deduped = dedupe_facts(parse_concept(companyfacts, concept, forms))
        facts_by_tag[concept], count = normalize_sign(deduped, metric.sign)
        flipped += count
    coverage = rank_coverage(facts_by_tag, metric.tags)
    ranked = [item.concept for item in coverage]
    stitched, used, overlaps, mismatches = stitch(ranked, facts_by_tag, tolerance)
    return TagSelection(
        metric=metric_name,
        facts=stitched,
        coverage=coverage,
        periods_used=used,
        overlap_periods=overlaps,
        overlap_mismatches=mismatches,
        flipped_signs=flipped,
    )

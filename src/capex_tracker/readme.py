"""Marker-based README rendering. Only text between markers is ever replaced."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path

import pandas as pd

from capex_tracker.config import Config
from capex_tracker.metrics import latest_complete
from capex_tracker.quarters import display_quarter

CHARTS = [
    ("headline.png", "Aggregate hyperscaler TTM capex and operating cash flow"),
    ("capex_by_company.png", "TTM capex by company"),
    ("intensity_by_company.png", "TTM capex intensity by company"),
    ("capex_vs_nvidia.png", "Aggregate hyperscaler TTM capex and Nvidia TTM revenue"),
    ("lease_adjustment.png", "Reported and finance-lease-adjusted capex"),
]
NOTE_FILE = re.compile(r"^(\d{4})-Q([1-4])\.md$")
NO_NOTES = "Notes coming soon."


class MarkerError(RuntimeError):
    """A README marker pair is missing or malformed."""


def billions(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value) / 1e9:,.1f}B"


def percent(value: float) -> str:
    return "n/a" if pd.isna(value) else f"{value:.0%}"


def signed_percent(value: float) -> str:
    return "n/a" if pd.isna(value) else f"{value:+.0%}"


def replace_section(text: str, name: str, body: str) -> str:
    """Replace the content between one marker pair, leaving everything else alone."""
    start = f"<!-- {name}:START -->"
    end = f"<!-- {name}:END -->"
    if text.count(start) != 1 or text.count(end) != 1 or text.index(start) > text.index(end):
        raise MarkerError(f"README must contain exactly one {start} followed by one {end}")
    before = text[: text.index(start) + len(start)]
    after = text[text.index(end) :]
    return f"{before}\n{body.strip()}\n{after}"


def apply_sections(text: str, sections: Mapping[str, str]) -> str:
    for name, body in sections.items():
        text = replace_section(text, name, body)
    return text


def join_names(names: Sequence[str]) -> str:
    """Join as 'A, B and C'."""
    if len(names) < 2:
        return "".join(names)
    return f"{', '.join(names[:-1])} and {names[-1]}"


def _partial_note(aggregate: pd.DataFrame, latest: pd.Series, config: Config) -> str:
    later = aggregate[aggregate["calendar_quarter"] > latest["calendar_quarter"]]
    partial = later[later["partial"] & (later["companies_reported"] > 0)]
    if partial.empty:
        return ""
    row = partial.iloc[-1]
    total = len(config.spenders)
    return (
        f" {display_quarter(row['calendar_quarter'])} is partial "
        f"({row['companies_reported']} of {total} companies have reported) and is excluded."
    )


def render_headline(aggregate: pd.DataFrame, config: Config) -> str:
    latest = latest_complete(aggregate)
    if latest is None:
        return "Not enough complete quarters yet to compute the headline."
    names = join_names([company.name for company in config.spenders])
    sentence = (
        f"In the four quarters to {display_quarter(latest['calendar_quarter'])}, {names} spent "
        f"{billions(latest['ttm_capex'])} on capex, equal to "
        f"{percent(latest['ttm_capex_intensity'])} of their operating cash flow"
    )
    year_ago_period = str(pd.Period(latest["calendar_quarter"], freq="Q") - 4)
    year_ago = aggregate[aggregate["calendar_quarter"] == year_ago_period]
    if not year_ago.empty and pd.notna(year_ago.iloc[0]["ttm_capex_intensity"]):
        prior = year_ago.iloc[0]["ttm_capex_intensity"]
        now_rounded, prior_rounded = (
            round(latest["ttm_capex_intensity"] * 100),
            round(prior * 100),
        )
        if now_rounded == prior_rounded:
            sentence += f", unchanged from {percent(prior)} a year earlier"
        else:
            direction = "up" if now_rounded > prior_rounded else "down"
            sentence += f", {direction} from {percent(prior)} a year earlier"
    return f"**{sentence}.**{_partial_note(aggregate, latest, config)}"


def render_latest_table(wide: pd.DataFrame, aggregate: pd.DataFrame, config: Config) -> str:
    latest = latest_complete(aggregate)
    if latest is None:
        return "No complete quarter yet."
    label = latest["calendar_quarter"]
    rows = wide[wide["calendar_quarter"] == label].set_index("ticker")
    lines = [
        f"**Latest complete calendar quarter: {display_quarter(label)}**",
        "",
        "| Company | Capex | OCF | FCF | Capex intensity | YoY capex growth |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for company in config.spenders:
        row = rows.loc[company.ticker]
        lines.append(
            f"| {company.name} | {billions(row['capex'])} | {billions(row['ocf'])} | "
            f"{billions(row['fcf'])} | {percent(row['capex_intensity'])} | "
            f"{signed_percent(row['capex_yoy'])} |"
        )
    yoy = _total_capex_yoy(aggregate, label)
    lines.append(
        f"| **Total** | **{billions(latest['total_capex'])}** | "
        f"**{billions(latest['total_ocf'])}** | **{billions(latest['total_fcf'])}** | "
        f"**{percent(latest['capex_intensity'])}** | **{signed_percent(yoy)}** |"
    )
    return "\n".join(lines)


def _total_capex_yoy(aggregate: pd.DataFrame, label: str) -> float:
    prior_label = str(pd.Period(label, freq="Q") - 4)
    by_quarter = aggregate.set_index("calendar_quarter")["total_capex"]
    if prior_label not in by_quarter.index:
        return float("nan")
    return by_quarter[label] / by_quarter[prior_label] - 1


def render_charts(config: Config) -> str:
    return "\n\n".join(
        f"![{alt}]({(config.paths.charts_dir / name).as_posix()})" for name, alt in CHARTS
    )


def render_updated(long: pd.DataFrame, config: Config) -> str:
    """Dated from the newest filing, so the README changes only when data changes."""
    reported = long[long["accession"] != ""].sort_values(["filed", "accession", "ticker"])
    newest = reported.iloc[-1]
    company = config.company(newest["ticker"]).name
    return (
        f"Last updated: {newest['filed']}. Latest filing included: {company} {newest['form']}, "
        f"accession {newest['accession']}, filed {newest['filed']}."
    )


def latest_note(notes_dir: Path) -> Path | None:
    """The newest notes/YYYY-QN.md file, or None."""
    notes = []
    for path in notes_dir.glob("*.md"):
        match = NOTE_FILE.match(path.name)
        if match:
            notes.append((int(match.group(1)), int(match.group(2)), path))
    return max(notes)[2] if notes else None


def render_notes(notes_dir: Path) -> str:
    path = latest_note(notes_dir)
    return path.read_text(encoding="utf-8").strip() if path else NO_NOTES


def render_readme(
    text: str, long: pd.DataFrame, wide: pd.DataFrame, aggregate: pd.DataFrame, config: Config
) -> str:
    """Return ``text`` with every auto-generated section refreshed."""
    return apply_sections(
        text,
        {
            "HEADLINE": render_headline(aggregate, config),
            "TABLE": render_latest_table(wide, aggregate, config),
            "CHARTS": render_charts(config),
            "UPDATED": render_updated(long, config),
            "NOTES": render_notes(config.paths.notes_dir),
        },
    )

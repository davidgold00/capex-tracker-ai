from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from capex_tracker.config import Config
from capex_tracker.readme import (
    NO_NOTES,
    MarkerError,
    apply_sections,
    billions,
    join_names,
    latest_note,
    render_headline,
    render_notes,
    render_updated,
    replace_section,
)

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = """# Title

Hand written intro.

<!-- HEADLINE:START -->
old headline
<!-- HEADLINE:END -->

## My section

Do not touch this.

<!-- NOTES:START -->
old notes
<!-- NOTES:END -->

Hand written ending.
"""


def test_only_content_between_markers_changes():
    result = replace_section(TEMPLATE, "HEADLINE", "new headline")
    assert "new headline" in result
    assert "old headline" not in result
    assert result.replace("new headline", "old headline") == TEMPLATE


def test_hand_written_text_survives_every_section():
    result = apply_sections(TEMPLATE, {"HEADLINE": "A", "NOTES": "B"})
    for kept in ("Hand written intro.", "Do not touch this.", "Hand written ending."):
        assert kept in result
    assert "<!-- NOTES:END -->" in result


def test_rendering_twice_is_stable():
    once = apply_sections(TEMPLATE, {"HEADLINE": "A", "NOTES": "B"})
    assert apply_sections(once, {"HEADLINE": "A", "NOTES": "B"}) == once


def test_missing_marker_raises():
    with pytest.raises(MarkerError):
        replace_section("no markers here", "HEADLINE", "x")


def test_duplicate_marker_raises():
    with pytest.raises(MarkerError):
        replace_section(TEMPLATE + "<!-- HEADLINE:START -->", "HEADLINE", "x")


def test_reversed_markers_raise():
    text = "<!-- HEADLINE:END --> <!-- HEADLINE:START -->"
    with pytest.raises(MarkerError):
        replace_section(text, "HEADLINE", "x")


def test_billions_formats_negatives_with_the_sign_first():
    assert billions(-9_060_000_000) == "-$9.1B"
    assert billions(1_234_500_000_000) == "$1,234.5B"


def test_join_names():
    assert join_names(["A"]) == "A"
    assert join_names(["A", "B"]) == "A and B"
    assert join_names(["A", "B", "C"]) == "A, B and C"


def aggregate_frame(partial_last: bool) -> pd.DataFrame:
    rows = []
    for index, period in enumerate(pd.period_range("2024Q1", periods=6, freq="Q")):
        rows.append(
            {
                "calendar_quarter": str(period),
                "partial": False,
                "companies_reported": 5,
                "total_capex": 10e9,
                "total_ocf": 20e9,
                "ttm_capex": 100e9 + index * 10e9,
                "ttm_capex_intensity": 0.40 + index * 0.05,
            }
        )
    if partial_last:
        rows[-1].update(
            {
                "partial": True,
                "companies_reported": 4,
                "total_capex": float("nan"),
                "total_ocf": float("nan"),
                "ttm_capex": float("nan"),
                "ttm_capex_intensity": float("nan"),
            }
        )
    return pd.DataFrame(rows)


def test_headline_uses_latest_complete_quarter(config: Config):
    text = render_headline(aggregate_frame(partial_last=False), config)
    assert "In the four quarters to Q2 2025" in text
    assert "Microsoft, Alphabet, Amazon, Meta and Oracle" in text
    assert "$150.0B" in text
    assert "65%" in text
    assert "up from 45% a year earlier" in text


def test_headline_excludes_a_partial_quarter_and_says_so(config: Config):
    text = render_headline(aggregate_frame(partial_last=True), config)
    assert "In the four quarters to Q1 2025" in text
    assert "Q2 2025 is partial (4 of 5 companies have reported) and is excluded" in text


def test_headline_reports_a_decline(config: Config):
    frame = aggregate_frame(partial_last=False)
    frame["ttm_capex_intensity"] = list(reversed(frame["ttm_capex_intensity"]))
    assert "down from" in render_headline(frame, config)


def test_updated_line_uses_newest_filing_not_todays_date(config: Config):
    long = pd.DataFrame(
        [
            {"ticker": "MSFT", "accession": "a", "form": "10-Q", "filed": "2026-01-01"},
            {"ticker": "AMZN", "accession": "b", "form": "10-K", "filed": "2026-02-01"},
            {"ticker": "MSFT", "accession": "", "form": "", "filed": "2026-03-01"},
        ]
    )
    text = render_updated(long, config)
    assert "Last updated: 2026-02-01" in text
    assert "Amazon 10-K" in text


def test_notes_picks_newest_quarter_and_ignores_template(tmp_path: Path):
    (tmp_path / "TEMPLATE.md").write_text("template", encoding="utf-8")
    (tmp_path / "2025-Q4.md").write_text("older", encoding="utf-8")
    (tmp_path / "2026-Q1.md").write_text("newest", encoding="utf-8")
    assert latest_note(tmp_path).name == "2026-Q1.md"
    assert render_notes(tmp_path) == "newest"


def test_notes_placeholder_when_none_exist(tmp_path: Path):
    (tmp_path / "TEMPLATE.md").write_text("template", encoding="utf-8")
    assert render_notes(tmp_path) == NO_NOTES


def test_repo_prose_and_comments_have_no_em_dashes():
    paths = [ROOT / "README.md", ROOT / "CLAUDE.md", *(ROOT / "src").rglob("*.py")]
    offenders = [
        p.name for p in paths if p.exists() and chr(0x2014) in p.read_text(encoding="utf-8")
    ]
    assert offenders == []

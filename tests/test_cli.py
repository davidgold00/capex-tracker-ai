"""End-to-end build tests against a cached, hand-built companyfacts file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from capex_tracker.cli import main
from conftest import ROOT

CAPEX = "PaymentsToAcquirePropertyPlantAndEquipment"
OCF = "NetCashProvidedByUsedInOperatingActivities"
REVENUE = "Revenues"
CACHE_NAME = "companyfacts_AAA_20260101T000000Z.json"


def fact(start: str, end: str, value: float, form: str = "10-Q") -> dict[str, Any]:
    return {
        "start": start,
        "end": end,
        "val": value,
        "accn": "0000-1",
        "fy": 2024,
        "fp": "FY",
        "form": form,
        "filed": "2025-02-01",
    }


def year_of_direct_facts(annual: float) -> list[dict[str, Any]]:
    return [
        fact("2024-01-01", "2024-03-31", 10.0),
        fact("2024-04-01", "2024-06-30", 20.0),
        fact("2024-07-01", "2024-09-30", 30.0),
        fact("2024-10-01", "2024-12-31", 40.0),
        fact("2024-01-01", "2024-06-30", 30.0),
        fact("2024-01-01", "2024-09-30", 60.0),
        fact("2024-01-01", "2024-12-31", annual, form="10-K"),
    ]


def write_workspace(tmp_path: Path, capex_annual: float) -> Path:
    settings = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    settings["companies"] = [
        {"ticker": "AAA", "name": "Aaa", "role": "spender", "color": "#2a78d6"},
    ]
    settings["paths"] = {
        "raw_dir": str(tmp_path / "raw"),
        "processed_dir": str(tmp_path / "processed"),
        "charts_dir": str(tmp_path / "charts"),
        "notes_dir": str(tmp_path / "notes"),
        "readme": str(tmp_path / "README.md"),
    }
    settings["data_start"] = "2024-01-01"
    settings["chart_start"] = "2024-01-01"
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(settings), encoding="utf-8")

    raw = tmp_path / "raw"
    raw.mkdir()
    usd = {
        CAPEX: year_of_direct_facts(capex_annual),
        OCF: year_of_direct_facts(100.0),
        REVENUE: year_of_direct_facts(100.0),
    }
    payload = {
        "facts": {"us-gaap": {tag: {"units": {"USD": rows}} for tag, rows in usd.items()}},
    }
    (raw / CACHE_NAME).write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_build_writes_outputs_on_good_data(tmp_path: Path):
    config_path = write_workspace(tmp_path, capex_annual=100.0)
    assert main(["--config", str(config_path), "build"]) == 0
    processed = tmp_path / "processed"
    assert "**Status: PASS**" in (processed / "validation_report.md").read_text(encoding="utf-8")
    assert (processed / "quarterly.csv").exists()
    assert (processed / "wide.csv").exists()
    assert (processed / "aggregate.csv").exists()
    assert (processed / "tag_report.csv").exists()


def test_build_exits_non_zero_and_writes_no_data_on_bad_data(tmp_path: Path):
    config_path = write_workspace(tmp_path, capex_annual=110.0)
    assert main(["--config", str(config_path), "build"]) == 1
    processed = tmp_path / "processed"
    report = (processed / "validation_report.md").read_text(encoding="utf-8")
    assert "**Status: FAIL**" in report
    assert "annual_sum" in report
    assert not (processed / "quarterly.csv").exists()


def test_build_output_is_byte_identical_across_runs(tmp_path: Path):
    config_path = write_workspace(tmp_path, capex_annual=100.0)
    processed = tmp_path / "processed"
    assert main(["--config", str(config_path), "build"]) == 0
    first = {path.name: path.read_bytes() for path in processed.iterdir()}
    assert main(["--config", str(config_path), "build"]) == 0
    assert {path.name: path.read_bytes() for path in processed.iterdir()} == first


def test_build_without_cached_data_fails_clearly(tmp_path: Path, caplog):
    config_path = write_workspace(tmp_path, capex_annual=100.0)
    (tmp_path / "raw" / CACHE_NAME).unlink()
    assert main(["--config", str(config_path), "build"]) == 1
    assert "fetch" in caplog.text


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["inspect", "--ticker", "ZZZ", "--metric", "capex"], "unknown ticker"),
        (["inspect", "--ticker", "AAA", "--metric", "nope"], "unknown metric"),
    ],
)
def test_inspect_rejects_unknown_inputs(tmp_path: Path, caplog, args: list[str], expected: str):
    config_path = write_workspace(tmp_path, capex_annual=100.0)
    assert main(["--config", str(config_path), *args]) == 1
    assert expected in caplog.text


def test_inspect_prints_tag_facts_and_quarters(tmp_path: Path, capsys):
    config_path = write_workspace(tmp_path, capex_annual=100.0)
    assert (
        main(["--config", str(config_path), "inspect", "--ticker", "AAA", "--metric", "capex"]) == 0
    )
    output = capsys.readouterr().out
    assert f"Chosen tag: {CAPEX}" in output
    assert "Raw facts used" in output
    assert "FY2024 Q4" in output

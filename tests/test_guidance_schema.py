import hashlib
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from capex_tracker.guidance.schema import Period, Proposal


def test_frozen_split_and_fiscal_year():
    root = Path("eval/gold")
    assert (
        hashlib.sha256((root / "test.json").read_bytes()).hexdigest()
        == (root / "test.sha256").read_text().strip()
    )
    assert Period.annual("ORCL", 2026).start == date(2025, 6, 1)
    assert Period.annual("MSFT", 2026).end == date(2026, 6, 30)


def test_direction_is_never_a_numeric_forecast():
    with pytest.raises(ValidationError):
        Proposal(
            guidance_kind="directional",
            fiscal_year=2026,
            direction="up",
            low_usd=5,
            high_usd=5,
            confidence=1,
            rationale="test",
        )


def test_coreweave_is_opt_in_for_financials_and_guidance(tmp_path):
    import yaml

    from capex_tracker.config import load_config
    from capex_tracker.guidance.sources import CIKS

    assert len(load_config().spenders) == 5
    with pytest.raises(KeyError):
        load_config().company("CRWV")
    settings = yaml.safe_load(Path("config.yaml").read_text())
    next(c for c in settings["companies"] if c["ticker"] == "CRWV")["enabled"] = True
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(settings))
    cfg = load_config(path)
    assert len(cfg.spenders) == 6 and cfg.company("CRWV").start_at(cfg.data_start) == date(
        2024, 1, 1
    )
    assert CIKS["CRWV"] == 1769628 and Period.annual("CRWV", 2025).end == date(2025, 12, 31)

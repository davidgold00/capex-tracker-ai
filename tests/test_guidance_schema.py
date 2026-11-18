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

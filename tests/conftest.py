"""Shared helpers for building companyfacts-style test data."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from capex_tracker.config import Config, Durations, load_config
from capex_tracker.facts import Fact

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def config() -> Config:
    return load_config(ROOT / "config.yaml")


@pytest.fixture(scope="session")
def bands(config: Config) -> Durations:
    return config.durations


@pytest.fixture
def load_fixture() -> Any:
    def _load(name: str) -> dict[str, Any]:
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    return _load


def make_fact(
    start: str,
    end: str,
    value: float,
    concept: str = "Tag",
    filed: str = "2025-01-01",
    accession: str = "0001",
    form: str = "10-Q",
) -> Fact:
    return Fact(
        concept=concept,
        start=date.fromisoformat(start),
        end=date.fromisoformat(end),
        value=value,
        accession=accession,
        form=form,
        filed=date.fromisoformat(filed),
    )

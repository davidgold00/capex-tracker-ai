"""Load and validate config.yaml."""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Role = Literal["spender", "receiver"]
Sign = Literal["outflow", "as_reported"]

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
DEFAULT_CONFIG_PATH = Path("config.yaml")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Company(_Strict):
    ticker: str
    name: str
    role: Role
    color: str

    @field_validator("color")
    @classmethod
    def _check_color(cls, value: str) -> str:
        if not HEX_COLOR.match(value):
            raise ValueError(f"color must look like #rrggbb, got {value!r}")
        return value


class Metric(_Strict):
    tags: list[str] = Field(min_length=1)
    sign: Sign = "as_reported"
    required: bool = True


class DurationBand(_Strict):
    min_days: int
    max_days: int

    @model_validator(mode="after")
    def _check_order(self) -> DurationBand:
        if self.min_days > self.max_days:
            raise ValueError("min_days must not exceed max_days")
        return self


class Durations(_Strict):
    quarter: DurationBand
    six_months: DurationBand
    nine_months: DurationBand
    year: DurationBand


class Validation(_Strict):
    annual_sum_tolerance: float = Field(gt=0, lt=1)
    qoq_warn_threshold: float = Field(gt=0)
    cross_check_tolerance: float = Field(gt=0, lt=1)


class Sec(_Strict):
    tickers_url: str
    companyfacts_url: str
    request_delay_seconds: float = Field(ge=0.11)
    max_retries: int = Field(ge=0)
    backoff_seconds: float = Field(gt=0)
    timeout_seconds: float = Field(gt=0)
    cache_ttl_hours: float = Field(ge=0)


class Paths(_Strict):
    raw_dir: Path
    processed_dir: Path
    charts_dir: Path
    notes_dir: Path
    readme: Path


class Config(_Strict):
    companies: list[Company] = Field(min_length=1)
    metrics: dict[str, Metric]
    durations: Durations
    validation: Validation
    sec: Sec
    paths: Paths
    data_start: date
    chart_start: date
    forms: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_consistency(self) -> Config:
        tickers = [company.ticker for company in self.companies]
        if len(set(tickers)) != len(tickers):
            raise ValueError("company tickers must be unique")
        if not self.spenders:
            raise ValueError("at least one company must have role 'spender'")
        missing = {"capex", "ocf", "revenue", "finance_lease_principal"} - set(self.metrics)
        if missing:
            raise ValueError(f"config is missing required metrics: {sorted(missing)}")
        if self.chart_start < self.data_start:
            raise ValueError("chart_start must not be earlier than data_start")
        return self

    @property
    def spenders(self) -> Sequence[Company]:
        return [company for company in self.companies if company.role == "spender"]

    @property
    def receivers(self) -> Sequence[Company]:
        return [company for company in self.companies if company.role == "receiver"]

    def company(self, ticker: str) -> Company:
        for company in self.companies:
            if company.ticker == ticker:
                return company
        configured = [company.ticker for company in self.companies]
        raise KeyError(f"unknown ticker {ticker!r}; configured: {configured}")


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    """Read and validate the YAML config at ``path``."""
    with path.open(encoding="utf-8") as handle:
        return Config.model_validate(yaml.safe_load(handle))

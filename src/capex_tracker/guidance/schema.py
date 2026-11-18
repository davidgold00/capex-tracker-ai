"""A proposal describes one target. Source metadata and calendar mapping come from code."""

import calendar
from datetime import date, timedelta
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Kind = Literal["numeric_range", "numeric_point", "directional", "none"]
Direction = Literal["up", "down", "flat"]
Series = Literal["capex", "capex_lease_adjusted", "unresolved"]
Company = Literal["META", "GOOGL", "MSFT", "AMZN", "ORCL"]


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    guidance_kind: Kind
    fiscal_year: int | None = Field(ge=2000, le=2100)
    low_usd: int | None = Field(ge=0)
    high_usd: int | None = Field(ge=0)
    direction: Direction | None
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.guidance_kind.startswith("numeric"):
            if self.low_usd is None or self.high_usd is None or self.low_usd > self.high_usd:
                raise ValueError("Numeric guidance requires ordered dollar bounds")
            if (self.low_usd == self.high_usd) != (self.guidance_kind == "numeric_point"):
                raise ValueError("Equal bounds denote a point, different bounds a range")
        elif self.low_usd is not None or self.high_usd is not None:
            raise ValueError("Only numeric guidance can have dollar bounds")
        if self.guidance_kind == "directional" and self.direction is None:
            raise ValueError("Directional guidance requires a direction")
        if self.guidance_kind != "directional" and self.direction is not None:
            raise ValueError("Only qualitative guidance uses direction")
        return self


class Period(BaseModel):
    fiscal_year: int
    start: date
    end: date

    @classmethod
    def annual(cls, ticker: Company, year: int):
        month = {"MSFT": 6, "ORCL": 5}.get(ticker, 12)
        end = date(year, month, calendar.monthrange(year, month)[1])
        start = end.replace(year=year - 1) + timedelta(days=1)
        return cls(fiscal_year=year, start=start, end=end)


class Guidance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    company: Company
    statement_date: date
    source_accession: str = Field(pattern=r"^\d{10}-\d{2}-\d{6}$")
    source_url: str = Field(pattern=r"^https://www\.sec\.gov/Archives/edgar/data/")
    form: Literal["8-K", "10-Q", "10-K"]
    target_period: Period | None
    proposal: Proposal
    definition_note: str
    comparison_series: Series
    mapping_reason: str
    evidence_quote: str = Field(min_length=1)

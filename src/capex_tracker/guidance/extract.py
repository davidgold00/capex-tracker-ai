"""Rules, series mapping and deterministic checks shared by both proposal sources."""

import re
from decimal import Decimal

from capex_tracker.guidance.schema import Guidance, Period, Proposal
from capex_tracker.guidance.sources import CAPEX, FUTURE, digest

MONEY = re.compile(
    r"\$\s*(?P<first>\d+(?:,\d{3})*(?:\.\d+)?)\s*(?P<u1>billion|million)?"
    r"(?:\s*(?:[-\u2013]|to|and)\s*\$?\s*(?P<last>\d+(?:,\d{3})*(?:\.\d+)?)"
    r"\s*(?P<u2>billion|million)?)?",
    re.I,
)
YEAR = re.compile(r"\b20\d{2}\b")
UP = re.compile(r"\b(increase|grow|higher|exceed|rise|growth)\b", re.I)
DOWN = re.compile(r"\b(decrease|decline|lower|fall)\b", re.I)
FLAT = re.compile(r"\b(flat|remain unchanged|stay stable)\b", re.I)


def target_clause(sentence):
    """Isolate the current spending expectation from historicals, revisions and drivers."""
    text = re.split(
        r",?\s+(?:lowered from|raised from|increased from|narrowed from|"
        r"updated from|unchanged from|up from|down from|driven by|primarily driven|"
        r"with growth driven|to support|primarily due to)",
        sentence,
        flags=re.I,
    )[0]
    return text.strip()


def amounts(clause):
    bounds = []
    for match in MONEY.finditer(clause):
        first, u1, last, u2 = match.groups()
        if not (u1 or u2):
            continue

        def usd(number, unit):
            scale = {"billion": 10**9, "million": 10**6}[unit.lower()]
            return int(Decimal(number.replace(",", "")) * scale)

        lo = usd(first, u1 or u2)
        hi = usd(last, u2 or u1) if last else lo
        bounds.append((lo, hi))
    return bounds


def target_year(clause):
    text = re.split(r"\b(?:than|relative to|exceed)\b", clause, flags=re.I)[0]
    years = set(YEAR.findall(text))
    if len(years) == 1 and not re.search(r"\bquarter\b|\bQ[1-4]\b", text, re.I):
        return int(years.pop())
    return None


def direction(text):
    for word, pattern in [("down", DOWN), ("up", UP), ("flat", FLAT)]:
        if pattern.search(text):
            return word
    return None


def proposal(kind="none", year=None, bounds=(None, None), movement=None, reason="No target."):
    return Proposal(
        guidance_kind=kind,
        fiscal_year=year,
        low_usd=bounds[0],
        high_usd=bounds[1],
        direction=movement,
        confidence=1,
        rationale=reason,
    )


def numeric_bounds(sentence):
    """Only amounts tied to the capex clause, excluding amounts for another line item."""
    text = target_clause(sentence)
    match = CAPEX.search(text)
    if not match:
        return []
    after = text[match.end() :]
    if re.search(r"^\s+(?:were|was|increased by|decreased by)\b", after, re.I):
        return []
    if re.search(
        r"\b(net proceeds|financing|acquisition costs|depreciation expense)\b", text, re.I
    ):
        return []
    after = re.split(
        r",\s*(?:a \$|and |with |reflecting )|"
        r"\band (?:total )?(?:revenue|expenses|operating income)",
        after,
        flags=re.I,
    )[0]
    values = amounts(after)
    if values:
        return values
    before = re.search(
        r"\b(?:invest|spend)\s+(?:about |approximately |around )?"
        r"(\$[^;]{1,45}?)\s+(?:in|on)\s*$",
        text[: match.start()],
        re.I,
    )
    return amounts(before[1]) if before else []


def rules(sentence):
    if not CAPEX.search(sentence) or not FUTURE.search(sentence):
        return proposal()
    text = target_clause(sentence)
    year = target_year(text)
    values = numeric_bounds(sentence)
    if len(values) == 1:
        bounds = values[0]
        return proposal(
            "numeric_point" if bounds[0] == bounds[1] else "numeric_range",
            year,
            bounds,
            reason="Dollar target attached to the spending clause.",
        )
    capex = CAPEX.search(text)
    if capex and re.match(
        r"\s+(?:to |will |in (?:fiscal )?20\d{2} to |dollar growth will )"
        r"(?:be |meaningfully |significantly )?(?:increase|grow|exceed|"
        r"decrease|decline|higher|lower|flat|remain unchanged)",
        text[capex.end() :],
        re.I,
    ):
        movement = direction(text[capex.end() :])
        if movement:
            return proposal("directional", year, movement=movement, reason="Explicit movement.")
    return proposal()


def definition(ticker, text):
    leases = re.search(
        r"capital expenditures,? including principal payments on finance leases", text, re.I
    )
    if leases:
        return "capex_lease_adjusted", leases[0], "The issuer explicitly adds lease principal."
    if ticker == "GOOGL":
        label = re.search(
            r"We define free cash flow as net cash provided by operating activities"
            r" less capital expenditures",
            text,
            re.I,
        )
        if label and "purchases of property and equipment" in text.lower():
            return "capex", label[0], "The cash flow reconciliation identifies purchases of PP&E."
    if ticker == "ORCL" and re.search(
        r"Cash Flows From Investing Activities:[\s\S]{0,1000}?"
        r"\nCapital expenditures\n",
        text,
        re.I,
    ):
        return "capex", "Capital expenditures", "The investing cash-flow statement uses this label."
    net = re.search(
        r"purchases of property and equipment, net of proceeds from sales and incentives",
        text,
        re.I,
    )
    if net:
        return "unresolved", net[0], "Net proceeds can differ from the XBRL purchases series."
    return "unresolved", "", "No matching spending definition established in this document."


def attach(row, sentence, result, basis):
    series, note, reason = basis
    year = result.fiscal_year
    return Guidance(
        company=row["company"],
        statement_date=row["filed"],
        source_accession=row["accession"],
        source_url=row["url"],
        form=row["form"],
        target_period=Period.annual(row["company"], year) if year else None,
        proposal=result,
        definition_note=note,
        comparison_series=series,
        mapping_reason=reason,
        evidence_quote=sentence,
    )


def verify(statement, source):
    p = statement.proposal
    quote = statement.evidence_quote
    normalize = lambda s: " ".join(s.split())  # noqa: E731
    year = target_year(target_clause(quote))
    date_ok = statement.target_period and statement.statement_date <= statement.target_period.end
    amounts_ok = not p.guidance_kind.startswith("numeric") or numeric_bounds(quote) == [
        (p.low_usd, p.high_usd)
    ]
    return {
        "verbatim_quote": bool(quote.strip()) and normalize(quote) in normalize(source),
        "capex_outlook": bool(CAPEX.search(quote) and FUTURE.search(quote)),
        "dollars_and_units": amounts_ok,
        "annual_period": bool(year and p.fiscal_year == year and date_ok),
        "direction": p.direction is None or p.direction == direction(target_clause(quote)),
        "comparison_series": statement.comparison_series != "unresolved"
        and statement.definition_note in source,
    }


def candidate_id(row, sentence):
    return row["company"] + "-" + digest(row["accession"] + "\n" + sentence)[:12]

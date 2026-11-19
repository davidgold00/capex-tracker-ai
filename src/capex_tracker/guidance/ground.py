"""Bind every publishable sentence to company, period, metric, value and direction."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from capex_tracker.guidance.sources import digest
from capex_tracker.metrics import latest_complete
from capex_tracker.quarters import display_quarter
from capex_tracker.readme import billions, replace_section


@dataclass(frozen=True)
class Facts:
    # Each group is one required claim. The model may choose a phrasing and order.
    groups: tuple[tuple[str, ...], ...]

    @property
    def key(self):
        return digest(json.dumps(self.groups))


def factbook(aggregate, long, approved, config):
    latest = latest_complete(aggregate)
    if latest is None:
        return Facts(())
    quarter = pd.Period(latest["calendar_quarter"], freq="Q")
    current = float(latest["total_capex"])
    groups = []
    for offset in (1, 4):
        ref = str(quarter - offset)
        prior = aggregate[(aggregate["calendar_quarter"] == ref) & ~aggregate["partial"]]
        if prior.empty:
            return Facts(())
        value = float(prior.iloc[0]["total_capex"])
        verb = "rose" if current > value else "fell" if current < value else "was unchanged"
        q, old = display_quarter(str(quarter)), display_quarter(ref)
        groups.append(
            (
                f"Aggregate capex {verb} from {billions(value)} in {old} to "
                f"{billions(current)} in {q}.",
                f"In {q}, aggregate capex {verb} to {billions(current)} from "
                f"{billions(value)} in {old}.",
            )
        )
    # Use filing cycles, including the releases filed after quarter end.
    directory = config.paths.processed_dir.parent / "guidance"
    manifest = json.loads((directory / "sources.json").read_text())

    def cutoff(q):
        filing_dates = []
        for company in config.spenders:
            rows = long[(long["calendar_quarter"] == str(q)) & (long["ticker"] == company.ticker)]
            if rows.empty:
                continue
            period_end = str(rows["period_end"].max())
            after = [
                r["filed"]
                for r in manifest
                if r["company"] == company.ticker
                and r["form"] in ("10-Q", "10-K")
                and r["filed"] > period_end
            ]
            if after:
                filing_dates.append(min(after))
        return max(filing_dates, default=str(q.end_time.date()))

    start, end = cutoff(quarter - 1), cutoff(quarter)
    latest_guidance = {}
    for r in sorted(approved, key=lambda r: (r["statement_date"], r["id"])):
        if (
            r["company"] in {c.ticker for c in config.spenders}
            and start < r["statement_date"] <= end
        ):
            latest_guidance[(r["company"], r["period"], bool(r["low"]))] = r
    for (ticker, year, _), r in sorted(latest_guidance.items()):
        company = config.company(ticker).name
        if not r["low"]:
            description = (
                "spending to "
                + {"up": "increase", "down": "decrease", "flat": "stay flat"}[r["direction"]]
            )
        else:
            description = billions(int(r["low"]))
            if r["low"] != r["high"]:
                description += " to " + billions(int(r["high"]))
        groups.append((f"{company} guided to {description} for FY{year}.",))
    return Facts(tuple(groups))


def check(paragraph, facts):
    sentences = re.split(r"(?<=\.)\s+", paragraph.strip()) if paragraph.strip() else []
    if not facts.groups:
        return ["No complete quarter comparisons"]
    allowed = {s: i for i, options in enumerate(facts.groups) for s in options}
    used = set()
    reasons = []
    for sentence in sentences:
        if sentence in allowed:
            key = allowed[sentence]
            if key in used:
                reasons.append("Repeated comparison or guidance")
            used.add(key)
            continue
        # A near match supplies diagnostics only. Publication requires an exact fact.
        from difflib import get_close_matches

        near = get_close_matches(sentence, allowed, n=1, cutoff=0.1)
        reference = near[0] if near else ""
        dollars = r"\$[\d,.]+B"
        dirs = r"\b(rose|fell|was unchanged|increase|decrease|stay flat)\b"
        if re.findall(dollars, sentence) != re.findall(dollars, reference):
            reasons.append("Dollar value or its comparison period differs from the ledger")
        if re.findall(dirs, sentence) != re.findall(dirs, reference):
            reasons.append("Direction differs from the ledger")
        reasons.append("Unsupported company, period, claim or wording: " + sentence)
    if used != set(range(len(facts.groups))):
        reasons.append("Missing required quarter comparison or approved guidance")
    return reasons


def template(facts):
    paragraph = " ".join(group[0] for group in facts.groups)
    return paragraph if not check(paragraph, facts) else ""


def publish(text, path: Path, facts):
    paragraph = template(facts)
    label = "template-generated, fact-checked"
    if path.is_file():
        data = json.loads(path.read_text())
        if data.get("facts_sha256") == facts.key and not check(data.get("paragraph", ""), facts):
            paragraph = data["paragraph"]
            if data.get("basis", "local-model") == "local-model":
                label = "local-model rephrasing, fact-checked"
    body = f"{paragraph}\n\n*{label}*" if paragraph else "Not measured (n=0 complete comparisons)."
    return replace_section(text, "WHAT_CHANGED", body)

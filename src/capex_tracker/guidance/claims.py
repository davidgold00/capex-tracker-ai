"""Index distinct guidance claims and retain every source passage behind them."""

import json
from collections import defaultdict
from datetime import date

from capex_tracker.guidance.review import csv_row, decision_input
from capex_tracker.guidance.sources import DATA


def event_dates(manifest):
    """Date a paired release and periodic report to the first public filing."""
    groups = defaultdict(list)
    dates = {s["accession"]: s["filed"] for s in manifest}
    for source in manifest:
        if source.get("results_period"):
            groups[source["company"], source["results_period"]].append(source)
    for documents in groups.values():
        if len(documents) != 2 or {d["form"] == "8-K" for d in documents} != {True, False}:
            continue
        release, periodic = sorted(documents, key=lambda d: d["form"] != "8-K")
        gap = date.fromisoformat(periodic["filed"]) - date.fromisoformat(release["filed"])
        if 0 <= gap.days <= 1:
            dates[periodic["accession"]] = release["filed"]
    return dates


def index(directory=DATA):
    manifest = directory / "sources.json"
    dates = event_dates(json.loads(manifest.read_text())) if manifest.exists() else {}
    groups = defaultdict(list)
    for path in sorted((directory / "traces").glob("*.json")):
        trace = json.loads(path.read_text())
        data = decision_input(trace, "rules")
        if data is None:
            continue
        statement, checks, dual = data
        row = csv_row(trace, statement, checks, dual)
        event = dates.get(row["accession"], row["statement_date"])
        key = (
            row["company"],
            event,
            row["period"],
            row["low"],
            row["high"],
            row["direction"],
            row["comparison_series"],
        )
        # Ambiguous proposals have no defensible cross-document identity.
        complete = bool(
            row["period"]
            and row["kind"] not in (None, "none")
            and row["comparison_series"] != "unresolved"
        )
        if not complete:
            key += (row["id"],)
        groups[key].append((trace, row))
    return groups


def inventory(groups):
    claims = []
    for key, entries in groups.items():
        # Stable, earliest evidence represents the claim; retain every filing date separately.
        entries.sort(key=lambda e: (e[1]["statement_date"], e[1]["id"]))
        row = entries[0][1]
        evidence = [
            dict(
                id=r["id"],
                accession=r["accession"],
                form=r["form"],
                filed=r["statement_date"],
                url=r["source_url"],
                quote=r["evidence_quote"],
            )
            for _, r in entries
        ]
        claims.append(
            dict(
                id=row["id"],
                company=row["company"],
                statement_date=key[1],
                year=row["period"],
                low=row["low"],
                high=row["high"],
                direction=row["direction"],
                definition=row["comparison_series"],
                kind=row["kind"],
                evidence=evidence,
            )
        )
    return sorted(claims, key=lambda c: c["id"])


if __name__ == "__main__":
    from capex_tracker.guidance.records import write_record

    write_record(DATA / "claims.json", {"claims": inventory(index())})

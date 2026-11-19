"""Apply decisions from VS Code. The audit ledger is authoritative and replayable."""

import argparse
import csv
import fcntl
import json
import re

from capex_tracker.guidance.extract import attach, definition, verify
from capex_tracker.guidance.records import write_record
from capex_tracker.guidance.schema import Guidance, Proposal
from capex_tracker.guidance.sources import CAPEX, DATA, FUTURE, RAW, digest

FIELDS = [
    "id",
    "company",
    "statement_date",
    "period",
    "calendar_start",
    "calendar_end",
    "kind",
    "low",
    "high",
    "direction",
    "evidence_quote",
    "source_url",
    "accession",
    "form",
    "comparison_series",
    "definition_note",
    "mapping_reason",
    "verification",
    "dual_match",
    "approved_by",
]
EDITS = ["decision", "edit_period", "edit_low", "edit_high", "edit_direction", "edit_kind"]
MATCH = ("guidance_kind", "fiscal_year", "low_usd", "high_usd", "direction")


def read_csv(path):
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def read_approved(directory):
    """Check published rows against recorded approvals before using their values."""
    rows = read_csv(directory / "approved.csv")
    ledger = directory / "audit.json"
    events = json.loads(ledger.read_text())["decisions"] if ledger.is_file() else {}
    expected = []
    for _, event in sorted(events.items()):
        if event["decision"] == "approve":
            expected.append({k: "" if v is None else str(v) for k, v in event["row"].items()})
    if rows != expected:
        raise ValueError("Approved table differs from its audit log. Reapply saved decisions.")
    return rows


def write_csv(path, fields, rows):
    temp = path.with_suffix(".tmp")
    with temp.open("w", newline="") as f:
        writer = csv.DictWriter(f, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def decision_input(trace, primary):
    methods = (primary, "rules" if primary == "ollama" else "ollama")
    finals = [(trace.get(m) or [{}])[-1] for m in methods]
    attempts = [attempt for m in methods for attempt in reversed(trace.get(m, []))]
    positives = [
        a
        for a in attempts
        if a.get("statement", {}).get("proposal", {}).get("guidance_kind", "none") != "none"
    ]
    if not positives and not any("error" in a for a in attempts):
        return None
    chosen = positives[0] if positives else next((a for a in attempts if "statement" in a), {})
    result = chosen.get("statement")
    pair = [a.get("statement", {}).get("proposal", {}) for a in finals]
    dual = (
        bool((trace.get("ollama") or [{}])[-1].get("cassette"))
        and all(a.get("checks") and all(a["checks"].values()) for a in finals)
        and all(pair[0].get(k) == pair[1].get(k) for k in MATCH)
    )
    return (
        result,
        {m: [a.get("checks", a.get("error")) for a in trace.get(m, [])] for m in methods},
        dual,
    )


def csv_row(trace, statement, checks, dual):
    src = trace["source"]
    p = (statement or {}).get("proposal", {})
    period = (statement or {}).get("target_period") or {}
    # A release may join quotations on one line. Display the single target
    # sentence when unique, retaining the entire original window in the trace.
    passage = trace["passage"]
    sentences = re.split(r"(?<=[.!?])\s+(?=[\u201c\u2018])", passage)
    excerpts = [s for s in sentences if CAPEX.search(s) and FUTURE.search(s)]
    quote = excerpts[0] if len(excerpts) == 1 else passage
    return dict(
        id=trace["id"],
        company=src["company"],
        statement_date=src["filed"],
        period=p.get("fiscal_year"),
        calendar_start=period.get("start"),
        calendar_end=period.get("end"),
        kind=p.get("guidance_kind"),
        low=p.get("low_usd"),
        high=p.get("high_usd"),
        direction=p.get("direction"),
        evidence_quote=quote,
        source_url=src["url"],
        accession=src["accession"],
        form=src["form"],
        comparison_series=(statement or {}).get("comparison_series", "unresolved"),
        definition_note=(statement or {}).get("definition_note", ""),
        mapping_reason=(statement or {}).get("mapping_reason", ""),
        verification=json.dumps(checks, sort_keys=True),
        dual_match=bool(dual),
        approved_by="",
    )


def manual(trace, statement, edits):
    src = trace["source"]
    source = (RAW / "clean" / (src["accession"] + ".txt")).read_text()
    if digest(source) != src["sha256"]:
        raise ValueError("Changed source: " + src["accession"])
    old = (
        Guidance.model_validate(statement).proposal.model_dump()
        if statement
        else {
            "confidence": 1,
            "rationale": "Human edit",
            "guidance_kind": "none",
            "direction": None,
            "low_usd": None,
            "high_usd": None,
            "fiscal_year": None,
        }
    )
    for col, field in [
        ("period", "fiscal_year"),
        ("low", "low_usd"),
        ("high", "high_usd"),
        ("direction", "direction"),
        ("kind", "guidance_kind"),
    ]:
        value = edits.get("edit_" + col, "").strip()
        if value:
            old[field] = None if value.lower() == "null" else value
    g = attach(
        src, trace["passage"], Proposal.model_validate(old), definition(src["company"], source)
    )
    checks = verify(g, source)
    if g.proposal.guidance_kind == "none" or not all(checks.values()):
        raise ValueError(f"{trace['id']} cannot be approved: {checks}")
    return g.model_dump(mode="json"), checks


def apply(directory=DATA, auto=False):
    directory.mkdir(parents=True, exist_ok=True)
    # Lock the containing directory, so a crash leaves no stale lockfile.
    import os

    fd = os.open(directory, os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        _apply(directory, auto)
    finally:
        os.close(fd)


def _apply(directory, auto):
    from capex_tracker.guidance.claims import index, inventory, paired_reports
    from capex_tracker.guidance.policy import conflicts, policy

    audit = directory / "audit.json"
    book = json.loads(audit.read_text()) if audit.exists() else {}
    old = book.get("decisions", {})
    history = book.get("history", [])
    events = {k: v for k, v in old.items() if v["approved_by"] == "manual"}
    edits_by_id = {r["id"]: r for r in read_csv(directory / "pending.csv")}
    pending = []
    groups = index(directory)
    catalog = inventory(groups)
    manifest = directory / "sources.json"
    pairs = paired_reports(json.loads(manifest.read_text())) if manifest.exists() else {}
    competing = conflicts(groups)
    for key, entries in groups.items():
        ids = [r["id"] for _, r in entries]
        if any(cid in events for cid in ids):
            continue
        edited = [cid for cid in ids if any(edits_by_id.get(cid, {}).get(k) for k in EDITS)]
        if len(edited) > 1:
            raise ValueError(f"Multiple edits to the same claim: {edited}")
        actor, reason = policy(key, entries, competing, pairs)
        # Use a dual-verified passage if that is the approval basis.
        chosen = next(((t, r) for t, r in entries if r["dual_match"]), entries[0])
        if actor == "auto-corroborated":
            chosen = next(
                (t, r)
                for t, r in entries
                if t["rules"][-1].get("checks") and all(t["rules"][-1]["checks"].values())
            )
        elif actor != "auto-dual-match":
            chosen = entries[0]
        if edited:
            chosen = next((t, r) for t, r in entries if r["id"] == edited[0])
        trace, row = chosen
        cid = row["id"]
        edits = {k: edits_by_id.get(cid, {}).get(k, "") for k in EDITS}
        action = edits["decision"].strip().lower()
        if action not in ("", "approve", "reject"):
            raise ValueError(f"{cid}: unknown decision {action}")
        if action:
            actor = "manual"
            reason = "Reviewer decision"
            if action == "approve":
                statement, checks, dual = decision_input(trace, "rules")
                statement, checks["manual"] = manual(trace, statement, edits)
                row = csv_row(trace, statement, checks, dual)
        elif actor and not edited and (auto or any(i in old for i in ids)):
            action = "approve"
        if action:
            row["approved_by"] = actor if action == "approve" else ""
            events[cid] = dict(
                decision=action,
                approved_by=actor,
                row=row,
                edits=edits,
                evidence_ids=ids,
                reason=reason,
            )
        else:
            pending.append({**row, **edits})
    for cid in sorted(old.keys() | events.keys()):
        if old.get(cid) != events.get(cid):
            history.append(dict(id=cid, before=old.get(cid), after=events.get(cid)))
    write_record(directory / "claims.json", {"claims": catalog})
    approved = [v["row"] for _, v in sorted(events.items()) if v["decision"] == "approve"]
    # Persist decisions first. Rerunning recreates either derived CSV after interruption.
    write_record(audit, {"decisions": events, "history": history})
    write_csv(directory / "approved.csv", FIELDS, approved)
    write_csv(directory / "pending.csv", FIELDS + EDITS, sorted(pending, key=lambda r: r["id"]))
    suggestions = directory / "adjudications.json"
    if suggestions.is_file():
        hints = json.loads(suggestions.read_text())["items"]
        hashes = {t["id"]: t["source"].get("sha256") for group in groups.values() for t, _ in group}
        assisted = []
        for row in sorted(pending, key=lambda r: r["id"]):
            hint = hints.get(row["id"], {})
            if (
                hint.get("eligible")
                and hint["source_sha256"] == hashes[row["id"]]
                and hint["quote"] in row["evidence_quote"]
            ):
                assisted.append(
                    dict(
                        id=row["id"],
                        bucket="model-assisted",
                        company=row["company"],
                        year=hint["year"],
                        direction=hint["direction"],
                        quote=hint["quote"],
                        source_url=row["source_url"],
                        cassette=hint["cassette"],
                    )
                )
        write_csv(
            directory / "model_assisted.csv",
            ["id", "bucket", "company", "year", "direction", "quote", "source_url", "cassette"],
            assisted,
        )
    print(f"{len(approved)} approved, {len(pending)} pending.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auto", "--auto-dual-match", action="store_true")
    apply(auto=parser.parse_args().auto)

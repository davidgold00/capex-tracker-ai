"""Interview demo. Explanations use committed evidence, model records and XBRL only."""

import argparse
import json
import re

from capex_tracker.cli import _read_processed
from capex_tracker.config import load_config
from capex_tracker.guidance.extract import rules
from capex_tracker.guidance.ground import check, factbook
from capex_tracker.guidance.report import audit_status, finding, paths
from capex_tracker.guidance.review import read_approved, read_csv
from capex_tracker.guidance.sources import DATA, digest
from capex_tracker.readme import billions


def money(value):
    return billions(int(value)) if value is not None else "no dollar amount"


def describe(p):
    kind = p["guidance_kind"]
    if kind == "none":
        return "No guidance proposed."
    period = f"FY{p['fiscal_year']}" if p["fiscal_year"] else "no single fiscal year"
    if kind.startswith("numeric"):
        return f"{period}, {money(p['low_usd'])} to {money(p['high_usd'])}."
    return f"{period}, {p['direction']}."


def explain(cid, detailed=True):
    if not re.fullmatch(r"(?:AMZN|GOOGL|MSFT|META|ORCL)-[0-9a-f]{12}", cid):
        raise ValueError("Unrecognized candidate ID")
    trace = json.loads((DATA / "traces" / (cid + ".json")).read_text())
    row = trace["source"]
    lines = [
        f"{cid} | {row['company']} {row['form']} filed {row['filed']}",
        row["url"],
        f"Passage: {trace['passage']}",
    ]
    if detailed:
        lines.append(f"Clean document SHA-256: {row['sha256']}")
    # Recompute the baseline and check all stored model responses without importing a provider.
    baseline = rules(trace["passage"]).model_dump()
    assert trace["rules"][0]["statement"]["proposal"] == baseline
    for label, method in [("Rules", "rules"), ("Local model", "ollama")]:
        for i, a in enumerate(trace.get(method, []), 1):
            key = a.get("cassette")
            if key:
                cassette = json.loads((DATA / "cassettes" / (key + ".json")).read_text())
                if digest(json.dumps(cassette["request"], sort_keys=True)) != key:
                    raise ValueError("Cassette does not match request")
                if "statement" in a:
                    from capex_tracker.guidance.schema import Proposal

                    replay = Proposal.model_validate_json(cassette["response"])
                    assert replay.model_dump() == a["statement"]["proposal"]
                elif "error" in a:
                    try:
                        bad = json.loads(cassette["response"])
                        lines.append(
                            f"Recorded fields: kind={bad.get('guidance_kind')}, "
                            f"year={bad.get('fiscal_year')}, low={bad.get('low_usd')}, "
                            f"high={bad.get('high_usd')}, direction={bad.get('direction')}."
                        )
                    except (ValueError, AttributeError):
                        lines.append("Recorded response is not a guidance object.")
                if detailed:
                    lines.append(f"Recorded {cassette['request']['model']} call {key[:12]}.")
            if "statement" in a:
                st = a["statement"]
                lines.append(f"{label}, attempt {i}: " + describe(st["proposal"]))
                for name, ok in a["checks"].items():
                    lines.append(f"  {'PASS' if ok else 'FAIL'}  {name.replace('_', ' ')}")
                if detailed and st["mapping_reason"]:
                    lines.append(f"  Series: {st['comparison_series']}. {st['mapping_reason']}")
                    if st["definition_note"]:
                        lines.append(f"  Filing definition: {st['definition_note']}")
            else:
                lines.append(f"{label}, attempt {i}: schema rejected. {a['error']}")
    approved = read_approved(DATA)
    pending = read_csv(DATA / "pending.csv")
    audit = json.loads((DATA / "audit.json").read_text())["decisions"]
    claim_id = next(
        (k for k, v in audit.items() if cid == k or cid in v.get("evidence_ids", [])), cid
    )
    result = audit.get(claim_id)
    catalog = json.loads((DATA / "claims.json").read_text())["claims"]
    claim = next((c for c in catalog if any(e["id"] == cid for e in c["evidence"])), None)
    if claim:
        lines.append(f"Claim date: {claim['statement_date']}; {len(claim['evidence'])} passage(s).")
        for e in claim["evidence"]:
            lines.append(f"  {e['id']} | {e['form']} filed {e['filed']} | {e['accession']}")
            lines.extend(["  " + e["quote"], "  " + e["url"]])
    lines.append(
        f"Review: {result['decision']} by {result['approved_by']}. {result.get('reason', '')}"
        if result
        else "Review: pending in the browser queue."
        if claim and any(r["id"] in {e["id"] for e in claim["evidence"]} for r in pending)
        else "Review: both extractors abstained."
    )
    _, wide, _ = _read_processed(load_config())
    rows = paths(approved, wide)
    plotted = next((r for r in rows if r["id"] == claim_id), None)
    if plotted:
        lines.append(
            f"Chart: {plotted['stage']} in FY{plotted['fiscal_year']}; "
            + (
                f"actual {money(plotted['actual'])}."
                if plotted["actual"] is not None
                else "a complete actual is unavailable."
            )
        )
    else:
        lines.append("Chart: no point for this passage.")
    lines.append(finding(rows, audit_status(DATA)))
    return "\n".join(lines)


def demo_id():
    # A fixed example keeps the live demonstration and printed walkthrough in sync.
    return "META-6e73e0ba7afe"


def policy_demo():
    from capex_tracker.guidance.claims import index, paired_reports
    from capex_tracker.guidance.policy import conflicts, policy

    groups = index()
    competing = conflicts(groups)
    pairs = paired_reports(json.loads((DATA / "sources.json").read_text()))
    lines = []
    for cid in ("META-7dcf3e00303f", "GOOGL-9eb6791813d9", "GOOGL-cbe5e60f03e9"):
        key, entries = next(
            (k, rows) for k, rows in groups.items() if any(r["id"] == cid for _, r in rows)
        )
        actor, reason = policy(key, entries, competing, pairs)
        lines.append(f"{key[0]} | {key[1]} | FY{key[2]} | {actor or 'pending'}: {reason}")
        for other_key, evidence in groups.items():
            if other_key == key or (key[:3] in competing and other_key[:3] == key[:3]):
                for _, r in evidence:
                    lines.append(f"  {r['id']} | {r['form']} | {r['evidence_quote']}")
                    lines.append("  " + r["source_url"])
    return "\n".join(lines)


def guard_demo():
    config = load_config()
    long, _, aggregate = _read_processed(config)
    facts = factbook(aggregate, long, read_approved(DATA), config)
    good = " ".join(g[0] for g in facts.groups)
    bad = re.sub(r"\$[\d,.]+B", "$0.0B", good, count=1)
    bad = re.sub(r"\b(rose|fell)\b", lambda m: "fell" if m[0] == "rose" else "rose", bad, count=1)
    reasons = check(bad, facts)
    if check(good, facts) or not reasons:
        raise ValueError("Guard demo failed")
    return "\n".join(["ACCEPT: " + good, "REJECT: " + bad, *["  " + r for r in reasons]])


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["demo", "guard", "explain", "policy"])
    p.add_argument("id", nargs="?")
    args = p.parse_args()
    if args.command == "policy":
        print(policy_demo())
    elif args.command == "guard":
        print(guard_demo())
    else:
        print(explain(args.id or demo_id(), detailed=args.command == "explain"))

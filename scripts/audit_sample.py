"""Freeze a seeded claim sample once, then summarize browser-entered verdicts."""

import argparse
import json
import random
from collections import Counter
from pathlib import Path

from capex_tracker.guidance.review import read_approved, read_csv, write_csv
from capex_tracker.guidance.sources import DATA

SEED = 20261119
FIELDS = [
    "id",
    "policy",
    "company",
    "statement_date",
    "period",
    "kind",
    "low",
    "high",
    "direction",
    "comparison_series",
    "definition_note",
    "evidence_quote",
    "source_url",
    "supporting_evidence",
    "david_verdict",
    "david_note",
]


def sample(directory):
    path = directory / "audit_sample.csv"
    if path.exists():
        raise ValueError("Sample already exists. Preserve the frozen rows and verdicts.")
    approved = [r for r in read_approved(directory) if r["approved_by"] == "auto-corroborated"]
    pending = read_csv(directory / "pending.csv")
    claims = json.loads((directory / "claims.json").read_text())["claims"]
    evidence = {e["id"]: c["evidence"] for c in claims for e in c["evidence"]}
    rng = random.Random(SEED)
    chosen = rng.sample(approved, min(len(approved), 20))
    chosen += rng.sample(pending, min(len(pending), 30 - len(chosen)))
    rows = []
    for row in chosen:
        entry = {k: row.get(k, "") for k in FIELDS}
        entry["policy"] = row["approved_by"] or "pending"
        entry["supporting_evidence"] = json.dumps(evidence[row["id"]], ensure_ascii=False)
        rows.append(entry)
    write_csv(path, FIELDS, rows)


def report(path):
    rows = read_csv(path)
    if not rows:
        raise ValueError("Missing audit sample")
    lines = []
    for group in ("auto-corroborated", "pending"):
        counts = Counter(r["david_verdict"].strip().lower() for r in rows if r["policy"] == group)
        if counts.keys() - {"", "correct", "incorrect", "unsure"}:
            raise ValueError("Verdict must be correct, incorrect, unsure or blank")
        n = counts["correct"] + counts["incorrect"]
        score = (
            f"{counts['correct'] / n:.1%} ({counts['correct']}/{n}, n={n})"
            if n
            else "Not measured (n=0)"
        )
        lines.append(f"{group}: agreement {score}; unsure {counts['unsure']}; blank {counts['']}.")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--directory", type=Path, default=DATA)
    args = parser.parse_args()
    if args.create:
        sample(args.directory)
    print(report(args.directory / "audit_sample.csv"))

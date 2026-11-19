"""Render the short repository status from the same persisted evidence as the README."""

import json
from collections import Counter

from capex_tracker.guidance.report import audit_line, audit_status, finding
from capex_tracker.guidance.review import read_approved, read_csv


def render(directory, rows):
    approved = read_approved(directory)
    counts = Counter(r["approved_by"] for r in approved)
    pending = read_csv(directory / "pending.csv")
    assist = len(read_csv(directory / "model_assisted.csv"))
    claims = json.loads((directory / "claims.json").read_text())["claims"]
    all_counts = Counter(c["company"] for c in claims)
    annual = Counter(c["company"] for c in claims if c["year"] and c["kind"] not in (None, "none"))
    sources = json.loads((directory / "sources.json").read_text())
    lines = [
        "# Guidance status",
        "",
        finding(rows, audit_status(directory)),
        "",
        "| Approved by corroboration | Dual extractor | Manual | "
        "Model-assisted pending | Other pending |",
        "|---:|---:|---:|---:|---:|",
        f"| {counts['auto-corroborated']} | {counts['auto-dual-match']} | {counts['manual']} "
        f"| {assist} | {len(pending) - assist} |",
        "",
        f"**Coverage.** {sum('sha256' in s for s in sources)} SEC documents. "
        f"{len(claims)} distinct review items, including {sum(annual.values())} "
        "positive proposals with an annual target. Items / annual proposals: "
        + ", ".join(f"{k} {n}/{annual[k]}" for k, n in sorted(all_counts.items()))
        + ".",
        "",
        "**Frozen test.** Rules precision 13/13 and recall 13/13. Qwen 1.5B precision 5/7 "
        "and recall 5/13. Fully verified rules predictions: 7/13 originally, 8/13 in the "
        "[post-fix diagnostic](eval/VERIFICATION_DIAGNOSIS.md).",
        "",
        audit_line(directory) + " [Fill the audit CSV](data/guidance/audit_sample.csv) "
        "and [review pending decisions](data/guidance/pending.csv) in the GitHub web editor.",
        "",
        "[Filing evidence](data/guidance/README.md) · [Dev bake-off](eval/MODEL_BAKEOFF.md) "
        "· [Initial run](docs/history/INITIAL_GUIDANCE_RUN.md) · "
        "[Overnight record](docs/history/OVERNIGHT_PROGRESS.md)",
    ]
    return "\n".join(lines) + "\n"

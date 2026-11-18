"""Score fixed gold passages once. Preserve per-passage predictions behind each denominator."""

import argparse
import hashlib
import json
from pathlib import Path

from capex_tracker.guidance.extract import definition
from capex_tracker.guidance.pipeline import extract
from capex_tracker.guidance.records import write_record
from capex_tracker.guidance.sources import DATA, RAW, digest

GOLD = Path("eval/gold")


def ratio(correct, total):
    return {"correct": correct, "n": total, "value": correct / total if total else None}


def scores(rows):
    certain = [r for r in rows if not r["gold"]["uncertain"]]
    positives = [r for r in certain if r["gold"]["kind"] != "none"]
    predicted = [r for r in certain if r["kind"] not in ("none", "invalid")]
    numeric = [r for r in positives if r["gold"]["low"] is not None]
    periods = [r for r in positives if r["gold"]["year"] is not None]
    tp = sum(r["gold"]["kind"] != "none" for r in predicted)
    return dict(
        precision=ratio(tp, len(predicted)),
        recall=ratio(tp, len(positives)),
        numeric_accuracy=ratio(
            sum((r["low"], r["high"]) == (r["gold"]["low"], r["gold"]["high"]) for r in numeric),
            len(numeric),
        ),
        period_accuracy=ratio(
            sum(
                r["kind"] not in ("none", "invalid") and r["year"] == r["gold"]["year"]
                for r in periods
            ),
            len(periods),
        ),
        verification=ratio(sum(r["verified"] for r in predicted), len(predicted)),
    )


def evaluate(split, record):
    destination = Path(f"eval/{split}_results.json")
    if destination.exists():
        raise SystemExit(f"Scoring already completed: {destination}")
    path = GOLD / f"{split}.json"
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    if split == "test" and checksum != (GOLD / "test.sha256").read_text().strip():
        raise ValueError("Frozen test changed")
    sources = {r["accession"]: r for r in json.loads((DATA / "sources.json").read_text())}
    report = {"split_sha256": checksum, "methods": {}}
    for method in ("rules", "ollama"):
        rows = []
        for gold in json.loads(path.read_text()):
            row = sources[gold["accession"]]
            source = (RAW / "clean" / (row["accession"] + ".txt")).read_text()
            assert digest(source) == row["sha256"] and gold["text"] in source
            last = extract(
                method, row, gold["text"], source, definition(row["company"], source), record
            )[-1]
            p = last.get("statement", {}).get("proposal", {})
            checks = last.get("checks", {})
            label = {k: gold[k] for k in ("kind", "year", "low", "high", "uncertain")}
            rows.append(
                dict(
                    id=gold["id"],
                    kind=p.get("guidance_kind", "invalid"),
                    year=p.get("fiscal_year"),
                    low=p.get("low_usd"),
                    high=p.get("high_usd"),
                    gold=label,
                    verified=bool(checks) and all(checks.values()),
                    cassette=last.get("cassette"),
                )
            )
        report["methods"][method] = {"scores": scores(rows), "predictions": rows}
    a, b = (report["methods"][m]["scores"] for m in ("rules", "ollama"))
    report["selected"] = (
        "ollama"
        if (
            b["recall"]["value"] >= a["recall"]["value"] + 0.10
            and b["precision"]["value"] >= a["precision"]["value"]
        )
        else "rules"
    )
    write_record(destination, report)
    print(destination, report["selected"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split", choices=["dev", "test"])
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    evaluate(args.split, args.record)

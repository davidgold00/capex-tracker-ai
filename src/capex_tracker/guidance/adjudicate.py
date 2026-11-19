"""Optional local classification for human review. Never produces an approval."""

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Literal

import requests
from pydantic import BaseModel, Field, ValidationError

from capex_tracker.guidance.extract import direction, rules
from capex_tracker.guidance.provider import call
from capex_tracker.guidance.records import write_record
from capex_tracker.guidance.review import apply, read_csv
from capex_tracker.guidance.sources import CAPEX, DATA, FUTURE, RAW, digest

MODEL = "phi3.5"


class Verdict(BaseModel):
    direction: Literal["up", "down", "flat", "none"]
    year: int | None = Field(ge=2000, le=2100)
    company_wide: bool
    quote: str
    confidence: float = Field(ge=0, le=1)


def eligible(v, passage):
    return (
        v.confidence >= 0.9
        and v.company_wide
        and v.direction != "none"
        and v.year is not None
        and str(v.year) in v.quote
        and v.quote in passage
        and bool(CAPEX.search(v.quote))
        and bool(FUTURE.search(v.quote))
        and direction(v.quote) == v.direction
    )


def classify(passage, live):
    try:
        response, key = call(
            "directional_v1",
            json.dumps({"passage": passage}),
            Verdict.model_json_schema(),
            record=live,
        )
    except (OSError, ValueError, RuntimeError, requests.RequestException) as exc:
        return {"eligible": False, "error": type(exc).__name__}
    try:
        v = Verdict.model_validate_json(response)
    except ValidationError:
        return {"eligible": False, "cassette": key, "error": "Schema rejected"}
    return {"eligible": bool(eligible(v, passage)), "cassette": key, **v.model_dump()}


def run(live):
    os.environ["GUIDANCE_MODEL"] = MODEL
    labels = json.loads(Path("eval/gold/dev.json").read_text())
    results = []
    signatures = ("direction", "year", "company_wide")
    for g in labels:
        if g["uncertain"]:
            continue
        v = classify(g["text"], live)
        positive = g["kind"] == "directional"
        expected = (g["direction"], g["year"], True) if positive else ("none", None, False)
        p = rules(g["text"])
        results.append(
            dict(
                id=g["id"],
                directional=positive,
                correct=tuple(v.get(k) for k in signatures) == expected,
                rules_correct=(p.direction, p.fiscal_year) == expected[:2] if positive else None,
                **v,
            )
        )
    write_record(Path("eval/directional_dev.json"), {"model": MODEL, "results": results})
    suggestions = {}
    for r in read_csv(DATA / "pending.csv"):
        passage = r["evidence_quote"]
        if r["kind"] not in ("directional", "none", "") or not direction(passage):
            continue
        trace = json.loads((DATA / "traces" / (r["id"] + ".json")).read_text())
        src = trace["source"]
        raw = (RAW / "clean" / (src["accession"] + ".txt")).read_text()
        if digest(raw) != src["sha256"] or passage not in raw:
            raise ValueError("Filing evidence mismatch")
        suggestions[r["id"]] = dict(source_sha256=src["sha256"], **classify(passage, live))
    write_record(DATA / "adjudications.json", {"model": MODEL, "items": suggestions})
    apply()
    print(f"{len(results)} dev cases, {len(suggestions)} pending passages examined.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true")
    live = parser.parse_args().record
    try:
        run(live)
    finally:
        if live:
            subprocess.run(["ollama", "stop", MODEL], check=False)

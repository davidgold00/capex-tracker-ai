"""Compare one small local model at a time, using only dev passages and dev filing dates."""

import argparse
import json
import os
import subprocess
import time
from functools import partial
from pathlib import Path

import pandas as pd
import requests

from capex_tracker.cli import _read_processed
from capex_tracker.config import load_config
from capex_tracker.guidance.draft import rephrase
from capex_tracker.guidance.evaluate import scores
from capex_tracker.guidance.extract import definition
from capex_tracker.guidance.ground import factbook
from capex_tracker.guidance.pipeline import extract
from capex_tracker.guidance.provider import call
from capex_tracker.guidance.records import write_record
from capex_tracker.guidance.sources import DATA, RAW, digest

OUT = Path("eval/bakeoff")
MODELS = ("qwen2.5:1.5b-instruct", "qwen2.5:3b-instruct", "llama3.2:3b", "phi3.5")
CASSETTES = OUT / "cassettes"


def run(model, live):
    os.environ["GUIDANCE_MODEL"] = model
    invoke = partial(call, directory=CASSETTES)
    dev = json.loads(Path("eval/gold/dev.json").read_text())
    sources = {r["accession"]: r for r in json.loads((DATA / "sources.json").read_text())}
    rows, drafts = [], []
    rules_seconds = 0.0
    result = {"model": model, "extraction": rows, "rephrasing": drafts}
    try:
        for g in dev:
            r = sources[g["accession"]]
            source = (RAW / "clean" / (r["accession"] + ".txt")).read_text()
            assert digest(source) == r["sha256"] and g["text"] in source
            basis = definition(r["company"], source)
            start = time.perf_counter()
            attempts = extract(
                "rules" if model == "rules" else "ollama",
                r,
                g["text"],
                source,
                basis,
                record=live,
                invoke=invoke,
            )
            rules_seconds += time.perf_counter() - start
            a = attempts[-1]
            p = a.get("statement", {}).get("proposal", {})
            rows.append(
                dict(
                    id=g["id"],
                    kind=p.get("guidance_kind", "invalid"),
                    year=p.get("fiscal_year"),
                    low=p.get("low_usd"),
                    high=p.get("high_usd"),
                    verified=bool(a.get("checks")) and all(a["checks"].values()),
                    gold={k: g[k] for k in ("kind", "year", "low", "high", "uncertain")},
                    cassettes=[a["cassette"] for a in attempts if a.get("cassette")],
                )
            )
        result["scores"] = scores(rows)
        if model == "rules":
            # Hardware timings vary between runs. Persist a new measurement only on request.
            summary = dict(
                model="rules",
                scores=result["scores"],
                extraction=[{k: v for k, v in r.items() if k != "cassettes"} for r in rows],
            )
            dest = OUT / "rules.json"
            if live:
                write_record(
                    dest, dict(**summary, extraction_seconds_per_item=rules_seconds / len(rows))
                )
            else:
                saved = json.loads(dest.read_text())
                assert all(saved[k] == v for k, v in summary.items())
            return
        config = load_config()
        long, _, agg = _read_processed(config)
        # Latest complete quarter preceding each dev filing's calendar quarter.
        for q in sorted({str(pd.Period(g["filed"], freq="Q") - 1) for g in dev}):
            facts = factbook(agg[agg["calendar_quarter"] <= q], long, [], config)
            d = rephrase(facts, partial(invoke, record=live))
            drafts.append(dict(quarter=q, model_pass=d["basis"] == "local-model", **d))
            if any("error" in a for a in d["attempts"]):
                raise RuntimeError("Local rephrasing transport failure")
    except (OSError, ValueError, requests.RequestException, RuntimeError) as exc:
        result["failure"] = type(exc).__name__
        if isinstance(exc, RuntimeError) and str(exc).startswith("Recorded transport failure: "):
            result["failure"] = str(exc).split(": ")[-1]
    finally:
        if live and model != "rules":
            subprocess.run(["ollama", "stop", model], check=False)
    for job, groups in (
        ("extraction", [r["cassettes"] for r in rows]),
        ("rephrasing", [[a["cassette"] for a in d["attempts"] if "cassette" in a] for d in drafts]),
    ):
        times = [
            json.loads((CASSETTES / (k + ".json")).read_text()).get("duration_ns")
            for group in groups
            for k in group
        ]
        result[job + "_seconds_per_item"] = (
            sum(times) / 1e9 / len(groups)
            if groups and times and all(x is not None for x in times)
            else None
        )
    path = OUT / (model.replace(":", "_") + ".json")
    if live:
        write_record(path, result)
    elif result != json.loads(path.read_text()):
        raise ValueError("Replay differs from the recorded dev benchmark")
    print(model, len(rows), len(drafts), result.get("failure", "completed"), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("model", choices=("rules", *MODELS))
    p.add_argument("--record", action="store_true")
    a = p.parse_args()
    run(a.model, a.record)

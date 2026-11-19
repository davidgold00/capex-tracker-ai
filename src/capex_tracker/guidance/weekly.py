"""Incremental SEC guidance updates and browser decisions. Model-free entry point."""

import argparse
import json

from capex_tracker.config import load_config
from capex_tracker.guidance import sources
from capex_tracker.guidance.extract import attach, candidate_id, definition, rules, verify
from capex_tracker.guidance.records import write_record
from capex_tracker.guidance.review import apply, read_csv, write_csv
from capex_tracker.guidance.sources import DATA, RAW
from capex_tracker.sec_client import SecClient


def scan(row, text, directory, coverage):
    if sources.digest(text) != row["sha256"]:
        raise ValueError("Source hash mismatch")
    basis = definition(row["company"], text)
    for passage in sources.windows(text):
        cid = candidate_id(row, passage)
        p = rules(passage)
        statement = attach(row, passage, p, basis)
        checks = verify(statement, text) if p.guidance_kind != "none" else {}
        path = directory / "traces" / (cid + ".json")
        trace = json.loads(path.read_text()) if path.exists() else {}
        trace.update(
            id=cid,
            source=row,
            passage=passage,
            rules=[dict(statement=statement.model_dump(mode="json"), checks=checks, cassette=None)],
        )
        write_record(path, trace)
        if p.guidance_kind != "none":
            lang = "numeric" if p.guidance_kind.startswith("numeric") else "directional"
            old = coverage.get(row["accession"], {})
            if not old or (lang == "numeric" and old["language"] != "numeric"):
                coverage[row["accession"]] = dict(
                    company=row["company"],
                    accession=row["accession"],
                    language=lang,
                    evidence_id=cid,
                )


def hydrate_decisions(directory=DATA):
    client = None
    clean_dir = RAW / "clean"
    for r in read_csv(directory / "pending.csv"):
        if r["decision"].strip().lower() != "approve":
            continue
        # Resolve the URL and checksum from the saved filing trace, never the edited CSV.
        trace = json.loads((directory / "traces" / (r["id"] + ".json")).read_text())
        src = trace["source"]
        path = clean_dir / (src["accession"] + ".txt")
        if path.exists() and sources.digest(path.read_text()) == src["sha256"]:
            continue
        client = client or SecClient(load_config())
        raw = sources.download(client, src["url"])
        text = sources.clean(raw.decode("utf-8", errors="replace"), src["form"])
        if sources.digest(text) != src["sha256"]:
            raise ValueError("Cannot reproduce filing text: " + src["accession"])
        clean_dir.mkdir(exist_ok=True, parents=True)
        path.write_text(text)


def weekly(refresh=True, decisions_only=False):
    if not decisions_only:
        coverage = {r["accession"]: r for r in read_csv(DATA / "coverage.csv")}
        sources.fetch(refresh=refresh, on_new=lambda row, text: scan(row, text, DATA, coverage))
        write_csv(
            DATA / "coverage.csv",
            ["company", "accession", "language", "evidence_id"],
            sorted(coverage.values(), key=lambda r: (r["company"], r["accession"])),
        )
    hydrate_decisions()
    apply(auto=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--decisions-only", action="store_true")
    p.add_argument("--cached", action="store_true")
    args = p.parse_args()
    weekly(not args.cached, args.decisions_only)

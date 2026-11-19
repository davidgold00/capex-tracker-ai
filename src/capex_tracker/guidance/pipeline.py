"""Record or replay both extractors on the SEC inventory. Retain attempts and failures."""

import argparse
import json

from pydantic import ValidationError

from capex_tracker.guidance.extract import attach, candidate_id, definition, rules, verify
from capex_tracker.guidance.provider import call
from capex_tracker.guidance.records import write_record
from capex_tracker.guidance.schema import Proposal
from capex_tracker.guidance.sources import DATA, RAW, digest, windows


def extract(method, row, sentence, source, basis, record=False, invoke=call):
    attempts = []
    failure = ""
    for _ in range(2 if method == "ollama" else 1):
        key = None
        if method == "rules" or not windows(sentence):
            result = rules(sentence)
        else:
            content = json.dumps({"passage": sentence}, ensure_ascii=False)
            if failure:
                content += "\nCheck the preceding proposal again: " + failure
            raw, key = invoke("extract_v1", content, Proposal.model_json_schema(), record=record)
            try:
                result = Proposal.model_validate_json(raw)
            except ValidationError as exc:
                failure = "; ".join(str(e["loc"]) + " " + e["msg"] for e in exc.errors())
                attempts.append({"cassette": key, "error": failure})
                continue
        statement = attach(row, sentence, result, basis)
        checks = verify(statement, source) if result.guidance_kind != "none" else {}
        attempt = {
            "statement": statement.model_dump(mode="json"),
            "checks": checks,
            "cassette": key,
        }
        attempts.append(attempt)
        failure = ", ".join(k for k, ok in checks.items() if not ok)
        if not failure:
            break
    return attempts


def run(record=False):
    for row in json.loads((DATA / "sources.json").read_text()):
        if "sha256" not in row:
            continue
        source = (RAW / "clean" / (row["accession"] + ".txt")).read_text()
        if digest(source) != row["sha256"]:
            raise ValueError("Clean document hash mismatch")
        basis = definition(row["company"], source)
        for sentence in windows(source):
            cid = candidate_id(row, sentence)
            trace = {"id": cid, "source": row, "passage": sentence}
            for method in ("rules", "ollama"):
                trace[method] = extract(method, row, sentence, source, basis, record)
            write_record(DATA / "traces" / (cid + ".json"), trace)
        print(row["company"], row["filed"], row["windows"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true")
    run(parser.parse_args().record)

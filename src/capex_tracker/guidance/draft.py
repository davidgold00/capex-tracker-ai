"""Locally draft one quarterly paragraph, retaining responses for offline replay."""

import argparse
import json

from pydantic import BaseModel, ValidationError

from capex_tracker.cli import _read_processed
from capex_tracker.config import load_config
from capex_tracker.guidance.ground import check, factbook
from capex_tracker.guidance.provider import call
from capex_tracker.guidance.records import write_record
from capex_tracker.guidance.review import read_csv
from capex_tracker.guidance.sources import DATA


class Draft(BaseModel):
    paragraph: str


def draft(record):
    config = load_config()
    long, _, aggregate = _read_processed(config)
    facts = factbook(aggregate, long, read_csv(DATA / "approved.csv"), config)
    request = json.dumps(facts.groups)
    attempts = []
    paragraph = ""
    for _ in range(2):
        raw, key = call("draft_v1", request, Draft.model_json_schema(), record=record)
        try:
            candidate = Draft.model_validate_json(raw).paragraph
            reasons = check(candidate, facts)
        except ValidationError:
            reasons = ["Invalid paragraph object"]
        attempts.append(dict(cassette=key, reasons=reasons))
        if not reasons:
            paragraph = candidate
            break
        request = json.dumps(facts.groups) + "\nRepair the draft: " + "; ".join(reasons)
    write_record(
        DATA / "draft.json", dict(facts_sha256=facts.key, paragraph=paragraph, attempts=attempts)
    )
    print(paragraph or "Draft withheld after two failed checks.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--record", action="store_true")
    draft(p.parse_args().record)

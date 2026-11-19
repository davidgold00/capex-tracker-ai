"""Locally draft one quarterly paragraph, retaining responses for offline replay."""

import argparse
import json

import requests
from pydantic import BaseModel, ValidationError

from capex_tracker.cli import _read_processed
from capex_tracker.config import load_config
from capex_tracker.guidance.ground import check, factbook, template
from capex_tracker.guidance.provider import call
from capex_tracker.guidance.records import write_record
from capex_tracker.guidance.review import read_approved
from capex_tracker.guidance.sources import DATA


class Draft(BaseModel):
    paragraph: str


def rephrase(facts, invoke):
    plan = json.dumps({"planned_facts": facts.groups})
    request = plan
    attempts = []
    paragraph = ""
    for _ in range(2 if facts.groups and invoke else 0):
        try:
            raw, key = invoke("draft_v2", request, Draft.model_json_schema())
        except (OSError, RuntimeError, ValueError, requests.RequestException) as exc:
            attempts.append(dict(error=type(exc).__name__, reasons=["Local call unavailable"]))
            break
        try:
            candidate = Draft.model_validate_json(raw).paragraph
            reasons = check(candidate, facts)
        except ValidationError:
            reasons = ["Invalid paragraph object"]
        attempts.append(dict(cassette=key, reasons=reasons))
        if not reasons:
            paragraph = candidate
            break
        request = plan + "\nRepair the draft: " + "; ".join(reasons)
    return dict(
        facts_sha256=facts.key,
        paragraph=paragraph or template(facts),
        basis="local-model" if paragraph else "template",
        attempts=attempts,
    )


def draft(record):
    config = load_config()
    long, _, aggregate = _read_processed(config)
    facts = factbook(aggregate, long, read_approved(DATA), config)
    result = rephrase(facts, lambda *args: call(*args, record=record))
    write_record(DATA / "draft.json", result)
    print(result["basis"], result["paragraph"])


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--record", action="store_true")
    draft(p.parse_args().record)

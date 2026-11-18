import json
from pathlib import Path

import pytest

from capex_tracker.cli import _read_processed
from capex_tracker.config import load_config
from capex_tracker.guidance.ground import check, factbook, publish
from capex_tracker.guidance.review import read_csv


def ledger():
    config = load_config()
    long, _, aggregate = _read_processed(config)
    return factbook(aggregate, long, read_csv(Path("data/guidance/approved.csv")), config)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda text: text.replace("$", "$9", 1),
        lambda text: (
            text.replace("rose", "fell", 1) if "rose" in text else text.replace("fell", "rose", 1)
        ),
        lambda text: text + " Acme expanded.",
        lambda text: "During Q1 2099 " + text,
        lambda text: text + " Management expects further gains.",
        lambda text: "It did not happen. " + text,
    ],
)
def test_reject_unbound_claims(mutate):
    facts = ledger()
    good = " ".join(g[0] for g in facts.groups)
    assert not check(good, facts)
    assert check(mutate(good), facts)


def test_reject_stale_published_draft(tmp_path):
    facts = ledger()
    path = tmp_path / "draft.json"
    para = " ".join(g[0] for g in facts.groups)
    text = "<!-- WHAT_CHANGED:START -->\nold\n<!-- WHAT_CHANGED:END -->"
    path.write_text(json.dumps({"paragraph": para, "facts_sha256": "stale"}))
    assert para not in publish(text, path, facts)
    path.write_text(json.dumps({"paragraph": para, "facts_sha256": facts.key}))
    assert para in publish(text, path, facts)

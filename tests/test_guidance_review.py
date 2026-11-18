import json

import pytest

from capex_tracker.guidance.extract import attach, rules, verify
from capex_tracker.guidance.review import EDITS, FIELDS, apply, read_csv, write_csv


def test_auto_then_manual_review_is_idempotent(tmp_path, monkeypatch):
    from capex_tracker.guidance import review

    passage = "We expect 2026 capital expenditures of $12 to $14 billion."
    note = "Capital expenditures, including principal payments on finance leases"
    source = passage + "\n" + note
    from capex_tracker.guidance.sources import digest

    row = dict(
        company="META",
        filed="2025-11-03",
        form="8-K",
        sha256=digest(source),
        url="https://www.sec.gov/Archives/edgar/data/1/a.htm",
        accession="0000000001-25-000001",
    )
    s = attach(
        row, passage, rules(passage), ("capex_lease_adjusted", note, "Includes lease principal")
    )
    attempt = {"statement": s.model_dump(mode="json"), "checks": verify(s, source)}
    traces = tmp_path / "traces"
    traces.mkdir()
    for cid, b in [
        ("yes", {**attempt, "cassette": "recorded-fixture"}),
        ("needs-review", {"error": "invalid JSON"}),
    ]:
        trace = {"id": cid, "source": row, "passage": passage, "rules": [attempt], "ollama": [b]}
        (traces / (cid + ".json")).write_text(json.dumps(trace))
    apply(tmp_path, auto=True)
    assert [r["id"] for r in read_csv(tmp_path / "approved.csv")] == ["yes"]
    pending = read_csv(tmp_path / "pending.csv")
    assert [r["id"] for r in pending] == ["needs-review"]
    pending[0]["decision"] = "approve"
    write_csv(tmp_path / "pending.csv", FIELDS + EDITS, pending)
    monkeypatch.setattr(review, "RAW", tmp_path)
    (tmp_path / "clean").mkdir()
    (tmp_path / "clean" / (row["accession"] + ".txt")).write_text(source)
    apply(tmp_path)
    first = (tmp_path / "audit.json").read_bytes()
    apply(tmp_path)
    assert (tmp_path / "audit.json").read_bytes() == first
    assert {r["approved_by"] for r in read_csv(tmp_path / "approved.csv")} == {
        "manual",
        "auto-dual-match",
    }

    assert len(review.read_approved(tmp_path)) == 2
    changed = read_csv(tmp_path / "approved.csv")
    changed[0]["low"] = "1"
    write_csv(tmp_path / "approved.csv", FIELDS, changed)
    with pytest.raises(ValueError, match="audit log"):
        review.read_approved(tmp_path)

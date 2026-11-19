import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

from test_cli import write_workspace


def test_complete_update_cannot_import_model_or_open_network(tmp_path):
    config = write_workspace(tmp_path, capex_annual=100.0)
    paths = config.parent
    (paths / "notes").mkdir(exist_ok=True)
    (paths / "README.md").write_text(Path("README.md").read_text())
    # A miniature cache uses the same SEC client as the weekly Action.
    raw = paths / "raw"
    cached = next(raw.glob("companyfacts_*"))
    settings = yaml.safe_load(config.read_text())
    companies = yaml.safe_load(Path("config.yaml").read_text())["companies"]
    settings["companies"] = companies
    config.write_text(yaml.safe_dump(settings))
    tickers = {}
    for index, c in enumerate(companies):
        ticker = c["ticker"]
        tickers[str(index)] = {"ticker": ticker, "cik_str": index + 1}
        (raw / f"companyfacts_{ticker}_20990101T000000Z.json").write_bytes(cached.read_bytes())
    (raw / "company_tickers_20990101T000000Z.json").write_text(json.dumps(tickers))
    guidance = paths / "guidance"
    guidance.mkdir()
    (guidance / "sources.json").write_text("[]")
    (guidance / "approved.csv").write_text("id,company,period,comparison_series\n")
    code = """
import sys, socket
class Block:
    def find_spec(self, name, *args):
        if name.startswith(("capex_tracker.guidance.provider","ollama")):
            raise AssertionError("Weekly update imported a model provider")
sys.meta_path.insert(0,Block())
def offline(*args, **kwargs):
    raise AssertionError("Weekly rendering attempted a network connection")
socket.socket.connect=offline
from capex_tracker.cli import main
sys.exit(main(["--config",sys.argv[1],"update"]))
"""
    env = {**os.environ, "SEC_USER_AGENT": "offline-test"}
    subprocess.run([sys.executable, "-c", code, str(config)], check=True, env=env)
    assert (paths / "charts" / "guidance_path.png").exists()
    assert (paths / "processed" / "guidance_paths.csv").exists()


def test_incremental_rules_and_policy_run_without_model(tmp_path, monkeypatch):
    from capex_tracker.guidance import sources, weekly
    from capex_tracker.guidance.review import apply, read_approved, read_csv

    passage = "We expect 2025 capital expenditures of $64 to $72 billion."
    note = "Capital expenditures, including principal payments on finance leases."
    release = dict(
        company="META",
        accession="0000000001-25-000001",
        form="8-K",
        filed="2025-04-30",
        results_period="2025-03-31",
        url="https://www.sec.gov/Archives/edgar/data/1/release.htm",
    )
    filing = {
        **release,
        "accession": "0000000001-25-000002",
        "form": "10-Q",
        "filed": "2025-05-01",
        "url": release["url"].replace("release", "report"),
    }
    rows = []
    coverage = {}
    for r in (release, filing):
        text = r["form"] + "\n" + note + "\n" + passage
        r["sha256"] = sources.digest(text)
        weekly.scan(r, text, tmp_path, coverage)
        rows.append(r)
    (tmp_path / "sources.json").write_text(json.dumps(rows))
    apply(tmp_path, auto=True)
    assert len(read_approved(tmp_path)) == 1 and len(coverage) == 2
    # No model attempt is invented for CI-only material.
    assert all(
        "ollama" not in json.loads(p.read_text()) for p in (tmp_path / "traces").glob("*.json")
    )
    text = note + "\n" + passage + "\n" + passage.replace("72", "76")
    filing["sha256"] = sources.digest(text)
    weekly.scan(filing, text, tmp_path, coverage)
    apply(tmp_path, auto=True)
    assert not read_approved(tmp_path)
    assert len(read_csv(tmp_path / "pending.csv")) == 2
    assert json.loads((tmp_path / "audit.json").read_text())["history"][-1]["after"] is None


def test_weekly_module_has_no_model_dependency():
    code = """
import sys
class Block:
    def find_spec(self, name, *args):
        if name.startswith(("capex_tracker.guidance.provider", "ollama")):
            raise AssertionError(name)
sys.meta_path.insert(0, Block())
from capex_tracker.guidance import weekly
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_review_issue_sync_is_idempotent(monkeypatch):
    import runpy

    script = runpy.run_path("scripts/review_issue.py")
    sync = script["sync"]
    issue = {}
    changes = []

    def api(*args, payload=None):
        if payload:
            changes.append(payload)
            issue.update(payload)
            issue.update(number=1, state="open", user={"login": "github-actions[bot]"})
            return issue
        if "comments" in args[-1]:
            return [[]]
        return [[issue]] if issue else [[]]

    monkeypatch.setitem(sync.__globals__, "gh", api)
    sync()
    sync()
    assert len(changes) == 1
    assert changes[0]["title"] == "Guidance claims awaiting review"
    assert "https://www.sec.gov/" in changes[0]["body"]

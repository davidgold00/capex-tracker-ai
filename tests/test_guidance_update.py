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

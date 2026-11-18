"""Only local commands import this module. The replay path performs no I/O over HTTP."""

import json
import os
from pathlib import Path

import requests

from capex_tracker.guidance.records import write_record
from capex_tracker.guidance.sources import DATA, digest

PROMPTS = Path(__file__).with_name("prompts")
DEFAULT_MODEL = "qwen2.5:7b-instruct"


def call(task, content, schema, *, record=False, directory=DATA / "cassettes"):
    settings = DATA / "model.json"
    recorded = json.loads(settings.read_text())["model"] if settings.is_file() else DEFAULT_MODEL
    model = os.environ.get("GUIDANCE_MODEL", recorded)
    system = (PROMPTS / (task + ".txt")).read_text().strip()
    payload = dict(
        model=model,
        system=system,
        prompt=content,
        format=schema,
        stream=False,
        options={"temperature": 0, "seed": 42, "num_predict": 350},
    )
    key = digest(json.dumps(payload, sort_keys=True))
    path = directory / (key + ".json")
    if path.exists():
        cached = json.loads(path.read_text())
        if cached["key"] != key or cached["request"] != payload:
            raise ValueError("Cassette does not match request")
        return cached["response"], key
    if not record:
        raise FileNotFoundError(f"Missing offline cassette {key}")
    # Verify the tag exists locally. Reject cloud-only tags and never follow redirects.
    with requests.Session() as session:
        session.trust_env = False
        base = "http://127.0.0.1:11434"
        info = session.post(
            base + "/api/show", json={"model": model}, timeout=20, allow_redirects=False
        )
        info.raise_for_status()
        details = info.json()
        if details.get("remote_model") or details.get("remote_host") or "cloud" in model.lower():
            raise ValueError("A locally installed model is required")
        res = session.post(base + "/api/generate", json=payload, timeout=180, allow_redirects=False)
        res.raise_for_status()
        response = res.json()["response"]
    write_record(path, {"key": key, "request": payload, "response": response})
    return response, key

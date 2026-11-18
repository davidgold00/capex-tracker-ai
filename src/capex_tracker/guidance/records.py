"""JSON records contain application data only. Discard HTTP metadata at any depth."""

import json
from pathlib import Path


def public_record(value):
    if isinstance(value, dict):
        return {
            key: public_record(item)
            for key, item in value.items()
            if "header" not in key.lower()
            and key.lower() not in {"authorization", "cookie", "set-cookie", "user-agent"}
        }
    if isinstance(value, (tuple, list)):
        return [public_record(item) for item in value]
    return value


def write_record(path: Path, record: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(public_record(record), indent=2, sort_keys=True) + "\n")
    temp.replace(path)

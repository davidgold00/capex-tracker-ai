"""Refresh only the embedded data in the standalone GitHub Pages explainer."""

import json
import re
from pathlib import Path

from capex_tracker.guidance.review import read_csv

ROOT = Path(__file__).resolve().parents[1]


def data(root=ROOT):
    readme = (root / "README.md").read_text()

    def section(name):
        return readme.split(f"<!-- {name}:START -->")[1].strip().split("\n")[0].strip("*")

    directory = root / "data/processed"
    actuals = [
        dict(
            q=r["calendar_quarter"],
            capex=float(r["ttm_capex"]) / 1e9,
            ocf=float(r["ttm_ocf"]) / 1e9,
        )
        for r in read_csv(directory / "aggregate.csv")
        if r["partial"].lower() == "false" and r["ttm_capex"] and r["ttm_ocf"]
    ]
    truth = json.loads((root / "eval/test_results.json").read_text())
    models = []
    for model in ("rules", "qwen2.5_1.5b-instruct", "qwen2.5_3b-instruct", "llama3.2_3b", "phi3.5"):
        r = json.loads((root / f"eval/bakeoff/{model}.json").read_text())
        drafts = r.get("rephrasing", [])
        models.append(
            dict(
                name=r["model"],
                scores=r.get("scores", {}),
                passed=sum(d["model_pass"] for d in drafts),
                plans=len(drafts),
                extract_seconds=r.get("extraction_seconds_per_item"),
                draft_seconds=r.get("rephrasing_seconds_per_item"),
            )
        )
    return dict(
        headline=section("HEADLINE"),
        finding=section("GUIDANCE"),
        actuals=actuals,
        guidance=read_csv(directory / "guidance_paths.csv"),
        models=models,
        test={method: r["scores"] for method, r in truth["methods"].items()},
        changed=section("WHAT_CHANGED"),
    )


def render(root=ROOT):
    path = root / "docs/index.html"
    payload = json.dumps(data(root), ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    payload = payload.replace("<", "\\u003c")
    original = path.read_text()
    revised, n = re.subn(
        r'(?s)(<script type="application/json" id="evidence">).*?(</script>)',
        lambda m: m[1] + payload + m[2],
        original,
    )
    if n != 1:
        raise ValueError("Expected one embedded evidence object")
    path.write_text(revised)


if __name__ == "__main__":
    render()

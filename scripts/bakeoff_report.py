"""Render the dev bake-off from recorded observations."""

import json
from pathlib import Path

from model_bakeoff import MODELS, OUT


def fraction(count, n):
    return f"{count / n:.1%} ({count}/{n}, n={n})" if n else "Not measured"


def fmt(value):
    return "Not measured" if value is None else f"{value:.4f}"


def size(value):
    return f"{value / 2**30:.2f} GiB" if value else "Not measured"


def main():
    lines = [
        "# Small-model bake-off on the dev split",
        "",
        "Each extractor saw the same 21 dev passages. One uncertain label is excluded "
        "from scoring. Precision and recall score positive detection. Verification requires "
        "all checks on the predicted positives. Each writer received the same six plans, "
        "one per distinct preceding calendar quarter represented by dev filing dates. "
        "Plans include the quarterly and annual capex comparisons. No held-out passage "
        "or current-quarter plan is used for model selection.",
        "",
        "| Method | Precision | Recall | Verified | Extraction s/item | Grounded | Draft s/plan |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    models = []
    for name in ("rules", *MODELS):
        result = json.loads((OUT / (name.replace(":", "_") + ".json")).read_text())
        scores = result.get("scores", {})
        drafts = result.get("rephrasing", [])
        cells = [name]
        for key in ("precision", "recall", "verification"):
            s = scores.get(key, {})
            cells.append(fraction(s.get("correct", 0), s.get("n", 0)))
        cells.append(fmt(result.get("extraction_seconds_per_item")))
        cells.append(fraction(sum(d["model_pass"] for d in drafts), len(drafts)))
        cells.append(fmt(result.get("rephrasing_seconds_per_item")))
        lines.append("| " + " | ".join(cells) + " |")
        if name != "rules":
            models.append(result)
    eligible = [m for m in models if "scores" in m and len(m["rephrasing"]) == 6]
    writer = max(
        eligible,
        key=lambda m: (
            sum(d["model_pass"] for d in m["rephrasing"]),
            -m["rephrasing_seconds_per_item"],
        ),
    )

    def directional_score(model):
        rows = model["extraction"]
        directionals = [
            r
            for r in rows
            if not r["gold"]["uncertain"]
            and r["gold"]["kind"] == "directional"
            and r["kind"] == "directional"
        ]
        return (
            len(directionals),
            model["scores"]["recall"]["value"],
            model["scores"]["precision"]["value"] or 0,
        )

    extractor = max(eligible, key=directional_score)
    lines.extend(
        [
            "",
            "**Extraction:** rules. The original rule requires a 0.10 recall "
            "advantage without losing precision. No model can exceed rules on this dev split. "
            "The original frozen test remains the only selection test.",
            "",
            f"**Rephrasing:** {writer['model']} had the highest number of verified plans "
            "(lowest measured seconds per plan breaks ties). "
            "No template fallback counts as a model pass.",
            "",
            f"**Adjudication candidate:** {extractor['model']} among completed local models, "
            "ordered by correct directional detections, then overall recall and precision. "
            "This exploratory dev choice still needs a separate classification measurement.",
            "",
            "One Llama 3.2 proposal passed all original checks on gold-f5972fda04, a negative "
            "example about depreciation expenses. A direction word, year and capex reference "
            "can coexist without referring to the same metric. A verification pass by itself "
            "does not establish correct classification.",
            "",
            "Time is total Ollama generate duration including retries and initial load, "
            "divided by all 21 passages or six plans. Screened-out passages contribute zero "
            "model time. Rules time is a wall-clock measurement of proposal and verification "
            "on 21 in-memory documents with precomputed definitions. File I/O is excluded.",
            "",
            "| Local model | Load / completion | Largest observed allocation | "
            "Largest observed runner RSS |",
            "|---|---|---:|---:|",
        ]
    )
    memory = json.loads((OUT / "memory.json").read_text())
    for m in models:
        stats = memory.get(m["model"], {})

        lines.append(
            f"| {m['model']} | {m.get('failure', 'Completed')} | "
            f"{size(stats.get('max_ollama_allocation'))} | {size(stats.get('max_runner_rss'))} |"
        )
    lines.extend(
        [
            "",
            "Memory is a sampled high-water observation, not a process lifetime peak. "
            "Allocation includes memory Ollama attributes to the loaded model. RSS excludes "
            "some GPU allocations. Qwen 1.5B has a single observation. Rate samples for "
            "the remaining runners were taken about every two seconds.",
            "",
            "[Per-item results, request/response cassettes and durations](bakeoff/). "
            "Replay from the cached clean filing texts with "
            "`PYTHONPATH=src python scripts/model_bakeoff.py MODEL`. "
            "Only `--record` permits loopback inference. The defaults limit live model size.",
        ]
    )
    Path("eval/MODEL_BAKEOFF.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()

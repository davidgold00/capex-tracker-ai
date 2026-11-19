"""Keep one GitHub review issue in sync with the browser-editable queue."""

import json
import subprocess

from capex_tracker.guidance.review import read_csv
from capex_tracker.guidance.sources import DATA

TITLE = "Guidance claims awaiting review"
MARK = "<!-- capex-review-page-"


def gh(*args, payload=None):
    raw = subprocess.check_output(
        ["gh", "api", *args, *(["--input", "-"] if payload else [])],
        input=json.dumps(payload) if payload else None,
        text=True,
    )
    return json.loads(raw) if raw.strip() else None


def pages(rows):
    result = [
        "Edit the decision column in [pending.csv]("
        "https://github.com/davidgold00/capex-tracker-ai/blob/main/data/guidance/pending.csv) "
        "on GitHub. Use approve or reject. Approvals must pass filing checks.\n\n"
        f"Pending review items: {len(rows)}."
    ]
    for r in rows:
        quote = r["evidence_quote"].replace("\n", " ")
        if len(quote) > 1300:
            quote = quote[:1300].rsplit(" ", 1)[0] + " [...]"
        label = f"{r['form']}, {r['statement_date']}"
        line = f"\n\n**{r['id']}** ([{label}]({r['source_url']}))\n> {quote}"
        if len(result[-1]) + len(line) > 55000:
            result.append("")
        result[-1] += line
    return result


def sync():
    root = "repos/{owner}/{repo}/issues"
    rows = read_csv(DATA / "pending.csv")
    issues = gh("--paginate", "--slurp", root + "?state=all&per_page=100")
    issue = next(
        (
            i
            for page in issues
            for i in page
            if i["title"] == TITLE
            and "pull_request" not in i
            and i["user"]["login"] == "github-actions[bot]"
        ),
        None,
    )
    if not rows and not issue:
        return
    chunks = pages(rows)
    state = "open" if rows else "closed"
    if issue:
        endpoint = root + "/" + str(issue["number"])
        if issue["body"] != chunks[0] or issue["state"] != state:
            gh("-X", "PATCH", endpoint, payload={"body": chunks[0], "state": state})
    else:
        issue = gh("-X", "POST", root, payload={"title": TITLE, "body": chunks[0]})
        endpoint = root + "/" + str(issue["number"])
    existing = gh("--paginate", "--slurp", endpoint + "/comments?per_page=100")
    owned = {
        c["body"].splitlines()[0]: c
        for page in existing
        for c in page
        if c["user"]["login"] == "github-actions[bot]" and c["body"].startswith(MARK)
    }
    for i, chunk in enumerate(chunks[1:], 1):
        marker = f"{MARK}{i} -->"
        body = marker + "\n" + chunk
        comment = owned.pop(marker, None)
        if comment is None:
            gh("-X", "POST", endpoint + "/comments", payload={"body": body})
        elif comment["body"] != body:
            gh("-X", "PATCH", root + "/comments/" + str(comment["id"]), payload={"body": body})
    for comment in owned.values():
        gh("-X", "DELETE", root + "/comments/" + str(comment["id"]))


if __name__ == "__main__":
    sync()

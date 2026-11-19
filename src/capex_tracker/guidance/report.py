"""Publish only reviewed rows, joined by fiscal year and matching spending definition."""

import csv
import json
from collections import Counter, defaultdict
from statistics import median

import pandas as pd

from capex_tracker.guidance.review import read_approved, read_csv
from capex_tracker.readme import replace_section


def paths(approved, wide):
    rows = []
    keys = ["company", "period", "comparison_series"]
    groups = defaultdict(list)
    for r in approved:
        groups[tuple(r[k] for k in keys)].append(r)
    for (ticker, year, series), observations in sorted(groups.items()):
        fiscal = wide[
            (wide["ticker"] == ticker)
            & wide["fiscal_label"].isin([f"FY{year} Q{q}" for q in range(1, 5)])
        ]
        actual = None
        if (
            len(fiscal) == 4
            and fiscal["fiscal_label"].nunique() == 4
            and fiscal[series].notna().all()
        ):
            actual = int(fiscal[series].sum())
        initial = previous = None
        seen = set()
        for r in sorted(observations, key=lambda r: (r["statement_date"], r["id"])):
            low, high = (int(r[k]) if r[k] else None for k in ("low", "high"))
            mid = (low + high) / 2 if low is not None and high is not None else None
            change = None
            if mid is None:
                stage = "directional"
            elif previous == (low, high):
                stage = "reaffirmed"
            elif initial is None:
                stage, initial = "initial", mid
            else:
                stage = "revision"
                change = mid - sum(previous) / 2
            if mid is not None:
                previous = (low, high)
            signature = (r["statement_date"], low, high, r["direction"])
            if signature in seen:
                continue
            seen.add(signature)
            rows.append(
                dict(
                    id=r["id"],
                    company=ticker,
                    fiscal_year=year,
                    date=r["statement_date"],
                    end=r["calendar_end"],
                    series=series,
                    stage=stage,
                    low=low,
                    high=high,
                    direction=r["direction"],
                    revision_usd=change,
                    actual=actual,
                    gap=(actual / initial - 1 if actual is not None and initial else None),
                    source=r["source_url"],
                    approved_by=r.get("approved_by", "manual"),
                )
            )
    return rows


def finding(rows, audit_status="pending human audit"):
    if not rows:
        return (
            "No annual forecast passed review (n=0). Actual versus initial midpoint: Not measured."
        )
    counts = Counter(r["company"] for r in rows)
    ticker, count = counts.most_common(1)[0]
    focus = [r for r in rows if r["company"] == ticker] if count > len(rows) / 2 else rows
    name = {
        "META": "Meta",
        "AMZN": "Amazon",
        "GOOGL": "Alphabet",
        "MSFT": "Microsoft",
        "ORCL": "Oracle",
    }.get(ticker, ticker)
    subject = name if count > len(rows) / 2 else "The covered issuers"
    revisions = [r for r in focus if r["stage"] == "revision"]
    raised = sum(r["revision_usd"] > 0 for r in revisions)
    completed = [r["gap"] for r in focus if r["stage"] == "initial" and r["gap"] is not None]
    basis = Counter(r.get("approved_by", "manual") for r in rows)
    bases = ", ".join(f"{n} {k}" for k, n in sorted(basis.items()))
    coverage = (
        f"{count}/{len(rows)} from {name}" if len(focus) == count else f"{len(counts)} issuers"
    )
    movement = (
        f"{subject} raised the midpoint in {raised} of {len(revisions)} revisions"
        if revisions
        else f"{subject} had no observed revisions (n=0)"
    )
    gap = (
        f"actual spending was a median {median(completed):+.1%} versus the first approved "
        f"midpoint (n={len(completed)} completed fiscal years)"
        if completed
        else "actual versus first approved midpoint was Not measured (n=0 completed fiscal years)"
    )
    return f"{movement} and {gap}, based on {bases} SEC claims ({coverage}, {audit_status})."


def fiscal_table(rows):
    lines = [
        "| Issuer / FY | First approved range | Last approved range | Actual | "
        "Gap vs first midpoint |",
        "|---|---:|---:|---:|---:|",
    ]
    from capex_tracker.readme import billions

    groups = defaultdict(list)
    for row in rows:
        if row["low"] is not None:
            groups[row["company"], row["fiscal_year"], row["series"]].append(row)
    for (company, year, series), group in groups.items():
        first, last = group[0], group[-1]
        ranges = [f"{billions(r['low'])} to {billions(r['high'])}" for r in (first, last)]
        actual = billions(first["actual"]) if first["actual"] is not None else "Not measured"
        gap = f"{first['gap']:+.1%} (n=1)" if first["gap"] is not None else "Not measured"
        measure = (
            "including lease principal" if series == "capex_lease_adjusted" else "reported capex"
        )
        lines.append(
            f"| {company} FY{year}, {measure} | {ranges[0]} | {ranges[1]} | {actual} | {gap} |"
        )
    return "\n".join(lines) if groups else ""


def coverage(manifest, evidence, config):
    notes = []
    for company in config.spenders:
        docs = {
            r["accession"] for r in manifest if r["company"] == company.ticker and "sha256" in r
        }
        matches = [r for r in evidence if r["accession"] in docs]
        numeric = sum(r["language"] == "numeric" for r in matches)
        directional = len(matches) - numeric
        notes.append(
            f"{company.name} {len(matches)}/{len(docs)} ({numeric} numeric, "
            f"{directional} direction only)"
        )
    return (
        "Documents with an identified company-wide spending forecast among SEC filings read: "
        + ", ".join(notes)
        + ". One document counts once. Additional guidance given on calls "
        "is outside this filing-only search."
    )


def chart(rows, config, path):
    from matplotlib import pyplot as plt
    from matplotlib.lines import Line2D

    from capex_tracker import charts

    charts.apply_style()
    groups = defaultdict(list)
    for row in rows:
        groups[(row["company"], row["fiscal_year"], row["series"])].append(row)
    cols = min(3, max(1, len(groups)))
    nrows = max(1, (len(groups) + cols - 1) // cols)
    fig, axes = plt.subplots(nrows, cols, squeeze=False, figsize=(10, 2.45 * nrows + 1.65))
    for ax in axes.flat:
        ax.set_visible(False)
    if not groups:
        ax = axes[0, 0]
        ax.set_visible(True)
        ax.set_axis_off()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.text(
            0.05, 0.85, "Filed guidance versus actual capital spending", fontsize=16, weight="bold"
        )
        ax.text(0.05, 0.63, "No approved annual forecasts", fontsize=13)
        ax.text(
            0.05,
            0.48,
            "Initial guidance, revisions and spending gaps: Not measured (n=0).",
            fontsize=11,
        )
        for index, c in enumerate(config.spenders):
            x = 0.05 + 0.185 * index
            ax.plot([x, x + 0.12], [0.28, 0.28], color=c.color, lw=3)
            ax.text(x, 0.18, c.name, fontsize=9)
        ax.text(
            0.05,
            0.02,
            "Source: approved SEC filing records. Pending rows are excluded.",
            fontsize=9,
            color=charts.INK_SECONDARY,
        )
        fig.subplots_adjust(left=0.03, right=0.99, bottom=0.12, top=0.97)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return
    for ax, ((ticker, year, _series), group) in zip(axes.flat, groups.items(), strict=False):
        ax.set_visible(True)
        c = config.company(ticker)
        ax.set_title(f"{c.name} FY{year}", fontsize=10)
        num = [r for r in group if r["low"] is not None and r["stage"] != "reaffirmed"]
        dates = pd.to_datetime([r["date"] for r in num])
        mids = [(r["low"] + r["high"]) / 2e9 for r in num]
        ax.plot(dates, mids, marker="o", ms=4, color=c.color)
        for x, r in zip(dates, num, strict=True):
            ax.vlines(x, r["low"] / 1e9, r["high"] / 1e9, color=c.color, lw=2)
        for r in group:
            if r["stage"] == "directional":
                symbol = {"up": "^", "down": "v", "flat": ">"}[r["direction"]]
                ax.plot(
                    pd.Timestamp(r["date"]),
                    0.04,
                    transform=ax.get_xaxis_transform(),
                    marker=symbol,
                    color=c.color,
                    ms=6,
                    clip_on=False,
                )
        actual = group[0]["actual"]
        if actual is not None:
            ax.plot(pd.Timestamp(group[0]["end"]), actual / 1e9, "D", color=charts.INK, ms=5)
        from matplotlib.dates import AutoDateLocator, ConciseDateFormatter

        locator = AutoDateLocator(minticks=2, maxticks=4)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(ConciseDateFormatter(locator))
        ax.margins(x=0.12, y=0.25)
        ax.set_ylabel("USD billions", fontsize=8)
    fig.suptitle(
        "Filed capital spending guidance and fiscal-year actuals",
        x=0.07,
        ha="left",
        y=0.98,
        fontweight="bold",
    )
    handles = [
        Line2D([], [], marker=m, color=charts.INK, linestyle="none", label=s)
        for m, s in [
            ("o", "Forecast midpoint (bar shows range)"),
            ("D", "Fiscal-year actual"),
            ("^", "Direction only, at axis"),
        ]
    ]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.06, 0.93), ncol=3)
    fig.text(
        0.07,
        0.015,
        "Source: approved SEC filing passages and four matched XBRL quarters. "
        "Each panel uses its own scale.",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.055, 1, 0.87))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def render(config, wide, text):
    directory = config.paths.processed_dir.parent / "guidance"
    approved = read_approved(directory)
    rows = paths(approved, wide)
    manifest = json.loads((directory / "sources.json").read_text())
    fields = (
        "id",
        "company",
        "fiscal_year",
        "date",
        "end",
        "series",
        "stage",
        "low",
        "high",
        "direction",
        "revision_usd",
        "actual",
        "gap",
        "source",
        "approved_by",
    )
    with (config.paths.processed_dir / "guidance_paths.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    chart(rows, config, config.paths.charts_dir / "guidance_path.png")
    section = "\n\n".join(
        [
            finding(rows),
            fiscal_table(rows),
            "Initial means the earliest approved range in this filing sample. "
            "Earlier single-source forecasts can remain pending.",
            coverage(manifest, read_csv(directory / "coverage.csv"), config),
            "![Approved forecasts and fiscal-year actuals](docs/charts/guidance_path.png)",
            "[Dated ranges, revisions, definitions and actuals](data/processed/guidance_paths.csv)",
        ]
    )
    return replace_section(text, "GUIDANCE", section)

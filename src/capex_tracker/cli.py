"""Command line entry point: fetch, build, charts, readme, update, inspect, latest."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from capex_tracker.config import DEFAULT_CONFIG_PATH, Company, Config, load_config
from capex_tracker.facts import select_metric
from capex_tracker.metrics import (
    AGGREGATE_RATIO_COLUMNS,
    RATIO_COLUMNS,
    CompanyData,
    build_aggregate,
    build_long,
    build_wide,
    latest_complete,
)
from capex_tracker.quarters import classify_duration, derive_quarters, display_quarter
from capex_tracker.readme import render_readme
from capex_tracker.sec_client import (
    CacheMissError,
    MissingUserAgentError,
    RawCache,
    SecClient,
    SecRequestError,
    cache_key,
)
from capex_tracker.validate import ValidationResult, render_report, run_checks

logger = logging.getLogger("capex_tracker")

RATIO_DECIMALS = 6
RECEIVER_METRICS = ("revenue",)
TAG_REPORT_COLUMNS = [
    "company",
    "ticker",
    "metric",
    "tag",
    "role",
    "periods_available",
    "periods_used",
    "first_period_end",
    "last_period_end",
    "overlap_periods",
    "overlap_mismatches",
]


class ValidationFailedError(RuntimeError):
    """One or more consistency checks failed."""


def _metrics_for(company: Company, config: Config) -> list[str]:
    return list(RECEIVER_METRICS) if company.role == "receiver" else list(config.metrics)


def analyze_company(company: Company, config: Config, cache: RawCache) -> CompanyData:
    """Select tags and derive quarters for one company from its cached facts."""
    companyfacts = cache.read(cache_key(company.ticker))
    selections = {}
    derivations = {}
    for name in _metrics_for(company, config):
        selection = select_metric(
            companyfacts,
            name,
            config.metrics[name],
            config.forms,
            config.validation.cross_check_tolerance,
        )
        if not selection.facts:
            logger.warning(
                "%s: no facts found for %s under any configured tag", company.ticker, name
            )
        selections[name] = selection
        derivations[name] = derive_quarters(selection.facts, config.durations)
    return CompanyData(company=company, selections=selections, derivations=derivations)


def tag_report(companies: Sequence[CompanyData]) -> pd.DataFrame:
    """One row per company, metric and tag, showing which tags supplied the data."""
    rows = []
    for data in companies:
        for metric, selection in data.selections.items():
            base = {
                "company": data.company.name,
                "ticker": data.company.ticker,
                "metric": metric,
            }
            if not selection.coverage:
                rows.append({**base, "tag": "", "role": "not_found"})
                continue
            for item in selection.coverage:
                used = selection.periods_used.get(item.concept, 0)
                role = "primary" if item.concept == selection.primary else "stitched"
                rows.append(
                    {
                        **base,
                        "tag": item.concept,
                        "role": role if used else "unused",
                        "periods_available": item.periods,
                        "periods_used": used,
                        "first_period_end": item.first_end.isoformat(),
                        "last_period_end": item.last_end.isoformat(),
                        "overlap_periods": selection.overlap_periods.get(item.concept, 0),
                        "overlap_mismatches": selection.overlap_mismatches.get(item.concept, 0),
                    }
                )
    frame = pd.DataFrame(rows, columns=TAG_REPORT_COLUMNS)
    for column in ("periods_available", "periods_used", "overlap_periods", "overlap_mismatches"):
        frame[column] = frame[column].astype("Int64")
    return frame.sort_values(["ticker", "metric", "role", "tag"], ignore_index=True)


def _write_csv(frame: pd.DataFrame, path: Path, usd: Sequence[str], ratios: Sequence[str]) -> None:
    """Write with fixed precision so reruns on the same data are byte-identical."""
    output = frame.copy()
    for column in usd:
        output[column] = output[column].round(0).astype("Int64")
    for column in ratios:
        output[column] = output[column].round(RATIO_DECIMALS)
    output.to_csv(path, index=False, lineterminator="\n")


def _processed(config: Config, name: str) -> Path:
    return config.paths.processed_dir / name


def command_fetch(config: Config, refresh: bool) -> None:
    SecClient(config).fetch_all(list(config.companies), refresh=refresh)


def _report_validation(result: ValidationResult, config: Config) -> None:
    path = _processed(config, "validation_report.md")
    path.write_text(render_report(result), encoding="utf-8")
    for issue in result.warnings:
        logger.warning("%s %s %s: %s", issue.check, issue.ticker, issue.metric, issue.message)
    for issue in result.failures:
        logger.error("%s %s %s: %s", issue.check, issue.ticker, issue.metric, issue.message)
    logger.info(
        "Validation: %d failures, %d warnings. Report: %s",
        len(result.failures),
        len(result.warnings),
        path,
    )


def command_build(config: Config) -> None:
    config.paths.processed_dir.mkdir(parents=True, exist_ok=True)
    cache = RawCache(config.paths.raw_dir)
    companies = [analyze_company(company, config, cache) for company in config.companies]
    _write_csv(tag_report(companies), _processed(config, "tag_report.csv"), [], [])

    result = run_checks(companies, config)
    _report_validation(result, config)
    if not result.passed:
        raise ValidationFailedError(
            f"{len(result.failures)} validation checks failed. "
            f"See {_processed(config, 'validation_report.md')}"
        )

    long = build_long(companies, config.data_start)
    wide = build_wide(long)
    aggregate = build_aggregate(
        wide,
        [company.ticker for company in config.spenders],
        [company.ticker for company in config.receivers],
    )

    _write_csv(long, _processed(config, "quarterly.csv"), ["value_usd"], [])
    usd_columns = [
        column
        for column in wide.columns
        if column.startswith("ttm_") and column not in RATIO_COLUMNS
    ] + ["capex", "ocf", "revenue", "finance_lease_principal", "fcf"]
    usd_columns += ["capex_lease_adjusted", "fcf_lease_adjusted"]
    _write_csv(wide, _processed(config, "wide.csv"), usd_columns, RATIO_COLUMNS)
    aggregate_usd = [
        column
        for column in aggregate.columns
        if column not in AGGREGATE_RATIO_COLUMNS
        and column.startswith(("total_", "ttm_", "receiver_"))
    ]
    _write_csv(
        aggregate, _processed(config, "aggregate.csv"), aggregate_usd, AGGREGATE_RATIO_COLUMNS
    )
    logger.info("Wrote processed data to %s", config.paths.processed_dir)


def _read_processed(config: Config) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    long = pd.read_csv(
        _processed(config, "quarterly.csv"),
        keep_default_na=False,
        na_values=[""],
        dtype={"accession": str, "form": str},
    )
    long["accession"] = long["accession"].fillna("")
    wide = pd.read_csv(_processed(config, "wide.csv"))
    aggregate = pd.read_csv(
        _processed(config, "aggregate.csv"),
        keep_default_na=False,
        na_values=[""],
        dtype={"missing_companies": str},
    )
    return long, wide, aggregate


def command_charts(config: Config) -> None:
    from capex_tracker.charts import render_all

    long, wide, aggregate = _read_processed(config)
    render_all(wide, aggregate, long, config)
    logger.info("Wrote charts to %s", config.paths.charts_dir)


def command_readme(config: Config) -> None:
    long, wide, aggregate = _read_processed(config)
    path = config.paths.readme
    text = path.read_text(encoding="utf-8")
    rendered = render_readme(text, long, wide, aggregate, config)
    if "<!-- GUIDANCE:START -->" in rendered:
        from capex_tracker.guidance.report import render

        rendered = render(config, wide, rendered)
    path.write_text(rendered, encoding="utf-8")
    logger.info("Updated %s", path)


def command_latest(config: Config) -> None:
    """Print the latest complete quarter, for the Action's commit message."""
    _, _, aggregate = _read_processed(config)
    latest = latest_complete(aggregate)
    print(display_quarter(latest["calendar_quarter"]) if latest is not None else "no data")


def command_inspect(config: Config, ticker: str, metric: str) -> None:
    """Show how one company's metric was built, from raw facts to quarters."""
    company = config.company(ticker.upper())
    if metric not in config.metrics:
        raise KeyError(f"unknown metric {metric!r}; configured: {sorted(config.metrics)}")
    if metric not in _metrics_for(company, config):
        raise KeyError(f"{company.name} is a receiver and only tracks revenue")
    data = analyze_company(company, config, RawCache(config.paths.raw_dir))
    selection = data.selections[metric]
    derivation = data.derivations[metric]

    print(f"{company.name} ({company.ticker}): {metric}")
    print(f"Chosen tag: {selection.primary or 'NONE FOUND'}")
    print("\nTag coverage, best first:")
    for item in selection.coverage:
        print(
            f"  {item.concept}: {item.periods} periods, {item.first_end} to {item.last_end}, "
            f"supplied {selection.periods_used.get(item.concept, 0)}"
        )

    window = [q for q in derivation.quarters if q.period_end >= config.data_start]
    facts = sorted(
        {fact for quarter in window for fact in quarter.inputs},
        key=lambda f: (f.end, f.start),
    )
    print(f"\nRaw facts used ({len(facts)}):")
    for fact in facts:
        duration = classify_duration(fact.start, fact.end, config.durations)
        print(
            f"  {fact.start} to {fact.end}  {duration.value:<12} {fact.value / 1e9:>10.3f}B  "
            f"{fact.form:<6} filed {fact.filed}  {fact.accession}  {fact.concept}"
        )

    print(f"\nDiscrete quarters ({len(window)}):")
    for quarter in window:
        how = "derived from YTD" if quarter.derived else "reported directly"
        cross = ""
        if quarter.cross_check_value is not None:
            cross = f"  (YTD-derived check {quarter.cross_check_value / 1e9:.3f}B)"
        print(
            f"  {quarter.fiscal_label}  {display_quarter(quarter.calendar_quarter)}  "
            f"{quarter.period_start} to {quarter.period_end}  {quarter.value / 1e9:>10.3f}B  "
            f"{how}{cross}"
        )
    for gap in derivation.gaps:
        if gap.period_end and gap.period_end >= config.data_start:
            print(f"  GAP FY{gap.fiscal_year} Q{gap.fiscal_quarter}: {gap.reason}")


def command_update(config: Config, refresh: bool) -> None:
    command_fetch(config, refresh)
    command_build(config)
    command_charts(config)
    command_readme(config)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="capex_tracker", description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in [
        ("fetch", "download SEC data into the raw cache"),
        ("update", "fetch, build, charts and readme"),
    ]:
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("--refresh", action="store_true", help="ignore the raw cache")
    commands.add_parser("build", help="parse, derive, compute and validate")
    commands.add_parser("charts", help="render charts from processed data")
    commands.add_parser("readme", help="refresh auto-generated README sections")
    commands.add_parser("latest", help="print the latest complete calendar quarter")
    inspect = commands.add_parser("inspect", help="show how a metric was built")
    inspect.add_argument("--ticker", required=True)
    inspect.add_argument("--metric", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = load_config(args.config)
    try:
        if args.command == "fetch":
            command_fetch(config, args.refresh)
        elif args.command == "build":
            command_build(config)
        elif args.command == "charts":
            command_charts(config)
        elif args.command == "readme":
            command_readme(config)
        elif args.command == "latest":
            command_latest(config)
        elif args.command == "inspect":
            command_inspect(config, args.ticker, args.metric)
        elif args.command == "update":
            command_update(config, args.refresh)
    except (
        MissingUserAgentError,
        SecRequestError,
        CacheMissError,
        ValidationFailedError,
        KeyError,
    ) as error:
        logger.error("%s", error.args[0] if error.args else error)
        return 1
    return 0

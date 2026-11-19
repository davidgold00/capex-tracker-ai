"""Matplotlib charts. Fixed fonts, sizes and metadata keep the PNGs reproducible."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.dates import DateFormatter, YearLocator, date2num
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from capex_tracker.config import Company, Config

logger = logging.getLogger(__name__)

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
CONTEXT_LINE = "#d6d5ce"
# Aggregates are not companies, so they use colors no company has.
AGGREGATE_CAPEX = "#6250d6"
AGGREGATE_OCF = "#52514e"

FIGURE_WIDTH = 9.0
FIGURE_DPI = 150
LINE_WIDTH = 2.0
BILLION = 1e9
LABEL_GAP_FRACTION = 0.055
LEASE_COMPANIES = ("AMZN", "MSFT")


@dataclass(frozen=True)
class EndLabel:
    x: pd.Timestamp
    y: float
    text: str


def apply_style() -> None:
    """Fixed style. DejaVu Sans ships with matplotlib, so every machine matches."""
    plt.rcdefaults()
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.titlecolor": INK,
            "axes.labelsize": 10,
            "axes.labelcolor": INK_SECONDARY,
            "axes.edgecolor": AXIS,
            "axes.linewidth": 0.8,
            "axes.facecolor": SURFACE,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "axes.axisbelow": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "figure.facecolor": SURFACE,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "lines.linewidth": LINE_WIDTH,
            "lines.solid_capstyle": "round",
            "lines.solid_joinstyle": "round",
            "xtick.color": INK_MUTED,
            "ytick.color": INK_MUTED,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "ytick.major.size": 0,
            "legend.frameon": False,
            "legend.fontsize": 9.5,
            "legend.labelcolor": INK_SECONDARY,
        }
    )


def quarter_end(labels: pd.Series) -> pd.DatetimeIndex:
    """Plot each calendar quarter at its last day."""
    return pd.PeriodIndex(labels, freq="Q").to_timestamp(how="end").normalize()


def in_window(frame: pd.DataFrame, config: Config) -> pd.DataFrame:
    return frame[quarter_end(frame["calendar_quarter"]) >= pd.Timestamp(config.chart_start)]


def _billions_axis(ax: Axes) -> None:
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v / BILLION:,.0f}B"))
    ax.set_ylim(bottom=0)


def _percent_axis(ax: Axes) -> None:
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_ylim(bottom=0)


def _year_axis(ax: Axes) -> None:
    ax.xaxis.set_major_locator(YearLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%Y"))
    ax.tick_params(axis="x", length=3, color=AXIS)


def _series(x: pd.DatetimeIndex, y: pd.Series) -> tuple[pd.DatetimeIndex, pd.Series]:
    mask = y.notna().to_numpy()
    return x[mask], y[mask]


def _end_marker(ax: Axes, x: pd.Timestamp, y: float, color: str) -> None:
    ax.plot(
        [x],
        [y],
        marker="o",
        markersize=7,
        color=color,
        markeredgecolor=SURFACE,
        markeredgewidth=2,
        zorder=5,
        clip_on=False,
    )


def _spread(values: Sequence[float], min_gap: float) -> list[float]:
    """Push label positions apart by ``min_gap`` while keeping their order."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    placed = [values[i] for i in order]
    for _ in range(50):
        moved = False
        for lower in range(len(placed) - 1):
            overlap = min_gap - (placed[lower + 1] - placed[lower])
            if overlap > 1e-9:
                placed[lower] -= overlap / 2
                placed[lower + 1] += overlap / 2
                moved = True
        if not moved:
            break
    result = [0.0] * len(values)
    for position, index in enumerate(order):
        result[index] = placed[position]
    return result


def _end_labels(ax: Axes, labels: Sequence[EndLabel]) -> None:
    """Label line ends at the right edge, with leader lines where labels had to move."""
    bottom, top = ax.get_ylim()
    gap = (top - bottom) * LABEL_GAP_FRACTION
    positions = _spread([label.y for label in labels], gap)
    x_max = date2num(max(label.x for label in labels))
    x_min, _ = ax.get_xlim()
    text_x = x_max + (x_max - x_min) * 0.025
    for label, y in zip(labels, positions, strict=True):
        if abs(y - label.y) > gap * 0.15:
            ax.plot(
                [date2num(label.x), text_x],
                [label.y, y],
                color=AXIS,
                linewidth=0.8,
                zorder=1,
                clip_on=False,
            )
        ax.text(
            text_x,
            y,
            f" {label.text}",
            va="center",
            ha="left",
            fontsize=9,
            color=INK_SECONDARY,
            clip_on=False,
        )


def _footer(fig: Figure, updated: str, extra: str = "") -> None:
    text = f"Source: SEC EDGAR XBRL. Updated {updated}."
    if extra:
        text = f"{text} {extra}"
    fig.text(0.012, 0.012, text, fontsize=8, color=INK_MUTED, ha="left", va="bottom")


def _save(fig: Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=FIGURE_DPI, facecolor=SURFACE, metadata={"Software": None})
    plt.close(fig)


def _line_with_label(
    ax: Axes, x: pd.DatetimeIndex, y: pd.Series, color: str, name: str
) -> pd.Timestamp | None:
    x_values, y_values = _series(x, y)
    if y_values.empty:
        logger.warning("Nothing to plot for %s", name)
        return None
    ax.plot(x_values, y_values, color=color, label=name)
    _end_marker(ax, x_values[-1], y_values.iloc[-1], color)
    return x_values[-1]


def headline_chart(aggregate: pd.DataFrame, config: Config, updated: str, path: Path) -> None:
    data = in_window(aggregate, config)
    x = quarter_end(data["calendar_quarter"])
    fig, (top, bottom) = plt.subplots(
        2,
        1,
        figsize=(FIGURE_WIDTH, 5.8),
        sharex=True,
        gridspec_kw={"height_ratios": [3, 1.25], "hspace": 0.32},
    )
    names = {"ttm_capex": "Capex", "ttm_ocf": "Operating cash flow"}
    colors = {"ttm_capex": AGGREGATE_CAPEX, "ttm_ocf": AGGREGATE_OCF}
    short_names = {"ttm_capex": "Capex", "ttm_ocf": "OCF"}
    labels = []
    for column, name in names.items():
        last = _line_with_label(top, x, data[column], colors[column], name)
        if last is not None:
            value = data[column].dropna().iloc[-1]
            labels.append(EndLabel(last, value, f"{short_names[column]} ${value / BILLION:,.1f}B"))
    top.set_title("Hyperscaler capex and operating cash flow, trailing 12 months", pad=12)
    top.set_ylabel("USD billions, trailing 12 months")
    _billions_axis(top)
    top.legend(loc="upper left", ncols=2)
    _end_labels(top, labels)

    last = _line_with_label(
        bottom, x, data["ttm_capex_intensity"], AGGREGATE_CAPEX, "Capex intensity"
    )
    bottom.set_title("Capex intensity (capex / operating cash flow)", fontsize=11, pad=8)
    bottom.set_ylabel("Share of OCF")
    _percent_axis(bottom)
    bottom.set_xlabel("Calendar quarter")
    _year_axis(bottom)
    if last is not None:
        value = data["ttm_capex_intensity"].dropna().iloc[-1]
        _end_labels(bottom, [EndLabel(last, value, f"{value:.0%}")])
    names_text = ", ".join(company.ticker for company in config.spenders)
    fig.subplots_adjust(left=0.09, right=0.84, top=0.93, bottom=0.135)
    _footer(fig, updated, f"Sum of {names_text}.")
    _save(fig, path)


def capex_by_company_chart(wide: pd.DataFrame, config: Config, updated: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH, 4.9))
    data = in_window(wide, config)
    labels = []
    for company in config.spenders:
        rows = data[data["ticker"] == company.ticker].sort_values("calendar_quarter")
        x = quarter_end(rows["calendar_quarter"])
        last = _line_with_label(ax, x, rows["ttm_capex"], company.color, company.name)
        if last is not None:
            value = rows["ttm_capex"].dropna().iloc[-1]
            labels.append(EndLabel(last, value, f"{company.name} ${value / BILLION:,.1f}B"))
    ax.set_title("Capex by company, trailing 12 months", pad=12)
    ax.set_ylabel("USD billions, trailing 12 months")
    ax.set_xlabel("Calendar quarter")
    _billions_axis(ax)
    _year_axis(ax)
    ax.legend(loc="upper left", ncols=3)
    _end_labels(ax, labels)
    fig.subplots_adjust(left=0.085, right=0.82, top=0.92, bottom=0.155)
    _footer(fig, updated)
    _save(fig, path)


def _intensity_panels(config: Config) -> list[Company | None]:
    """One panel per spender, then one for the aggregate."""
    return [*config.spenders, None]


def intensity_by_company_chart(
    wide: pd.DataFrame, aggregate: pd.DataFrame, config: Config, updated: str, path: Path
) -> None:
    panels = _intensity_panels(config)
    columns = 3
    rows_needed = (len(panels) + columns - 1) // columns
    fig, axes = plt.subplots(
        rows_needed,
        columns,
        figsize=(FIGURE_WIDTH, 2.55 * rows_needed + 0.9),
        sharex=True,
        sharey=True,
    )
    flat = axes.flatten()
    data = in_window(wide, config)
    spender_rows = {
        company.ticker: data[data["ticker"] == company.ticker].sort_values("calendar_quarter")
        for company in config.spenders
    }
    ceiling = max(
        float(rows["ttm_capex_intensity"].max())
        for rows in spender_rows.values()
        if rows["ttm_capex_intensity"].notna().any()
    )
    aggregate_rows = in_window(aggregate, config)

    for ax, company in zip(flat, panels, strict=False):
        for other in config.spenders:
            if company is not None and other.ticker == company.ticker:
                continue
            rows = spender_rows[other.ticker]
            x, y = _series(quarter_end(rows["calendar_quarter"]), rows["ttm_capex_intensity"])
            ax.plot(x, y, color=CONTEXT_LINE, linewidth=1.0, zorder=1)
        if company is None:
            source = aggregate_rows
            name = "All five, aggregate" if len(config.spenders) == 5 else "All spenders, aggregate"
            color = AGGREGATE_CAPEX
        else:
            source = spender_rows[company.ticker]
            name = company.name
            color = company.color
        x, y = _series(quarter_end(source["calendar_quarter"]), source["ttm_capex_intensity"])
        ax.plot(x, y, color=color, zorder=3)
        ax.set_title(name, fontsize=10.5, pad=6)
        if not y.empty:
            _end_marker(ax, x[-1], y.iloc[-1], color)
            # Sits above the plot, so it cannot collide with any line.
            ax.text(
                1.0,
                1.035,
                f"{y.iloc[-1]:.0%}",
                transform=ax.transAxes,
                ha="right",
                va="bottom",
                fontsize=10.5,
                fontweight="bold",
                color=INK,
            )
        _percent_axis(ax)
        ax.set_ylim(0, ceiling * 1.12)
        ax.xaxis.set_major_locator(YearLocator(2))
        ax.xaxis.set_major_formatter(DateFormatter("%Y"))
        ax.tick_params(axis="x", length=3, color=AXIS, labelbottom=True)
    for ax in flat[len(panels) :]:
        ax.set_visible(False)

    fig.suptitle(
        "Capex intensity by company (capex / operating cash flow), trailing 12 months",
        x=0.012,
        ha="left",
        fontsize=13,
        fontweight="bold",
        color=INK,
    )
    fig.supylabel("Share of operating cash flow", x=0.012, fontsize=10, color=INK_SECONDARY)
    fig.subplots_adjust(left=0.085, right=0.985, top=0.885, bottom=0.115, hspace=0.32, wspace=0.1)
    _footer(fig, updated, "Top right of each panel: latest value. Gray: the other companies.")
    _save(fig, path)


def capex_vs_nvidia_chart(
    aggregate: pd.DataFrame, config: Config, updated: str, path: Path
) -> None:
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH, 4.9))
    data = in_window(aggregate, config)
    x = quarter_end(data["calendar_quarter"])
    receiver_names = " + ".join(company.name for company in config.receivers)
    receiver_color = config.receivers[0].color
    series = [
        ("ttm_capex", "Hyperscaler capex", AGGREGATE_CAPEX),
        ("receiver_ttm_revenue", f"{receiver_names} revenue", receiver_color),
    ]
    labels = []
    for column, name, color in series:
        last = _line_with_label(ax, x, data[column], color, name)
        if last is not None:
            value = data[column].dropna().iloc[-1]
            labels.append(EndLabel(last, value, f"${value / BILLION:,.1f}B"))
    ax.set_title(f"Hyperscaler capex and {receiver_names} revenue, trailing 12 months", pad=12)
    ax.set_ylabel("USD billions, trailing 12 months")
    ax.set_xlabel("Calendar quarter")
    _billions_axis(ax)
    _year_axis(ax)
    ax.legend(loc="upper left", ncols=2)
    _end_labels(ax, labels)
    fig.subplots_adjust(left=0.085, right=0.89, top=0.92, bottom=0.155)
    _footer(fig, updated, "Lines can end on different quarters as filing dates differ.")
    _save(fig, path)


def lease_adjustment_chart(wide: pd.DataFrame, config: Config, updated: str, path: Path) -> None:
    data = in_window(wide, config)
    panels = []
    for ticker in LEASE_COMPANIES:
        rows = data[data["ticker"] == ticker].sort_values("calendar_quarter")
        if rows["ttm_capex_lease_adjusted"].notna().any():
            panels.append((config.company(ticker), rows))
        else:
            logger.warning("%s has no lease-adjusted capex to chart", ticker)
    if not panels:
        logger.warning("Skipping the lease adjustment chart: no data")
        return

    fig, axes = plt.subplots(
        1, len(panels), figsize=(FIGURE_WIDTH, 4.5), sharey=True, squeeze=False
    )
    for ax, (company, rows) in zip(axes[0], panels, strict=True):
        x = quarter_end(rows["calendar_quarter"])
        reported = rows["ttm_capex"]
        adjusted = rows["ttm_capex_lease_adjusted"]
        both = reported.notna() & adjusted.notna()
        ax.fill_between(
            x[both.to_numpy()], reported[both], adjusted[both], color=company.color, alpha=0.14
        )
        x_reported, y_reported = _series(x, reported)
        x_adjusted, y_adjusted = _series(x, adjusted)
        ax.plot(x_reported, y_reported, color=company.color, label="Reported capex")
        ax.plot(
            x_adjusted,
            y_adjusted,
            color=company.color,
            linestyle=(0, (4, 2)),
            label="Reported + finance lease principal",
        )
        _end_marker(ax, x_reported[-1], y_reported.iloc[-1], company.color)
        _end_marker(ax, x_adjusted[-1], y_adjusted.iloc[-1], company.color)
        ax.set_title(company.name, fontsize=11.5, pad=8)
        _billions_axis(ax)
        ax.xaxis.set_major_locator(YearLocator(2))
        ax.xaxis.set_major_formatter(DateFormatter("%Y"))
        ax.tick_params(axis="x", length=3, color=AXIS)
        ax.set_xlabel("Calendar quarter")
        ax.legend(loc="upper left")
        ax.annotate(
            f"${y_adjusted.iloc[-1] / BILLION:,.1f}B adjusted\n"
            f"${y_reported.iloc[-1] / BILLION:,.1f}B reported",
            xy=(0.985, 0.04),
            xycoords="axes fraction",
            ha="right",
            va="bottom",
            fontsize=9,
            color=INK_SECONDARY,
        )
    axes[0][0].set_ylabel("USD billions, trailing 12 months")
    fig.suptitle(
        "Reported vs finance-lease-adjusted capex, trailing 12 months",
        x=0.012,
        ha="left",
        fontsize=13,
        fontweight="bold",
        color=INK,
    )
    fig.subplots_adjust(left=0.09, right=0.985, top=0.84, bottom=0.17, wspace=0.08)
    _footer(fig, updated)
    _save(fig, path)


def render_all(
    wide: pd.DataFrame, aggregate: pd.DataFrame, long: pd.DataFrame, config: Config
) -> None:
    """Render every chart. The footer date is the newest filing, so reruns are stable."""
    apply_style()
    updated = str(long["filed"].max())
    directory = config.paths.charts_dir
    headline_chart(aggregate, config, updated, directory / "headline.png")
    capex_by_company_chart(wide, config, updated, directory / "capex_by_company.png")
    intensity_by_company_chart(
        wide, aggregate, config, updated, directory / "intensity_by_company.png"
    )
    capex_vs_nvidia_chart(aggregate, config, updated, directory / "capex_vs_nvidia.png")
    lease_adjustment_chart(wide, config, updated, directory / "lease_adjustment.png")

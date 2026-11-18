# capex-tracker-ai

Tracks how much cash the largest technology companies are putting into AI infrastructure, and how much of their operating cash flow it absorbs, using SEC EDGAR filings.

<!-- HEADLINE:START -->
**In the four quarters to Q3 2026, Microsoft, Alphabet, Amazon, Meta and Oracle spent $691.0B on capex, equal to 95% of their operating cash flow, up from 64% a year earlier.**
<!-- HEADLINE:END -->

<!-- UPDATED:START -->
Last updated: 2026-10-30. Latest filing included: Amazon 10-Q, accession 0001018724-26-000040, filed 2026-10-30.
<!-- UPDATED:END -->

<!-- TABLE:START -->
**Latest complete calendar quarter: Q3 2026**

| Company | Capex | OCF | FCF | Capex intensity | YoY capex growth |
|---|---:|---:|---:|---:|---:|
| Microsoft | $39.4B | $58.0B | $18.6B | 68% | +103% |
| Alphabet | $51.4B | $42.3B | -$9.1B | 121% | +114% |
| Amazon | $77.3B | $42.4B | -$34.8B | 182% | +120% |
| Meta | $33.9B | $32.8B | -$1.2B | 104% | +80% |
| Oracle | $28.5B | $23.1B | -$5.4B | 123% | +235% |
| **Total** | **$230.4B** | **$198.6B** | **-$31.8B** | **116%** | **+118%** |
<!-- TABLE:END -->

## Charts

<!-- CHARTS:START -->
![Aggregate hyperscaler TTM capex and operating cash flow](docs/charts/headline.png)

![TTM capex by company](docs/charts/capex_by_company.png)

![TTM capex intensity by company](docs/charts/intensity_by_company.png)

![Aggregate hyperscaler TTM capex and Nvidia TTM revenue](docs/charts/capex_vs_nvidia.png)

![Reported and finance-lease-adjusted capex](docs/charts/lease_adjustment.png)
<!-- CHARTS:END -->

## Guidance versus actual spending

<!-- GUIDANCE:START -->
No annual forecast passed review (n=0), so upward revisions, the gap from initial guidance to actual spending, and company reliability remain unmeasured.

SEC filing coverage by document: Microsoft 0 approved / 16 language hits / 32 read, Alphabet 0 approved / 11 language hits / 33 read, Amazon 0 approved / 18 language hits / 32 read, Meta 0 approved / 32 language hits / 32 read, Oracle 0 approved / 17 language hits / 30 read. Calls are outside the corpus. A missing filed forecast leaves a coverage gap.

![Approved forecasts and fiscal-year actuals](docs/charts/guidance_path.png)

[Dated ranges, revisions, definitions and actuals](data/processed/guidance_paths.csv)
<!-- GUIDANCE:END -->

## What changed (machine-drafted and fact-checked)

<!-- WHAT_CHANGED:START -->

<!-- WHAT_CHANGED:END -->

## My read this quarter

<!-- NOTES:START -->
Notes coming soon.
<!-- NOTES:END -->

## About me

_Placeholder: why I built this and what I am looking for._

## Why this matters

Microsoft, Alphabet, Amazon, Meta and Oracle are building data centers for AI workloads, and investors and analysts follow their capital spending closely. Capital expenditure is paid from the cash these companies generate, so its size relative to operating cash flow shows how much of that cash is being committed to infrastructure. Nvidia sells much of the hardware used in these data centers, which makes its revenue a useful view of the other side of the same spending. Companies do not break out AI spending separately, so reported capex is the closest public measure available.

## Methodology

All figures come from the XBRL data companies file with the SEC. No figure is estimated or hand-entered.

**Choosing tags.** Companies label the same line item with different XBRL tags, and change labels over time. `config.yaml` lists candidate tags for each metric. For each company, tags are ranked by the most recent period they cover, then by how many periods they cover. Each period takes its value from the highest-ranked tag that has it, and every data point records its tag. Amazon's capex, for example, moves across three tags between 2017 and 2018. `data/processed/tag_report.csv` shows every choice.

**Turning year-to-date figures into quarters.** Cash flow statements in 10-Qs are cumulative: the Q2 filing reports six months, and Q3 reports nine. Discrete quarters are derived by subtraction (Q2 is six months minus Q1, Q3 is nine months minus six months, Q4 is the full year minus nine months). Periods are classified by their actual start and end dates, within tolerances: 85 to 100 days is a quarter, 175 to 190 is six months, 265 to 280 is nine months, and 355 to 375 is a year. Where a true three-month figure is reported, it is used and compared against the derived one.

Two filing quirks needed handling. Amazon reports trailing-twelve-month figures in its 10-Qs, so a year-long period only counts as a fiscal year if it comes from a 10-K or starts on the same day as a year-to-date period. Oracle's data for fiscal 2018 to 2022 tags the full-year revenue figure as a three-month period, so a three-month value equal to the full-year figure is rejected in favor of the derived one and listed as a warning.

**Duplicates and restatements.** Later filings repeat earlier periods as comparatives. For each tag and period, only the most recently filed value is kept, so restatements win. Accession number breaks ties, and each row keeps its accession number and form type.

**Fiscal calendars.** Microsoft's fiscal year ends in June, Oracle's in May, and Nvidia's in late January. Each quarter is assigned to the calendar quarter containing its midpoint, and both the fiscal label and calendar quarter are stored. A calendar quarter is only aggregated once all five spenders have reported it. A later quarter still in progress is marked partial and excluded from the headline.

**Signs and units.** Capex and lease repayments are stored as positive numbers. Values are stored in US dollars and shown in billions.

**Lease-adjusted capex.** Reported capex excludes assets financed through finance leases. The adjusted version adds principal repayments of finance leases, which follows the free cash flow measure Amazon publishes. The two versions are kept in separate columns, and a quarter without a reported lease figure stays blank rather than being treated as zero.

**Checks on every update.** Results are written to `data/processed/validation_report.md`, and a failure stops the update before anything is published.

- For each fiscal year with a 10-K, the four quarters must sum to the annual figure within 0.5%. When every quarter comes from year-to-date subtraction this holds by construction, so the check mainly catches missing periods and quarters that were reported directly.
- Derived quarterly capex can never be negative.
- Capex moves of more than 60% quarter over quarter are listed for review, but do not stop the update.

## Limitations

- **Finance leases.** Coverage varies by company. Alphabet's quarterly lease figures begin in 2024, and Oracle's stop after its February 2026 quarter, so lease-adjusted figures are incomplete for both. The adjustment counts cash repaid on leases, not the value of assets newly acquired under them, so it understates capacity added recently through leasing.
- **Capex is not only AI.** Companies do not report AI capex separately. These totals include warehouses, logistics, offices and other non-AI spending.
- **Tag inconsistency.** Older periods can come from a different tag with a slightly different definition. Amazon's older capex tag, for example, was reported net of incentives. The tag report records where tags disagree.
- **Partial recasts.** When a later filing changes only an annual figure, the difference falls into the derived fourth quarter. Meta's January 2025 10-K restated 2022 and 2023 capex net of proceeds, without recasting the earlier quarters, which shifts about $0.2B into each of those fourth quarters.
- **Calendar mapping.** Midpoint mapping is an approximation. Oracle's quarter ending in August counts as the calendar third quarter, and Nvidia's quarter ending in October does too, though neither lines up exactly with July to September.
- **Freshness.** The data is only as current as the latest 10-Q or 10-K. Companies report on different dates, and a filing can arrive weeks after a quarter ends.

## How to run it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export SEC_USER_AGENT="Your Name <your email address>"

pytest
python -m capex_tracker update
```

SEC requires a User-Agent that identifies you. Other commands:

| Command | What it does |
|---|---|
| `python -m capex_tracker fetch [--refresh]` | Download SEC data into the local cache |
| `python -m capex_tracker build` | Parse, derive, compute and validate |
| `python -m capex_tracker charts` | Render the charts |
| `python -m capex_tracker readme` | Refresh the generated README sections |
| `python -m capex_tracker update [--refresh]` | Run all of the above |
| `python -m capex_tracker inspect --ticker MSFT --metric capex` | Show the chosen tag, every raw fact, and the derived quarters |

## How the automation works

A GitHub Action runs every Monday and on demand. It installs pinned dependencies, runs the tests, refetches SEC data and rebuilds everything. If the processed data, charts or README changed, it commits them. If a validation check fails, the job stops and nothing is committed. Dates in the charts and README come from the newest filing rather than the day of the run, so a week with no new filings produces no commit.

## License

MIT

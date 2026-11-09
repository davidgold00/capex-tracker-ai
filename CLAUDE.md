# capex-tracker-ai

Self-updating tracker of hyperscaler capex against operating cash flow, built only from SEC EDGAR XBRL data. Spenders are MSFT, GOOGL, AMZN, META and ORCL. NVDA is the receiver and only tracks revenue. Companies, tags, tolerances and paths live in `config.yaml`.

## Commands

```bash
pip install -e ".[dev]"                     # pinned dependencies, Python 3.11+
export SEC_USER_AGENT="Your Name <your email address>"

pytest                                      # no network
ruff check src tests && ruff format src tests

python -m capex_tracker fetch [--refresh]
python -m capex_tracker build               # exits non-zero if validation fails
python -m capex_tracker charts
python -m capex_tracker readme
python -m capex_tracker update [--refresh]  # all of the above, used by the Action
python -m capex_tracker inspect --ticker MSFT --metric capex
python -m capex_tracker latest              # latest complete quarter, for commit messages
```

## Layout

`src/capex_tracker/`: `config` (pydantic), `sec_client` (HTTP, cache), `facts` (parse, dedupe, tag ranking and stitching), `quarters` (durations, YTD differencing, calendar mapping), `metrics`, `validate`, `charts`, `readme`, `cli`. Raw JSON is cached in `data/raw/` (gitignored). Outputs go to `data/processed/` and `docs/charts/`.

## Data gotchas

- **Tags vary by company and over time.** Rank by most recent coverage, then completeness, then config order. Stitch by period and record the tag used.
- **Cash flow facts in 10-Qs are year-to-date.** Q2 = 6M - Q1, Q3 = 9M - 6M, Q4 = FY - 9M. Classify periods from start and end dates. Never rely on `fp`, which describes the filing.
- **Year-to-date facts in a fiscal year share a start date.** That is how facts are grouped into fiscal years. A year with only Q1 filed is anchored by the prior year's end.
- **Prefer a direct 3-month value** and cross-check it against the derived one.
- **Restatements.** Dedupe on (concept, start, end), keeping the newest `filed` date, tie-break on accession.
- **Calendar quarter comes from the period midpoint.** Aggregate a quarter only once all five spenders have reported it.
- **Outflows are stored positive.** Lease figures that are unknown stay blank, never zero.
- **quarterly.csv holds USD values only.** Ratios are in `wide.csv` and `aggregate.csv`.

## Quirks found in the real data

- Amazon files trailing-twelve-month figures in 10-Qs. These are year-long but are not fiscal years (`_fiscal_years_only`).
- Amazon's capex uses three tags: `PaymentsToAcquirePropertyPlantAndEquipment` through Q1 2017, `PaymentsForProceedsFromProductiveAssets` from Q2 2017 to Q2 2018, then `PaymentsToAcquireProductiveAssets`.
- Oracle's FY2018 to FY2022 data has "3-month" revenue facts holding the full-year figure. They are rejected and listed as warnings (`_equals_full_year`).
- Oracle stopped tagging finance lease principal after February 2026, and Alphabet's quarterly lease data starts in 2024.
- Meta's January 2025 10-K recast 2022 and 2023 annual capex net of proceeds without recasting quarters, so about $0.2B falls into each derived Q4.

## Rules

- Do not loosen validation tolerances to get a build through. Find the root cause.
- Outputs must stay deterministic: sorted rows, no run timestamps. Chart and README dates come from the newest filing, not today.
- README sections between markers are generated. `My read this quarter` and `About me` belong to the author, so never write market commentary or opinions.
- No em-dashes in the README or code comments. Never hardcode an email address.
- The annual-sum check is an identity for years built purely from YTD subtraction. It only has real power where quarters are reported directly.

# One approved Meta forecast

Run `make explain ID=META-6e73e0ba7afe` or read these same records on GitHub. The ID selects the 10-K passage. The first public filing represents the grouped claim.

| Evidence | Filing | Filed statement |
|---|---|---|
| META-7dcf3e00303f | [8-K earnings exhibit, February 1, 2024](https://www.sec.gov/Archives/edgar/data/1326801/000132680124000010/meta-12312023xexhibit991.htm) | “We anticipate our full-year 2024 capital expenditures will be in the range of $30-37 billion, a $2 billion increase of the high end of our prior range.” |
| META-6e73e0ba7afe | [10-K MD&A, February 2, 2024](https://www.sec.gov/Archives/edgar/data/1326801/000132680124000012/meta-20231231.htm) | “We anticipate making capital expenditures of approximately $30 billion to $37 billion in 2024.” |

1. **Extract.** Both rules proposals produce FY2024 and USD 30,000,000,000 to 37,000,000,000. The model's first 10-K response failed schema validation. Its second proposed $3B to $3.7B without a fiscal year. [10-K trace and cassette keys](../data/guidance/traces/META-6e73e0ba7afe.json)
2. **Verify and match.** Both rules proposals pass the quote, capex outlook, dollar, period, direction and definition checks. Each filing identifies capital expenditures including principal payments on finance leases. The two distinct filings concern the same December 2023 results period. Preserve both filing dates and date the claim to February 1. [Release trace](../data/guidance/traces/META-7dcf3e00303f.json)
3. **Apply the policy.** The claims agree on company, target, dollars and spending definition. No conflicting claim exists for this event and year. The ledger records one approval under `auto-corroborated` with both passage IDs. [Audit ledger](../data/guidance/audit.json)
4. **Compare and publish.** The first approved FY2024 midpoint was $33.5B. The last approved range was $38B to $40B. The four FY2024 quarters of lease-adjusted capex sum to $39.225B, or +17.1% against the first approved midpoint (n=1 fiscal year). The chart plots the actual separately from the range. [Fiscal paths](../data/processed/guidance_paths.csv) · [Chart](charts/guidance_path.png)

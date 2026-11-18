# One filing, two proposals

This is the output of `make explain ID=META-6e73e0ba7afe`. The checks show how a tenfold dollar error and a missing target year keep a real Meta filing out of the chart.

```text
META-6e73e0ba7afe | META 10-K filed 2024-02-02
https://www.sec.gov/Archives/edgar/data/1326801/000132680124000012/meta-20231231.htm
Passage: We anticipate making capital expenditures of approximately $30 billion to $37 billion in 2024.
Clean document SHA-256: 85364e0cba33cb294f5e780c61f6e454f69b740e6ba31b6f71c1e6531cee9d45
Rules, attempt 1: FY2024, $30.0B to $37.0B.
  PASS  annual period
  PASS  capex outlook
  PASS  comparison series
  PASS  direction
  PASS  dollars and units
  PASS  verbatim quote
  Series: capex_lease_adjusted. The issuer explicitly adds lease principal.
  Filing definition: Capital expenditures, including principal payments on finance leases
Recorded fields: kind=directional, year=None, low=3000000000, high=3700000000, direction=up.
Recorded qwen2.5:1.5b-instruct call e08a91e880fe.
Local model, attempt 1: schema rejected. () Value error, Only numeric guidance can have dollar bounds
Recorded qwen2.5:1.5b-instruct call 6cfd84bd915f.
Local model, attempt 2: no single fiscal year, $3.0B to $3.7B.
  FAIL  annual period
  PASS  capex outlook
  PASS  comparison series
  PASS  direction
  FAIL  dollars and units
  PASS  verbatim quote
  Series: capex_lease_adjusted. The issuer explicitly adds lease principal.
  Filing definition: Capital expenditures, including principal payments on finance leases
Review: pending in VS Code.
Chart: no point for this passage.
No annual forecast passed review (n=0), so upward revisions, the gap from initial guidance to actual spending, and company reliability remain unmeasured.
```

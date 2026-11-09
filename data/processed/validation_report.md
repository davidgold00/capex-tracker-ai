# Validation report

**Status: PASS**

- Fiscal years where four quarters sum to the 10-K: 181
- Failures: 0
- Warnings: 16

## Failures

None.

## Warnings

| Check | Company | Metric | Detail |
|---|---|---|---|
| direct_rejected | ORCL | revenue | FY2018 Q4: reported 3-month value $39.383B equals the full-year figure, so it was treated as a tagging error. Used YTD-derived $11.014B |
| direct_rejected | ORCL | revenue | FY2019 Q4: reported 3-month value $39.506B equals the full-year figure, so it was treated as a tagging error. Used YTD-derived $11.137B |
| direct_rejected | ORCL | revenue | FY2020 Q4: reported 3-month value $39.068B equals the full-year figure, so it was treated as a tagging error. Used YTD-derived $10.439B |
| direct_rejected | ORCL | revenue | FY2021 Q4: reported 3-month value $40.479B equals the full-year figure, so it was treated as a tagging error. Used YTD-derived $11.227B |
| direct_rejected | ORCL | revenue | FY2022 Q4: reported 3-month value $42.440B equals the full-year figure, so it was treated as a tagging error. Used YTD-derived $11.840B |
| qoq_move | GOOGL | capex | Q1 2018 (FY2018 Q1) moved +69% QoQ: $4.307B to $7.299B |
| qoq_move | META | capex | Q4 2024 (FY2024 Q4) moved +75% QoQ: $8.258B to $14.425B |
| qoq_move | ORCL | capex | Q2 2021 (FY2021 Q4) moved +73% QoQ: $0.414B to $0.717B |
| qoq_move | ORCL | capex | Q2 2024 (FY2024 Q4) moved +67% QoQ: $1.674B to $2.798B |
| qoq_move | ORCL | capex | Q3 2026 (FY2027 Q1) moved +73% QoQ: $16.493B to $28.499B |
| qoq_move | ORCL | capex | Q4 2024 (FY2025 Q2) moved +72% QoQ: $2.303B to $3.970B |
| tag_disagreement | AMZN | capex | PaymentsForProceedsFromProductiveAssets disagrees with the higher-ranked tag on 3 of 10 shared periods |
| tag_disagreement | AMZN | capex | PaymentsToAcquirePropertyPlantAndEquipment disagrees with the higher-ranked tag on 4 of 10 shared periods |
| tag_disagreement | MSFT | revenue | SalesRevenueNet disagrees with the higher-ranked tag on 3 of 10 shared periods |
| tag_disagreement | ORCL | revenue | Revenues disagrees with the higher-ranked tag on 4 of 14 shared periods |
| tag_disagreement | ORCL | revenue | SalesRevenueNet disagrees with the higher-ranked tag on 16 of 16 shared periods |

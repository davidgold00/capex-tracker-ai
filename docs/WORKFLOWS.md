# From filing to finding

## The system

```mermaid
flowchart TD
    W[Weekly GitHub Action] --> X[SEC companyfacts XBRL]
    W --> F[New earnings releases and periodic MD&A]
    X --> V[Build and validate discrete quarters]
    F --> R[Rules propose filed guidance]
    R --> E[Verify source quote, dollars, year, direction and definition]
    E --> C[Group the same dated claim across filings]
    C --> A[Corroboration or verified dual agreement]
    C --> H[Browser review queue]
    H --> A2[Verified manual decision]
    A --> L[Approval ledger]
    A2 --> L
    L --> J[Join approved claims to four matched fiscal quarters]
    V --> J
    J --> O[Finding, chart and README]
    V --> O
```

## 1. Financial actuals

```mermaid
flowchart LR
    X[USD duration facts] --> D[Deduplicate restatements]
    D --> T[Rank and stitch configured tags]
    T --> Q[Classify by actual duration and fiscal start]
    Q --> S[Use direct quarter or subtract YTD totals]
    S --> V{Validation}
    V -->|Failure| Stop[Stop publication]
    V -->|Pass| F[Aggregate complete periods and publish provenance]
```

Oracle's reported three-month FY2022 Q4 revenue equaled its full-year value. The build derived Q4 from the annual and nine-month totals and recorded the warning. [Validation report](../data/processed/validation_report.md)

## 2. Extraction, review and approval

```mermaid
flowchart TD
    P[Filing passage] --> R[Deterministic rules]
    P --> M[Optional local extraction or recorded response]
    R --> G[Verify each proposal against its own document]
    M --> G
    G --> K[Group by issuer, event, target, values and definition]
    K --> B{Conflicting claim?}
    B -->|Yes| H[Pending human review]
    B -->|No| C{Verified release and periodic report agree?}
    C -->|Yes| AC[auto-corroborated]
    C -->|No| D{Two verified extractors agree?}
    D -->|Yes| AD[auto-dual-match]
    D -->|No| H
    H --> M2[Optional local directional adjudication]
    M2 --> MP[model-assisted pending subset]
    MP --> H2[Browser decision]
    H --> H2
    H2 -->|Approve and reverify| MA[manual]
    H2 -->|Reject| RJ[Audit rejection]
    AC --> A[Approved ledger]
    AD --> A
    MA --> A
```

Meta's FY2024 range of $30B to $37B appears in the February 1 release and February 2 10-K. [Release trace](../data/guidance/traces/META-7dcf3e00303f.json) · [10-K trace](../data/guidance/traces/META-6e73e0ba7afe.json)

## 3. Evaluate the extractor and local model jobs

```mermaid
flowchart TD
    G[Label SEC passages and flag uncertainty] --> S[Freeze dev and later-year test]
    S --> P[Record selection rule before extraction]
    P --> V[Develop on 2023 and 2024 dev passages]
    V --> T[Score frozen 2025 and 2026 test once]
    T --> R[Select rules for extraction]
    T --> F[Diagnose field and verification failures]
    F --> D[Label post-fix diagnostic separately]
    R --> B[Compare four small models on dev only]
    B --> J[Choose local rephrasing and trial directional review]
```

The frozen test selected rules with 13/13 detected positives. Four later dev comparisons supplied a different measurement for each model job. [Frozen scores](../eval/test_results.json) · [Bake-off](../eval/MODEL_BAKEOFF.md)

## 4. Publish the quarterly paragraph

```mermaid
flowchart TD
    D[Complete quarter comparisons and approved guidance] --> P[Plan dated amounts and direction words]
    P --> T[Construct deterministic sentences]
    P --> M[Optional local rephrasing]
    M --> G{Every planned fact exactly once?}
    G -->|Pass| L[Publish labeled local draft]
    G -->|Fail once| Retry[One repair attempt]
    Retry --> G2{Grounded?}
    G2 -->|Pass| L
    G2 -->|Fail| T
    T --> K{Template passes same checker?}
    K -->|Yes| O[Publish template-generated, fact-checked]
    K -->|No complete plan| U[Report Not measured]
```

For Q3 2026 the planner compares $230.4B with $181.5B a quarter earlier and $105.8B a year earlier. The current plan also includes Meta's approved range. [Planner and checker](../src/capex_tracker/guidance/ground.py)

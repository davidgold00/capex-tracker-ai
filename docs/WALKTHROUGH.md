# Interview walkthrough

Open the repository folder in VS Code. Under **Terminal > Run Task**, select **Guidance: run interview demo**. The menu starts the replay. It uses committed filing evidence and works offline with the project's Python environment. The equivalent command is `make demo`.

## Two minutes

**Question.** If a hyperscaler tells investors how much it expects to spend, how far does its actual spending finish from that first forecast? A useful comparison needs the company's reporting period and its definition of spending. A number lifted from a press release supplies neither on its own.

**Finding.** No annual forecast passed review (n=0), so upward revisions, the gap from initial guidance to actual spending, and company reliability remain unmeasured.

**Show the filing.** Run the interview demo and read Meta's sentence aloud. The company expected $30 billion to $37 billion in 2024. The rules captured those endpoints and the year. Elsewhere in that filing Meta says capital expenditures include principal payments on finance leases. That wording points to the lease-adjusted XBRL series.

The local model's retry returned $3 billion to $3.7 billion. Its explanation described the original range correctly, but its structured dollar fields were ten times too small. The fiscal year was empty. Both errors are visible on screen. A match in the prose is insufficient to approve those fields.

**Limitation.** This run required verified agreement between the extractors for automatic approval. All 156 passages stayed in the review queue. The chart shows why a spending comparison is unavailable. The evaluation answers a narrower interview question: on the held-out passages the rules recovered all nine numeric targets, and the local model recovered none.

## Five minutes

Use the two-minute opening and demo. Spend the remaining time on how the two data sources meet.

**Minute three.** Start with the actual. A financial statement already identifies a company's cash expenditure, the period and the reporting concept. The pipeline ranks XBRL tags, resolves duplicate filings and turns year-to-date cash flows into discrete quarters. An annual comparison requires all four fiscal quarters of the same measure. The validation report records 181 successful annual checks and 16 warnings in this snapshot. Open the Oracle warning and follow its arithmetic.

**Minute four.** The model sees one prospective passage from an SEC earnings exhibit or MD&A section. It proposes structured fields. Code checks the quote against the cached text, the dollar units against the spending clause, the annual target against the wording, and the definition against the filing. Model confidence never grants approval. A reviewer can open the evidence URL, correct supported fields, then approve or reject a row in VS Code. The audit retains the decision and its origin.

**Minute five.** The test contains 24 passages from later filings. Two labels were uncertain, leaving 22 scored passages and 13 positives. The selection rule required a recall gain of at least ten percentage points at equal or better precision. Rules detected 13 of 13 positives. Local Qwen detected 5 of 13. Rules became the primary proposal source. A quote can express a real forecast and still lack a fiscal year or a comparable spending definition. Seven of the 13 positive rules predictions passed every check. The weekly pipeline reads decisions already on disk, so its financial update can run on a machine without Ollama.

If there is time, run **Guidance: run grounding demo**. It compares the latest capex total with the previous quarter and year-ago quarter. The planted draft changes both a dollar value and a direction. The rejection prints both reasons. [Evaluation and denominators](../GUIDANCE_PROGRESS.md)

## Fifteen minutes

### 1. Can the actual be reconstructed? (three minutes)

**point to make** The comparison starts with a reproducible cash-flow series.

- Read a six-month cash flow as a cumulative figure. Subtract Q1 to recover Q2. Subtract nine months from the full year to recover Q4.
- Oracle's fiscal 2018 revenue tagged as a three-month value equals the $39.383 billion annual amount. The derived Q4 was $11.014 billion. The validation report records the rejected direct value.
- Amazon also files trailing-twelve-month cash flows in quarterly reports. A twelve-month duration alone cannot identify a fiscal year. The code checks the form or an aligned year-to-date start.
- Tag switches require ranking and stitching by period. Every observation preserves its source tag. Four quarters must reconcile with the annual filing within the configured 0.5% tolerance. For quarters made entirely by subtraction, that check is an arithmetic identity.

**show this** [Validation report](../data/processed/validation_report.md) and [quarter derivation](../src/capex_tracker/quarters.py)

### 2. Follow one forecast from text to review (three minutes)

**point to make** A model proposal becomes an auditable claim only when its evidence, target and units can be checked.

- Start with the accession and filing URL. The source manifest records separate hashes for the raw document and the cleaned text.
- Narrow the input to a sentence with a capex phrase and a forward-looking cue. The rules and local model receive that passage independently. Source metadata comes from the filing inventory.
- Read the retry on Meta's range. Its explanation is plausible while both structured endpoints have the wrong scale. The quote check can pass even when the dollar check fails.
- Show the pending row. A human can reject it or save a supported correction. Numeric revisions and direction-only markers become publishable only after approval.

**show this** `make explain ID=META-6e73e0ba7afe` and [the same trace in print](TRACE_EXAMPLE.md)

### 3. Compare the extractors (two minutes)

**point to make** Model selection needs a fixed decision rule and explicit denominators.

- The gold set deliberately includes ranges, points, directions, historical expenditures, financing proceeds and forecasts of other line items. It includes examples from all five companies.
- The dev split uses 2023 and 2024 filings. The held-out set uses later filings and was hash-locked before extractor development. It contains 24 of 45 passages. Similar issuer wording can recur across years.
- The rules had 13 correct detections in 13 predictions. The model had five in seven predictions. Numeric accuracy counts missed gold targets as errors. The denominators for verification are predictions, so they differ.
- These were purposively selected passages with one annotator. The test cannot establish the error rate across all SEC filings, all prompts, or larger models.

**show this** [Locked gold set](../eval/gold/test.json), [held-out predictions](../eval/test_results.json) and [selection rule](../GUIDANCE_PROGRESS.md)

### 4. Match the spending definition (two minutes)

**point to make** A close forecast can look inaccurate if the actual measures different spending.

- Meta explicitly includes principal payments on finance leases. Add reported principal to reported purchases for the comparison. A missing lease quarter prevents an annual comparison.
- Alphabet's free-cash-flow reconciliation identifies purchases of property and equipment. Oracle's cash-flow statement labels the investing outflow directly in the example release.
- Amazon also uses purchases net of proceeds from sales and incentives. If the filing does not establish a match to the available XBRL series, keep the candidate pending.
- The first observed, approved numeric midpoint anchors the gap. Reaffirmations retain their date and do not count as revisions. The gap is signed. A company ranking would use median absolute gaps and require at least two completed years in each of two companies.

**show this** [Series mapping](../src/capex_tracker/guidance/extract.py), [wide XBRL series](../data/processed/wide.csv) and [guidance chart](charts/guidance_path.png)

### 5. Guard the quarterly paragraph (two minutes)

**point to make** A correct dollar amount can become a false claim when paired with the wrong period.

- Form a ledger of comparisons from the latest complete quarter and its two reference quarters. Add new approved guidance from the filing cycle.
- Ask the local model to assemble a paragraph from eligible claims. The checker binds each complete sentence to its subject, dates, amounts and direction. It rejects extra clauses and missing comparisons.
- Run the guard demo. Then inspect the saved draft attempts. The model joined two comparisons as a sequence. Both attempts were rejected, leaving the machine-drafted README section empty.
- A future weekly update checks the ledger fingerprint and the paragraph again. A change in facts makes an old paragraph ineligible.

**show this** `make demo-guard` and [the recorded draft decisions](../data/guidance/draft.json)

### 6. What failed and what changed? (three minutes)

**point to make** The record distinguishes a resource limit, an extraction error and a publication decision.

- The installed 7B model timed out before returning its first dev answer on the 8 GB Mac. The switch to the local 1.5B model happened before held-out scoring. The cassettes identify the measured model.
- The smaller model missed the annual target on every scored annual positive. Rules became the primary extractor under the prewritten decision rule. The automatic approval threshold stayed in place.
- The coverage pass found real filed outlooks in all five companies. Microsoft's identified outlooks described directions over multiple years. Filing coverage and an approved annual comparison answer different questions.
- The offline demo preserves the failed attempt and retry. An interviewer can inspect the source, repeat the baseline and see where publication stopped. [DAVID: why I built this]

**show this** [Run log](../GUIDANCE_PROGRESS.md), [model configuration](../data/guidance/model.json) and [review queue](../data/guidance/pending.csv)

## Design tradeoffs

| Decision | Alternative | Why | Cost |
|---|---|---|---|
| XBRL for actual spending | Model-read tables | Tagged periods and cash-flow amounts can be reconciled to annual facts. | Tags and restatements need explicit handling. |
| SEC earnings exhibits and MD&A | Include call transcripts | Filed evidence is publicly traceable by accession. | Call-only guidance stays missing. |
| One local model | Hosted inference | The assignment requires local processing and offline replay. | Available memory limited the measured model. |
| Sentence windows | Whole filing as model input | A short evidence span is directly checkable. | Adjacent context can carry the missing year. |
| Frozen later-filing test | Tune and score on the same passages | The decision can be compared with a rule written in advance. | A small holdout has limited precision and recurrent language. |
| Require dual agreement for unattended approval | Publish the baseline alone | The unattended run has no human reviewer. | Every passage stayed pending. |
| Match lease definitions explicitly | One reported capex series everywhere | A forecast can include lease principal or net proceeds. | Some companies and fiscal years cannot be compared. |
| Sentence-level grounding | Accept any prose with matching numbers | The checker binds the numbers to a subject, dates and direction. | Even potentially correct paraphrases can be rejected. |

## Ten interview questions

1. **Why use a model here?** Filed outlooks vary in wording and sometimes mix past spending, guidance and other line items. That makes extraction a testable use of a language model. This run favored rules.
2. **Why not use an API model?** Local inference was a project requirement. Recorded responses allow offline demos and keep inference out of the weekly job. Hosted-model accuracy and cost were not measured.
3. **How do you know an extraction is right?** Inspect the filing, verify the units and year, and check the spending definition. Compare predictions against labeled passages. A high model confidence cannot substitute for these checks.
4. **What was the error rate, on how many examples?** With invalid outputs counted as abstentions, rules made zero detection errors on 22 certain test passages. The model had eight missed positives and two false positives. Its predictions matched zero of nine numeric targets. No production error rate was measured for approved rows (n=0).
5. **Did the LLM beat the baseline?** No. Its recall was 5/13 and rules recall was 13/13. The prewritten rule selected rules. Those results apply to the recorded 1.5B configuration.
6. **What about guidance given only on calls?** It stays a coverage gap. All five issuers had some filed outlook language in the reviewed windows. That does not establish what was said exclusively on calls.
7. **Which company guided most reliably?** The run supports no ranking. Each ranking needs completed fiscal years with an approved initial forecast and four matched XBRL quarters.
8. **What is the weakest part?** The model added review work without yielding an automatic approval. The gold set is small and purposive, and single-sentence windows can miss context.
9. **What stops a plausible but wrong summary?** A published sentence must match a current ledger claim. A retry that still fails leaves the generated section empty. The repository retains the attempted text and reasons.
10. **How would a reviewer change the outcome?** Open `data/guidance/pending.csv` in VS Code, follow the source link, enter `approve` or `reject` in `decision`, and save. Optional `edit_*` fields replace individual proposed values. Use `null` to clear a field. Run **Guidance: apply saved CSV decisions**, then **Guidance: render chart and README**. Manual approvals recheck the original source hash and every gate. On a new checkout, **Guidance: cache SEC source documents** prepares the private cache using the ignored contact file.

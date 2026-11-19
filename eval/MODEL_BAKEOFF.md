# Small-model bake-off on the dev split

Each extractor saw the same 21 dev passages. One uncertain label is excluded from scoring. Precision and recall score positive detection. Verification requires all checks on the predicted positives. Each writer received the same six plans, one per distinct preceding calendar quarter represented by dev filing dates. Plans include the quarterly and annual capex comparisons. No held-out passage or current-quarter plan is used for model selection.

| Method | Precision | Recall | Verified | Extraction s/item | Grounded | Draft s/plan |
|---|---:|---:|---:|---:|---:|---:|
| rules | 100.0% (8/8, n=8) | 100.0% (8/8, n=8) | 62.5% (5/8, n=8) | 0.0002 | Not measured | Not measured |
| qwen2.5:1.5b-instruct | 44.4% (4/9, n=9) | 50.0% (4/8, n=8) | 0.0% (0/9, n=9) | 2.3847 | 100.0% (6/6, n=6) | 1.6057 |
| qwen2.5:3b-instruct | 100.0% (3/3, n=3) | 37.5% (3/8, n=8) | 0.0% (0/3, n=3) | 3.3441 | 100.0% (6/6, n=6) | 3.3782 |
| llama3.2:3b | 50.0% (1/2, n=2) | 12.5% (1/8, n=8) | 50.0% (1/2, n=2) | 3.3604 | 50.0% (3/6, n=6) | 5.2037 |
| phi3.5 | 60.0% (6/10, n=10) | 75.0% (6/8, n=8) | 40.0% (4/10, n=10) | 4.1669 | 16.7% (1/6, n=6) | 3.2365 |

**Extraction:** rules. The original rule requires a 0.10 recall advantage without losing precision. No model can exceed rules on this dev split. The original frozen test remains the only selection test.

**Rephrasing:** qwen2.5:1.5b-instruct had the highest number of verified plans (lowest measured seconds per plan breaks ties). No template fallback counts as a model pass.

**Adjudication candidate:** phi3.5 among completed local models, ordered by correct directional detections, then overall recall and precision. This exploratory dev choice still needs a separate classification measurement.

One Llama 3.2 proposal passed all original checks on gold-f5972fda04, a negative example about depreciation expenses. A direction word, year and capex reference can coexist without referring to the same metric. A verification pass by itself does not establish correct classification.

Time is total Ollama generate duration including retries and initial load, divided by all 21 passages or six plans. Screened-out passages contribute zero model time. Rules time is a wall-clock measurement of proposal and verification on 21 in-memory documents with precomputed definitions. File I/O is excluded.

| Local model | Load / completion | Largest observed allocation | Largest observed runner RSS |
|---|---|---:|---:|
| qwen2.5:1.5b-instruct | Completed | 1.02 GiB | 0.15 GiB |
| qwen2.5:3b-instruct | Completed | 1.94 GiB | 0.19 GiB |
| llama3.2:3b | Completed | 2.16 GiB | 0.32 GiB |
| phi3.5 | Completed | 2.81 GiB | 0.91 GiB |

Memory is a sampled high-water observation, not a process lifetime peak. Allocation includes memory Ollama attributes to the loaded model. RSS excludes some GPU allocations. Qwen 1.5B has a single observation. Rate samples for the remaining runners were taken about every two seconds.

[Per-item results, request/response cassettes and durations](bakeoff/). Replay from the cached clean filing texts with `PYTHONPATH=src python scripts/model_bakeoff.py MODEL`. Only `--record` permits loopback inference. The defaults limit live model size.

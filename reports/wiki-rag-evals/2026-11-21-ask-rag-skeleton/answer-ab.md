# Ask-rag skeleton: end-to-end A/B (2026-11-21)

17 reviewed cases (DMT 5, ontology 4, physical-division 8) × skeleton on/off × two retrieval strategies, run on one server (`ask-rag` vs `ask-rag-noskeleton`).

- Answerer: `claude-sonnet-5-5`.
- Judge: the eval script's default `claude-sonnet-4-6`.
- Raw rows are in `reports/wiki-ragas-evals/2026-11-21-skeleton-ab-*`.

| Strategy · set | Arm | Page recall | Wrong-page pass | Required terms | Answer accuracy | Faithfulness | Latency |
|---|---|---|---|---|---|---|---|
| legacy · DMT | on | **0.95** | 1.00 | **1.00** | – | 0.90 | 8.6 s |
| legacy · DMT | off | 0.23 | 0.80 | 0.50 | – | 0.91 | 5.8 s |
| legacy · ontology | on | 0.88 | 0.75 | 1.00 | 0.75 | 0.94 | 4.8 s |
| legacy · ontology | off | 0.88 | 0.75 | 1.00 | 0.81 | 0.94 | 4.9 s |
| legacy · phys-div | on | **1.00** | 1.00 | 1.00 | 0.72 | 0.80 | 5.7 s |
| legacy · phys-div | off | 0.92 | 1.00 | 1.00 | 0.63 | 0.80 | 5.8 s |
| diverse · DMT | on | **1.00** | **0.60** | **1.00** | – | 0.90 | 9.5 s |
| diverse · DMT | off | 0.28 | 0.20 | 0.50 | – | 0.83 | 7.9 s |
| diverse · ontology | on | 0.88 | 0.25 | 1.00 | 0.75 | 0.95 | 5.4 s |
| diverse · ontology | off | 0.88 | 0.00 | 1.00 | 0.75 | 0.92 | 4.2 s |
| diverse · phys-div | on | 1.00 | 0.75 | 1.00 | 0.72 | 0.78 | 6.8 s |
| diverse · phys-div | off | 1.00 | 0.75 | 1.00 | 0.72 | 0.71 | 7.2 s |

"Wrong-page pass" is the share of runs that returned no page on the case's must-not list.

**Tokens per request (mean over 17 cases):**
- legacy: 5,145 → 11,025 (+5.9k)
- diverse: 6,032 → 11,079 (+5.0k)

**Reading:**
- The fix closes the DMT coding-question gap: must-have recall rises from 0.23–0.28 to 0.95–1.00. DMT-ASK-011 names F08 only with the fix on, and its other-domain overlays disappear.
- On the ontology and physical-division sets, answer quality is unchanged or slightly better. The one lower score, ontology accuracy on legacy (0.75 vs 0.81 on 4 cases), amounts to one judge point.
- Faithfulness is equal or higher in every set except legacy DMT (0.90 vs 0.91).
- The cost roughly doubles answerer input, about 5–6k tokens per request, and DMT latency rises by 1.6–2.8 s.
- Leaks that remain with the fix on are `maintenance-*` and `domoic-acid-scallops.md`, plus overlays on ontology questions that name no domain. These are by design: maintenance pages are kept, and the filter applies only when a domain is named.

# DMT Ten-Question Ask vs Ask-RAG Pilot

Date: 2026-07-30

Dataset: `evals/wiki-rag/dmt_end_to_end_cases.json`

Raw results: `results.json`

## Scope

- Ten questions supplied from DMT.
- Endpoints: `/wiki/ask` and wiki-mode `/wiki/ask-rag`.
- Answer models: `claude-sonnet-4-6` and
  `lmstudio:google/gemma-4-12b`.
- `/wiki/ask` selector held fixed at `claude-sonnet-5`.
- `/wiki/ask-rag` used `diverse_pages` with a seven-page limit.
- No Ragas judge metrics were run for the full matrix because six cases do not
  yet have independently reviewed reference answers. A separate one-case smoke
  confirmed that Ragas faithfulness executes successfully.

The summary below was recalculated after fixing two evaluator semantics:
unlabelled cases no longer count as automatic deterministic passes, and reviewed
acceptable support pages count toward precision without counting toward
must-have recall.

## Corrected Summary

| Endpoint | Answer model | Success | Mean latency | Median latency | Reviewed page precision | Reviewed must-have recall | Reviewed leak-free |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `/wiki/ask` | Claude Sonnet 4.6 | 10/10 | 21.5 s | 20.2 s | 65.7% | 100.0% | 0/4 |
| `/wiki/ask-rag` | Claude Sonnet 4.6 | 10/10 | 11.9 s | 11.9 s | 71.4% | 41.7% | 0/4 |
| `/wiki/ask` | Gemma 4 12B | 2/10 | 60.9 s among successes | 60.9 s | 66.7% on one successful reviewed case | 100.0% on that case | 0/1 |
| `/wiki/ask-rag` | Gemma 4 12B | 9/10 | 68.6 s among successes | 72.4 s | 71.4% | 41.7% | 0/4 |

## Main Findings

### `/wiki/ask` has complete core recall but expands too far

Claude `/wiki/ask` retrieved every must-have page in the four reviewed cases.
However, final contexts contained 12-15 pages despite `max_pages=7`. The
graph-expanded output also included `index.md` in every reviewed case and added
maintenance or wrong-domain pages in three of four cases.

This large context directly broke Gemma with its current 8192-token context:

- six requests failed because the initial prompt required 8,588-12,784 tokens;
- two more returned an empty final response;
- only two of ten `/wiki/ask` requests succeeded.

The result is not evidence that Gemma cannot answer FoodEx2 questions. It is
evidence that the current `/wiki/ask` context assembly is incompatible with this
8192-token local deployment.

### `/wiki/ask-rag` is smaller and more reliable, but retrieval is incomplete

`/wiki/ask-rag` was faster than `/wiki/ask` for Claude and much more reliable
for Gemma. It retrieved the correct domain overlay in all four reviewed cases,
but consistently omitted core construction pages:

- pesticides and contaminants cases: 1/3 must-have pages;
- VMPR and additives cases: 2/4 must-have pages;
- mean must-have recall: 41.7%.

Every reviewed RAG case also leaked at least one prohibited page. Examples
include contaminants/additives/domoic-acid pages in the pesticides case,
pesticides/additives/domoic-acid pages in the contaminants case,
`maintenance-2024.md` in VMPR, and the contaminants overlay in additives.

This confirms the previously identified RAG defect: semantic retrieval finds
the domain page, but does not enforce the required base-term and validation
skeleton or exclude wrong-domain and maintenance material.

### Answer-level observations

- All successful models and endpoints correctly refused the bicycle-tyre
  negative control as outside FoodEx2.
- Claude `/ask`, Claude `/ask-rag`, and Gemma `/ask-rag` agreed that
  `A02MA#F21.A07SE` is appropriate for organic skimmed cow milk and that the
  skimmed property should not be duplicated.
- For the coated roasted nut, both Claude paths correctly treated `A014C` as
  provisional pending a derivative-base catalogue check. Gemma `/ask-rag` was
  more willing to accept `A014C` and did not clearly enforce the derivative-base
  check.
- The smoked nitrite-free ham answers exposed a genuine attribution problem:
  Claude `/ask` proposed that a supported nitrite-free descriptor might belong
  under `F10`, while Claude `/ask-rag` said the supplied pages do not support
  such an absence facet. This case needs a catalogue-backed reference answer
  before it can be scored as correct.

## Interpretation

For the current configurations:

- Claude Sonnet 4.6 is operationally reliable on both endpoints.
- Claude `/wiki/ask` gives much stronger core page recall, but its context
  assembly needs capping and filtering.
- `/wiki/ask-rag` is the safer endpoint for the current local Gemma deployment,
  but it is not yet trustworthy as the sole retrieval mechanism because 58.3%
  of must-have pages were missed.
- Gemma 4 12B at an 8192-token context is not usable with current
  graph-expanded `/wiki/ask`.
- A faithfulness score alone would not resolve these issues: an answer can be
  perfectly faithful to incomplete or misrouted context.

## Next Evaluation Step

Before running the full Ragas suite, independently review reference answers for
all ten cases, especially the ham and coated-nut cases. Then add stable required
and forbidden facts. After the retrieval fixes, rerun the identical dataset and
use answer accuracy plus faithfulness; compare the new raw page sets before
interpreting aggregate judge scores.

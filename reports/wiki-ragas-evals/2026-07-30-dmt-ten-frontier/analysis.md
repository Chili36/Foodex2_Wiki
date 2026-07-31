# Frontier model evaluation: `/wiki/ask` versus `/wiki/ask-rag`

Date: 2026-07-30

## Bottom line

Use `gpt-5.6-terra` as the current default answer model for this pilot. It was
one of two models with 20/20 first-pass endpoint success, had the highest
`/ask-rag` Ragas faithfulness score, was close to the fastest models, and did
not show the answer contradictions found in the other 20/20 model, Haiku.

Do not treat the current `/ask-rag` retrieval path as production-ready merely
because Terra answers its context well. On the four cases with reviewed page
gold, it retrieved only 41.7% of required pages and returned a prohibited page
in every case. Changing the answer model cannot repair missing or misleading
retrieval context.

`/ask` has much better reviewed-page recall (93.8–100%), but graph expansion
inflates its context from the configured seven selected pages to 12.8–13.7
pages on average. It is therefore slower and less precise than its
`max_pages=7` setting suggests.

## Canonical results

The table uses one successful response for every question, endpoint, and model.
Two transient failures were replaced by their exact one-case retries:

- Luna `/ask`, DMT-ASK-010: empty final answer on the first attempt;
- Sonnet `/ask`, DMT-ASK-006: empty page-selector response before the answerer
  ran.

Sonnet's answer generation uses Anthropic JSON-schema structured output in the
canonical run. Before that integration fix, Sonnet returned malformed JSON on
several questions even though its prose answer was present.

| Endpoint | Answer model | First-pass success | Canonical mean latency | Mean pages | Ragas faithfulness |
| --- | --- | ---: | ---: | ---: | ---: |
| `/ask` | Claude Sonnet 5 | 9/10 | 27.73 s | 12.8 | 0.694 |
| `/ask` | Claude Haiku 4.5 | 10/10 | 12.42 s | 13.7 | 0.663 |
| `/ask` | GPT-5.6 Terra | 10/10 | 13.65 s | 13.5 | 0.798 |
| `/ask` | GPT-5.6 Luna | 9/10 | 12.71 s | 13.2 | **0.864** |
| `/ask-rag` | Claude Sonnet 5 | 10/10 | 13.35 s | 7.0 | 0.632 |
| `/ask-rag` | Claude Haiku 4.5 | 10/10 | 5.18 s | 7.0 | 0.425 |
| `/ask-rag` | GPT-5.6 Terra | 10/10 | 5.43 s | 7.0 | **0.795** |
| `/ask-rag` | GPT-5.6 Luna | 10/10 | **5.11 s** | 7.0 | 0.747 |

The canonical mean includes the successful retry latency for the two retried
cells. First-pass success deliberately does not.

## Retrieval findings

Page metrics are available for four reviewed cases. The remaining six questions
still need expert page labels.

| Endpoint | Reviewed-page precision | Required-page recall | Prohibited-page pass |
| --- | ---: | ---: | ---: |
| `/ask` | 0.663–0.671 | 0.938–1.000 | 0.000 |
| `/ask-rag` | 0.714 | 0.417 | 0.000 |

The small differences between `/ask` answer-model rows are not caused by the
answer model. The Sonnet 5 selector was held fixed, but it was rerun for every
cell and selection is stochastic. A stronger future experiment should freeze
one selected page set per question before sweeping answer models.

The retrieval conclusion is much stronger than the model ranking:

- `/ask-rag` is fast and returns exactly seven pages, but misses most of the
  reviewed must-have evidence;
- `/ask` finds most must-have evidence, but graph expansion adds roughly six
  pages beyond the selection budget;
- both paths leaked at least one explicitly prohibited page on every reviewed
  case.

## Answer-quality review

Manual inspection found differences that a mean faithfulness score cannot
express:

- Terra was the most consistently cautious on ambiguous coated-nut questions:
  it required checking whether a derivative or composite base term exists
  before confirming `A014C` plus facets.
- Luna was concise and highly grounded, but one `/ask` response was empty and
  its bicycle-tyre answer was arguably too terse.
- Sonnet produced strong explanatory prose, but was much slower. JSON-schema
  output was required to make the API integration reliable.
- Haiku contradicted itself on organic skimmed cow milk: it opened by saying
  the proposed code was incorrect, then concluded that the same code was
  correct. On another RAG answer it suggested adding an explicit facet “for
  clarity” even though the supplied rules prohibit duplicating an implicit
  facet. Haiku should not be the default despite its speed.

All models scored poorly on at least one organic skimmed-milk answer
(DMT-ASK-008). This is a useful diagnostic: the answerers knew or inferred more
than the returned page context explicitly supported. It may indicate missing
wiki evidence, weak retrieval, or an overly specific question relative to the
current pages.

## What Ragas does and does not establish

Ragas faithfulness decomposes each answer into claims and checks whether those
claims are supported by the exact page content captured in the endpoint
response. Claude Sonnet 4.6 was used as a single judge, with retrieval and
answer generation frozen before judging.

Faithfulness is not correctness. A model can score highly by faithfully
summarizing incomplete or wrong retrieved pages. Conversely, a correct statement
can score poorly if the retriever failed to supply its evidence. The current
dataset has no independent expert `reference_answer`, so answer accuracy,
factual correctness, and answer-based context recall were intentionally not
reported.

The next evaluation step is for DMT to review the ten expected answers and page
sets. Then rerun:

- Ragas answer accuracy and factual correctness;
- Ragas context recall and precision against the expert answer;
- deterministic must-say and must-not-say assertions;
- at least three repeats for selector reliability, while freezing a selected
  page set for the answer-model sweep.

## Source artifacts

- Endpoint outputs:
  [`results.json`](results.json)
- Repaired Sonnet outputs:
  [`../2026-07-30-dmt-ten-frontier-sonnet-structured-valid/results.json`](../2026-07-30-dmt-ten-frontier-sonnet-structured-valid/results.json)
- Non-Sonnet offline Ragas scores:
  [`../2026-07-30-dmt-frontier-ragas-nonsonnet/results.json`](../2026-07-30-dmt-frontier-ragas-nonsonnet/results.json)
- Sonnet offline Ragas scores:
  [`../2026-07-30-dmt-frontier-ragas-sonnet/results.json`](../2026-07-30-dmt-frontier-ragas-sonnet/results.json)
- Sonnet retry Ragas score:
  [`../2026-07-30-dmt-frontier-ragas-sonnet-retry/results.json`](../2026-07-30-dmt-frontier-ragas-sonnet-retry/results.json)
- Luna retry Ragas score:
  [`../2026-07-30-dmt-frontier-ragas-luna-retry/results.json`](../2026-07-30-dmt-frontier-ragas-luna-retry/results.json)

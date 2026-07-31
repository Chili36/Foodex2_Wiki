# Context-Pack Selector Comparison: Sonnet 5 vs Terra

Date: 2026-07-30

## Scope

This comparison exercises the production DMT retrieval surface:

- Endpoint: `POST /wiki/context-pack`
- Catalog scope: `coding`
- Gold set: all 39 reviewed cases in `evals/selection/gold_cases.json`
- Strict final page cap: 7
- Quality repeats: 3 per model, 117 calls per model
- Latency pass: 39 calls per model
- Graph expansion and answer generation: not applicable

The models ran on separate local API instances with the same repository,
wiki state, gold labels, and request payloads. Sonnet used the Anthropic
tool-call selector. Terra used the JSON page-selector implementation because
the default context-pack singleton currently assumes a messages-client model.

## Quality

| Metric | Claude Sonnet 5 | GPT-5.6 Terra | Difference |
|---|---:|---:|---:|
| Required-page recall, median pass | 91.79% | 81.24% | Sonnet +10.56 pp |
| Required-page recall, pass range | 91.79–91.88% | 79.19–81.24% | — |
| Precision, median pass | 94.49% | 97.01% | Terra +2.52 pp |
| Leak-free cases | 100% | 100% | Tie |
| Skeleton backfill case rate, median | 38.46% | 23.08% | — |
| Mean returned pack size, median | 19,866 chars | 19,202 chars | Terra −3.3% |

Terra's quality loss is systematic. It repeatedly omitted specific
construction pages, especially:

- `term-type-facet-constraints.md`
- `ingredient-facets.md`
- `facet-coding-rules.md`
- `implicit-vs-explicit-facets.md`
- `code-string-format.md`
- `validation-rules.md`

The deterministic skeleton often recognized that a broad role was missing,
but a generic backfill did not necessarily restore the exact page required by
the reviewed gold case.

## Latency

| Metric | Claude Sonnet 5 | GPT-5.6 Terra | Terra reduction |
|---|---:|---:|---:|
| Mean | 8.27 s | 5.60 s | 32.3% |
| Median | 6.44 s | 4.72 s | 26.7% |
| p95 | 11.46 s | 9.64 s | 15.9% |
| Minimum | 3.48 s | 2.73 s | — |
| Maximum | 62.21 s | 14.73 s | 76.3% |

Sonnet's mean is distorted by one 62.21-second provider/model call, but that
outlier is operationally important: it demonstrates the long tail visible to
DMT users. A separate Sonnet latency attempt also returned HTTP 503 after four
successful calls. The no-retry 39-case capture summarized above completed
without failures. Terra completed its 39-case latency pass without endpoint
failures.

## Conclusion

Terra is faster on the actual DMT endpoint, but the current implementation
gives up about 10.6 percentage points of required-page recall. That is too much
grounding loss to make Terra the context-pack default today.

Keep Sonnet 5 as the context-pack selector for now. The next useful optimization
is to reduce Sonnet's output/long-tail latency or strengthen deterministic
page-role enforcement enough that Terra's recurring omissions are repaired
without forcing seven generic pages into every pack.

## Artifacts

- `../2026-07-30-2026-07-30-sonnet5-context-pack-r3/results.json`
- `../2026-07-30-2026-07-30-terra-context-pack-r3/results.json`
- `../2026-07-30-2026-07-30-terra-context-pack-latency-r1/results.json`

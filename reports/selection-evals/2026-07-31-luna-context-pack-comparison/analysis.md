# Luna Context-Pack Selector Evaluation

Date: 2026-07-31

## Scope

- Endpoint: `POST /wiki/context-pack`
- Catalog scope: `coding`
- Gold set: all 39 reviewed cases in `evals/selection/gold_cases.json`
- Strict final page cap: 7
- Repeats: 3
- Calls: 117 per model
- Luna selector implementation: OpenAI JSON completion

Luna used the same wiki state, gold labels, candidate-aware request payloads,
selection prompt, skeleton enforcement, and page budget as the preceding
Sonnet 5 and Terra runs.

## Quality

| Metric | Sonnet 5 | Terra | Luna |
|---|---:|---:|---:|
| Required-page recall, median pass | **91.79%** | 81.24% | 86.54% |
| Required-page recall, pass range | 91.79–91.88% | 79.19–81.24% | 84.19–87.39% |
| Precision, median pass | 94.49% | **97.01%** | 96.50% |
| Leak-free cases | 100% | 100% | 100% |
| Perfect case-calls | **85/117** | 51/117 | 70/117 |
| Mean pages returned | 6.47 | 6.69 | 6.87 |

Luna closes half of Terra's recall deficit relative to Sonnet:

- Luna is 5.30 percentage points above Terra.
- Luna is 5.26 percentage points below Sonnet.

Luna's remaining systematic misses concentrate in:

- `code-string-format.md`
- `term-type-facet-constraints.md`
- `facet-coding-rules.md`
- `ingredient-facets.md`
- `implicit-vs-explicit-facets.md`
- `business-rules.md`
- `validation-rules.md`

Luna already returns nearly the full seven-page budget, so improving recall
requires better replacement/ranking of pages rather than simply returning more.

## Latency

Luna latency is measured across all 117 calls. Terra and Sonnet figures use
their comparable 39-case latency captures.

| Metric | Sonnet 5 | Terra | Luna |
|---|---:|---:|---:|
| Mean | 8.27 s | **5.60 s** | 5.66 s |
| Median | 6.44 s | **4.72 s** | 5.43 s |
| p95 | 11.46 s | 9.64 s | **8.11 s** |
| Maximum | 62.21 s | **14.73 s** | 18.11 s |

Luna completed all 117 calls without an endpoint failure. Its typical latency
is similar to Terra's and materially better than Sonnet's long-tail behavior.

## Cost At The 2026-07-31 Rates

Rates used:

- Sonnet 5: $2.00 input / $10.00 output per million tokens through
  2026-08-31
- Luna: $0.20 input / $1.20 output per million tokens
- Terra: $2.00 input / $12.00 output per million tokens

| Metric | Sonnet 5 | Terra | Luna |
|---|---:|---:|---:|
| Mean selector cost per request | $0.014076 | $0.008891 | **$0.000994** |
| Cost per 1,000 requests | $14.08 | $8.89 | **$0.99** |
| Cost of the 117-call run | $1.65 | $1.04 | **$0.12** |

Luna was about 8.9 times cheaper than Terra in these measured selector calls.
It was about 14.2 times cheaper than Sonnet 5 at Sonnet's introductory rate.
Sonnet 5's announced standard rate after 2026-08-31 would make the same
measured token usage cost $21.11 per 1,000 selector requests.

## Recommendation

Luna is not a quality-equivalent drop-in replacement for Sonnet today. Sonnet
still provides the strongest and most stable required-page recall.

Luna is, however, a credible cost-first selector:

- substantially better recall than Terra;
- no forbidden-page leakage;
- no failures across 117 calls;
- similar latency to Terra and better tail latency than Sonnet;
- under one dollar per 1,000 measured selections.

Keep Sonnet as the quality-first default for now. The strongest next design is
a Luna-first hybrid with targeted deterministic replacement or Sonnet fallback
for the recurring complex construction cases. Re-evaluate that hybrid against
the same gold before changing DMT's default.

## Artifacts

- Luna:
  `../2026-07-31-2026-07-31-luna-context-pack-r3/results.json`
- Sonnet:
  `../2026-07-30-2026-07-30-sonnet5-context-pack-r3/results.json`
- Terra:
  `../2026-07-30-2026-07-30-terra-context-pack-r3/results.json`

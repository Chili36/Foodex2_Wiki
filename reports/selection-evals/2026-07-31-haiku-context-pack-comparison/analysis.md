# Haiku Context-Pack Selector Evaluation

Date: 2026-07-31

## Scope

- Endpoint: `POST /wiki/context-pack`
- Catalog scope: `coding`
- Gold set: all 39 reviewed cases in `evals/selection/gold_cases.json`
- Strict final page cap: 7
- Repeats: 3
- Calls: 117 per model
- Haiku model: `claude-haiku-4-5-20251001`

Haiku used the same wiki state, gold labels, candidate-aware request payloads,
selection prompt, skeleton enforcement, and page budget as the Sonnet 5,
Terra, and Luna runs.

## Quality

| Metric | Sonnet 5 | Terra | Luna | Haiku 4.5 |
|---|---:|---:|---:|---:|
| Required-page recall, median pass | **91.79%** | 81.24% | 86.54% | 79.96% |
| Required-page recall, pass range | 91.79–91.88% | 79.19–81.24% | 84.19–87.39% | 78.97–84.19% |
| Precision, median pass | 94.49% | 97.01% | 96.50% | 96.58% |
| Leak-free cases | 100% | 100% | 100% | 100% |
| Perfect case-calls | **85/117** | 51/117 | 70/117 | 51/117 |
| Mean pages returned | 6.47 | 6.69 | 6.87 | 6.68 |

Haiku has the weakest median recall of the four:

- 1.28 percentage points below Terra;
- 6.58 percentage points below Luna;
- 11.83 percentage points below Sonnet 5.

Its 78.97–84.19% pass range also shows more run-to-run variation than the
other models. High precision is not enough to compensate: Haiku is choosing
plausible pages, but omitting too many pages required by the reviewed cases.

Recurring misses include:

- `term-type-facet-constraints.md`
- `process-validation-rules.md`
- `facet-coding-rules.md`
- `code-string-format.md`
- `ingredient-facets.md`
- `structural-validation.md`
- `validation-rules.md`

## Latency

Haiku and Luna latency is measured across all 117 calls. Terra and Sonnet
figures use their comparable 39-case latency captures.

| Metric | Sonnet 5 | Terra | Luna | Haiku 4.5 |
|---|---:|---:|---:|---:|
| Mean | 8.27 s | **5.60 s** | 5.66 s | 6.45 s |
| Median | 6.44 s | **4.72 s** | 5.43 s | 6.56 s |
| p95 | 11.46 s | 9.64 s | **8.11 s** | 8.96 s |
| Maximum | 62.21 s | **14.73 s** | 18.11 s | 13.58 s |

Haiku completed all 117 calls without an endpoint failure. Its tail is
controlled, but its median is slower than both Terra and Luna and even
slightly slower than the measured Sonnet median.

## Cost At Current Rates

Rates used:

- Sonnet 5: $2.00 input / $10.00 output per million tokens through
  2026-08-31
- Haiku 4.5: $1.00 input / $5.00 output per million tokens
- Luna: $0.20 input / $1.20 output per million tokens
- Terra: $2.00 input / $12.00 output per million tokens

| Metric | Sonnet 5 | Terra | Luna | Haiku 4.5 |
|---|---:|---:|---:|---:|
| Mean selector cost per request | $0.014076 | $0.008891 | **$0.000994** | $0.005749 |
| Cost per 1,000 requests | $14.08 | $8.89 | **$0.99** | $5.75 |
| Cost of the 117-call run | $1.65 | $1.04 | **$0.12** | $0.67 |

Haiku is approximately 5.8 times as expensive as Luna for these measured
requests while returning lower required-page recall.

Sonnet 5's announced standard rate after 2026-08-31 is $3.00 input /
$15.00 output per million tokens. At that rate, the same measured token usage
would cost $21.11 per 1,000 selector requests.

## Recommendation

Do not use Haiku 4.5 as the context-pack selector in the current design. It
offers no useful tradeoff against the tested alternatives:

- Sonnet 5 is materially more accurate;
- Luna is both more accurate and much cheaper;
- Terra has slightly better median recall and better typical latency.

Keep Sonnet 5 as the quality-first selector. Luna remains the strongest
cost-first candidate and the most promising model for a deterministic or
Sonnet-fallback hybrid.

## Artifacts

- Haiku:
  `../2026-07-31-2026-07-31-haiku45-context-pack-r3/results.json`
- Luna:
  `../2026-07-31-2026-07-31-luna-context-pack-r3/results.json`
- Sonnet:
  `../2026-07-30-2026-07-30-sonnet5-context-pack-r3/results.json`
- Terra:
  `../2026-07-30-2026-07-30-terra-context-pack-r3/results.json`

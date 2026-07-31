# Sonnet 5 versus Terra as `/wiki/ask` page selector

Date: 2026-07-30

## Method

Both models ran the current eight-case reviewed `/wiki/ask/select-pages` gold
set five times. Each model therefore made 40 selector-only calls. The endpoint
does not invoke graph expansion or an answerer.

The models used identical questions, per-case page budgets, ask-scope catalog,
wiki state, gold labels, and scoring code.

## Results

| Metric | Claude Sonnet 5 | GPT-5.6 Terra |
| --- | ---: | ---: |
| Must-have recall, median pass | 1.000 | 1.000 |
| Must-have recall, min–max | 1.000–1.000 | 1.000–1.000 |
| Leak-free rate, median pass | 1.000 | 1.000 |
| Precision, median pass | **0.906** | 0.863 |
| Precision, min–max | 0.906–0.913 | 0.838–0.919 |
| Mean selector latency, 40 calls | 3.778 s | **2.675 s** |
| Median selector latency, 40 calls | 3.542 s | **2.276 s** |
| P95 selector latency | 5.699 s | **4.944 s** |
| Mean pages selected | 2.60 | 2.65 |

Terra reduced mean selector latency by 29.2% and median latency by 35.7%.
Its P95 improvement was smaller at 13.2%.

Provider token totals are not treated as directly comparable because Anthropic
and OpenAI use different tokenizers and accounting conventions.

## Precision difference

Both models selected every must-have page and no must-not page in all 40 calls.
Terra's lower precision came mainly from over-selection:

- packaging versus process (`ASK-0005`): Sonnet selected 3.0 pages with 1.000
  mean precision; Terra selected 5.8 pages with 0.520 mean precision;
- multi-F04 construction (`ASK-0008`): Sonnet mean precision was 0.760 versus
  Terra's 0.690;
- VMPR (`ASK-0006`) favored Terra: 0.820 precision versus Sonnet's 0.500.

Terra was also more variable across repeats. Its pass-level precision ranged
from 0.838 to 0.919, while Sonnet stayed between 0.906 and 0.913.

## Interpretation

Terra is viable as the `/wiki/ask` selector on this gold set: it preserved the
two safety-critical metrics—required-page recall and prohibited-page
avoidance—while saving roughly 1.1 seconds per selector call.

Sonnet remains the more selective and stable model. The practical end-to-end
speed gain will be smaller than 29%, because answer generation is unchanged;
only the selector stage is shortened.

This gold set is deliberately a small eight-case regression guard. It supports
a cautious runtime choice for `/wiki/ask`, not a claim that Terra is universally
better on the broader 39-case context-pack selection problem.

## Source reports

- Terra:
  [`results.json`](results.json)
- Sonnet 5:
  [`../2026-07-30-sonnet5-selector-r5-current/results.json`](../2026-07-30-sonnet5-selector-r5-current/results.json)

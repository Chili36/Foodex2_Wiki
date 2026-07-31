# Strict `/wiki/ask` page-budget verification

Date: 2026-07-30

The four reviewed DMT questions were rerun with Sonnet 5 as selector and
GPT-5.6 Terra as answerer after correcting `/wiki/ask` graph expansion.

| Mode | Mean pages | Required-page recall | Page precision | Prohibited-page pass | Mean latency |
| --- | ---: | ---: | ---: | ---: | ---: |
| Old uncontrolled expansion | 13.5 | 0.938 | 0.663 | 0.000 | 13.6 s |
| New default, expansion off | 4.75 | 0.708 | 1.000 | 1.000 | 9.3 s |
| New safe expansion | 7.0 | 0.938 | 1.000 | 1.000 | 13.7 s |

The old run's latency and mean page count cover all ten questions; its
precision, recall, and prohibited-page metrics cover the same four reviewed
questions as the two new runs.

The corrected endpoint has two honest modes:

- default expansion-off mode returns only the selector's pages and exposes the
  selector's current 70.8% reviewed required-page recall;
- explicit expansion mode recovers 93.8% recall inside the same seven-page cap,
  without adding prohibited or cross-domain pages.

`index.md` is no longer returned by the `/ask` selector. The selector already
receives the page catalog separately, so the index was redundant evidence and
consumed one answer-context slot.

Safe expansion may add only runtime, guidance, or validation neighbours. Domain
overlays remain the selector's responsibility, preventing a pesticides question
from acquiring a contaminants overlay (and vice versa) through graph traversal.

One reviewed miss remains: the additives case did not receive
`term-type-facet-constraints.md`. That is now a visible selector/coverage issue,
not something hidden by an oversized context.

Source results:

- default expansion off:
  [`../2026-07-30-strict-seven-ask-reviewed-no-index/results.json`](../2026-07-30-strict-seven-ask-reviewed-no-index/results.json)
- safe expansion:
  [`results.json`](results.json)
- historical uncontrolled run:
  [`../2026-07-30-dmt-ten-frontier/results.json`](../2026-07-30-dmt-ten-frontier/results.json)

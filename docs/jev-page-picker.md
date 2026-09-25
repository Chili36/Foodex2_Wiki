# Jev as the default page picker

Jev's sheer speed, together with no noticeable degradation in page-picking
quality in our pilot, made it the obvious practical default. It replaces the
page-selection model only. Users bring their own credentials and can choose
another supported model through the existing configuration.

## Page-picker evidence

On 25 September 2026, we compared the frozen Jev contrast-score prompt with the
existing Sonnet 5 selector on 20 new cases, with three repeats per model. Both
used the same catalogue, seven-page limit including runtime rules, and original
structural page-allocation policy.

| Metric | Jev 1.13.0 | Sonnet 5 |
| --- | ---: | ---: |
| Median selection time | 0.390 s | 8.104 s |
| 95th percentile selection time | 1.347 s | 15.208 s |
| Required-page recall after shared policy | 92.50% | 89.31% |
| All required pages selected | 42/60 | 39/60 |
| Failed selection calls | 0/60 | 1/60 |
| Estimated cost for 60 selections | $0.0231 | $0.5380 |
| Estimated cost per 1,000 selections | $0.385 | $8.966 |

This is approximately 21 times faster at the median and 23 times cheaper for
page picking. The Sonnet failure exhausted its existing 1,500-token output
limit and remains in the primary denominator. Its separate retry is excluded
from the table. Costs use returned token usage, including Anthropic cache writes
and reads, and public rates at the time of testing. They are estimates, not
invoices. Answer generation and automated grading are excluded from every
number above.

The sample comprises twelve previously unused DMT facet-review records and
eight synthetic stress cases, fourteen of them Swedish-only. Labels remain
unreviewed drafts. The paired recall difference was +3.19 percentage points for
Jev, with an exploratory case-bootstrap interval of -4.44 to +10.97 points.
The pilot supports the practical choice; it does not establish universal
accuracy superiority. Sonnet used its existing configuration, including default
high reasoning effort; this was not a comparison against every possible Sonnet
optimization.

## Runtime behavior

- Default model: `jev-1.13.0`, pinned to the tested version.
- One Score question per catalogue page, submitted in one request.
- Four fixed rubric levels; normalize the returned 0–3 score and retain scores
  at least 0.35, ranked highest first with filename tie-breaking.
- Keep the existing page cap, coding structural backfill and runtime-rules page.
- Use separate coding and ask catalogues, as before.
- Reject missing or unexpected question IDs, invalid scores and invalid usage;
  surface provider failures without exposing upstream response bodies.
- Preserve existing model overrides and provider routing. `TYPESAFE_API_KEY`
  enables Jev; selecting another model uses that provider's credentials.

The API's answerer, solver and policy generation are separate model roles.

References: [TypeSafe HTTP API](https://docs.typesafe.ai/api),
[Score primitive](https://docs.typesafe.ai/primitives/score),
[TypeSafe models and pricing](https://docs.typesafe.ai/models),
[Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing).

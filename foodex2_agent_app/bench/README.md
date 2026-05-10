# Bench

A small fixed-case bench for the FoodEx2 coding agent. The Ralph Loop
(`ralph/agent-md-self-improve` branch) uses this bench to gate
`AGENT.md` edits: every iteration runs the bench and only the cases that
fail are eligible to drive the next edit.

## Files

- `cases.json` — the case set. Five cases: three current/recent
  failures plus two positive regressions that must keep passing.
- `../scripts/run_bench.py` — the driver. Calls the real agent against
  real local services (wiki, catalogue/validator, Qdrant) using the
  real OpenAI API. Writes `../logs/bench-<bench-id>.json`.

## Running

```bash
cd foodex2_agent_app
python scripts/run_bench.py                       # default: gpt-5.4-mini
python scripts/run_bench.py --bench-id smoketest  # named bench
python scripts/run_bench.py --agent-model gpt-5.5 --bench-id final-5.5
python scripts/run_bench.py --no-update-budget    # smoke runs that don't count toward the loop ceiling
```

Required services on localhost (per the app `.env`):

- wiki API at `127.0.0.1:8010`
- catalogue/validator at `localhost:5178`
- Qdrant search service at `127.0.0.1:8001`

## cases.json schema

Top-level:

| Field | Type | Default | Purpose |
|---|---|---|---|
| `bench_token_budget` | int | 350_000 | Soft per-iteration spend cap, informational |
| `loop_token_ceiling` | int | 2_500_000 | Hard cumulative ceiling — when the budget sidecar shows `cumulativeTokens >= this`, the loop must self-terminate |
| `cases` | array | — | The case list |

Per case:

| Field | Type | Required | Purpose |
|---|---|---|---|
| `id` | string | yes | Stable slug used in bench output and loop commits |
| `search_term` | string | yes | Verbatim text the agent codes |
| `language_hint` | string\|null | no | Passed through to `CodeRequest.language_hint` |
| `domain` | string\|null | no | Reporting domain hint |
| `human_reference` | string\|null | no | Expert reference code for the self-evaluator to compare against |
| `expected_code` | string\|null | no | Reserved for future use; not gated on |
| `token_budget` | int | no (60_000) | Per-case spend cap. Going over makes the case `PASS_EXPENSIVE` |
| `notes` | string | no | Free-text rationale for inclusion |
| `max_tool_rounds` | int | no | Per-case override; falls back to `--max-tool-rounds` CLI flag, then to `AGENT_MAX_TOOL_ROUNDS` env |

## Pass criterion

A case passes when **all** hold:

1. `status == "completed"` — the run did not hit max-tool-rounds or
   raise a fatal error.
2. `validator.passes == true` with zero hard warnings
   (severity ∈ {hard, error, critical, high}). Soft warnings do not
   fail a case.
3. `selfEvaluation.verdict == "accept"` OR
   (`verdict == "review"` AND `score >= 4`). A `revise` verdict is
   always a fail.
4. `factCoverageRisks` is empty — no entries in the `factCoverage`
   ledger with disposition `missed`, `ambiguous`, `uncertain`, or
   `not_codeable`.

The bench passes when all cases pass **and** at least 4 of 5 are within
their per-case `token_budget`. A correctness-passing case that exceeded
its token budget is a `PASS_EXPENSIVE` — eligible to be the next
iteration's improvement target even though it is otherwise green.

## Interpreting `logs/bench-<id>.json`

```jsonc
{
  "benchRunId": "...",
  "agentMdPath": "/abs/path/AGENT.md",
  "agentMdSha": "<sha256[:12] of AGENT.md bytes>",
  "agentModel": "gpt-5.4-mini",
  "selfEvaluationModel": "gpt-5.4-mini",
  "cases": [ ... per-case rows ... ],
  "summary": {
    "total": 5,
    "passed": 3,
    "failed": 2,
    "maxToolRoundsHit": 1,
    "infraSkipped": 0,
    "failingCaseIds": ["brined_onion"],
    "tokenSpend": {
      "total": 281540,
      "medianPerCase": 52308,
      "overBudgetCaseIds": ["sliceable_hard_cheese_45pct"],
      "vsPreviousIterationDelta": "+12.3%"
    }
  }
}
```

`agentMdSha` is the first 12 hex chars of `sha256(AGENT.md bytes)` —
useful for confirming the loop is iterating on the file we think it
is.

`vsPreviousIterationDelta` compares against the most recent prior
`bench-*.json` in `logs/` (by mtime). The loop uses this as a
direction-of-travel signal: edits should reduce or hold tokens.

## Budget sidecar

`<project_root>/.claude/ralph-loop-budget.json` records cumulative
spend across loop iterations:

```jsonc
{
  "cumulativeTokens": 481200,
  "loop_token_ceiling": 2500000,
  "iterations": [
    {"benchRunId": "...", "agentMdSha": "...", "tokenSpend": 281540, "passed": 3, "total": 5, "ts": "..."}
  ]
}
```

The loop reads this before deciding whether to make an edit. When
`cumulativeTokens >= loop_token_ceiling`, the loop runs `/cancel-ralph`
with a `BUDGET_EXHAUSTED` final message instead of editing `AGENT.md`.

Smoke-test runs should pass `--no-update-budget` so they don't burn
through the production ceiling.

## Adding cases

Resist the urge. The bench is intentionally small and stable so
iterations are reproducible. Add a case only when:

- A repeated production failure isn't reflected in the existing cases
  (you've checked `logs/failure_learning.jsonl`), or
- A loop iteration is overfitting a specific food class and the bench
  needs a counter-example.

Removing a case mid-loop is forbidden — the pass bar would shift
silently. Removals are PR-time decisions.

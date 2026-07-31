# Wiki-RAG Evaluation

This directory contains reviewed cases for measuring wiki-mode Qdrant retrieval
and a schema for end-to-end `/wiki/ask` versus `/wiki/ask-rag` evaluation.

The evaluation deliberately separates:

- raw ranked chunks returned by Qdrant;
- final unique pages produced by retrieval assembly;
- answer quality, which belongs in a separate end-to-end evaluation.

The initial five cases cover pesticides, additives/process handling, VMPR,
packaging, and structural validation. Expand the set after the upcoming wiki
update, reviewing page labels whenever pages are added, renamed, consolidated,
or materially changed.

The page labels are diagnostic. They are based on the context-pack rubric, so
they measure whether RAG retrieves the comprehensive evidence set expected for a
coding brief; they are not themselves an answer-accuracy score.

Run:

```bash
.venv/bin/python scripts/wiki_rag_retrieval_eval.py \
  --label diverse-pages-smoke \
  --repeats 1
```

The runner writes:

```text
reports/wiki-rag-evals/<date>-<label>/retrieval-results.json
```

Important metrics:

- `mean_must_have_recall`
- `mean_precision`
- `leak_free_rate`
- `mean_unique_pages`
- `mean_duplicate_slot_waste`
- `mean_role_coverage`
- `mean_retrieval_ms`
- `p95_retrieval_ms`

## End-to-end answer evaluation

Use [end_to_end_cases.schema.json](end_to_end_cases.schema.json) for the ten DMT
questions. A minimal case can contain only `id`, `reviewed`, and `question`, but
that supports only response collection and reference-free faithfulness scoring.
For a meaningful comparison, review each case before the run and add:

- `reference_answer`: the expected substance, phrased as an answer rather than
  copied from one model;
- `reference_pages`: must-have wiki pages expected to contain the necessary
  evidence;
- `acceptable_pages`: relevant support pages that count toward page precision
  but are not required for must-have recall;
- `required_answer_terms` and `forbidden_answer_terms`: a few stable,
  case-insensitive assertions for deterministic checks;
- `must_not_pages`: known irrelevant or misleading pages, when applicable;
- `rubric`: optional case-specific five-point Ragas rubric.

When the reporting domain is metadata rather than part of the visible question,
store the original wording in `question` and the exact endpoint input in
`request_question`. The DMT dataset uses this to append explicit
`Reporting domain: ...` text because the current ask endpoint accepts a question
string, not a separate domain field.

Do not generate the reference answer with one of the models under test. The
reviewed reference and deterministic assertions are the protection against
Ragas simply rewarding a fluent but incorrect answer.

The same answer model is used on both endpoints. `/wiki/ask` keeps its selector
fixed at Sonnet 5 by default, while `/wiki/ask-rag` uses Qdrant
`diverse_pages`. For example:

```bash
.venv/bin/python scripts/wiki_ragas_eval.py \
  --cases evals/wiki-rag/dmt_end_to_end_cases.json \
  --label dmt-pilot \
  --answerer-models claude-sonnet-4-6,lmstudio:gpt-oss-120b \
  --only-reviewed \
  --dry-run
```

Remove `--dry-run` to execute the matrix. With ten cases, two endpoints, and two
models, the run makes 40 endpoint calls. The default Ragas metrics are
`answer_accuracy` and `faithfulness`; the dry-run also prints the number of
metric invocations. Use a judge model that is not one of the answer models when
practical:

```bash
.venv/bin/python scripts/wiki_ragas_eval.py \
  --cases evals/wiki-rag/dmt_end_to_end_cases.json \
  --label dmt-pilot \
  --answerer-models claude-sonnet-4-6,lmstudio:gpt-oss-120b \
  --judge-model claude-sonnet-4-6 \
  --metrics answer_accuracy,faithfulness \
  --only-reviewed
```

For a cheaper collection-only pass, disable Ragas while retaining deterministic
checks:

```bash
.venv/bin/python scripts/wiki_ragas_eval.py \
  --cases evals/wiki-rag/dmt_end_to_end_cases.json \
  --label dmt-answers-only \
  --answerer-models lmstudio:gpt-oss-120b \
  --metrics ""
```

To add Ragas metrics to frozen endpoint outputs without rerunning stochastic
retrieval or answer generation, use:

```bash
.venv/bin/python scripts/wiki_ragas_score_results.py \
  --input-results reports/wiki-ragas-evals/<run>/results.json \
  --cases evals/wiki-rag/dmt_end_to_end_cases.json \
  --label <scored-run> \
  --metrics faithfulness \
  --judge-model claude-sonnet-4-6
```

Use `--answerer-models` to score only selected models from a multi-model result
file. Offline scoring preserves each response's captured `pages` as the judge
context, so the score cannot be confounded by a new selector or retriever run.

Results are written to:

```text
reports/wiki-ragas-evals/<date>-<label>/results.json
```

Interpret Ragas scores as comparative judge signals, not ground truth. Inspect
the stored answers, citations, page sets, deterministic failures, and per-case
judge reasons before choosing an endpoint or model.

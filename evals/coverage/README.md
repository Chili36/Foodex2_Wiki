# Source-driven coverage evaluation

This suite asks the inverse of the existing witness tests: what facts in the
authoritative EFSA sources can the production wiki path not answer? Coverage failures
are the deliverable. They never gate a merge, and none of the existing eval schemas are
modified.

## Start with the mechanical map

```bash
python evals/coverage/coverage_index.py \
  --output evals/coverage/reports/coverage-index.json
```

The command makes zero model calls. Only explicit source page citations receive
page-level credit; broad labels remain visible but do not make an entire document look
covered. The first run on 2026-08-01 found 5 explicitly covered pages out of 257 (1.95%).

## Chunk and generate a versioned testset

DeepEval is isolated because its pytest plugin dependencies conflict with the main
repo's pytest 9 constraint:

```bash
python -m venv .venv-coverage
.venv-coverage/bin/pip install -r evals/coverage/requirements.txt
export COVERAGE_LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
export COVERAGE_GENERATOR_MODEL='<local-moe-model-id>'
export COVERAGE_AUDITOR_MODEL='<independent-local-auditor-model-id>'
export COVERAGE_SELECTOR_MODEL='<local-selector-model-id>'
export COVERAGE_DMT_ANSWERER_MODEL='<the model used by DMT>'
export COVERAGE_JUDGE_MODEL='<strongest local model that fits>'
.venv-coverage/bin/python -m evals.coverage.generate \
  --config evals/coverage/config/efsa-core-v1.template.yaml \
  --output evals/coverage/testsets/efsa-core-v1.json
```

Generation refuses missing files and hash drift. It never falls back to wiki content.
Before DeepEval sees a chunk, an automated qualifier extracts only facts whose omission
could change a concrete base-term, facet, code-construction, validation, reporting, or
ontology-boundary decision. Administrative facts about maintenance and publication are
excluded even when source-grounded. Eligible claims must
be operational, structural, or exceptions and must include an exact evidence span that is
verified against the source. DeepEval receives those claims—not the incidental remainder
of the chunk. A second model gate rejects quotation, page-number, citation, footnote,
publication-metadata, and non-transferable example questions. Human review is not required.
The configured local qualifier performs both gates; it can be set independently of the
DeepEval generator when stronger separation is worth the added runtime.
The qualifier also performs a second completeness pass over the original chunk and the
first-pass claims, so an empty or sparse extraction is not silently treated as proof that
the source section contains nothing the wiki should preserve.
Claim paraphrases also pass a strict claim-versus-evidence check plus a conservative lexical
scope check. When either check objects, generation uses the verified exact evidence as the
claim instead of discarding the source fact or trusting an expanded paraphrase.
By default the qualifier uses the local generator model for throughput; `models.qualifier`
can override it independently. The final coverage judge remains separately configurable and
should use the strongest local model that fits.

Each accepted question carries its stable parent `chunk_id`, source identity, page range,
qualified claims, and screening decision. Excluded claims/chunks and rejected questions
remain in the testset audit metadata but do not enter the coverage denominator.
Generation also writes `config/efsa-core-v1.yaml`: the frozen per-testset manifest with
source versions/hashes, resolved generator and judge model IDs, parameters, evolution
weights, and generation time. Commit that YAML with the testset. Regeneration requires
`--force` and should only happen for a deliberate new version.

Before running coverage, independently audit and freeze the generated candidate pool. The
auditor re-applies deterministic source and question-shape gates, then uses a local model
different from the generator to reject questions that are vague, historical, source-recall,
garbled, or not answerable from their qualified claims:

```bash
.venv-coverage/bin/python -m evals.coverage.audit \
  --config evals/coverage/config/efsa-core-v1.yaml \
  --testset evals/coverage/testsets/efsa-core-v1.json \
  --output evals/coverage/testsets/efsa-core-v1-audited.json \
  --manifest-output evals/coverage/config/efsa-core-v1-audited.yaml
```

Only the audited testset enters the coverage denominator. Rejected candidates remain in its
audit metadata, and the frozen manifest records the auditor model and acceptance counts.

## Run against production retrieval, locally

The default config calls `/wiki/context-pack`, passes a per-request local selector, and
uses the configured DMT answer model to answer from the returned page content. Both the
answerer and grounded three-way judge call LM Studio. Public endpoints are rejected, and
the run aborts unless the wiki response trace confirms `lmstudio:` routing. Start the wiki
service with `WIKI_LMSTUDIO_BASE_URL` pointing at the same local/private LM Studio host.

```bash
export COVERAGE_SELECTOR_MODEL='<local-selector-model-id>'
export COVERAGE_DMT_ANSWERER_MODEL='<the model used by DMT>'
export COVERAGE_JUDGE_MODEL='<strongest local model that fits>'
python -m evals.coverage.run \
  --config evals/coverage/config/efsa-core-v1.yaml \
  --testset evals/coverage/testsets/efsa-core-v1.json \
  --judge-repeats 3
```

Detailed results and the chunk-keyed gap backlog are ignored under a timestamped report
directory. The latest aggregate `reports/summary.json` is retained. It includes per-source
coverage, exact judge agreement, and the count of cases whose repeated verdicts varied.

The deterministic loopback acceptance run observed 100% agreement across two repeated
judgments and zero variable cases; this validates the variance accounting. On 2026-08-02,
three source-review candidates were rerun locally with GPT-OSS 120B using three judgments
per case; all three had 100% verdict agreement. That selective confirmation is evidence of
stability for those cases, not a suite-wide noise estimate. Do not treat small coverage
deltas as meaningful until the complete frozen testset has also been run with repeats.

Use repeatable `--case-id COV-...` arguments to confirm selected frozen cases without
overwriting the complete-suite summary. Subset and `--max-cases` runs write only to their
explicit output directory.

`--escalate-judge` is off by default. When enabled, only local `partial` and `missing`
results are confirmed by `models.escalation_judge`; that is the only default workflow
branch permitted to use a hosted endpoint.

## Source revision staleness

Create old and new source manifests and run:

```bash
python -m evals.coverage.staleness \
  --old-manifest path/to/old.yaml \
  --new-manifest evals/coverage/sources/manifest.yaml \
  --output evals/coverage/reports/staleness.json
```

The report lists changed page numbers and every wiki page or existing witness case whose
source citation overlaps them. Broad citations are conservatively flagged whenever that
source changes.

---
title: "Maintenance Workflow"
last_updated: "2026-05-23"
sources:
  - "PROJECT_CONTEXT.md"
  - "KNOWLEDGE_ARCHITECTURE.md"
  - "INGEST_WORKFLOW.md"
  - "SCHEMA.md"
related:
  - "[[KNOWLEDGE_ARCHITECTURE]]"
  - "[[INGEST_WORKFLOW]]"
  - "[[SCHEMA]]"
  - "[[RUNTIME_RULES]]"
---

# Maintenance Workflow

This page defines the continuous maintenance loop for the FoodEx2 wiki.

The repo should use deterministic checks for mechanical health and supervised LLM review for semantic drift. Scheduled automation may report problems, but it should not silently rewrite the wiki or merge knowledge changes.

## Purpose

The maintenance layer exists to catch problems that accumulate even when new source data is rare:

- broken wiki links and stale local references
- pages served by the API but missing from `index.md`
- pages listed in `index.md` but not served by the API
- missing page-category registration
- prompt-facing pages that project to empty model context
- orphan pages in the markdown-derived graph
- source references that no longer resolve to committed source artifacts

These checks keep the wiki useful as a compiled knowledge base instead of letting it decay into disconnected notes.

## Deterministic Wiki Doctor

Run the deterministic maintenance check with:

```bash
python -m wiki_api.doctor
```

In GitHub Actions, use annotation output:

```bash
python -m wiki_api.doctor --format github
```

For scheduled or manual maintenance, add external URL checking:

```bash
python -m wiki_api.doctor --format github --check-external-links
```

The doctor treats these as hard errors:

- a served catalog page missing from `index.md`
- an `index.md` local target that does not resolve
- a served page missing explicit `page_categories` registration
- an unresolved `[[wikilink]]`
- a wiki link written with a `.md` suffix instead of an extensionless target
- a broken local markdown link
- a prompt-facing page category that produces no prompt content
- a non-prompt page category that unexpectedly produces prompt content
- a graph orphan with no incoming or outgoing links

The doctor treats unresolved source references as warnings by default. Some source names are historical aliases or virtual references to validator and documentation layers, so warnings should be reviewed but should not block every maintenance pass unless a maintainer explicitly runs with `--strict-warnings`.

External `http` and `https` markdown links are optional warnings because remote sites can throttle or block automated checks. They are useful for maintenance reports, but they should not block normal PR work.

## Deterministic Wiki RAG Index Checks

The curated wiki Qdrant collection is a derived artifact of the markdown wiki. The markdown files remain the source of truth; Qdrant must be treated as stale whenever page hashes, chunk hashes, embedding settings, or selected page membership drift.

Check live drift with:

```bash
python scripts/wiki_rag_status.py
```

Print the expected markdown-derived manifest without contacting Qdrant:

```bash
python scripts/wiki_rag_status.py --manifest-only
```

Include the Qdrant drift check in the doctor when Qdrant is available:

```bash
python -m wiki_api.doctor --check-rag-index
```

The same status is exposed at:

```text
GET /wiki/rag/status
```

The status check reports:

- markdown pages selected for wiki RAG but missing from Qdrant
- stale chunks where the markdown-derived content hash no longer matches
- embedding model or dimension mismatches
- orphaned Qdrant chunks for removed, renamed, or no-longer-selected pages
- malformed Qdrant points without wiki chunk metadata

Rebuild or sync the curated markdown collection with:

```bash
python scripts/index_wiki_qdrant.py --delete-orphans --manifest-path reports/wiki-rag-manifest.json
```

Use `--recreate` when you want a clean rebuild of the whole collection. Use `--delete-orphans` when incrementally upserting and removing stale chunks left by page deletion, renaming, heading changes, or category changes.

## Scheduled Maintenance

GitHub Actions should run the doctor on:

- pull requests
- pushes to maintained branches
- a weekly schedule
- manual `workflow_dispatch`

The scheduled job is a monitor. It reports drift; it does not change files.

## LLM Lint Pass

The LLM-maintenance role is useful after deterministic checks have made the repo mechanically healthy.

Run a targeted lint pass with:

```bash
python -m wiki_api.llm_lint --page facet-coding-rules.md --focus "F09 examples"
```

For a broader but higher-token review, run:

```bash
python -m wiki_api.llm_lint --all-pages --max-page-chars 6000
```

Reports are written under `reports/` by default. They are review artifacts, not source-of-truth wiki pages.

LLM lint is an offline semantic review task, so it uses Anthropic adaptive thinking by default when run against Claude models. Disable it with `--no-thinking` for a cheaper comparison run, or set `WIKI_LINT_THINKING=0`.

Use an LLM to read:

- the doctor report
- `index.md`
- the page or page family being maintained
- the relevant source material or normalized source artifact
- recent `log.md` entries

The LLM lint pass should look for:

- contradictions between pages
- stale or misleading index summaries
- missing routing signals for domain overlays
- pages that are too broad for reliable retrieval
- missing source traceability
- claims that should be downgraded from rule language to example language
- new rules that were added as prose but not linked from related pages

The output should be a report or a reviewed PR. It should not auto-merge semantic changes.

## Maintainer Loop

For a normal maintenance or ingest pass:

1. Run `python -m wiki_api.doctor`.
2. Fix deterministic errors before making semantic edits.
3. Use the LLM lint pass for contradictions, routing gaps, and stale guidance.
4. Update `index.md` whenever a page is added, removed, renamed, or meaningfully re-scoped.
5. Update `log.md` for material maintenance work.
6. Run the test suite.
7. Restart the local wiki service if page registration, selector-visible summaries, or API code changed.

## Source Intake Reports

Before ingesting a source that might materially change wiki guidance, run:

```bash
python -m wiki_api.source_intake \
  --source-file foodex2_docs/new-source.pdf \
  --source-tier expert_guidance \
  --page base-term-selection.md \
  --page facet-coding-rules.md
```

The source-intake runner writes a maintainer report under `reports/source-intake/` and uses `WIKI_INTAKE_MODEL`, falling back to `WIKI_LINT_MODEL` and then `WIKI_LIBRARIAN_MODEL`. It uses Anthropic adaptive thinking by default because the task is source evaluation, not runtime retrieval. Disable with `--no-thinking` or `WIKI_INTAKE_THINKING=0`.

## Do Not

- Do not edit source files in `foodex2_docs/` to match generated interpretation.
- Do not auto-ingest unreviewed source material just because a file appears.
- Do not let scheduled automation silently rewrite wiki pages.
- Do not treat unresolved source-reference warnings as proof that the wiki content is wrong.
- Do not move prompt policy into hidden service code when it can live in markdown.

## Relevant Policy

- [[policy-contract]] `C02`: the base-term choice remains the main decision surface; maintenance should preserve decision-order clarity.
- [[policy-contract]] `C05`: rules outrank examples, so lint should flag pages where examples read like rules.
- [[policy-contract]] `C10`: domain overlays are opt-in, so maintenance should check routing signals rather than broadening default prompt context.

## Relevant Business Rules

No single FoodEx2 `BRxx` validation rule governs this process page directly. This page governs wiki hygiene and source traceability around the rule pages.

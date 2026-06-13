---
title: "Ingest Workflow"
last_updated: "2026-06-12"
related:
  - "[[KNOWLEDGE_ARCHITECTURE]]"
  - "[[MAINTENANCE_WORKFLOW]]"
  - "[[SCHEMA]]"
  - "[[RUNTIME_RULES]]"
---

# FoodEx2 Wiki Ingest Workflow

This document is the practical playbook for ingesting new PDFs or source documents into the FoodEx2 wiki.

It exists for two reasons:

- to keep future ingests consistent
- to avoid the common failure mode where an LLM tries to digest an entire PDF in one pass and collapses under context and synthesis pressure

# Core Principle

Do not treat ingest as "summarize one whole PDF perfectly."

Treat ingest as:

1. discover the document's structure
2. decide which wiki topics it changes
3. extract only the durable rules, examples, and terminology that belong in those topics
4. leave gaps visible for later refinement

The goal is not perfect one-shot completeness. The goal is a durable, updateable knowledge layer.

# What To Optimize For

- Topic-oriented extraction, not document-order notes
- Durable rules over transient prose
- Small pages with strong scope
- Clear source attribution
- Fast incremental progress
- Easy future patching when real cases expose gaps

# What Not To Do

- Do not try to hold an entire long PDF in working memory and rewrite all of it at once.
- Do not dump document sections into giant markdown pages.
- Do not force every detail into the first ingest pass.
- Do not silently invent rules when the source is unclear.
- Do not optimize for "complete summary of the PDF"; optimize for "useful wiki pages that improve future decisions."

# Standard Workflow

## 1. Intake The Source

- Add the source file to `foodex2_docs/`.
- Keep the raw file immutable.
- Do not edit or rename the source casually after ingest starts.
- Assign a source tier when the authority distinction matters:
  - `authoritative_rule` for EFSA catalogue/rules, validator behaviour, ChemMon reporting guidance, legislation, or other sources that can define obligations
  - `expert_guidance` for official institutional or expert coding guidance, training, examples, and conventions
  - `local_policy` for project-specific scoring references or grey-area decisions
  - `diagnostic` for model logs, retrieval comparisons, and failure analyses
- A lower-tier source can improve explanations and examples, but it must not silently override a higher-tier rule source.

## 2. Run A Structure Scan First

Before writing pages, answer:

- What kind of document is this?
- What source tier applies, and what can this source legitimately change?
- Is it core FoodEx2 guidance, annual maintenance, domain overlay, validator policy, or a clarification?
- Which existing wiki pages are likely affected?
- Does this document introduce a new topic that deserves its own page?

This pass should be shallow and fast. It exists to prevent blind summarization.

## 3. Write A Source Impact Report

Before editing operational pages, write a short source impact report. This can be LLM-assisted, but it is a maintainer decision aid rather than an authority source.

The report should answer:

- Source identity: title, file, source tier, version, date, and intended audience.
- Scope: which FoodEx2 topics the source covers.
- Novelty: what the source adds beyond the current wiki.
- Overlap: which existing pages already cover the same concepts.
- Conflicts or tension: where it might disagree with current catalogue data, business rules, validator behaviour, domain guidance, or local policy.
- Ingest risk: old FoodEx2 version, OCR noise, ambiguous examples, domain leakage, or examples that could overfit prompts.
- Recommended action: no ingest, source note only, patch existing pages, create a new page, add tests, or defer.
- Candidate test cases: concrete examples that would show whether the source improves coding decisions.

Keep source impact reports under `reports/source-intake/`. Reports are not runtime rules. They are audit records explaining why the wiki was, or was not, changed.

For LLM-assisted intake, use:

```bash
python -m wiki_api.source_intake \
  --source-file foodex2_docs/new-source.pdf \
  --source-tier expert_guidance \
  --page base-term-selection.md
```

This offline command uses `WIKI_INTAKE_MODEL` and Anthropic adaptive thinking by default. Use `--no-thinking` when comparing cost or when the source is trivial.

## 4. Build Or Update The Topic Map

Decide whether the source should:

- update existing pages
- create one or two new pages
- create a new overlay page
- create only a log entry because it adds no durable rule content

Good heuristic:

- if the rule belongs naturally to an existing page, patch that page
- if the document introduces a stable new concept or rule family, create a new page
- if it is year-specific or reporting-specific, prefer an overlay page rather than polluting core guidance pages

## 5. Extract Durable Content Only

Move only the parts that compound in value:

- definitions
- rule statements
- tie-break logic
- worked examples
- explicit exceptions
- terminology that future coding decisions depend on

Do not over-extract:

- narrative scaffolding
- repeated motivational framing
- long legal boilerplate
- every example in the source

## 6. Write Into Small Topic Pages

Each page should stay narrow in scope.

Preferred page shape:

- short title
- YAML frontmatter
- sources
- related links
- a few clear sections
- worked examples only when they teach a reusable rule

If a page starts becoming a second document dump, split it.

## 7. Always Check Relevant Policy And Business Rules

For every page touched during ingest or maintenance, explicitly ask:

- Which policy rules from `[[policy-contract]]` govern this topic?
- Which `BRxx` rules from `[[business-rules]]` materially constrain this topic?

This applies even when the truthful answer is:

- no single `BRxx` rule governs this page directly
- this page is mainly historical or conceptual

For operational pages, explicitly ask:

- Which `BRxx` rules govern this topic?
- Which of those rules are central enough to deserve a backlink from this page?

This is mandatory for ingest and maintenance passes, with the strongest expectation on:

- base-term pages
- facet pages
- validation pages
- domain overlay pages
- maintenance and history pages that affect current reportability or scope interpretation

Preferred pattern inside the page:

```md
## Relevant Policy

- [[policy-contract]] `C01`: determine food type before choosing the base term
- [[policy-contract]] `C08`: add only explicit facets that are not already implicit
```

And, where applicable:

```md
## Relevant Business Rules

- `BR03`: composites cannot use `F01`
- `BR04`: composites cannot use `F27`
- `BR12`: `F04` on raw/derivative terms is minor-ingredient only
```

Those rule references should link back to [[business-rules]] as the canonical wiki target for validator rules.

Do not force irrelevant rules onto a page. The point is not to maximize tags; the point is to make the governing constraints explicit and to say clearly when a page is policy-driven rather than validator-driven.

# Page Writing Heuristics

## Write For Reuse

A wiki page should answer a future class of questions, not only the current ingest task.

Prefer:

- "Use a derivative base when a nature-changing process defines a standard group"

Over:

- "In section 4.2 the document discusses several examples of processed foods"

## Write For Retrieval

The model will later retrieve pages in small batches.

So each page should make its central rule visible quickly:

- lead with the rule
- then give the qualifier
- then give the example

Do not bury the operative rule after paragraphs of context.

## Keep Examples Subordinate

Examples are useful, but they should support a rule, not replace it.

Preferred pattern:

- rule
- why it matters
- one example

Avoid building pages out of examples without a governing principle.

# Handling Large PDFs

When a source is long or dense, split the ingest mentally into three passes.

Use [[KNOWLEDGE_ARCHITECTURE]] as the governing architecture: long-document structure is an ingest aid, not a second runtime knowledge base. The durable output should be patched topic pages, index summaries, source notes, and log entries.

## Long-Source Workspace

For dense PDFs, complex tables, or multi-modal source material, create a temporary working map before editing the wiki:

- document outline
- section summaries
- table notes
- page-range notes
- affected-page map
- explicit uncertainty list

This can be produced with manual reading, OCR/markdown conversion, or a tree-style long-document pass. The important rule is that the temporary map must retain source filename and page-range traceability.

Do not commit bulky extraction dumps unless they are intentionally curated source artifacts. Most long-source notes should resolve into concise page updates or be discarded after the ingest pass.

## Pass A: Skeleton

Goal:

- identify affected page families
- note new topics
- note obvious high-value rules

Output:

- page update plan

## Pass B: Durable Rule Extraction

Goal:

- patch or create the highest-value pages first

Output:

- concise topic pages with source-backed claims

## Pass C: Gap Sweep

Goal:

- look for missing exceptions, examples, or validation nuances

Output:

- targeted follow-up edits, not a rewrite

This is the main technique that prevents "AI collapses on one PDF."

# Decision Rules For New Pages

Create a new page when:

- the topic has stable long-term value
- the topic would otherwise overload an existing page
- retrieval will benefit from isolating it
- the topic represents a distinct overlay or schema layer

Do not create a new page when:

- the content is just one more bullet in an existing page
- the source only restates a known rule
- the topic is too narrow and case-specific

# Logging And Traceability

Every meaningful ingest or maintenance pass should also:

- update `index.md` if navigation changed
- run `python -m wiki_api.doctor`
- update `log.md`
- explain whether the change is:
  - `ingest`
  - `maintenance`
  - `service`

The log should capture:

- what changed
- why it changed
- what source triggered it
- which business rules became newly relevant, if that was part of the pass

# How To Know An Ingest Is "Good Enough"

An ingest pass is good enough when:

- the source is represented in the wiki at the right topic level
- the main durable rules are captured
- the page map is clearer than before
- the work creates fewer future ambiguities than it leaves behind

An ingest pass does not need to:

- encode every detail from the source
- settle every edge case immediately
- produce perfect coverage in one sitting

# Feedback Loop After Ingest

The ingest is not finished forever after the first pass.

Real coding runs should be used to test the wiki.

When a case fails, ask:

1. Was the needed knowledge missing from the wiki?
2. Was the knowledge present but phrased too weakly?
3. Was retrieval wrong?
4. Was policy/order-of-operations missing?

Only then decide whether to:

- patch a page
- add a page
- strengthen policy
- improve retrieval

# The Short Version

If you are under time pressure, do this:

1. Add the raw source to `foodex2_docs/`
2. Identify affected wiki pages
3. Patch only the highest-signal rules
4. Add one or two worked examples if they teach a reusable principle
5. Update `index.md` only if navigation changed
6. Run `python -m wiki_api.doctor`
7. Add a `log.md` entry
8. Stop before the page turns into a document dump

That is better than a heroic one-shot ingest that becomes unreadable or brittle.

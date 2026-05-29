---
title: "Knowledge Architecture"
last_updated: "2026-05-29"
source_inspiration:
  - "https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f"
  - "https://github.com/VectifyAI/OpenKB"
  - "https://microsoft.github.io/graphrag/query/overview/"
  - "https://arxiv.org/abs/2401.18059"
  - "https://arxiv.org/abs/2406.15319"
  - "https://arxiv.org/abs/2405.14831"
related:
  - "[[PROJECT_CONTEXT]]"
  - "[[INGEST_WORKFLOW]]"
  - "[[MAINTENANCE_WORKFLOW]]"
  - "[[SCHEMA]]"
  - "[[RUNTIME_RULES]]"
  - "[[policy-contract]]"
---

# Knowledge Architecture

This page defines the practical architecture for the FoodEx2 LLM wiki.

The project already follows the core LLM-wiki idea: raw sources stay immutable, and durable knowledge is compiled into interlinked markdown that can be improved over time. The next step is not to replace that with a heavier RAG stack. The next step is to make the markdown graph, retrieval contract, and occasional long-source ingest path more explicit.

## Current Decision

- Keep markdown as the canonical knowledge layer.
- Keep the authored wiki graph in frontmatter, inline links, `index.md`, policy links, and business-rule links.
- Keep `/wiki/ask` as the compact guidance surface for short strategy questions.
- Keep `/wiki/context-pack` as the primary page-evidence surface for DMT and other downstream classifiers.
- Treat long-document indexing as an ingest aid, not the runtime source of truth.
- Treat deterministic doctor checks as the first maintenance gate, with LLM lint as supervised review rather than autonomous rewriting.
- Do not add a vector database, graph database, or watch-mode ingestion loop until the data volume or update frequency justifies the operational cost.

This matches the project reality: FoodEx2 source data changes rarely, but the interpretation has high consequence. The best return comes from careful compilation, cross-linking, regression tests, and source traceability.

## Layer Model

1. Source layer: immutable EFSA PDFs, validator exports, and other primary sources in `foodex2_docs/` or adjacent source folders.
2. Long-source workspace: optional temporary indexes, outlines, page summaries, or extraction notes used only while ingesting dense PDFs or tables.
3. Compiled wiki layer: durable topic pages, runtime pages, validation pages, domain overlays, and maintenance pages.
4. Markdown graph layer: generated from frontmatter `related`, inline links, `Relevant Policy`, `Relevant Business Rules`, and `index.md`.
5. Maintenance layer: `wiki_api.doctor`, GitHub Actions, and supervised LLM lint described in [[MAINTENANCE_WORKFLOW]].
6. Retrieval API layer: `wiki_api/`, especially `/wiki/ask`, `/wiki/context-pack`, `/wiki/graph`, `/wiki/graph/compact`, `/wiki/policy-pack`, and `/wiki/solve`.
7. Caller layer: DMT or another downstream application that supplies the user query, candidate hints, and final prompt assembly.

## What Popular Patterns Mean Here

### LLM Wiki / OpenKB

The useful pattern is compilation: the LLM reads raw documents, writes durable topic pages, maintains cross-links, and lets the knowledge base compound instead of re-deriving answers every time.

For this repo, the OpenKB-style long-document lesson matters more than watch mode. We should handle dense PDFs with structure-preserving extraction and hierarchical summaries when needed, but the stable output should still be curated wiki pages.

### GraphRAG

GraphRAG separates local, global, and community-aware retrieval modes. We should borrow the query-shape distinction, not the full infrastructure.

- Local question: use selected pages plus near neighbors.
- Global question: use `index.md`, graph summaries, and maintenance overview pages before drilling into details.
- Drift or broad exploration question: expand from the chosen page into related domain overlays, validation pages, and policy pages.

The existing markdown graph is enough for this phase. If graph expansion becomes a bottleneck, improve traversal and summaries before adding a graph database.

### RAPTOR And LongRAG

RAPTOR and LongRAG are useful warnings against tiny blind chunks. Long PDFs often need retrieval units that preserve section and document-level context.

For FoodEx2, this means:

- During ingest, create or use outlines, section summaries, table notes, and page-range summaries before writing topic pages.
- Keep long-source summaries tied to page ranges and source filenames.
- Compile durable rules into topic pages after the long-source pass.
- At runtime, prefer the compiled page over raw chunk retrieval unless the user explicitly asks to verify against source material.

### HippoRAG And Long-Term Memory

HippoRAG-style long-term memory emphasizes entity and relation traversal. Our equivalent is explicit page links, policy edges, business-rule edges, and candidate-aware retrieval.

We should add more structure only where it improves a real FoodEx2 decision:

- Base term to facet constraints.
- Domain overlay to validation rule.
- Reporting context to legislative mapping.
- Maintenance change to affected coding rule.

## Retrieval Modes

### Guidance Brief

Use this when the caller needs a short answer to shape the next move rather than raw page text.

The API surface is `POST /wiki/ask`.

Good uses:

- "What should I think about before coding this?"
- "Is this likely raw, derivative, or composite?"
- "Which facet families might matter?"
- "Does this look like a domain-overlay case?"
- "Should I escalate to full page context?"

This mode selects pages, optionally expands to related-page summaries, and runs a concise wiki answerer. The result is a strategy brief with citations. It is useful before candidate retrieval when the source wording is confusing, and after deconstruction when extracted facts can be turned into a sharper guidance question.

Do not treat this mode as a catalogue, validator, or final-code authority. It should not invent FoodEx2 codes or facet descriptors beyond the provided page evidence.

### Default Case Retrieval

Use this when the caller needs page evidence for ordinary FoodEx2 coding.

The API surface is `POST /wiki/context-pack`.

1. Attach `RUNTIME_RULES.md`.
2. Use the selector to choose the smallest useful page set.
3. Include pages as projected prompt content, omitting examples, appendices, and maintenance bulk unless needed.
4. Let the downstream caller or solver make the final coding decision against candidate data.

This mode is heavier than `/wiki/ask`, but better when the downstream model needs exact rule text, auditability, or a prompt context pack.

### Graph Expansion

Use this when the selected page is likely incomplete without neighbors.

Good triggers:

- Candidate list contains both base-term and facet-like options.
- Query has a reporting-domain signal such as pesticide, contaminants, VMPR, additives, or flavourings.
- Selected page links to `policy-contract.md`, `business-rules.md`, or a domain overlay.
- User asks a broad "how should I think about this" question.

Bad triggers:

- Simple base-term selection already has enough context.
- The extra neighbors would mostly add examples or appendix tables.
- The user needs a final answer under a tight token budget.

### Flow Selection

The caller should choose the lightest retrieval surface that can answer the case:

```text
quick strategy:
query -> /wiki/ask

strategy before candidates:
query -> deconstruct query -> /wiki/ask -> candidate retrieval -> downstream classifier -> validator

page-evidence classification:
query -> deconstruct query -> candidate retrieval -> /wiki/context-pack -> downstream classifier -> validator

wiki-owned solving experiment:
query -> candidate retrieval -> /wiki/solve -> external validation or human review
```

The strategy-before-candidates flow is useful when the wiki answer can change what the caller searches for, for example derivative bases before raw commodities, raw terms as possible `F27` or `F04` facet values, or domain overlays only when explicitly supplied.

### Long-Source Verification

Use this when a claim needs source audit or when ingesting a new dense source.

The output of long-source verification should be a page update, a source note, or a log entry. It should not become a permanent parallel retrieval corpus unless repeated source audits show that compiled pages are missing important detail.

## Ingest Strategy For Rare Updates

Because source additions are rare, ingestion should optimize for correctness over automation:

1. Convert or inspect the source while preserving structure.
2. Build a temporary outline or page-range map for long documents.
3. Identify affected existing pages before creating new pages.
4. Update the smallest durable page set.
5. Add cross-links and index summaries.
6. Run the wiki doctor, graph tests, and API tests.
7. Record the ingest in `log.md`.

Do not enable watch-mode auto-ingest by default. Automatic file watching is useful for high-volume personal-note workflows, but this repo needs deliberate review because source interpretations affect coding behavior.

## When To Add Infrastructure

Add a vector index only if selector failures show that keyword, index, and graph selection cannot find the right page.

Add a graph database only if markdown-derived adjacency is no longer enough for traversal, filtering, or explanation.

Add a long-document index only if source PDFs repeatedly exceed what a careful ingest pass can inspect reliably.

Add persistent conversational memory only if repeated user sessions need preferences or project decisions that do not belong in the FoodEx2 knowledge base itself.

Until then, the cheaper path is better:

- better page summaries
- stronger links
- focused tests
- source-backed log entries
- explicit retrieval modes

## Quality Gates

Every architecture change should preserve these constraints:

- Markdown remains the source of truth.
- Runtime prompts read wiki pages, not hidden service prompts.
- Raw source files are never overwritten by generated interpretation.
- Graph data is derived from authored markdown.
- Domain overlays stay conditional.
- Business rules are retrieved through relevant pages, not attached blindly.
- Long-source notes must resolve into durable pages or source audit artifacts.
- Scheduled maintenance reports wiki drift; it does not silently rewrite or merge knowledge changes.

## Near-Term Improvements

- Add selector tests for graph-expansion trigger cases.
- Add ingest notes for long PDFs so future EFSA sources can be compiled with page-range traceability.
- Add a retrieval evaluation set for common FoodEx2 failure modes: raw-vs-derivative, composite ingredients, packaging, VMPR wild/game mapping, contaminants, pesticides, and additives.

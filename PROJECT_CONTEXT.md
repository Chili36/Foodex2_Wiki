---
title: "Project Context"
last_updated: "2026-05-14"
source_inspiration:
  - "https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f"
  - "https://github.com/VectifyAI/OpenKB"
  - "https://microsoft.github.io/graphrag/query/overview/"
related:
  - "[[KNOWLEDGE_ARCHITECTURE]]"
  - "[[INGEST_WORKFLOW]]"
  - "[[SCHEMA]]"
---

# What We Are Building

We are building a persistent markdown knowledge base for FoodEx2 guidance and validation policy so an LLM can support FoodEx2 coding from a maintained body of structured knowledge instead of re-reading raw PDFs and rule repositories from scratch each time.

In this workspace, that means:

- `foodex2_docs/` holds the immutable source PDFs.
- `raw/efsa-guidance/` holds the LLM-maintained markdown pages extracted, organized, cross-linked, and kept concise for both human reading and machine use.
- The knowledge base is topic-oriented rather than document-oriented, so rules about base terms, facets, process codes, code syntax, and validation behavior live in dedicated pages instead of a single large dump.

# Why We Are Building It

The goal is not simple document retrieval. The goal is to compile knowledge once, preserve the synthesis, and keep improving it over time.

Why this matters for FoodEx2:

- FoodEx2 guidance is spread across multiple PDFs, tables, appendices, training material, and domain-specific reporting rules.
- Many coding questions require combining rules from several places, such as base-term choice, implicit vs explicit facets, process handling, and validator-specific business rules.
- A maintained wiki reduces repeated interpretation work, surfaces contradictions or edge cases earlier, and makes downstream coding more consistent.
- Structured markdown pages are easier for an LLM to search, update, cite, and cross-reference than raw PDFs or one-off chat history.

# Operating Model

- New source documents are added to the raw source layer first.
- The LLM reads them, extracts the durable rules, and updates the markdown knowledge base.
- The markdown layer becomes the default working context for answering questions, while the raw PDFs and validator source material remain the source of truth for verification.

# Design Principle

This project follows the general pattern described in Andrej Karpathy's `llm-wiki` gist published on April 4, 2026: raw sources stay immutable, while the LLM incrementally builds and maintains a persistent interlinked wiki that compounds in value over time.

# Architecture Stance

The repo already has a markdown-native graph: frontmatter `related` links, inline `[[...]]` links, `Relevant Policy`, `Relevant Business Rules`, and `index.md` hub references. That graph should be strengthened before adding a separate graph database.

Because FoodEx2 source additions are rare, the project should favor deliberate compilation over automatic watch-mode ingestion. Long-document indexing, tree summaries, and long-context retrieval are useful during source ingest or source audit, but the durable runtime surface should remain compiled wiki pages served through `context-pack`.

The detailed architecture decision lives in [[KNOWLEDGE_ARCHITECTURE]].

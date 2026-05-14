---
title: "Wiki Index"
last_updated: "2026-05-14"
---

# Index

This is the content-oriented catalog for the FoodEx2 markdown wiki layer.

## Orientation

- [README.md](README.md): Repo overview, current status, directory layout, and working conventions.
- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md): What this wiki is for, why it exists, and the LLM-wiki operating model behind it.
- [KNOWLEDGE_ARCHITECTURE.md](KNOWLEDGE_ARCHITECTURE.md): Architecture stance for compiled markdown knowledge, graph retrieval, long-source ingest, and when not to add heavier RAG infrastructure.
- [INGEST_WORKFLOW.md](INGEST_WORKFLOW.md): Practical playbook for turning raw PDFs into stable topic pages without collapsing into one-shot summarization.
- [SCHEMA.md](SCHEMA.md): Page types, frontmatter fields, section conventions, and ingest schema for the FoodEx2 wiki.
- [RUNTIME_RULES.md](RUNTIME_RULES.md): Compact prompt-facing rules file always attached by `context-pack` before supporting guidance pages.
- [log.md](log.md): Chronological record of ingests and maintenance work.
- [policy-contract.md](raw/efsa-guidance/policy-contract.md): Richer control-layer page defining decision order, binding rules, tie-breaks, and anti-patterns for structured and solver-oriented flows.

## Guiding Principles

- FoodEx2 is a common scientific reporting language across food-safety domains, not a marketing or culinary description system. Code the food objectively by its nature, source, and treatment rather than by local commercial assumptions.
- FoodEx2 is built top-down. Choose the correct reportable base term first, then refine it with facets. Do not try to assemble the food bottom-up from arbitrary components if a standard FoodEx2 term already captures its identity.
- FoodEx2 prefers modular description over term proliferation. Use explicit facets to add meaningful detail, but only when that detail is not already implicit in the base term and is relevant to the coding purpose.
- Coding is an input/reporting task, not an analysis task. Describe the sample in front of you at the most specific reportable level available; downstream hierarchies and legislative mappings handle aggregation later.
- When in doubt, prefer the most specific objective biological/food-identity term available, add only the necessary modular refinements, and avoid encoding unnecessary commercial wording.

## FoodEx2 Guidance

- [foodex2-overview.md](raw/efsa-guidance/foodex2-overview.md): High-level explanation of FoodEx2 purpose, hierarchy model, and coding philosophy.
- [base-term-selection.md](raw/efsa-guidance/base-term-selection.md): Rules for choosing the right base term, including tie-breaks and missing-term handling.
- [facet-coding-rules.md](raw/efsa-guidance/facet-coding-rules.md): When to add facets, which facets matter most, and domain-specific exceptions.
- [implicit-vs-explicit-facets.md](raw/efsa-guidance/implicit-vs-explicit-facets.md): Distinguishes inherited facet information from coder-supplied facet detail.
- [code-string-format.md](raw/efsa-guidance/code-string-format.md): Exact FoodEx2 code syntax, separators, and ordering conventions.
- [process-facets.md](raw/efsa-guidance/process-facets.md): Compact reference for Appendix A2 process facet codes and when to use them.
- [ingredient-facets.md](raw/efsa-guidance/ingredient-facets.md): Rules for characterising ingredients, mixed foods, composite coding, and minor flavouring/added-ingredient use on derivatives.
- [packaging-facets.md](raw/efsa-guidance/packaging-facets.md): When to use `F18` packaging-format and `F19` packaging-material, and how they differ from `F28` process.
- [chemical-monitoring-foodex2.md](raw/efsa-guidance/chemical-monitoring-foodex2.md): Entry point for conditional chemical-monitoring overlays and routing to reporting-domain pages.
- [pesticides-foodex2.md](raw/efsa-guidance/pesticides-foodex2.md): Pesticide-residue overlay for Regulation (EC) No 396/2005, MATRIX mapping, MRL context, and pesticide-specific preparation assumptions.
- [contaminants-foodex2.md](raw/efsa-guidance/contaminants-foodex2.md): Contaminants overlay for OCC/chemAnalysis contexts, acrylamide F33, substance-specific reporting details, and contaminant-specific preparation assumptions.
- [vmpr-foodex2.md](raw/efsa-guidance/vmpr-foodex2.md): VMPR/VETDRUG overlay for explicit F01/F02, wild status, feed/water F23, non-food animal matrices, and Plan 3 F33.
- [vmpr-legislative-mapping.md](raw/efsa-guidance/vmpr-legislative-mapping.md): Downstream VMPR ETL/LLDB mapping from `sampMatCode` into `Game`, `Wild`, `FoodClassVMPR`, and final legislative commodity groups.
- [additives-flavourings-foodex2.md](raw/efsa-guidance/additives-flavourings-foodex2.md): Additives/flavourings overlay for mandatory or implicit F33, physical-state guidance, infant target-consumer, and non-reportable additive substance matrices.

## Validation Layer

- [business-rules.md](raw/efsa-guidance/business-rules.md): Canonical wiki target for `BR01`-`BR31`, used for page-level business-rule backlinks during ingest and retrieval.
- [validation-rules.md](raw/efsa-guidance/validation-rules.md): Overview of the validator's two-layer model, severities, and the most important blocking rules.
- [structural-validation.md](raw/efsa-guidance/structural-validation.md): Syntax, descriptor existence, implicit-facet cleanup, duplicates, and single-cardinality checks.
- [term-type-facet-constraints.md](raw/efsa-guidance/term-type-facet-constraints.md): Allowed and forbidden facets by FoodEx2 term type.
- [process-validation-rules.md](raw/efsa-guidance/process-validation-rules.md): Ordinal-group process conflicts, raw-vs-derivative process boundaries, and the main `F28` business rules.
- [domain-specific-validation.md](raw/efsa-guidance/domain-specific-validation.md): Context-activated validation constraints for VMPR/VETDRUG, additives/flavourings, contaminants substance rules, packaging, infant, and other reporting overlays.

## Maintenance History

- [maintenance-history.md](raw/efsa-guidance/maintenance-history.md): Cross-year timeline of FoodEx2 changes after revision 2.
- [maintenance-2015.md](raw/efsa-guidance/maintenance-2015.md): First annual maintenance after revision 2.
- [maintenance-2016-2018.md](raw/efsa-guidance/maintenance-2016-2018.md): Multi-year maintenance wave with major taxonomy and mapping work.
- [maintenance-2019.md](raw/efsa-guidance/maintenance-2019.md): Feed-focused revision plus bird and implicit-facet changes.
- [maintenance-2020.md](raw/efsa-guidance/maintenance-2020.md): Honey bees, birds, SIGMA, scallops, and reportability changes.
- [maintenance-2021.md](raw/efsa-guidance/maintenance-2021.md): EPPO plant mapping, matrix-code updates, and bird/F02 changes.
- [maintenance-2022.md](raw/efsa-guidance/maintenance-2022.md): PRIMo introduction and major feed/plant revisions.
- [maintenance-2023.md](raw/efsa-guidance/maintenance-2023.md): F34 Host-sampled, exposure-hierarchy redesign, and additives/flavourings mapping.
- [maintenance-2024.md](raw/efsa-guidance/maintenance-2024.md): VetDrugRes overhaul and expanded legislative mapping.

## Source Layer

- [foodex2_docs](foodex2_docs): Immutable EFSA PDF source collection used to build and verify the wiki.

---
title: "Wiki Index"
last_updated: "2026-04-05"
---

# Index

This is the content-oriented catalog for the FoodEx2 markdown wiki layer.

## Orientation

- [README.md](README.md): Repo overview, current status, directory layout, and working conventions.
- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md): What this wiki is for, why it exists, and the LLM-wiki operating model behind it.
- [log.md](log.md): Chronological record of ingests and maintenance work.

## FoodEx2 Guidance

- [foodex2-overview.md](raw/efsa-guidance/foodex2-overview.md): High-level explanation of FoodEx2 purpose, hierarchy model, and coding philosophy.
- [base-term-selection.md](raw/efsa-guidance/base-term-selection.md): Rules for choosing the right base term, including tie-breaks and missing-term handling.
- [facet-coding-rules.md](raw/efsa-guidance/facet-coding-rules.md): When to add facets, which facets matter most, and domain-specific exceptions.
- [implicit-vs-explicit-facets.md](raw/efsa-guidance/implicit-vs-explicit-facets.md): Distinguishes inherited facet information from coder-supplied facet detail.
- [code-string-format.md](raw/efsa-guidance/code-string-format.md): Exact FoodEx2 code syntax, separators, and ordering conventions.
- [process-facets.md](raw/efsa-guidance/process-facets.md): Compact reference for Appendix A2 process facet codes and when to use them.
- [ingredient-facets.md](raw/efsa-guidance/ingredient-facets.md): Rules for characterising ingredients, mixed foods, and minor ingredient use.
- [packaging-facets.md](raw/efsa-guidance/packaging-facets.md): When to use `F18` packaging-format and `F19` packaging-material, and how they differ from `F28` process.
- [chemical-monitoring-foodex2.md](raw/efsa-guidance/chemical-monitoring-foodex2.md): Small domain-specific overlay for how FoodEx2 is used in EFSA chemical-monitoring workflows.

## Validation Layer

- [validation-rules.md](raw/efsa-guidance/validation-rules.md): Overview of the validator's two-layer model, severities, and the most important blocking rules.
- [structural-validation.md](raw/efsa-guidance/structural-validation.md): Syntax, descriptor existence, implicit-facet cleanup, duplicates, and single-cardinality checks.
- [term-type-facet-constraints.md](raw/efsa-guidance/term-type-facet-constraints.md): Allowed and forbidden facets by FoodEx2 term type.
- [process-validation-rules.md](raw/efsa-guidance/process-validation-rules.md): Ordinal-group process conflicts and the main `F28` business rules.
- [domain-specific-validation.md](raw/efsa-guidance/domain-specific-validation.md): VMPR, additives, acrylamide, packaging, infant, and related context rules.

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

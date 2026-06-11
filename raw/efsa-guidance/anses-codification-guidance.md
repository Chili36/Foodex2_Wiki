---
title: "ANSES FoodEx2 Codification Guidance"
last_updated: "2026-06-12"
source_tier: "expert_guidance"
sources:
  - "FoodEx2 codification guidance_2025_12_v3.pdf"
related:
  - "[[base-term-selection]]"
  - "[[facet-coding-rules]]"
  - "[[implicit-vs-explicit-facets]]"
  - "[[INGEST_WORKFLOW]]"
---

# ANSES FoodEx2 Codification Guidance

<!-- Source: FoodEx2 codification guidance_2025_12_v3.pdf; Zenodo DOI 10.5281/zenodo.18229569 -->

## Source Tier

This source is `expert_guidance`.

Use it for:

- practical FoodEx2 coding workflow
- examples of expert coding conventions
- terminology explanations
- interpretation of common coding traps
- candidate topics for later wiki-page improvements

Do not use it to silently override:

- EFSA FoodEx2 catalogue data
- EFSA FoodEx2 business rules
- current validator behaviour
- ChemMon reporting guidance or domain-specific reporting rules
- legislation or official reporting-schema constraints

## Authority Boundary

The ANSES guidance is an official institutional expert source, not a local model observation. It can strengthen the wiki when it explains how experienced FoodEx2 coders apply official EFSA concepts.

When a claim from this source conflicts with an authoritative rule source, preserve the conflict explicitly and prefer the authoritative rule source for validation or reporting obligations.

## Ingest Use

Treat this document as a source for selective claim extraction, not as a page to summarize wholesale.

Before adding content from it to operational pages:

1. identify the exact claim and page reference
2. classify the claim as rule, convention, example, explanation, or tool instruction
3. check whether the same claim is already covered by EFSA, ChemMon, business-rule, or validator sources
4. add it as a rule only when supported by authoritative evidence
5. otherwise add it as expert guidance, a caveat, or a worked example

## Extracted Guidance

This ingest keeps the ANSES document as `expert_guidance`. The points below are durable coding guidance extracted from the December 2025 v3 PDF; they should be used to clarify existing FoodEx2 wiki pages, not to override current EFSA catalogue data, validator behaviour, ChemMon guidance, or domain-specific reporting rules.

### Base-Term Workflow

- The general coding method is: choose the right base term first, then add appropriate facet descriptors. Facets preserve relevant information only when the base term alone is insufficient. (ANSES guidance p24-25)
- The first decision is the food type: raw primary commodity, derivative, or composite. This is a question about the nature of the food itself, not the origin question "what is it made from?" (ANSES guidance p25)
- Base-term choice is analytically important because it places the sample in a FoodEx2 family; sometimes the selected family or branch matters as much as the exact code. (ANSES guidance p25)
- When raw-versus-derivative status is uncertain, check whether FoodEx2 has a processed or preserved derivative branch for the relevant raw commodity before adding `F28` to a raw base. (ANSES guidance p27-30)
- Browser tree order is not always the decision order. For processed/preserved products and balanced composite dishes, use the documented top-down priority rules rather than the visual order in the catalogue browser. (ANSES guidance p30, p33)
- For level of detail, prefer extended terms and core terms when they fit. Non-specific and generic non-hierarchy terms are fallbacks when the detailed term is missing or the coder lacks source detail. (ANSES guidance p35)

### Facet Workflow

- Implicit facets should not be reported explicitly, but they are useful evidence for deciding which explicit facet can legitimately narrow or supplement a base term. (ANSES guidance p36, p39-41)
- The number of explicit facets is not theoretically capped, but only facets that better define a subgroup or materially retain source information should be added. In practice, added facets are usually few. (ANSES guidance p37-38)
- `F01`, `F27`, and `F04` answer similar origin questions but depend on the selected base type: `F01` for raw commodities, `F27` for derivative source commodities and same-nature mixtures, and `F04` for composite characterising ingredients or minor later-added ingredients. (ANSES guidance p39-44, p95)
- `F04 Ingredient` is not a recipe field. It should usually name one or a few characterising ingredients, flavouring ingredients, coatings, or minor added ingredients, not every recipe component. (ANSES guidance p42-43)
- If a descriptor concept exists both as a process and as a qualitative product claim, the qualitative descriptor can be the better representation when the source wording is a product claim rather than a manufacturing fact. (ANSES guidance p45)

### Missing Terms

- If a detailed raw base term is missing, use the nearest generic raw base, add a more specific `F01` source when available, and add `F26.A07XE` (`other`). If no suitable `F01` descriptor exists, keep the generic base and preserve the missing detail in text. (ANSES guidance p48)
- If a detailed derivative base term is missing, use the nearest generic derivative base, add the best `F27` source-commodity descriptor, and add `F26.A07XE`. If the needed `F27` descriptor is missing but an `F01` source exists, ANSES treats `F01` as a narrow tolerated fallback only for this single-source missing-derivative case; it should not be generalized. (ANSES guidance p49-50)
- If a detailed composite base term is missing, choose a similar non-hierarchy composite base by use, meal position, and expected major ingredients, add characterising `F04` ingredients, and add `F26.A07XE`. (ANSES guidance p51)

### Mixed Products

- Same-nature mixes should normally stay on a generic raw or derivative base and list the components with multiple `F27` source-commodity descriptors. (ANSES guidance p52-53)
- Same-nature mixes with small amounts of different-nature ingredients can combine multiple `F27` descriptors for the main same-nature components with `F04` for the minor foreign components. (ANSES guidance p54)
- Balanced different-nature mixtures should move to a composite base and use `F04` for the characterising components. (ANSES guidance p55)

### Special Cases And Checks

- `F07` fat-content and `F11` alcohol-content are single-cardinality numeric facets. For range values, ANSES suggests using an average and the nearest available descriptor rather than adding both endpoints. Treat this as expert coding convention and verify it against the active reporting context. (ANSES guidance p58)
- For names containing alternatives such as "or", ANSES recommends using a general base and adding the alternative details as facets, even if the alternatives are mutually exclusive in a single marketed item. Treat this as a harmonisation convention for under-specified source text. (ANSES guidance p58)
- For dataset quality checks, ANSES recommends looking for feed/food mismatches, hierarchy terms used as bases, raw bases with derivative-creating process facets, flavour or infusion wording mismatches, `F04` on raw or derivative bases, and multiple `F01` source facets on raw bases. (ANSES guidance p89-92)

## Known Limits

- The document was written for food-database interoperability and harmonised codification. It is not itself a monitoring-domain reporting specification.
- The document cites MTX 15.0 as the current catalogue at the time of writing. This wiki currently tracks newer MTX and validator behaviour where available.
- Some ANSES examples and OCR text contain typographic or extraction noise. Use the PDF page reference and the current catalogue/validator before promoting any example into an operational rule.
- The section on spices and herbal infusion materials should be handled carefully: ANSES describes a dried-by-default convention for spices and infusion materials, but current catalogue terms and validator rules can still provide specific dried derivative terms for particular commodities. Do not use that convention to override a current valid derivative base term.

## Relevant Pages

- [[base-term-selection]]
- [[facet-coding-rules]]
- [[implicit-vs-explicit-facets]]
- [[INGEST_WORKFLOW]]

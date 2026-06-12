# Source Impact Report: ANSES FoodEx2 Codification Guidance v3

Date: 2026-06-12

Source file: `foodex2_docs/FoodEx2 codification guidance_2025_12_v3.pdf`

Source tier: `expert_guidance`

Status: retroactive report written after initial ingest.

## Intake Question

What does this source add to the FoodEx2 wiki that is not already covered by the authoritative EFSA catalogue, business rules, ChemMon/domain guidance, validator behaviour, or existing wiki pages?

## Source Identity

The document is official ANSES expert guidance for FoodEx2 codification, version 3 dated December 2025. It is useful as a practical coding guide and interoperability aid, not as a source that overrides EFSA catalogue data, business rules, reporting-domain obligations, or current validator behaviour.

The PDF text layer was sparse, so ingest required OCR before the body guidance could be reviewed.

## Scope

The source covers:

- FoodEx2 coding workflow and base-term-first reasoning.
- Raw, derivative, and composite base-term selection.
- Implicit and explicit facet handling.
- Missing-term conventions using generic bases, source facets, and `F26.A07XE`.
- Same-nature and mixed-nature product handling.
- Numeric range facets such as fat and alcohol content.
- Dataset quality-control checks for codification review.

It is not primarily a monitoring-domain document and should not be treated as a VMPR, pesticides, contaminants, or additives reporting overlay.

## Novel Contributions

- It clearly separates `what type of food is this?` from `what is it made from?`, which strengthens base-term selection.
- It treats implicit facets as useful evidence for narrowing decisions, not merely as facts to omit.
- It gives a practical explanation of why most FoodEx2 codes need only a few explicit facets.
- It adds human-coder workflow detail for missing terms and mixed products.
- It provides batch-review checks that are useful for finding systematic coding errors.
- It highlights range-value handling for single-cardinality numeric facets, especially `F07` and `F11`.

## Overlap With Existing Wiki

The source largely reinforces existing wiki direction rather than replacing it.

- `base-term-selection.md` already covered food type first, derivative bases, composite bases, and generic fallback logic.
- `facet-coding-rules.md` already covered minimal explicit facets and the main facet families.
- `implicit-vs-explicit-facets.md` already covered inherited facets and the direct origin facet model.
- `ingredient-facets.md` already covered `F04` as characterising ingredient logic rather than a full recipe field.
- `validation-rules.md` already covered structural validation and reportability checks.

The ANSES source improved those pages by adding expert-coder framing, extra caution around browser order, range facets, flavouring ambiguity, and batch QC checks.

## Conflicts Or Tension

- The source cites MTX 15.0, while this wiki currently tracks newer MTX and validator behaviour. Current catalogue and validator evidence must win.
- Some examples use expert conventions that may not be reporting-domain obligations.
- The spice and herbal-infusion discussion can be misread as a blanket dried-default rule. The wiki should not use that convention to override specific current derivative terms or validator rules.
- OCR noise means individual examples should not be promoted into operational rules without checking the PDF page and current catalogue.
- ANSES guidance on range values is useful expert convention, but active reporting contexts may require different handling.

## Ingest Risk

Main risks:

- Overfitting examples into hard rules.
- Treating expert guidance as authoritative validation policy.
- Importing old-catalogue assumptions into current MTX behaviour.
- Expanding operational pages with too many source-specific examples.

Risk control:

- Keep the page as `source_tier: "expert_guidance"`.
- Patch only reusable concepts into operational pages.
- Keep conflicts and limits visible on the ANSES source page.
- Verify promoted claims against catalogue, validator, and domain guidance before treating them as rules.

## Recommended Action

Recommended action was:

- Add the PDF as immutable source material.
- Create a concise `expert_guidance` source page.
- Patch existing operational pages instead of creating a document-order summary.
- Rebuild curated markdown RAG and raw-source RAG.
- Add OCR fallback to the raw-source indexer because the PDF text layer was incomplete.

This was the correct ingest shape. The missing pre-step was this explicit source impact report.

## Wiki Changes Justified

The report supports the following changes already made:

- `anses-codification-guidance.md`: source page and extracted durable expert guidance.
- `base-term-selection.md`: food type before origin, raw-vs-derivative branch check, browser-order caution, detail-level fallback framing.
- `facet-coding-rules.md`: few targeted facets, implicit facets as evidence, `F07`/`F11` range caution, product-claim versus process distinction.
- `implicit-vs-explicit-facets.md`: implicit facets as narrowing evidence and narrow missing-derivative fallback caveat.
- `ingredient-facets.md`: flavouring ingredient versus regulated flavouring distinction.
- `code-string-format.md`: no spaces, one code, stable facet ordering convention.
- `validation-rules.md`: batch-review checks for feed/food mismatch, hierarchy bases, raw base plus derivative-making processes, flavouring and infusion ambiguity, `F04` on raw/derivative bases, and multiple `F01` on raw bases.

## Candidate Test Cases

Use these to evaluate whether the ANSES guidance improves classifier behaviour without creating new overfit rules:

- Dried chili pepper: should keep the dried derivative base when available and use a source-commodity facet to preserve chili detail where valid.
- Fresh cheese with minimum fat content: should select the cheese derivative base and avoid converting a minimum value into an exact fat descriptor unless the reporting convention supports it.
- Same-nature mixed dried mushrooms: should keep a dried-mushroom derivative base and describe source commodities with appropriate facets where valid.
- Flavoured yoghurt or drink: should distinguish food ingredient flavouring from regulated flavouring descriptors.
- Infusion material versus prepared infusion: should distinguish dry material from final reconstituted beverage.
- Missing detailed derivative: should use generic derivative plus `F27` and `F26.A07XE` where the current catalogue lacks a detailed term.

## Decision

Keep the ANSES document in the wiki as expert guidance. Use it to improve reasoning, intake review, and QC checks. Do not use it as a standalone authority for validation, reporting-domain obligations, or catalogue facts.

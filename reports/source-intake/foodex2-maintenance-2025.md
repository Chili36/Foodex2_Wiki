# Source Impact Report: FoodEx2 Maintenance 2025

Date: 2026-10-01

## Source Identity And Authority

- Source: `foodex2_docs/EFSA Supporting Publications - 2026 -  - FoodEx2 maintenance 2025.pdf`.
- DOI: [10.2903/sp.efsa.2026.EN-10069](https://doi.org/10.2903/sp.efsa.2026.EN-10069).
- EFSA technical report, approved 1 April 2026, published 9 April 2026, 21 pages. Covers MTX 16.1, 16.2, 16.3 and the January 2026 MTX 17.0 release, starting from MTX 16.0.
- Source tier: `authoritative_rule` for the documented catalogue changes, bounded to those releases. It does not replace newer catalogue data, reporting guidance or validator behaviour.
- Intended audience: FoodEx2 data providers, catalogue users and maintainers across food-safety and exposure-assessment domains.
- Intake provenance: an existing Wiley-downloaded PDF in the local Downloads directory was copied unchanged after verifying its title, DOI and 21-page count against the linked publication. Direct scripted retrieval returned HTTP 403. No reconstructed PDF was substituted.

## Structure Scan And Topic Map

The PDF has a complete text layer. All 21 pages were inspected as text; pages 11 and 13-17 were also rendered to verify facet codes and Tables 1 and 3-6. The body is organised by surveillance/reporting domain and then facet family. Page 21 identifies two separate supplementary spreadsheets; it does not contain their data.

| Source pages | Durable contribution | Wiki action |
| --- | --- | --- |
| 3, 5-9, 12, 15-18 | Release scope, counts, bird/mammal/NORA taxonomy, EU FCDB, F31/F34 changes | Create `maintenance-2025.md`; extend `maintenance-history.md` |
| 10-11, 13, 16-17 | Additive F33 remapping, iced tea, supplement physical forms, dismissed generic class | Patch `additives-flavourings-foodex2.md` |
| 11-12 | Small/large radish leaves, changed pesticide matrixCode values, PRIMo reportability distinction | Patch `pesticides-foodex2.md` |
| 13-15, 17 | Multiple organs from one animal; special diets; domestic animals; F21 to F29 change | Patch `facet-coding-rules.md` |
| 14 | Boiling/draining, popping, scalding and pressure-cooking placement | Patch `process-facets.md` |
| 17 | A03PX is no longer reportable in Reporting; dismissal is hierarchy-specific | Patch `base-term-selection.md`; link the existing validation rule explanation |

## Novelty And Overlap

The wiki previously ended at maintenance 2024. The new source adds 79 terms, 358 revised scope notes and five hierarchy/facet-specific dismissals, with no deprecations. Per-facet addition counts overlap and must not be summed into a catalogue total. The report's 32 new bird entries include higher taxa and subspecies, not 32 species.

Existing pages already explain implicit-facet deduplication, conditional ChemMon overlays, reportability and the distinction between dismissal and deprecation. These principles stay in place. This ingest supplies concrete changed descriptors and decision boundaries; it does not introduce a new global coding policy or validator rule.

## Conflicts And Ingest Risks

- The PDF describes MTX 17.0, whereas the sibling validator has a local MTX 17.2 snapshot. Check descriptor identities and relevant hierarchy membership against that snapshot; do not claim it is the latest upstream catalogue.
- `A1A9M`, `A1A9N` and `A1A9P` are dismissed in F21 but reportable in F29. A global deletion claim would be wrong. Existing BR21 blocking behaviour remains unchanged.
- `A1B3H Small radish leaves` is present but not reportable in PRIMo; that is distinct from its Reporting-hierarchy availability.
- The old process page groups A07GK and A07GQ using the 2015 Appendix A2 organisation. Mark that list as historical and place the newer scalding/pressure-cooking guidance in prompt-visible text.
- Preserve the PDF's code `A1B1O` for Drops (letter O); the local catalogue confirms it. Do not silently substitute zero.
- New F23 vegan/vegetarian descriptors describe supported dietary information; do not infer such claims from incomplete ingredients. Avian-influenza multiple-organ sampling does not create a universal VMPR requirement.
- Appendix A (full change log) and Appendix B (MTX 17.0 catalogue) are separate spreadsheets and are outside this PDF ingest. Do not invent codes omitted by the report or claim an exhaustive catalogue import.

## Recommended Action

Preserve the PDF; add one annual maintenance page; patch the existing operational pages above; register the new page and update navigation, architecture range and log. Record catalogue checks and review the existing coverage findings affected by the edits. Sync both the curated wiki index and the new PDF in the raw-source collection, then run doctor, tests and a live page-read check.

## Candidate Verification Cases

- Farrow-to-finish pig sampling: F29 is available; F21 is not; no global deprecation.
- Generic infant-food base A03PX: reject as a Reporting base and choose an applicable reportable child.
- Small versus large radish leaves: distinct identities and parents; a PRIMo flag must not be mistaken for the Reporting flag.
- Effervescent versus chewable supplements, drops versus syrup: keep the supported F03 distinction.
- Boiled-and-drained food: retain the specific F28 detail only when not already implicit and keep the correct food base.
- Iced tea in additives reporting: inspect the dedicated base and its implicit flavoured-drinks class before adding F33.

Catalogue evidence is in [the read-only MTX 17.2 check](foodex2-maintenance-2025-catalogue-check.json). The [coverage follow-up](../source-coverage/2026-10-01-maintenance-2025.md) records semantic verification and the recheck of existing findings.

## Final Verification

- `pytest -q`: 254 passed. The earlier fixed-count audit assertion was updated to require the original 11 finding IDs and nonempty resolution evidence for every finding, allowing new source reviews without dropping prior checks.
- `python -m wiki_api.doctor --check-rag-index --strict-warnings`: zero errors and warnings; scoped coverage audit current.
- Curated wiki RAG: 34 pages, 287 chunks, no missing/stale/orphaned chunks.
- Raw-source RAG: 34 chunks for the new PDF, covering pages 1-21; stored content hashes equal the source-derived chunks. Existing source points were preserved.
- Restarted the existing local wiki LaunchAgent; live health, page registration, selector summary and RAG status passed. Coding projection checks confirm the new operational details survive prompt projection while the annual maintenance page remains outside automatic coding context.
- [Index and live-service evidence](foodex2-maintenance-2025-index-check.json).

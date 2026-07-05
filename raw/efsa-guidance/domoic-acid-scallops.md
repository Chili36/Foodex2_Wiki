---
title: "Domoic Acid In Scallops"
select_when: >-
  The case is a contaminants-monitoring analysis of domoic acid in a scallop
  matrix, where exact reportable sample-matrix codes and texts are required per
  species and analysed part, plus an area-of-origin code, drawn from a fixed
  lookup rather than reconstructed by the coder.
sources:
  - "Reportable Scallops list of FoodEx2 codes - MTX.xlsx"
  - "domoic_acid_scallops_mtx.csv"
related:
  - "[[chemical-monitoring-foodex2]]"
  - "[[contaminants-foodex2]]"
  - "[[domain-specific-validation]]"
  - "[[facet-coding-rules]]"
  - "[[implicit-vs-explicit-facets]]"
last_updated: "2026-05-19"
---

# Domoic Acid In Scallops

## Use Only For Domoic Acid Scallop Reporting

- This page is a conditional chemical-monitoring contaminants overlay. Use it when the analysis context is domoic acid and the matrix is scallop.
- Do not generalise this lookup to all shellfish, all scallops, or all contaminants. For ordinary contaminant cases, start with [[contaminants-foodex2]] and the candidate list returned by MTX.
- If the request or upstream metadata identifies domoic acid in scallops, treat the matrix mapping below as the reportable source for `sampMatCode` and `sampMatText`.

## Reporting Rule

- For data preparation related to domoic acid in scallops, `sampMatCode` and `sampMatText` are essential reporting fields.
- Choose the row that matches both the scallop species and the part analysed, then report the exact `sampMatCode` and corresponding `sampMatText` from the lookup table.
- If the exact scallop species is not registered in the MTX catalogue or is unavailable, use the `Pecten spp.` rows only as the source-provided fallback.
- Wherever possible, also include `origFishAreaCode`, the area of origin for fisheries and aquaculture activities code, selected from EFSA's FAREA catalogue.
- Do not invent a scallop species, part, `sampMatCode`, or `sampMatText` that is not present in the lookup. If the source sample description is ambiguous, preserve the uncertainty outside the FoodEx2 code and ask for clarification when the workflow allows it.

## Reportable Scallop Matrix Lookup

The table is normalised from `Reportable Scallops list of FoodEx2 codes - MTX.xlsx`; `domoic_acid_scallops_mtx.csv` is the machine-readable extract committed with the source file.

| Scientific name | Part analysed | sampMatCode | sampMatText |
| --- | --- | --- | --- |
| Chlamys islandica | Entire animal | `A02HN#F01.A0B0P$F03.A06HY` | Chlamys islandica, Entire animal |
| Chlamys islandica | Adductor muscle | `A02HN#F01.A0B0P` | Chlamys islandica, Adductor muscle |
| Chlamys islandica | Adductor muscle and Gonads | `A02HN#F01.A0B0P$F20.A18FK` | Chlamys islandica, Adductor muscle and Gonads |
| Chlamys islandica | Gonads | `A16FR#F01.A0B0P$F20.A18FK` | Chlamys islandica, Gonads |
| Chlamys islandica | Hepatopancreas | `A16FR#F01.A0B0P$F20.A18FH` | Chlamys islandica, Hepatopancreas |
| Chlamys islandica | Entire animal excluding Hepatopancreas | `A02HN#F01.A0B0P$F26.A07XE` | Chlamys islandica, Entire animal excluding Hepatopancreas |
| Chlamys islandica | Hepatopancreas and Mantle | `A16FR#F01.A0B0P$F20.A18FH$F20.A18FJ` | Chlamys islandica, Hepatopancreas and Mantle |
| Chlamys islandica | Hepatopancreas, Mantle and Gonads | `A16FR#F01.A0B0P$F20.A18FH$F20.A18FJ$F20.A18FK` | Chlamys islandica, Hepatopancreas and Mantle and Gonads |
| Chlamys islandica | Mantle | `A16FR#F01.A0B0P$F20.A18FJ` | Chlamys islandica, Mantle |
| Chlamys islandica | Entire animal excluding gonad and adductor muscle | `A16FR#F01.A0B0P` | Chlamys islandica, Entire animal excluding gonad and adductor muscle |
| Aequipecten opercularis | Entire animal | `A02HV#F03.A06HY` | Aequipecten opercularis, Entire animal |
| Aequipecten opercularis | Adductor muscle | `A02HV` | Aequipecten opercularis, Adductor muscle |
| Aequipecten opercularis | Adductor muscle and Gonads | `A02HV#F20.A18FK` | Aequipecten opercularis, Adductor muscle and Gonads |
| Aequipecten opercularis | Gonads | `A16FR#F01.A055R$F20.A18FK` | Aequipecten opercularis, Gonads |
| Aequipecten opercularis | Hepatopancreas | `A16FR#F01.A055R$F20.A18FH` | Aequipecten opercularis, Hepatopancreas |
| Aequipecten opercularis | Entire animal excluding Hepatopancreas | `A02HV#F26.A07XE` | Aequipecten opercularis, Entire animal excluding Hepatopancreas |
| Aequipecten opercularis | Hepatopancreas and Mantle | `A16FR#F01.A055R$F20.A18FH$F20.A18FJ` | Aequipecten opercularis, Hepatopancreas and Mantle |
| Aequipecten opercularis | Hepatopancreas, Mantle and Gonads | `A16FR#F01.A055R$F20.A18FH$F20.A18FJ$F20.A18FK` | Aequipecten opercularis, Hepatopancreas and Mantle and Gonads |
| Aequipecten opercularis | Mantle | `A16FR#F01.A055R$F20.A18FJ` | Aequipecten opercularis, Mantle |
| Aequipecten opercularis | Entire animal excluding gonad and adductor muscle | `A16FR#F01.A055R` | Aequipecten opercularis, Entire animal excluding gonad and adductor muscle |
| Mimachlamys varia | Entire animal | `A02HN#F01.A0B28$F03.A06HY` | Mimachlamys varia, Entire animal |
| Mimachlamys varia | Adductor muscle | `A02HN#F01.A0B28` | Mimachlamys varia, Adductor muscle |
| Mimachlamys varia | Adductor muscle and Gonads | `A02HN#F01.A0B28$F20.A18FK` | Mimachlamys varia, Adductor muscle and Gonads |
| Mimachlamys varia | Gonads | `A16FR#F01.A0B28$F20.A18FK` | Mimachlamys varia, Gonads |
| Mimachlamys varia | Hepatopancreas | `A16FR#F01.A0B28$F20.A18FH` | Mimachlamys varia, Hepatopancreas |
| Mimachlamys varia | Entire animal excluding Hepatopancreas | `A02HN#F01.A0B28$F26.A07XE` | Mimachlamys varia, Entire animal excluding Hepatopancreas |
| Mimachlamys varia | Hepatopancreas and Mantle | `A16FR#F01.A0B28$F20.A18FH$F20.A18FJ` | Mimachlamys varia, Hepatopancreas and Mantle |
| Mimachlamys varia | Hepatopancreas, Mantle and Gonads | `A16FR#F01.A0B28$F20.A18FH$F20.A18FJ$F20.A18FK` | Mimachlamys varia, Hepatopancreas and Mantle and Gonads |
| Mimachlamys varia | Mantle | `A16FR#F01.A0B28$F20.A18FJ` | Mimachlamys varia, Mantle |
| Mimachlamys varia | Entire animal excluding gonad and adductor muscle | `A16FR#F01.A0B28` | Mimachlamys varia, Entire animal excluding gonad and adductor muscle |
| Pecten maximus | Entire animal | `A02HS#F03.A06HY` | Pecten maximus, Entire animal |
| Pecten maximus | Adductor muscle | `A02HS` | Pecten maximus, Adductor muscle |
| Pecten maximus | Adductor muscle and Gonads | `A02HS#F20.A18FK` | Pecten maximus, Adductor muscle and Gonads |
| Pecten maximus | Gonads | `A16FR#F01.A055P$F20.A18FK` | Pecten maximus, Gonads |
| Pecten maximus | Hepatopancreas | `A16FR#F01.A055P$F20.A18FH` | Pecten maximus, Hepatopancreas |
| Pecten maximus | Entire animal excluding Hepatopancreas | `A02HS#F26.A07XE` | Pecten maximus, Entire animal excluding Hepatopancreas |
| Pecten maximus | Hepatopancreas and Mantle | `A16FR#F01.A055P$F20.A18FH$F20.A18FJ` | Pecten maximus, Hepatopancreas and Mantle |
| Pecten maximus | Hepatopancreas, Mantle and Gonads | `A16FR#F01.A055P$F20.A18FH$F20.A18FJ$F20.A18FK` | Pecten maximus, Hepatopancreas and Mantle and Gonads |
| Pecten maximus | Mantle | `A16FR#F01.A055P$F20.A18FJ` | Pecten maximus, Mantle |
| Pecten maximus | Entire animal excluding gonad and adductor muscle | `A16FR#F01.A055P` | Pecten maximus, Entire animal excluding gonad and adductor muscle |
| Pecten jacobaeus | Entire animal | `A02HN#F01.A117Y$F03.A06HY` | Pecten jacobaeus, Entire animal |
| Pecten jacobaeus | Adductor muscle | `A02HN#F01.A117Y` | Pecten jacobaeus, Adductor muscle |
| Pecten jacobaeus | Adductor muscle and Gonads | `A02HN#F01.A117Y$F20.A18FK` | Pecten jacobaeus, Adductor muscle and Gonads |
| Pecten jacobaeus | Gonads | `A16FR#F01.A117Y$F20.A18FK` | Pecten jacobaeus, Gonads |
| Pecten jacobaeus | Hepatopancreas | `A16FR#F01.A117Y$F20.A18FH` | Pecten jacobaeus, Hepatopancreas |
| Pecten jacobaeus | Entire animal excluding Hepatopancreas | `A02HN#F01.A117Y$F26.A07XE` | Pecten jacobaeus, Entire animal excluding Hepatopancreas |
| Pecten jacobaeus | Hepatopancreas and Mantle | `A16FR#F01.A117Y$F20.A18FH$F20.A18FJ` | Pecten jacobaeus, Hepatopancreas and Mantle |
| Pecten jacobaeus | Hepatopancreas, Mantle and Gonads | `A16FR#F01.A117Y$F20.A18FH$F20.A18FJ$F20.A18FK` | Pecten jacobaeus, Hepatopancreas and Mantle and Gonads |
| Pecten jacobaeus | Mantle | `A16FR#F01.A117Y$F20.A18FJ` | Pecten jacobaeus, Mantle |
| Pecten jacobaeus | Entire animal excluding gonad and adductor muscle | `A16FR#F01.A117Y` | Pecten jacobaeus, Entire animal excluding gonad and adductor muscle |
| Pecten spp. | Entire animal | `A02HN#F03.A06HY` | Pecten spp., Entire animal |
| Pecten spp. | Adductor muscle | `A02HN` | Pecten spp., Adductor muscle |
| Pecten spp. | Adductor muscle and Gonads | `A02HN#F20.A18FK` | Pecten spp., Adductor muscle and Gonads |
| Pecten spp. | Gonads | `A16FR#F20.A18FK` | Pecten spp., Gonads |
| Pecten spp. | Hepatopancreas | `A16FR#F20.A18FH` | Pecten spp., Hepatopancreas |
| Pecten spp. | Entire animal excluding Hepatopancreas | `A02HN#F26.A07XE` | Pecten spp., Entire animal excluding Hepatopancreas |
| Pecten spp. | Hepatopancreas and Mantle | `A16FR#F20.A18FH$F20.A18FJ` | Pecten spp., Hepatopancreas and Mantle |
| Pecten spp. | Hepatopancreas, Mantle and Gonads | `A16FR#F20.A18FH$F20.A18FJ$F20.A18FK` | Pecten spp., Hepatopancreas and Mantle and Gonads |
| Pecten spp. | Mantle | `A16FR#F20.A18FJ` | Pecten spp., Mantle |
| Pecten spp. | Entire animal excluding gonad and adductor muscle | `A16FR` | Pecten spp., Entire animal excluding gonad and adductor muscle |

## Retrieval Signals

- Trigger this page for domoic acid, scallops, `sampMatCode`, `sampMatText`, `origFishAreaCode`, FAREA, `Pecten`, `Chlamys islandica`, `Aequipecten opercularis`, `Mimachlamys varia`, `Pecten maximus`, `Pecten jacobaeus`, or `Pecten spp.` in a contaminants or chemical-monitoring context.
- The table is intentionally exact reference data. Use the row values directly instead of reconstructing these scallop matrices from memory.

## Relevant Policy

- [[policy-contract]] Decision Procedure step 5 governs this page: apply domain-specific reporting overlays only after the ordinary FoodEx2 base and facet structure is understood.
- [[policy-contract]] `C09` applies when the needed exact mapping is not present in the candidate list or source data: do not invent a code.

## Relevant Business Rules

- `BR14` and `BR15`: contextual validation paths activate only in the relevant reporting workflows. See [[business-rules]].
- `BR30` and `BR31`: explicit facets must use valid categories and descriptors. See [[business-rules]].

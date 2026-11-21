---
title: "Process Facets"
select_when: >-
  The case involves a treatment or processing step and must decide whether it
  belongs in the base-term choice or as an explicit process facet, and which
  specific process descriptor applies — heating, preservation, drying,
  fermentation, coating, grinding or milling, powder described by a process
  rather than F03, draining after boiling, popping, or similar transformations.
sources:
  - "EFSA Supporting Publications - 2026 -  - FoodEx2 maintenance 2025.pdf"
  - "EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf"
related:
  - "[[facet-coding-rules]]"
  - "[[base-term-selection]]"
  - "[[code-string-format]]"
  - "[[maintenance-2025]]"
last_updated: "2026-11-21"
---

# Process Facets

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p20, p44, p46-47, p58, p78-83 -->
## Rule Of Use

- Add `F28` only when the treatment makes the difference. If the derivative base term already implies the process, do not restate it. Read this together with [[base-term-selection]] when deciding whether the process belongs in the base term or in an explicit facet. (EFSA guidance p44, p46-47, p58)
- `F13-F16` are largely deprecated; use `F28`. The general "implicit vs explicit" boundary is summarized in [[implicit-vs-explicit-facets]], and the string syntax is in [[code-string-format]]. (EFSA guidance p46-47)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p43-44 Table 22, p52 section 5.9 -->
## Processes Applied Directly To Raw Commodities

- A treatment that does not create a new derivative nature is added to a raw-commodity base as an explicit `F28`; the base stays a raw primary commodity. Table 22 lists the processes normally applied this way. It is explicitly non-exhaustive, and only in rare, mostly legacy cases does a specific group for one of these processes exist (for example boiled potato and baked potato). The generic descriptors processed, preserved and semi-preserved name no specific process and are outside this rule. (EFSA guidance p43-44, Table 22)
- Table 22 covers physical division and dimension reduction (`A07KT` portioning, `A07KV` slicing, `A07KX` dicing/stripe-cutting, `A07KY` mincing/chopping/cutting, `A07KZ` grating, `A07LA` grinding/milling/crushing, `A0C6N` pulping/mashing), physical decontamination, lowering temperature, thermal preservation, **cooking and similar thermal preparation (`A0BA1` and its children: blanching, boiling, steaming, stewing, frying, baking, roasting, grilling, toasting)**, aseptic filling, vacuum-packing, and breading, battering, glazing/icing, sugar, chocolate or nut coating. Cooking is therefore not a derivative-creating process by default: a roasted, boiled or baked raw commodity keeps its raw base with the cooking descriptor in `F28`. (EFSA guidance p44, Table 22)
- Use a derivative group instead only for Table 22's listed exceptions, after checking the catalogue: some minced-meat groups; grain milling with separation, which creates grain derivatives with their own milling descriptors; mashing with separation and cooking, which leads to purée groups in some plant derivatives; frying or roasting potatoes; cooking eggs; and caramelisation/browning, e.g. in sugar and milk. (EFSA guidance p44, Table 22)
- When wording can be represented either as a changed physical state or as the treatment that produced it, give priority to the treatment when in doubt. Where both add information and are legal, the guidance suggests reporting both. (EFSA guidance p52, section 5.9)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p15-16, p43-44 Table 22, p48, p58-59 -->
## Physical Division And Derivative Production

- Physical division or size reduction does not automatically require a derivative base. EFSA lists grinding/milling/crushing (`F28.A07LA`) among processes normally applied directly to raw commodities. Where the raw base covers the food and no applicable derivative group covers the resulting product, retain the raw base and add the known, permitted process if it is not already implicit. Some physical-division products have their own groups; check the actual catalogue scope rather than inferring food type from the word "ground" or "powder". (EFSA guidance p43-44, Table 22)
- Distinguish simple grinding from grain milling associated with separation and production of recognised derivatives such as flours, bran or groats. Those products use an applicable derivative base; the specific grain-milling descriptors (`A0C03`, `A0C09`, `A0C0A`) are distinct from physical division `A07LA`. A missing species-specific derivative does not justify raw plus grinding when a suitable generic derivative covers the product; use the appropriate origin facets. (EFSA guidance p15-16, p44, p48, p58-59)
- `F03` powder describes a physical state; `F28.A07LA` describes a process. A BR13 rejection of F03 powder on a raw base does not itself require a derivative base. Known grinding may be represented by the permitted F28 process while retaining the appropriate raw base. A description explicitly stating "ground" supplies grinding evidence; "powder" alone does not establish how the powder was produced. Neither word alone settles the base-term class. Do not automatically replace F03 with F28 or use A07LA to evade a required derivative group. Read [[term-type-facet-constraints]] and [[base-term-selection]] together. (EFSA guidance p43-44; Business Rules `BR13`, `BR19`)

<!-- Source: EFSA Supporting Publications - 2026 -  - FoodEx2 maintenance 2025.pdf p14, Tables 3-4 -->
## Cooking Detail Added Or Revised In Maintenance 2025

| Descriptor | Interpretation |
| --- | --- |
| `F28.A1B1L Boiling and draining` | Boiling followed by draining; a child of `A07GL Boiling`. |
| `F28.A1B1M Boiling and undraining` | Boiling without draining; a child of `A07GL Boiling`. |
| `F28.A1B1K Popping` | Dry high-heat agitation that bursts the grain's outer skin and changes its shape. |
| `F28.A07GK Scalding` | Revised to a core term directly under `A0BA1 Cooking and similar thermal preparation processes`. |
| `F28.A07GQ Pressure cooking` | Revised to a core term directly under `A0BA1`; do not restrict its meaning to the old steaming grouping. |

Use the specific descriptor only when the treatment is known, relevant and not already implicit. These changes do not permit rebuilding a standard derivative from a raw base plus F28. Current catalogue scope and [[process-validation-rules]] govern the finished code. `A07GP` is named `Steaming without pressure`; its LanguaL attribute is `G0023`, while `A07HH Reheating in the pack` uses `G0040`. (2025 maintenance p14)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p78-83 -->
## Appendix A2 Codes

This is a historical reference to the 2015 Appendix A2. Later name and hierarchy changes, including scalding and pressure cooking above, take precedence when interpreting current candidates. Use the current catalogue for exact membership and scope.

- Generic: `A07HS raw`, `A0C0S unprocessed`, `A0C0R processed`, `A0CHR batch`, `A0CHS continuous`, `A0CHV preserved`, `A066E semi-preserved`.
- Physical division: `A07KT portioning`, `A07KV slicing`, `A07KX dicing`, `A07KY mincing/chopping/cutting`, `A07KZ grating`, `A07LA grinding/milling/crushing`, `A0C6N pulping/mashing`, `A0C0K maceration`.
- Non-nature-changing preservation:
  - Cleaning: `A07JB physical decontamination`, `A0BZG aspiration`, `A0BZL desliming`, `A07JE cleaning`, `A07JF brushing`, `A07JG washing`, `A07JH centrifugal clean`, `A0CSQ sanitizing`
  - Pressure and filtration: `A07JC pascalisation`, `A07JD micro-filtering`
  - Irradiation: `A07JJ irradiation`
  - Cold: `A07KP chilling`, `A07KQ freezing`, `A07KR IQF`
  - Thermal: `A07HT thermisation`, `A07HV pasteurisation`, `A07HX high pasteurisation`, `A07HY UHT`, `A07HZ sterilisation`, `A07JA hot fill`
- Cooking and thermal prep (normally applied directly to the raw commodity; see Processes Applied Directly To Raw Commodities):
  - Water: `A07GF blanching`, `A07GG/GH/GJ/GK/GL` water-cooking, `A07GM stewing`, `A07GP/GQ` steaming
  - Dry heat: `A07GR/GS/GT/GV` frying, `A07GX baking`, `A07GY roasting`, `A0EJY/A07GZ/A07HA` grilling, `A07HC toasting`
  - Other: `A07HB microwave-cooking`, `A0CRA infra-red micronisation`, `A07HD-A07HH` reheating, `A07HJ caramelization/browning`
- Packing and preservation with substances: `A0BYN aseptic filling`, `A0BYP canning/jarring`, `A07JK vacuum-packing`, `A07JP salt`, `A0F2N brining`, `A07JQ/A07JR` sugar-preserving/candying, `A07JS` preserving additives, `A0CER` alcohol, `A07JV` smoking
- Chemical, biological, phase and water change:
  - Chemical: `A07LQ alkalizing`, `A07JM acidifying`, `A07LR bleaching`, `A07JN carbonating`, `A07JT marinating`, `A07KC` pickling, `A0CRH seasoning`
  - Biological: `A07LX hydrolysis`, `A07LT hydrogenation`, `A0CQZ/A07JY/A07JZ/A07KA` fermentation family, `A07KB enzyme treatment`, `A07KD curing`, `A0C6F ripening`, `A0C0L malting`
  - Phase and mechanical: `A07LE aerating`, `A07LY aerosol pressurizing`, `A0CRK stirring`, `A0C0J liquefying`, `A0BZJ condensation`, `A0C0H melting`, `A07LF extrusion`, `A07LG flaking`, `A07LH flattening`, `A07LJ homogenizing`, `A07LK parboiling`, `A07LL puffing`, `A07LM texturing`, `A07XZ instantisation`, `A0C0G gelling`, `A0C0F micronisation`, `A07XY granulation`, `A0BZX pelleting`, `A07LN juicing`, `A07LP coagulating`
  - Drying: `A07KL semi-drying`, `A07KG drying`, `A07KH freeze-drying`, `A07KJ air/heat drying`, `A0C0C spray drying`, `A07KK sun drying`
  - Concentration and dilution: `A07KF concentration`, `A07KM condensed milk`, `A07MQ dilution`, `A07MR reconstitution`, `A07MS soaking`, `A07LV liquid injection`
- Separation, extraction, coating and whole production:
  - Separation: `A0BZY fractionation`, `A0BZH air fractionation`, `A07LB sifting`, `A0EKQ/A07MC/A0C0D` separation, `A0BZN pressing`, `A0BZP filtration`, `A07MD ultrafiltration`, `A07ME reverse osmosis`, `A07MF distillation`, `A07MG fat fractioning`, `A07MH churning`
  - Extraction and refining: `A07MJ/A0BZS/A0BZR/A0BZQ` extraction, `A07MK brewing/infusion`, `A0BZT refining`, `A0CRC rectification`, `A07ML crystallization`, `A07MM lactose reduction`, `A07MN decaffeinating`, `A0BZK depectinising`, `A0CQY degermination`, `A0BZM desugaring`
  - Removal: `A07LC removal of external layer`, `A0BZV polishing`, `A0C0M detoxification`, `A0F0A deodorization`
  - Mixing and coating: `A0CRJ blending`, `A0CRL mixing`, `A07MA filling`, `A07HK breading`, `A07HL battering`, `A07HM glazing/icing`, `A07HN sugar coating`, `A07HP chocolate coating`, `A07HQ nuts coating`
  - Whole production: `A0C00 winemaking`, `A0C01 beer production`, `A0C6E cheesemaking`, `A0C02/A0C06/A0C08/A0C07` oil production, `A0C03/A0C09/A0C0A` grain milling, `A0C0B starch production`, `A0C04 sugar production`, `A0C05 fodder production`, `A0CRB ensiling`, `A0C0E rumen protection`

- When one of these treatments already defines a standard derivative group, do not reconstruct the food from a raw commodity plus `F28`; step back to [[base-term-selection]]. If multiple explicit processes remain plausible, check [[process-validation-rules]] before composing the final code. (EFSA guidance p44, p58; Business Rules `BR16`, `BR19`, `BR26-BR28`)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p42, p56 -->
## Worked Examples

- Before: `fresh sage`. After: `A00YH#F28.A0C0S`. Fresh spices can use `unprocessed` because dried is often default; this is the same "only add what is not implicit" rule described in [[implicit-vs-explicit-facets]]. (EFSA guidance p42)
- Before: `candied citrus peel, chocolate-coated`. After: `A01PS#F04.A034G$F27.A01QE$F28.A07HP`. Add `F28.A07HP` for the coating. (EFSA guidance p56)
- Before: `dried kangaroo meat`. After: `A04MP#F01.A0F2G$F26.A07XE`. Drying is implicit in `A04MP`, so no `F28.A07KG` is added; the derivative-base choice comes from [[base-term-selection]]. (EFSA guidance p49)

## Relevant Policy

- [[policy-contract]] `C03`, `C04`, and `C08` govern this page directly: prefer derivative bases when a standard processed group exists, do not restate implicit processes, and add only process detail that contributes new information.
- [[policy-contract]] `R-DERIV-001`, `R-PROC-001`, `R-PROC-002`, `R-PROC-003`, `TB-001`, and `AP-001` cover the main decision pattern here: raw plus `F28` is not an acceptable reconstruction when the derivative base already exists, and explicit processes must respect implicit/detail ordering and root-scoped ordinal validation.

## Relevant Business Rules

- `BR11`: generic process descriptors are weak and should be replaced with more specific process terms when possible. See [[business-rules]].
- `BR16`: explicit processes cannot be broader than implicit ones. See [[business-rules]].
- `BR19`: derivative-creating processes are not allowed on raw bases. See [[business-rules]].
- `BR26`, `BR27`, and `BR28`: process ordinal conflicts and reconstitution restrictions. See [[business-rules]].

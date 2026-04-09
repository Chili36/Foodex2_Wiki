---
title: "Process Facets"
sources:
  - "EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf"
related:
  - "[[facet-coding-rules]]"
  - "[[base-term-selection]]"
  - "[[code-string-format]]"
last_updated: "2026-04-08"
---

# Process Facets

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p20, p44, p46-47, p58, p78-83 -->
## Rule Of Use

- Add `F28` only when the treatment makes the difference. If the derivative base term already implies the process, do not restate it. Read this together with [[base-term-selection]] when deciding whether the process belongs in the base term or in an explicit facet. (EFSA guidance p44, p46-47, p58)
- `F13-F16` are largely deprecated; use `F28`. The general "implicit vs explicit" boundary is summarized in [[implicit-vs-explicit-facets]], and the string syntax is in [[code-string-format]]. (EFSA guidance p46-47)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p78-83 -->
## Appendix A2 Codes

- Generic: `A07HS raw`, `A0C0S unprocessed`, `A0C0R processed`, `A0CHR batch`, `A0CHS continuous`, `A0CHV preserved`, `A066E semi-preserved`.
- Physical division: `A07KT portioning`, `A07KV slicing`, `A07KX dicing`, `A07KY mincing/chopping/cutting`, `A07KZ grating`, `A07LA grinding/milling/crushing`, `A0C6N pulping/mashing`, `A0C0K maceration`.
- Non-nature-changing preservation:
  - Cleaning: `A07JB physical decontamination`, `A0BZG aspiration`, `A0BZL desliming`, `A07JE cleaning`, `A07JF brushing`, `A07JG washing`, `A07JH centrifugal clean`, `A0CSQ sanitizing`
  - Pressure and filtration: `A07JC pascalisation`, `A07JD micro-filtering`
  - Irradiation: `A07JJ irradiation`
  - Cold: `A07KP chilling`, `A07KQ freezing`, `A07KR IQF`
  - Thermal: `A07HT thermisation`, `A07HV pasteurisation`, `A07HX high pasteurisation`, `A07HY UHT`, `A07HZ sterilisation`, `A07JA hot fill`
- Cooking and thermal prep:
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
- [[policy-contract]] `R-DERIV-001`, `R-PROC-001`, `R-PROC-002`, `TB-001`, and `AP-001` cover the main decision pattern here: raw plus `F28` is not an acceptable reconstruction when the derivative base already exists, and explicit processes must respect implicit/detail ordering.

## Relevant Business Rules

- `BR11`: generic process descriptors are weak and should be replaced with more specific process terms when possible. See [[business-rules]].
- `BR16`: explicit processes cannot be broader than implicit ones. See [[business-rules]].
- `BR19`: derivative-creating processes are not allowed on raw bases. See [[business-rules]].
- `BR26`, `BR27`, and `BR28`: process ordinal conflicts and reconstitution restrictions. See [[business-rules]].

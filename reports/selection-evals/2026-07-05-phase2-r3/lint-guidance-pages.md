---
generated_at: "2026-07-05T16:22:18"
model: "claude-sonnet-4-6"
pages_linted:
  - base-term-selection.md
  - implicit-vs-explicit-facets.md
  - process-facets.md
---
# FoodEx2 Wiki Lint Review

**Scope:** `base-term-selection.md`, `implicit-vs-explicit-facets.md`, `process-facets.md`
**Focus check:** `select_when` accuracy, intra-set contradictions, prompt-context risks

---

## 1. Verdict

**Material issues found.** One P1, six P2, and four P3 findings. The most urgent issue is a structural prompt-context mismatch on `process-facets.md`: its `select_when` promises specific-code lookup but the `prompt_projection_policy` omits the entire code list at runtime, making the page's primary value inaccessible in coding contexts. Several P2 issues concern citation traceability, overgeneralised example language, and an underselling index summary on the high-traffic hub page `implicit-vs-explicit-facets.md` that is already a documented selector miss.

---

## 2. Findings

### P1

---

**P1-01 — `process-facets.md`: `select_when` promises specific-code lookup; runtime projection delivers none**

`select_when` states the page is for deciding *"which specific process descriptor applies — heating, preservation, drying, fermentation, coating, milling, or similar transformations."*

The `prompt_projection_policy` lists `"appendix a2 codes"` in `omitted_sections`. The runtime `prompt_projection` therefore contains exactly two sentences of rule-of-use guidance and no codes whatsoever. Any coding session that retrieves this page via `context-pack` or `page-evidence` to answer *"which F28 code should I use for pasteurisation / freeze-drying / fermentation?"* gets nothing actionable.

The `index.md` entry reinforces the mismatch: *"Compact reference for Appendix A2 process facet codes and when to use them."* This description will cause the selector to prefer this page for specific-code questions — and then fail to deliver.

There is no other page in the wiki that carries the F28 code catalogue. This is a latent source of wrong or missing process descriptors in generated code strings.

---

### P2

---

**P2-01 — `implicit-vs-explicit-facets.md`: VMPR override claim is cited against Chemical Monitoring guidance**

> *"In VMPR workflows, explicit facets can override the implicit categorisation if they are reported, so unnecessary explicit repetition is not neutral. See [[vmpr-foodex2]] for the domain-specific overlay. (ChemMon 2026 p33)"*

The statement is scoped to VMPR, but the parenthetical traces it to the Chemical Monitoring 2026 guidance (p33). ChemMon is not the authority for VMPR behaviour. If the claim genuinely originates in ChemMon 2026 as a general principle that extends to VMPR, that reasoning is not stated. If it originates in VMPR guidance, the citation is wrong. Either way, a reviewer cannot follow the evidence chain. A downstream model treating this as authoritative may apply the VMPR override rule more broadly (or attribute it to the wrong regulatory context).

---

**P2-02 — `process-facets.md`: "largely deprecated" creates undocumented exceptions for F13–F16**

> *"`F13-F16` are largely deprecated; use `F28`."*

The qualifier *"largely"* implies there are valid surviving uses of F13–F16, but none are documented anywhere on this page or cross-referenced to another page. A model reading this may attempt to use F13–F16 in edge cases it invents, or may fail to flag a submitted code that erroneously uses them. The safe statement is either *"deprecated; use `F28`"* (if no exceptions exist) or *"largely deprecated; the surviving valid uses are: [list]"*.

---

**P2-03 — `process-facets.md` worked example: "dried is often default" for spices risks overgeneralisation**

> *"Fresh spices can use `unprocessed` because dried is often default"*

This is an example-specific observation about `A00YH` (sage), presented as a principle about spice coding. The phrase *"often default"* invites a downstream model to infer that all spices or herbs carry an implicit dried-state, which may not hold for every term. No hedge is present (e.g., *"for this term"* or *"check the implicit facets of the specific term"*). The worked examples section is included in `raw_content` but excluded from `prompt_projection` at runtime, so a model would not encounter it directly — but this example is cited in Rule-of-Use cross-references and could propagate into reasoning.

---

**P2-04 — `process-facets.md`: No routing to domain-specific process obligations (CHEMMON12 / F33, VMPR Plan 3)**

The page positions itself as the primary process-facet reference. `implicit-vs-explicit-facets.md` mentions the CHEMMON12 mandatory-F33 exception and routes to `contaminants-foodex2`. `process-facets.md` makes no reference to F33 at all, and does not route to contaminants, VMPR, or additives overlays where process facets have domain-specific mandatory or forbidden uses. A session that retrieves only `process-facets.md` for a contaminants or VMPR process question gets no signal that domain overlays exist.

---

**P2-05 — `implicit-vs-explicit-facets.md`: index summary undersells operational scope; contributes to documented selector miss**

`index.md` entry: *"Distinguishes inherited facet information from coder-supplied facet detail."*

The page also carries: the F27-vs-F04 routing decision for derivatives; the derivative reconstruction prohibition (AP-001 / BR19); the VMPR override note; the CHEMMON12 mandatory-F33 exception; and the F01 fallback rule for missing derivatives. These are operational decisions, not just conceptual distinctions. The thin summary accurately describes only the framing section, not the page's function.

This is not solely a cleanup issue: the evaluation log notes SEL-0011 (`implicit-vs-explicit-facets.md`) as a documented residual selector miss. An index summary that describes the page as a conceptual distinction page makes it less likely to be retrieved for operational questions about F27 vs F04 routing or derivative reconstruction errors.

---

**P2-06 — `base-term-selection.md` and `process-facets.md` `select_when` overlap on "process in base term or explicit?"**

`base-term-selection.md` `select_when`: *"deciding raw versus derivative versus composite"*
`process-facets.md` `select_when`: *"must decide whether it belongs in the base-term choice or as an explicit process facet"*

The second formulation is a sub-case of the first. A query like *"should this smoking step be in the base term or as F28?"* matches both `select_when` hints with similar weight. When both pages are retrieved, context is consumed but the guidance is additive. When only one is retrieved (more likely given pack size), the user may get base-term selection rules without F28 rule-of-use, or vice versa. The `select_when` for `process-facets.md` could be sharpened to make clear it applies *after* the base-term decision has been made.

---

### P3

---

**P3-01 — `implicit-vs-explicit-facets.md`: "narrow tolerated fallback" for F01 on derivatives is semantically opaque**

> *"F01 may be a narrow tolerated fallback only when it clearly refers to the single source commodity and `F26.A07XE` marks the missing detailed term. Do not generalise this into ordinary `F01` use on derivatives."*

"Tolerated" is not defined: does it mean the validator accepts it, that it passes BR05/BR07, or only that the coding community treats it as an acceptable workaround? A downstream model cannot determine the validation status of this pattern. The footnote source is ANSES guidance p49–50, not EFSA guidance or the validator — which makes it guidance-tier only. Clarifying whether this pattern passes or triggers a warning from the sibling validator would remove ambiguity.

---

**P3-02 — `implicit-vs-explicit-facets.md`: "Derivative (broad group)" table row could be read as a distinct food type**

The `When To Add An Explicit Facet` table has separate rows for `Derivative` and `Derivative (broad group)`. These are cases of the same food type, not distinct types. A downstream model extracting rows from this table could infer three food types (raw, derivative, composite, plus a fourth "broad derivative"), misaligning with the three-class model used throughout the rest of the wiki.

---

**P3-03 — `base-term-selection.md`: composite dominant-ingredient priority list presented without scope hedge**

> *"If a composite has no clear dominant ingredient, use this priority: meat, fish, cheese/dairy, egg, legume, potato, cereal, fruit, vegetable."*

The list contains nine categories. No hedge is present about composites that do not match any category (e.g., sugar-dominant confectionery, beverages, condiments). The list may be exhaustive for the relevant EFSA contexts, but without a statement such as *"for composites falling within these categories"* or a pointer to what to do when none match, a model may treat it as universal or silently fail on out-of-list composites.

---

**P3-04 — `base-term-selection.md`: F26 used in worked examples without in-context definition**

The worked examples use `F26.A07XE` but the prompt projection for this page never defines what F26 is. The surrounding prose explains that `A07XE` means *"other"* but does not define the facet family or its purpose. Since `worked examples` is omitted from prompt projection, the examples don't appear at runtime, but the F26 usage appears in tie-break rules prose (*"add `F26.A07XE` (`other`)"*) without definition. A model unfamiliar with FoodEx2 encoding would need to follow the link to `facet-coding-rules.md` or `term-type-facet-constraints.md`, neither of which is guaranteed to be in the same context pack.

---

## 3. Suggested Follow-ups

1. **P1-01 remediation (requires semantic judgment):** Decide whether the `"appendix a2 codes"` omission from `process-facets.md` runtime context is intentional (e.g., to reduce token cost) or an oversight. If intentional, the `select_when` and index summary for this page must be rewritten to reflect that the page delivers only decision rules at runtime, not code lookup. If the omission is an oversight, `"appendix a2 codes"` should be removed from the omitted_sections policy for this page (or the section renamed to something not on the blocklist). Either way, the select_when phrase *"which specific process descriptor applies"* should be removed or replaced until code lookup is available at runtime.

2. **P2-01 citation fix:** Check VMPR guidance for the explicit-facet override statement. If the claim originates in VMPR guidance, replace `(ChemMon 2026 p33)` with the correct VMPR source citation. If ChemMon 2026 p33 is genuinely the source, add a sentence explaining why ChemMon governs VMPR behaviour here.

3. **P2-02 F13–F16 clarification:** Confirm with validator ICT source whether any valid F13–F16 uses survive. Replace *"largely deprecated"* with either *"deprecated"* or a documented list of exceptions.

4. **P2-05 index summary:** Rewrite `implicit-vs-explicit-facets.md` index entry to surface the operational routing decisions (F27 vs F04, derivative reconstruction prohibition, VMPR override, CHEMMON12 exception) so the selector retrieves it for operational questions, not only conceptual distinction questions.

5. **P2-06 select_when sharpening:** Revise `process-facets.md` `select_when` to anchor it explicitly *after* the base-term class has been determined, e.g., *"…after the base term type has been fixed and the question is which explicit F28 descriptor (if any) applies to a known treatment step."*

6. **P3-01 tolerated-fallback clarification:** Add a parenthetical or note specifying the validator behaviour for F01 on derivatives (warning, error, or silent), and confirm whether the pattern is ANSES-specific guidance or EFSA-endorsed.

---

## 4. Notes On Non-Issues

- **Triple repetition of "do not rebuild raw + F28"** across all three pages: consistent, not contradictory. Redundancy is appropriate given the pages are retrieved independently and the rule is the most common anti-pattern.
- **Preservation tie-break ordered list in `base-term-selection.md`**: The ordered list (puree/textured → smoked) is sourced against EFSA guidance p18 and is consistent with how the 2015 guide presents priority. No contradiction with siblings.
- **select_when for `base-term-selection.md`**: Accurate, specific, and clearly distinguishable from sibling page hints.
- **select_when for `implicit-vs-explicit-facets.md`**: Accurate to the page's framing section, though the index summary issue (P2-05) is separate.
- **F26.A07XE usage in worked examples**: Consistent across both pages that use it. No contradiction.
- **CHEMMON12 F33 exception**: Correctly flagged as an exception in `implicit-vs-explicit-facets.md` with a routing pointer. No conflict with the general "do not restate implicit" rule.
- **Derivative table two-row structure (P3-02)**: The *content* of both rows is internally consistent; the risk is structural/presentational only.

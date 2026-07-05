---
generated_at: "2026-07-05T16:25:11"
model: "claude-sonnet-4-6"
pages_linted:
  - business-rules.md
  - validation-rules.md
  - structural-validation.md
  - term-type-facet-constraints.md
  - process-validation-rules.md
---
# FoodEx2 Wiki Lint Review — Validation Layer (5 Pages)

**Pages reviewed:** `business-rules.md`, `validation-rules.md`, `structural-validation.md`, `term-type-facet-constraints.md`, `process-validation-rules.md`

---

## 1. Verdict

The validation layer is internally coherent and well-sourced for its core claims. The deterministic doctor found zero issues. However, several findings warrant attention, primarily around severity-table inconsistencies between sibling pages, a `select_when` specificity gap, overgeneralisation risks from example material, weak sourcing for the ordinal-group taxonomy, and a `select_when` / content alignment issue on `validation-rules.md`. Two findings are P1 because they could cause a downstream model to misread which severity a rule carries or to misapply the ordinal-group table as exhaustive.

---

## 2. Findings

### P1-A — Severity table inconsistency: `BR19` and `BR20`/`BR21` differ between `business-rules.md` and `validation-rules.md`

**Pages:** `business-rules.md` (Severity Model table), `validation-rules.md` (Severity Model table)

`business-rules.md` lists the `ERROR` bucket as:
> `BR17`, `BR19`, `BR20`, `BR21`, `BR25`, `BR29`, `BR30`, `BR31`

`validation-rules.md` lists the `ERROR` bucket as:
> `BR29-BR31`

`BR17`, `BR19`, `BR20`, `BR21`, and `BR25` appear as `ERROR` in the canonical page but are **absent from the ERROR row** in the overview page, which only names `BR29-BR31` there. `validation-rules.md` does place `BR19-BR21` in the `HIGH` row:
> `BR01`, `BR03-BR08`, `BR13`, `BR16-BR17`, `BR19-BR21`, `BR24-BR28`

This directly contradicts `business-rules.md`, where `BR19`, `BR20`, and `BR21` are `ERROR`, and `BR17` and `BR25` are `ERROR`. A model reading only `validation-rules.md` would treat these as `HIGH` (hard warning, "validation fails") rather than `ERROR` (blocking). While the practical fail-state may be the same, the classification divergence undermines the stated authoritative hierarchy and creates a real risk if a downstream consumer reasons about severity levels precisely (e.g., "this is only HIGH, not ERROR").

**Risk:** Model or developer may quote `validation-rules.md` severity for `BR19`/`BR17` incorrectly.

---

### P1-B — Ordinal-group table in `process-validation-rules.md` reads as exhaustive but has no source citation and may be incomplete

**Page:** `process-validation-rules.md`, Ordinal Groups table

```
| `1.x` | Heating methods | Mutually exclusive within the group |
| `2.x` | Preservation | Mutually exclusive within the group |
| `3.x` | Physical treatments | Mutually exclusive within the group |
| `0` | Non-exclusive processes | Can coexist with other groups |
```

Source attribution is `(Compact JSON; BR26-BR27)`. The table implies exactly four ordinal categories exist and are complete. If FoodEx2 process ordinals extend beyond `0`, `1.x`, `2.x`, `3.x` (e.g. groups `4.x` or beyond), the table is wrong. The sibling validator's known `BR26` silence means this table cannot be cross-checked against live validator output. No EFSA PDF source is cited; the only attribution is `BUSINESS-RULES-COMPACT.json`, which is a derived artefact, not an authoritative EFSA source.

A downstream model using this table to reason about whether two processes conflict could confidently declare processes in unlisted groups as "non-exclusive" when they may not be. The `BR26` known-silence warning is present but positioned *after* the table rather than as a caveat *on the table itself*.

**Risk:** Wrong process-combination judgments for ordinal groups not listed or for an incomplete taxonomy.

---

### P2-A — `validation-rules.md` `select_when` does not match its content scope

**Page:** `validation-rules.md`, frontmatter

```
select_when: >-
  The case needs orientation to how validation works overall: the two-layer
  structure of structural checks then business rules, the severity model, which
  rules block a code outright, and practical batch-review checks — when the
  question is why a code would fail rather than one specific rule.
```

The page also contains a substantial **Practical Dataset Checks** section sourced from ANSES guidance (feed/food mismatches, infusion ambiguity, `F04` misuse, `F01` on mixed raw bases). This section is not reflected in the `select_when` hint at all. A selector reading the hint will not recognise that this page also covers batch-dataset QA patterns, making it likely to miss the page for queries about dataset review or QA workflows.

Separately, the `select_when` phrase "when the question is *why* a code would fail" is narrow and slightly misleading — the practical checks section covers proactive coding review, not post-failure diagnosis.

---

### P2-B — `structural-validation.md` `select_when` does not mention implicit-facet removal, which is one of the page's most distinctive topics

**Page:** `structural-validation.md`, frontmatter

```
select_when: >-\n  The case involves the pre-business-rule structural gate: base-term length and\n  existence, facet parsing, descriptor-to-category membership, automatic\n  removal of implicit facets, and duplicate or single-cardinality detection\n  that reject a code before any policy rule runs.
```

Implicit-facet removal *is* mentioned but buried in a list. The page's closest sibling `validation-rules.md` also mentions implicit-facet cleanup ("structural checks cover … implicit-facet cleanup") in its own body. A retrieval model could route implicit-facet questions to `implicit-vs-explicit-facets.md` (36 incoming links, strong hub) and never reach `structural-validation.md` because the `select_when` does not signal that *automatic removal as a mechanical validator step* (distinct from the conceptual question on `implicit-vs-explicit-facets.md`) lives here. The two pages cover different aspects but retrieval may conflate them.

---

### P2-C — `business-rules.md` `select_when` uses "validator data-status caveats" language that is not distinguishable from `process-validation-rules.md` for BR19/BR26 queries

**Pages:** `business-rules.md` and `process-validation-rules.md`, frontmatter `select_when` fields

`business-rules.md`:
> "whether a construction is a blocking error, a hard or soft warning, plus validator data-status caveats such as the disintegration physical-state, forbidden-process, and mutually-exclusive-process boundaries"

`process-validation-rules.md`:
> "The case involves combining or checking process facets and needs the process-specific validator logic: mutually exclusive ordinal groups, explicit-versus-implicit process detail level, forbidden derivative-creating processes on raw bases, and reconstitution limits"

Both hints fire on queries about "forbidden processes on raw bases" or "mutually exclusive process combinations." Since `business-rules.md` is the canonical reference and `process-validation-rules.md` is the operational elaboration, a retrieval model could return either or both, which is noisy but not catastrophic. The differentiation signal that `business-rules.md` is for *severity and rule identity* while `process-validation-rules.md` is for *operational application* is not clearly encoded in the hints.

---

### P2-D — `validation-rules.md` severity table in `HIGH` row lists `BR19-BR21` but body prose only discusses `BR20` and `BR21` under "High-Impact Blocking Rules" — `BR19` is absent from that section

**Page:** `validation-rules.md`, Severity Model table and High-Impact Blocking Rules section

The `HIGH` row includes `BR19`, but the High-Impact Blocking Rules prose section lists only `BR03`, `BR04`, `BR17`, `BR20`, `BR21`, and `BR29-BR31`. `BR19` — the forbidden-processes-on-raw ERROR rule — has no corresponding prose callout despite being operationally critical. This is inconsistent with how the page handles `BR20` and `BR21` (which both appear in the table and in prose). A model relying on the prose section for "what are the most important rules?" would silently omit `BR19`.

This also echoes P1-A: `BR19` is `ERROR` in `business-rules.md` but `HIGH` in `validation-rules.md`'s table, *and* then absent from the high-impact prose section — three inconsistent representations across one cluster.

---

### P2-E — `term-type-facet-constraints.md` Core Matrix column "No `F01` or `F04`" for raw terms may be overstated

**Page:** `term-type-facet-constraints.md`, Core Matrix table

> `r` raw commodity … No `F01` or `F04`

The prohibition on `F04` for raw terms is listed as a hard restriction in the matrix. `business-rules.md` BR12 says:
> `F04` should be used only for minor ingredients in those term types [raw and derivative]

BR12 severity is `LOW` (advisory). The Core Matrix presents the restriction as a definitive "No `F04`" without qualification, which overrepresents a soft advisory as a hard structural ban. A downstream model reading the matrix could reject valid minor-ingredient uses of `F04` on raw terms (e.g. a coating or flavour) that BR12 permits with a LOW warning.

---

### P2-F — `process-validation-rules.md` Worked Examples include a generalised claim that may be overgeneralised

**Page:** `process-validation-rules.md`, Worked Examples

> "Before: cereal grains + flaking process on a raw base. After: invalid, `BR19`; use the flaked cereal derivative."

Flaking is used as the paradigmatic "BR19" example. A model pattern-matching this example could overgeneralise and assume any physical-structure-altering process on a raw grain is always `BR19`-invalid, potentially conflating with BR13 (physical state) or misapplying to non-grain raw commodities where the specific process may have different BR19 coverage status. The example is not wrong, but no disclaimer flags it as illustrative of one confirmed case rather than a general pattern. The stale-data caveat (BR_Data.csv frozen 2020-05-20) makes this especially risky for newer taxonomy roots.

---

### P3-A — `structural-validation.md` sources list `docs/VBA_STRUCTURAL_RULES_SUMMARY.md` which is not in the main wiki index or graph

**Page:** `structural-validation.md`, frontmatter sources

```
sources:
  - "docs/VBA_STRUCTURAL_RULES_SUMMARY.md"
```

This source appears in no other page's source list and is absent from the wiki index. It is not clear whether it is an internal derived document, a committed file, or a transient artefact from the VBA validator. If it is not a stable committed file, citations to it are not reproducible. The same source appears in `process-validation-rules.md` as `docs/VALIDATION_RULES_SUMMARY.md` — a different filename — adding ambiguity.

---

### P3-B — `business-rules.md` body section heading "Physical State Creates Derivatives" does not match the operational reading stated inside it

**Page:** `business-rules.md`, BR13 section heading

Heading: `## BR13: Physical State Creates Derivatives`

But the body immediately clarifies:
> "It does not mean that every `F03` physical-state descriptor is forbidden on raw commodities."

The heading's plain reading ("physical state creates derivatives") implies a blanket rule, directly contradicting the nuanced content. Any context window that receives only the heading (e.g. a heading-indexed retrieval) gets a misleading signal. The heading should qualify this (e.g., "BR13: Disintegration Physical State Creates Derivatives").

---

### P3-C — `validation-rules.md` Practical Dataset Checks section cites ANSES page numbers (`p89`, `p90`, `p91`, `p92`) but the source PDF is not named precisely

**Page:** `validation-rules.md`, Practical Dataset Checks

> (ANSES guidance p89), (ANSES guidance p90), (ANSES guidance p91), (ANSES guidance p92)

The frontmatter sources include `"FoodEx2 codification guidance_2025_12_v3.pdf"`. The inline citations use the informal label "ANSES guidance" without naming the specific document. A reviewer cannot confirm whether page 89 of the v3 PDF matches these claims without identifying which PDF edition is meant. If the PDF is updated, the page numbers become stale. Stronger citation form would be: `(FoodEx2 codification guidance_2025_12_v3.pdf p89)`.

---

## 3. Suggested Follow-ups

1. **[P1-A]** Reconcile the severity tables across `business-rules.md` and `validation-rules.md`. The canonical page (`business-rules.md`) should be the single authority; `validation-rules.md` should either reproduce the same table or explicitly state "see business-rules.md for authoritative severity assignments." Do not silently move `BR17`, `BR19`, `BR20`, `BR21`, `BR25` between `ERROR` and `HIGH` across pages.

2. **[P1-B]** Add a source citation for the ordinal-group taxonomy in `process-validation-rules.md` that traces back to an EFSA PDF or ICT source, not just the derived JSON. Add a table footnote noting that the group list reflects the Compact JSON artefact and may be incomplete; flag that BR26 silence means unknown groups cannot be validated against live output.

3. **[P2-A]** Extend `validation-rules.md` `select_when` to include batch-dataset QA and proactive review patterns, not just failure diagnosis. Consider: "… or when reviewing a dataset batch for common coding pattern errors."

4. **[P2-B]** Consider differentiating `structural-validation.md` `select_when` from `implicit-vs-explicit-facets.md` more sharply by naming the *mechanical removal step* explicitly: "the validator's automatic removal of facets already implicit in the base term" vs. the conceptual question of what counts as implicit.

5. **[P2-C]** Add one distinguishing phrase to each `select_when`: `business-rules.md` → "to look up the authoritative severity of a specific BRxx rule"; `process-validation-rules.md` → "to apply the process-specific rules operationally when coding."

6. **[P2-D]** Add a `BR19` callout to the High-Impact Blocking Rules prose section in `validation-rules.md`, consistent with how `BR20`/`BR21` are treated there.

7. **[P2-E]** Add a qualification to the `r` raw commodity row in `term-type-facet-constraints.md`'s Core Matrix: change "No `F01` or `F04`" to "No `F01`; `F04` discouraged (BR12, LOW — minor ingredient use may be valid)" to reflect the advisory rather than blocking nature of BR12.

8. **[P2-F]** Add an illustrative disclaimer to the cereal/flaking worked example in `process-validation-rules.md`: note that BR19 coverage depends on BR_Data.csv (frozen 2020-05-20) and this example is a confirmed case, not a general pattern.

9. **[P3-A]** Confirm `docs/VBA_STRUCTURAL_RULES_SUMMARY.md` is a stable, committed file. If it is, register it in the wiki's source layer or log. If not, replace citations with the closest stable alternative.

10. **[P3-B]** Rename the BR13 section heading in `business-rules.md` to "BR13: Disintegration Physical State Creates Derivatives" or similar to match the nuanced content and prevent heading-only retrieval from returning a misleading signal.

11. **[P3-C]** Replace informal "ANSES guidance pXX" citations in `validation-rules.md` with the full filename from frontmatter sources, e.g. `(FoodEx2 codification guidance_2025_12_v3.pdf p89)`.

---

## 4. Notes On Non-Issues

- **Internal link graph**: All five pages are well-connected; no orphan risk. Cross-links between `business-rules.md ↔ process-validation-rules.md`, `business-rules.md ↔ term-type-facet-constraints.md`, and `validation-rules.md ↔ structural-validation.md` are appropriately bidirectional.

- **BR13 seven-code list**: The list (`A06JD`, `A06JE`, `A06JF`, `A06JG`, `A07Y2`, `A07Y3`, `A07Y4`) is consistent across both `business-rules.md` and `term-type-facet-constraints.md`. The operational reading ("not a blanket F03 ban") is present in all three relevant pages.

- **BR19+ extension mechanism**: Documented consistently across `business-rules.md` and `process-validation-rules.md`; the `STRICT_ICT_PARITY=1` flag is only in `business-rules.md`, which is appropriate since it is an operational implementation detail rather than guidance content.

- **BR26 known-divergence**: The caveat is present and consistent in all pages that mention BR26. The distinction between ICT silence and sibling-validator silence (different implementation cause, same outcome) is correctly maintained.

- **Prompt projection omissions**: The omitted sections (`appendix a2 codes`, `authority`, `worked examples`, etc.) are well-chosen; the retained sections for all five pages contain the operationally critical content and do not leave critical rules out of context-pack projection.

- **`select_when` sibling differentiation**: `structural-validation.md`, `term-type-facet-constraints.md`, and `process-validation-rules.md` are meaningfully differentiated from each other in their `select_when` hints. The business-rules/process-validation overlap (P2-C) is the only non-trivial collision.

- **Source traceability for BR rules**: The primary sources (`BUSINESS-RULES.md`, `BUSINESS-RULES-COMPACT.json`) are consistently cited for all BR-rule content. The chain from validator implementation to wiki page is traceable.

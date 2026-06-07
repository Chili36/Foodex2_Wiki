# VMPR blood — model cross-comparison

**Date:** 2026-06-06
**Question:** Is the under-coding of VMPR blood samples a *prompt* problem or a *model* problem?

## Setup
Four VMPR blood/plasma/serum samples coded through the live FoodEx2 classifier (Document Chat `/chat`, `mode=foodex2`, `use_wiki=true`, `reporting_domain=vmpr`) across six coder models. Same prompt, same wiki, same candidates; the only variable is the coder.

- **Wiki state:** the **depersonalized** `vmpr-foodex2.md` — i.e. *after* removing the overfit anti-pattern that named the exact wrong codes ("do not choose `A0F1T` / 'other slaughtering products'"). The wiki states the rule positively (blood/serum/plasma are non-food VMPR matrices → `A0C60` + F01 + F02, ChemMon 2025/2026 p36). The `vmpr-foodex2.md` page was selected in **every** run, so retrieval is constant.
- **Catalogue:** live `mtx_monitoring_openai_current` (MTX v17.1).
- **Scoring:** `A0C60` "Non-food animal-related matrices" = the ChemMon reporting **convention** (correct). `A0F1T` "Animal blood" = a *valid, VMPR-reportable* alternative (type `r`) — **not** an error, just not the convention. So this measures convention-adherence, not validity.

## Base-term verdict (cross-table)

| Blood sample | gemini-3.5-flash | gpt-5.4 | claude-sonnet-4-6 | mistral-large-2512 | gpt-oss-120b | deepseek-v4-pro |
|---|---|---|---|---|---|---|
| Cattle – blood/serum | A0C60 ✓ | A0C60 ✓ | A0F1T ✗ | A0F1T ✗ | A0F1T ✗ | A0C60 ✓ |
| Pig – blood/plasma | A0C60 ✓ | A0C60 ✓ | A0C60 ✓ | A0C60 ✓ | A0F1T ✗ | A0F1T ✗ |
| Horse – blood/plasma | A0F1T ✗ | A0C60 ✓ | A0C60 ✓ | A0F1T ✗ | A0F1T ✗ | A0F1T ✗ |
| Chicken – blood | A0F1T ✗ | A0C60 ✓ | A0F1T ✗ | A0F1T ✗ | A0F1T ✗ | A0F1T ✗ |
| **A0C60 /4 (convention)** | **2** | **4** | **2** | **1** | **0** | **1** |

## Full constructed codes

| Model | Cattle blood/serum | Pig blood/plasma | Horse blood/plasma | Chicken blood |
|---|---|---|---|---|
| **gpt-5.4** | A0C60#F01.A0F1V$F02.A0CEY | A0C60#F01.A01RG$F02.A0CEX | A0C60#F01.A0B9Z$F02.A06AL | A0C60#F01.A057Z$F02.A06AL |
| gemini-3.5-flash | A0C60#F01.A057E$F02.A0CEY | A0C60#F01.A057F$F02.A06AL | A0F1T#F01.A0B9Z | A0F1T#F01.A057Z$F21.A0C7G |
| claude-sonnet-4-6 | A0F1T#F01.A057E$F02.A0CEY | A0C60#F01.A01RG$F02.A0CEX | A0C60#F01.A0B9Z$F02.A06AL | A0F1T#F01.A057Z |
| mistral-large-2512 | A0F1T#F01.A057E$F02.A0CEY | A0C60#F01.A057F$F02.A06AL | A0F1T#F01.A0B9Z$F02.A0CEX | A0F1T#F01.A057Z |
| deepseek-v4-pro | A0C60#F01.A057E$F02.A0CEY | A0F1T#F01.A01RG$F02.A0CEX | A0F1T#F01.A0B9Z$F02.A0CEX | A0F1T#F01.A057Z$F26.A07XE |
| gpt-oss-120b | A0F1T#F02.A0CEY | A0F1T#F01.A057E | A0F1T | A0F1T#F01.A057Z |

## Findings
- **It's a model problem, not a prompt problem.** Same prompt + same wiki, and **only gpt-5.4 gets all four** (4/4), consistently. The other five range 0–2/4. The knowledge + prompt are *sufficient* (gpt-5.4 proves it); applying the convention over the tempting valid `A0F1T` candidate is a reasoning/instruction-following task most coders here fail.
- **Capability cliff:** gpt-5.4 4/4 ≫ gemini/sonnet 2/4 > mistral/deepseek 1/4 > gpt-oss-120b 0/4. gpt-oss also emitted facet-light/malformed codes (e.g. `A0F1T` with no F01 source).
- **The fix is model choice, not more prompt text** — adding wiki/prompt text aimed at our observed failures is the teaching-to-the-test trap (which is what we removed to get this clean read).

## Caveats
- **n = 4, single run per cell** — indicative, not statistical.
- **gemini run-to-run variance:** on the *contaminated* wiki (with the "don't use A0F1T" anti-pattern) it scored **3/4**; cleanly it ran **1–2/4** across runs. Removing the overfit dropped its score — that drop is what exposed the contamination and reframed this as a model issue.
- `A0F1T` is a valid VMPR code throughout — none of these are catalogue-invalid; they're convention choices.

## Related
- `ASK_ABLATION_REPORT.md` / `ASK_ABLATION_DECK.md` — the brief-vs-no-brief ablation.
- DMT test suite: `testdata/foodex2_masterlist_suite.json` (228 cases, `is_food` oracle) + `scripts/run_foodex2_masterlist_check.py` in the repo.

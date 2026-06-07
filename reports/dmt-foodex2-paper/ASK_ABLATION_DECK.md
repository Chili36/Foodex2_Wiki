---
marp: true
theme: default
paginate: true
title: Adding knowledge to FoodEx2 classification
---

# Adding knowledge to FoodEx2 classification

### What knowledge do we actually need to add — and which models are good enough to do it cheaply?

DMT FoodEx2 ablation · 5 coders × 4 conditions × 3 domains · 2026-05-31

---

## The question

FoodEx2 classification = **pick from retrieved candidates**.
But some correct answers are **never in the candidates**.

- The coder **always** gets the **curated wiki rule-pages** (they replaced the static prompt).
- The real question: when candidates *and* those pages fall short, do we **add a synthesised brief** — and **how cheaply?**

Layers of knowledge: **candidates** → **wiki rule-pages (always)** → **optional synthesised brief — the lever under test.**

> **And the brief isn't free: adding the ask ≈ 12.5k tokens/query** (measured; wiki LLM-synthesis — the RAG forms ≈ ⅓ that, ~4k). **That token cost is the basis of this study — is *adding the ask* worth ~12.5k, and where?**

---

## The four conditions — all share the wiki rules; they differ in the *added brief*

**Every condition** gives the coder: **candidates** + the **curated wiki pages** (chosen by the wiki page-picker). *Those pages ARE the FoodEx2 rules — there is no static rules prompt; `off` uses them too.* The conditions differ only in an **extra synthesised advisory brief** layered on top:

| Condition | Added advisory brief | Brief retrieval backing |
|---|---|---|
| **off** | none — wiki pages only | — |
| **wiki** | wiki **LLM-synthesis** (`/wiki/ask`) | curated wiki (LLM page-selector) |
| **wiki RAG** | Qdrant synthesis (`/wiki/ask-rag`) | **curated wiki markdown** |
| **source RAG** | Qdrant synthesis (`/wiki/ask-rag`) | **raw EFSA source PDFs** |

→ We test the **advisory-brief layer**, *not* "wiki vs no-wiki" — the wiki rules are present throughout. wiki RAG ≠ source RAG (different corpora).

---

## How DMT classifies — the pipeline under test

```
food description (any language)
   ▼  Deconstruct (LLM)      translate + split into base + facet sub-queries
   ▼  Retrieve candidates    parallel Qdrant search → merged candidate list (MTX catalogue)
   ▼  Wiki page-pick         curated wiki pages = the FoodEx2 RULES
   │                         ALWAYS injected — there is NO static "how FoodEx2 works" prompt
   ▼  [ + advisory brief ]   OPTIONAL synthesis on top (the 3 brief conditions)
   ▼  Coder LLM              template = thin task instructions + {{wiki rules}} + candidates
   ▼  FoodEx2 code           e.g. A0C60#F01.A056Y$F02.A0CEX
```

**The ablation toggles only the advisory brief.** Candidates + **wiki rules** + template are held constant — so `off` is *"wiki rules, no synthesised brief,"* not *"no wiki."*

---

## Experimental design

- **5 coders × 4 conditions × 3 suites ≈ 520 coder runs** (+ briefs), checkpointed per item.
- **Candidates frozen per item** — deconstruct + search run *once*, reused across all 4 conditions → the *only* thing that varies within an item is the brief → clean isolation of its effect.
- **Fairness verified** — thinking ON for every capable coder (gemini 8k budget · gpt-5.4 medium effort · opus adaptive). No model handicapped.
- **Brief answerer fixed** (claude-sonnet-4-6) → brief differences reflect the *retrieval backing*, not the answerer.

---

## Suites & scoring

**Three domains, by design:**
- **Consumption** — 12 cases from the Nutrients 2024 SCAI children's food-consumption paper.
- **Monitoring** — 4 cross-domain probes (sheep urine, wild-boar plasma, fish liver, dried chili).
- **Extension** — 10 realistic items from the EFSA/DMT monitoring masterlist (Swedish names, 5 domains).

**How:** a harness drives the **live DMT endpoints** (`/search`, `/wiki/ask` + `/wiki/ask-rag`, `/execute-prompt`).

**Scored on:** base-correct + facet recall / family vs a **grounded reference** (paper + catalogue-verified — *not* blind gold) · **catalogue-validity** of every code · **change-detection** across conditions.
*Caveat:* reference ≠ gold — near-synonym / wrong-group cases score as misses.

---

## Thread 1 — "Sheep urine": the answer retrieval can never reach

Correct base `A0C60` (non-food animal matrix) is **not in the candidate pool** — a food-tuned catalogue returns *food* terms (sheep milk, offal, kidney).

| | off | wiki | wiki RAG | source RAG |
|---|---|---|---|---|
| **5/5 coders** | A021H/A057G ✗ | 3/5 ✓ | **5/5 ✓** | **5/5 ✓** |

- **off (candidates + wiki rule-pages): 0/5** — even *with* the wiki pages, every model returns a wrong *food* term.
- **The synthesised brief is the only fix** — it adds the rule the page-selection missed → flips all 5 coders to `A0C60`.
- Proves: a coder **can** adopt a base that was never a candidate, when the brief supplies the rule.

→ Framing discovery: **some answers need knowledge *synthesised in* — beyond both retrieval and the static rule-pages.**

---

## Thread 2 — Monitoring: is the knowledge base needed beyond edge cases?

Realistic monitoring data (masterlist + cross-domain probes), 5 domains:

- **Mostly edible matrices** (fish, liver, meat, spice) → base **is** retrievable → brief is a wash.
- **Extension system-validity:** 51 codes, **0 invalid**; **8/10 items unanimous** base across all 5 coders.
- Brief **decisive only on sheep urine** (off 0/5 → brief 5/5 → `A0C60`).
- **Wild-boar plasma:** models pick `A0F1T` Animal-blood over reference `A0C60` regardless of brief — *defensible alternative, not gold* (expert review).
- **Dried chili:** all coders match the corrected reference `A019K#F27.A00JB` (dried-peppers base + chili source) — models right, old reference wrong.

→ **Knowledge base needed for the extreme cross-domain tail — not routinely.** Gate it.

---

## Thread 3 — Consumption: another story

Paper suite (12 food-consumption cases) — facet-recall / family (/38):

| Coder | off | wiki | wiki RAG | source RAG |
|---|---|---|---|---|
| gemini-3.5-flash | **32/29** | 31/28 | 32/28 | 32/29 |
| claude-opus-4-8 | 29/27 | 31/26 | 25/23 | 30/28 |
| gpt-5.4 | 27/25 | 29/28 | 22/22 | 23/21 |

- **Brief is a net wash** on facets — wrong tool here.
- **Facets are hard — and DMT is at expert level:** best coder **76%** facet-family vs EFSA human-expert ceiling **~70%.** *Not a failure — parity with experts.*
- Most residual "misses" are **ambiguous or defensible near-synonyms** (next slide).
- Any further gain → **coder + prompt + validation rules**, not the knowledge base.

→ Facet construction is the hard part — already near the human ceiling.

---

## What the facet "misses" actually are

Best coder (gemini), so you don't have to read the paper:

| Food | Expected | Model gave | "Error" type |
|---|---|---|---|
| Spreadable cheese, low-fat, 17% | F10 Low-fat **+** F07 17% | only F07 17% | **omission** (dropped qualitative) |
| Meat imitate, wheat+chickpea, salted | F27 source + F28 salt-preserve | F04 ingredient + F04 added-salt | **F04↔F27 / ingredient↔process** — both defensible |
| Canned corn, w/o medium | F20.A0F2X | F06.A0F2X (same value!) | **right fact, wrong group** |
| Tiramisu → coffee | F04 Coffee (avg strength) | F04 Coffee beverages | **defensible near-synonym** |

- Multi-facet mixes *work* when unambiguous (yoghurt: apricot + skimmed + no-sugar + 0.1% fat → all 4 ✓).
- **So "76%" understates it** — corn & tiramisu score as misses but are arguably right.

---

## The spectrum (synthesis)

> **Adding the ask pays off in inverse proportion to retrieval coverage.**

| Domain | Retrieval coverage | Add the ask? |
|---|---|---|
| Consumption | complete | ✗ no — ~12.5k tokens wasted |
| Monitoring (edible) | mostly complete | rarely |
| **Cross-domain / non-food** | **structurally blind** | **yes — the only fix** |

→ **Gate the ask on a cross-domain signal:** pay the ~12.5k (RAG: ~4k) **only where retrieval is blind**, not on the consumption + edible-monitoring majority.

---

## Which models are good enough — cheaply?

Cost × accuracy × sovereignty (verified prices):

| Coder | $/MTok in/out | consumption (rec/fam) | monitoring base /4 | flip |
|---|---|---|---|---|
| deepseek-v4-pro | 0.44 / 0.87 | 25/22 | 3/4 | ✓ |
| **mistral-3 (EU)** | **0.50 / 1.50** | 29/– (base 7/12) | **4/4 best** | ✓ |
| **gemini-3.5-flash** | 1.50 / 9.00 | **32/29** | 3/4 | ✓ |
| gpt-5.4 | 2.50 / 15.00 | 27/25 | 3/4 | ✓ |
| claude-opus-4-8 | 5.00 / 25.00 | 29/27 | 3/4 | ✓ |

- **All 5 coders flip the cross-domain case** → coder choice never affects the knowledge-add.
- **gpt-5.4 & Opus 4.8 are dominated** — pricier for no gain (Opus ~14× deepseek, lower accuracy).

---

## Best token-for-value

- **EU monitoring pipeline → Mistral Large 3** — 2nd-cheapest, EU-sovereign, **best on monitoring** (the real workload). Weak only on consumption *base* (7/12).
- **All-round accuracy → gemini-3.5-flash** — best facets, strong everywhere.
- **Rock-bottom cost → deepseek-v4-pro** — $0.44/$0.87, permanent.

The frontier flagship (Opus 4.8) buys *nothing* here for ~14× the price.

---

## Bonus — the wiki, and which brief?

**The curated wiki *pages* are the rule substrate in every condition** (they replaced the old static prompt). We never ran "no wiki" — they're foundational. So the real question is the **synthesised advisory brief** on top, and its backing:

| Advisory brief | cross-domain flip | cost / query | auditable | verdict |
|---|---|---|---|---|
| **wiki LLM-synthesis** (`/wiki/ask`) | 3/5 | **~12.5k tok** (2 LLM calls) | curated | **dominated — expensive *and* weakest** |
| **source RAG** (raw PDFs) | 5/5 | **~4k tok** (1 call) | ✗ raw-page cites | accurate, not defensible |
| **wiki RAG** (curated md) | 5/5 | **~4k tok** (1 call) | ✓ vetted, editable | **best served brief** |

- **Is the LLM *wiki* worth it? Yes — it's the rule substrate under all four conditions.**
- **Is the wiki's LLM-*synthesis* brief worth it? No — dominated** by both RAG briefs.
- **Source RAG brief:** accurate but un-auditable · **Wiki RAG brief:** best single served brief.
- **Best of both:** serve the **Wiki-RAG brief**; run **Source RAG** as the curated wiki's *completeness gap-finder*.

---

## Recommendation

1. **Add knowledge with a *gated* Wiki-RAG ask** — fire only on a cross-domain signal; skip the consumption + edible-monitoring majority.
2. **Coder = cost×accuracy×sovereignty:** Mistral Large 3 for EU monitoring · gemini for accuracy · deepseek for cost. Not gpt-5.4 / Opus.
3. **Source RAG = the wiki's completeness check**, not the served brief.

**One line:** *The knowledge base earns its keep only where retrieval is structurally blind (the cross-domain tail) — so gate it, serve it from Wiki RAG, and code with a cheap EU-friendly model.*

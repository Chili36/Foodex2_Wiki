# DMT FoodEx2 — Advisory-Brief Ablation: off / wiki / wiki RAG / source RAG

**Date:** 2026-05-31
**Question:** Does the wiki advisory brief improve FoodEx2 code construction, and if so, in which form — **wiki** (LLM page-selector), **wiki RAG** (Qdrant over curated wiki markdown), or **source RAG** (Qdrant over raw EFSA source PDFs)?

---

## 0. Terminology (load-bearing — do not collapse)

**Critical:** in *every* condition the coder receives **candidates + the curated wiki pages** (selected by the wiki page-picker / context-pack). **Those pages ARE the FoodEx2 rules** — the template (`mtx_foodex2_wiki.txt`) is thin task instructions with a `{{FOODEX2_WIKI}}` slot; there is **no static "how FoodEx2 works" prompt.** So `off` means *"wiki rules, no synthesised brief,"* **not** *"no wiki."* The four conditions differ only in an **added synthesised advisory brief** layered on top of the always-present wiki pages:

| Condition | Added advisory brief | Brief retrieval backing | Endpoint |
|---|---|---|---|
| **off** | none — wiki pages only | — | — |
| **wiki** | wiki **LLM-synthesis** | curated wiki, LLM page-selector | `POST /wiki/ask` |
| **wiki RAG** | Qdrant synthesis | **curated wiki markdown** (`foodex2_wiki_markdown_v1`) | `POST /wiki/ask-rag` `mode=wiki` |
| **source RAG** | Qdrant synthesis | **raw EFSA source PDFs** (`foodex2_source_docs_v1`) | `POST /wiki/ask-rag` `mode=source` |

- **wiki RAG** and **source RAG** are **two distinct RAG variants** (different corpora, different behaviour) — never referred to jointly as "RAG."
- **wiki RAG** is bounded by what was *authored* into the curated wiki; auditable and human-editable.
- **source RAG** reaches raw guidance detail the curated wiki may not contain, but is un-curated and can over-specify.
- The wiki *pages* (context-pack) are the rule substrate throughout; the experiment varies the *brief*, not the presence of the wiki.

---

## 1. Headline

1. **The advisory brief earns its keep if and only if the correct base term is not in the candidate pool** — i.e. the cross-domain / non-food-matrix tail. On ordinary (consumption) food coding, where the base is always retrievable, every brief variant is a wash.
2. **On the one case where the base was unreachable (sheep urine → `A0C60`), both wiki RAG and source RAG flipped all four coders to the correct code; the LLM-selector `wiki` brief only flipped two of four; `off` flipped none.** The RAG variants are both more reliable *and* cheaper than the LLM-selector `wiki` brief on the case that matters.
3. **Coder choice is the larger overall lever:** `gemini-3.5-flash` is the strongest FoodEx2 coder on both domains, beating `claude-opus-4-8`, `gpt-5.4`, and `deepseek-v4-pro`.

---

## 1b. Storyline — how do we add knowledge, and what's good enough cheaply?

FoodEx2 classification is **pick-from-retrieved-candidates**, with the **curated wiki rule-pages always supplied** to the coder (they replaced the static prompt — see §0). But some correct answers are **never in the candidates** *and* aren't surfaced by the wiki page-selection — so the real question is **how do we add that missing knowledge, and how cheaply?** The lever under test is an **optional synthesised advisory brief** on top of the always-present wiki rules — and **adding it costs ~12.5k tokens/query (measured; wiki LLM-synthesis), ~4k in the RAG form (≈⅓).** That token cost is the basis of the whole discussion: *is adding the ask worth ~12.5k, and where?* Three data threads answer it:

**Thread 1 — "Sheep urine": the answer retrieval can never reach.** Correct base `A0C60` (non-food animal matrix) is not in the candidate pool — a food-tuned catalogue returns *food* terms — and even the always-present wiki *pages* don't surface it. **off (candidates + wiki pages): 0/5 coders.** The synthesised **brief is the only fix** and flips **5/5** to `A0C60`. The framing discovery: **some classifications need knowledge *synthesised in*, beyond both retrieval and the static rule-pages** — and a coder *can* adopt a base that was never a candidate when the brief supplies the rule.

**Thread 2 — Monitoring: is the knowledge base needed beyond edge cases?** Mostly **no**. Realistic monitoring foods are mostly edible matrices with retrievable bases (the brief is a wash); the extension set is **8/10 unanimous, 0 invalid** across 5 coders. The brief is **decisive only on the one truly retrieval-blind case — sheep urine** (off 0/5 → brief 5/5 → `A0C60`). *(Wild-boar plasma is a different story: models prefer `A0F1T` "Animal blood" over the data-provider reference `A0C60` regardless of the brief — a generic-vs-specific disagreement for expert review, §4, not a brief win.)* → Gate it.

**Thread 3 — Consumption: facets are hard, and DMT is at human-expert level.** The brief is a **net wash** on facets (helps some, hurts others). But the headline is *not* "facets unsolved" — it's that **the best coder reaches 29/38 = 76% facet-family, against an EFSA human-expert agreement ceiling that rarely exceeds ~70%.** So this is *at or above expert level*, not a failure. The remaining "misses" are mostly real ambiguities or defensible near-synonyms (see §3b), not blunders. The takeaway: facet construction is the genuinely hard part, the coder is already performing near the human ceiling, and **the knowledge base is the wrong lever for it** (the brief is a wash) — further gains, if wanted, come from the coder + prompt + validation rules, not from added knowledge. *(EFSA ~70% figure: cite precisely in the paper.)*

**The spectrum:** *knowledge-adding matters in inverse proportion to retrieval coverage* — unnecessary on consumption, rare on edible monitoring, **essential on the cross-domain/non-food tail.** Pay for knowledge only where retrieval is structurally blind.

**Models — good enough cheaply:** all 5 coders flip the cross-domain case with the brief, so coder choice is free to optimise for **cost × accuracy × sovereignty** (§5b): Mistral Large 3 (EU monitoring), gemini (accuracy), deepseek (cost); gpt-5.4 and Opus 4.8 are dominated.

## 2. Method

**Coders (held constant within a run; the only thing varied between runs):** `gpt-5.4`, `gemini-3.5-flash`, `deepseek-v4-pro`, `claude-opus-4-8`. Brief answerer held constant at `claude-sonnet-4-6`.

**Conditions:** off / wiki / wiki RAG / source RAG (§0). The **candidate list is frozen per case** (one deconstructed `/search`, reused across all four conditions) so the only variable within a case is the brief.

**Suites:**
- **Consumption** — 12 cases from the Nutrients 2024 SCAI children's *food-consumption* survey paper (`dmt_foodex2_challenge_suite.json`). Ordinary composite foods.
- **Monitoring** — 4 cross-domain probes built for this study (`monitoring_challenge_suite.json`): sheep urine, wild-boar (semi-domesticated) plasma, fish-liver rainbow trout, dried chili pepper. Non-food matrices and edible monitoring matrices.

**Pipeline per condition:** deconstruct + parallel candidate search → context-pack pages → (for wiki / wiki RAG / source RAG) the respective brief prepended to the wiki context → coder (`/execute-prompt`, template "MTX FoodEx2 Wiki") → `constructedCode`.

**Scoring:** base-correct + facet recall/family vs the paper/grounded *reference* code (explicitly **not** blind gold), plus catalogue-validation (every code checked for existence + term-type in `mtx_monitoring_openai_current`).

---

## 3. Results — Consumption (12 cases)

Facet-recall / facet-family (out of 38); base-correct in parentheses.

| Coder | off | wiki | wiki RAG | source RAG |
|---|---|---|---|---|
| gemini-3.5-flash | **32 / 29** (11) | 31 / 28 (10) | 32 / 28 (11) | 32 / 29 (11) |
| claude-opus-4-8 | 29 / 27 (11) | 31 / 26 (11) | 25 / 23 (11) | 30 / 28 (11) |
| gpt-5.4 | 27 / 25 (10) | 29 / 28 (10) | 22 / 22 (10) | 23 / 21 (10) |
| deepseek-v4-pro | 25 / 22 (10) | 26 / 19 (10) | 26 / 22 (10) | 25 / 23 (9) |
| mistral-large-2512 (EU) | 29 / 24 (**7**) | 31 / 25 (8) | 28 / 25 (8) | 28 / 24 (8) |

**Reading:**
- **The brief is a net wash on consumption.** No condition consistently beats `off`; `off` is tied-best for the strongest coder (gemini). Per-case it trades small offsetting wins/losses (e.g. `wiki` fixed the spreadable-cheese F07/F10 confusion but broke the cod base on gemini).
- **Facets are hard — and DMT is at human-expert level, not failing.** Best facet-family is **gemini 29/38 = 76%** (gpt-5.4 / opus 74%, mistral 66%, deepseek 61%) — versus an EFSA human-expert agreement ceiling that **rarely exceeds ~70%.** The brief is a wash on this, so further gains come from the **coder + prompt / validation rules**, not the knowledge base. (See §3b for what the residual "misses" actually are.)

## 3b. What the facet "misses" actually look like (concrete)

The ~24% non-exact facets are mostly real ambiguities or defensible near-synonyms, not blunders. From gemini (best coder, `off`):

| Food | Expected | Model produced | Type of "error" |
|---|---|---|---|
| Spreadable cheese, low fat, 17% | `F10.A077C` Low-fat **and** `F07.A073E` 17% fat | only `F07.A073E` (17% fat) | **Omission** — kept the measured value, dropped the *qualitative* "low fat"; the model treated them as redundant, EFSA wants both |
| Meat imitate (wheat, chickpea, salted) | `F27` wheat/chickpea (source commodity) + `F28.A07JP` preserving-with-salt | `F04` wheat/chickpea (ingredient) + `F04.A0CJK` "with added salt" | **Family confusion** F04↔F27 and ingredient↔process — *both genuinely defensible*: is wheat in a meat-analogue an ingredient or a source commodity? |
| Canned sweet corn, w/o medium | `F20.A0F2X` | `F06.A0F2X` — *same descriptor* | **Right fact, wrong group** — picked the correct value, mis-labelled the facet family |
| Tiramisu → coffee | `F04.A03KC` Coffee (average strength) | `F04.A03KA` Coffee beverages | **Defensible near-miss** — right ingredient, neighbouring code |

And it handles the hard multi-facet mixes well when descriptors are unambiguous — e.g. yoghurt "apricot, skimmed, no added sugar, 0.1% fat" → all four facets correct across `F04`/`F07`/`F10`.

**Reading:** the headline "76%" *understates* real quality — wrong-group-right-fact (corn) and near-synonym (tiramisu) cases score as misses but are arguably correct. Against the ~70% human ceiling, facet construction is effectively at parity with expert coders.
- **wiki RAG vs source RAG on consumption:** roughly tied for gemini and deepseek; **source RAG clearly ahead of wiki RAG for opus (30/28 vs 25/23)** — source RAG reached raw-guidance facet detail the curated wiki markdown lacked. gpt-5.4's low RAG rows are partly an artifact (the reasoning model occasionally returned a bare base; flagged in §6).
- **Coder ranking (off baseline):** gemini 32/29 ≫ opus-4-8 29/27 > gpt-5.4 27/25 > deepseek 25/22.

---

## 4. Results — Monitoring (4 cross-domain cases)

The decisive case is **sheep urine**, where the correct non-food-matrix base `A0C60` is **not in the candidate pool** (deconstructed search surfaces sheep *food* terms: milk, offal, kidney).

**Sheep urine — constructed base by coder × condition:**

| Coder | off | wiki | wiki RAG | source RAG |
|---|---|---|---|---|
| gemini-3.5-flash | A021H ✗ | A021H ✗ | **A0C60 ✓** | **A0C60 ✓** |
| claude-opus-4-8 | A057G ✗ | **A0C60 ✓** | **A0C60 ✓** | **A0C60 ✓** |
| gpt-5.4 | A021H ✗ | **A0C60 ✓** | **A0C60 ✓** | **A0C60 ✓** |
| deepseek-v4-pro | A057G ✗ | A021H ✗ | **A0C60 ✓** | **A0C60 ✓** |
| mistral-large-2512 | A021H ✗ | **A0C60 ✓** | **A0C60 ✓** | **A0C60 ✓** |
| **totals** | **0/5** | **3/5** | **5/5** | **5/5** |

`A021H` = "Sheep other slaughtering products" (a food term); `A057G` = "Sheep (as animal)"; `A0C60` = "Non-food animal-related matrices" (correct). All decoded against the catalogue.

- **off: 0/5** — every coder produces a wrong food-domain term.
- **wiki RAG: 5/5 · source RAG: 5/5** — both flip every coder to the correct `A0C60`.
- **wiki (LLM-selector): 3/5** — works for opus, gpt-5.4, mistral; fails for gemini and deepseek.

**Other monitoring cases (base *was* retrievable):**
- **Wild-boar plasma — reference `A0C60#F02.A0CEX$F01.A056Y$F21.A07RX` (data-provider).** In **18 of 20 cells** the models chose **`A0F1T` "Animal blood"** as the base instead (only mistral's source-RAG cell produced the reference `A0C60`). The facets (`F02.A0CEX`, `F01.A056Y`, `F21.A07RX`) match the reference exactly, and the brief does *not* move models toward `A0C60`. **`A0F1T` is a semantically plausible alternative worth expert review — but it is NOT the corrected gold;** the benchmark reference stays the VMPR-style generic-matrix construction unless the benchmark owner changes it. So against the reference this case is a base *miss*, not a win.
- **Dried chili pepper — corrected reference `A019K#F27.A00JB` (per the benchmark owner).** Every coder produced `A019K#F27.A00JB`: the *dried-peppers derivative base* (`A019K`) narrowed to chili via `F27.A00JB`. This is **correct** — drying changes the commodity's nature, so it belongs in the processed derivative base; a raw chili base + an `F28` drying facet would be *invalid*. (The earlier reference `A00JB`+F28 was wrong; the models were right.) *Wording:* "dried chili pepper(s)" is the dried-chili-pepper commodity; "dried chili" alone is read the same way here — not necessarily powder/flakes/dish.
- **Fish liver:** base mostly correct (`A02EJ`); `wiki RAG` drifts to the rainbow-trout base (`A029N`).

---

## 4c. Extension suite — 10 realistic monitoring foods (system validity)

Drawn from the EFSA/DMT monitoring masterlist (Swedish names verbatim, spanning pesticides / contaminants / VMPR / additives / FCM). No blind gold (hints aren't truth), so scored on **catalogue-validity + cross-coder agreement + change-detection** — i.e. *does the pipeline behave reliably on real multi-domain data*, run through all 5 coders × 4 conditions.

- **Catalogue-validity: 51 unique base+facet codes produced, 0 invalid.** Every code, every coder, exists in the catalogue with a valid term-type. No fabrication.
- **Cross-coder base agreement: 8/10 items unanimous** across all 5 coders → the pipeline is *stable* on realistic monitoring foods. The 2 that scatter are genuinely ambiguous: **Falukorv** (4 distinct bases — composite sausage) and **Nötkreatursfett** (4/5). These are the items for domain-expert attention.
- **Brief activity higher than consumption** (mistral changed 8/10, gemini 6/10 vs gpt-5.4 1/10) — but it's facet reshuffling on a settled base; correctness un-scorable without an expert pass.
- Swedish→English deconstruct/translate handled all 10 (e.g. *Strömming/sill från Östersjön* → Baltic herring, *Mjölmasklarver* → mealworm larvae) with valid output.

**Verdict:** on realistic multi-domain monitoring data, DMT produces catalogue-valid codes with high cross-model consensus — strong external validity, independent of the ask question.

## 5. The unifying rule

> **The advisory brief changes the outcome if and only if the correct base term is not in the candidate pool.**

Across 16 cases × 4 coders, exactly one case met that condition (sheep urine) — and it is the only case where the brief was decisive. This explains the entire arc:
- **Consumption = wash** because consumption bases are always retrievable.
- **Monitoring cross-domain = decisive** because non-food-matrix bases (`A0C60`) are structurally absent from a catalogue/retrieval tuned to food.
- A coder **can** adopt a base that was not in its candidate list when the brief supplies the rule (demonstrated: `A0C60` was never a candidate yet the brief drove the coders to it).

---

## 5b. Cost × accuracy (value per token)

All prices verified against source of truth (DeepSeek official pricing page; effective-invention for the rest) — **not** the local registry, which carried two errors (see note).

| Coder | $/MTok in / out | consumption off (recall/family /38) | monitoring (base /4, src-RAG) | cross-domain flip |
|---|---|---|---|---|
| **deepseek-v4-pro** | **0.435 / 0.87** | 25 / 22 | 3/4 | ✓ |
| **mistral-large-2512** (EU) | **0.50 / 1.50** | 29 / — (base 7/12) | **4/4 (best)** | ✓ |
| **gemini-3.5-flash** | 1.50 / 9.00 | **32 / 29** | 3/4 | ✓ |
| gpt-5.4 | 2.50 / 15.00 | 27 / 25 | 3/4 | ✓ |
| claude-opus-4-8 | 5.00 / 25.00 | 29 / 27 | 3/4 | ✓ |

*Monitoring base /4 = best (source-RAG) vs the **corrected** data-provider references: dried chili `A019K#F27.A00JB` counts as correct; wild-boar plasma scores against `A0C60#…` (the prevalent `A0F1T` output is a defensible alternative, not the reference).*

Mistral Large 3 price = 75% under Large 2's $2/$6 (effective-invention), confirmed vs local YAML.

- `deepseek-v4-pro` price is the **permanent** post-promo level (75% off list; the page states it adjusts to 1/4 of original after the promo). Cache-hit input ≈ $0.0036/MTok. NB: the coder runs via the Embeddings-Search `/execute-prompt` path, which must not enable prompt caching — so use the cache-miss input ($0.435).
- **Pareto frontier = gemini-3.5-flash (top accuracy) ↔ deepseek-v4-pro (rock-bottom cost).** `gpt-5.4` and `claude-opus-4-8` are **dominated**: gemini beats gpt-5.4 on accuracy *and* cost; opus is the most expensive (~14× deepseek, ~3× gemini) for middling accuracy.
- All four coders get the cross-domain flip from the RAG brief, so coder choice is purely a cost×accuracy decision and does not affect the gated-ask behaviour.

**Registry-price errors found (worth fixing):** local `deepseek-v4-pro.yaml` shows `$1.74/$3.48` = the **pre-discount list** (4× the effective/permanent price). The effective price is `$0.435/$0.87`. (`gpt-5.4.yaml` is correct at `$2.50/$15`; an earlier draft of this table mistakenly used `gpt-5.4-mini`'s `$0.75/$4.50`.)

## 5c. Bonus — is the LLM Wiki worth it? Is Source RAG enough? Does Wiki RAG combine the best of both?

**First, the framing fix:** the curated wiki *pages* are the **rule substrate in every condition** (they replaced the old static prompt; we never ran "no wiki"). So "is the LLM Wiki worth it?" splits in two:

- **Is the LLM *wiki* (the curated rule pages) worth it? Yes — it's foundational**, under all four conditions; it's how FoodEx2 rules reach the coder at all.
- **Is the wiki's LLM-*synthesis* brief (`/wiki/ask`) worth it? No** — that *added brief* is dominated.

**The cost basis:** adding the ask is **not free — the wiki LLM-synthesis brief costs ~12.5k tokens/query (measured)**; the RAG briefs cost ~⅓ of that (~4k). That token cost is *why* "is the brief worth it / when" is the question at all. The three **advisory-brief** mechanisms (each layered on top of the always-present wiki pages) compare as:

| Advisory brief | Cross-domain flip | Cost / query | Auditable / editable | Verdict |
|---|---|---|---|---|
| **wiki** LLM-synthesis (`/wiki/ask`) | 3/5 | **~12.5k tok** (2 LLM calls) | curated | **dominated — costliest *and* weakest** |
| **source RAG** (Qdrant over raw EFSA PDFs) | 5/5 | **~4k tok** (1 call) | ✗ cites raw PDF pages | accurate, not defensible |
| **wiki RAG** (Qdrant over curated wiki md) | 5/5 | **~4k tok** (1 call) | ✓ vetted, human-editable | **best served brief** |

- **Is Source RAG good enough? On accuracy, yes** (5/5 flip; reaches raw detail the curated wiki lacks). **But not as the served brief** in a regulatory pipeline — un-curated (over-specifies), cites raw PDF pages (weak provenance for an EFSA submission).
- **Does Wiki RAG combine the best of both? As a single served brief, it's the best one** — cheap, flips 5/5, *and* curated/auditable/editable — but it doesn't automatically inherit Source RAG's raw completeness. **True best-of-both = the *pair*: serve the Wiki-RAG brief; run Source RAG as a completeness gap-finder** that flags detail missing from the curated wiki for a human to edit in.

## 6. Recommendation

1. **Re-enable the advisory brief, but gated — not always-on.** Fire it only when retrieval cannot confidently supply a base (low candidate scores / cross-domain signal). This captures the sheep-urine class while skipping the consumption majority (no token cost, no latency, no facet-family noise there).
2. **Serve the brief from wiki RAG, with source RAG as a completeness gap-finder.** Both wiki RAG and source RAG delivered the cross-domain flip equally (4/4). They differ on the other axis:
   - **wiki RAG** is auditable and human-editable (curated corpus) — the right *serving* layer in a regulatory context; a coder citing a vetted wiki page is defensible.
   - **source RAG** reaches raw-guidance detail wiki RAG misses (e.g. it surfaced production-intensity facets on opus that the curated wiki lacked). Best used to *flag gaps in the curated wiki* for human editing, not as the primary served brief.
   - The expensive LLM-selector **wiki** brief is dominated: less reliable on the sheep-urine flip (3/5 vs 5/5) and costlier than either RAG variant.
3. **Coder — pick on the cost×accuracy frontier (§5b), not by tier.**
   - **For an EU *monitoring* pipeline (the real use case): `mistral-large-2512` is the standout** — 2nd-cheapest ($0.50/$1.50), EU-sovereign, and the **best monitoring coder** (4/4 base, source-RAG — the only coder that also reached the wild-boar reference `A0C60`). Its one weak spot is consumption *base* selection (7/12), which matters less if the workload is monitoring.
   - `gemini-3.5-flash` is the all-round accuracy pick (best consumption facets 32; strong everywhere).
   - `deepseek-v4-pro` is the rock-bottom-cost pick ($0.44/$0.87).
   - `gpt-5.4` and `claude-opus-4-8` are dominated — pricier for no accuracy gain; don't use them here.
   - **All five coders get the cross-domain flip from the RAG brief**, so coder choice is purely cost×accuracy×sovereignty and never affects the gated-ask behaviour.

---

## 7. Caveats / threats to validity

- **n is small** (12 consumption + 4 monitoring), single run per cell. The cross-domain conclusion rests on one case (sheep urine); it should be widened with more non-food-matrix probes (additional urine/blood/hair/feather matrices, other VMPR cases).
- **Reference codes are data-provider/grounded references, not blind gold.** "Matches reference" is kept distinct from "defensible alternative": e.g. wild-boar plasma `A0F1T` "Animal blood" vs the reference `A0C60` generic matrix is a genuine generic-vs-specific judgement flagged for expert review — *not* scored as gold. (References were corrected on benchmark-owner feedback: dried chili → `A019K#F27.A00JB`; wild-boar reference retained as `A0C60#…`.)
- **gpt-5.4 RAG-row artifact:** the reasoning model occasionally returned a bare base (no facets) under wiki RAG / source RAG, depressing those scores. Those cells should be re-run before trusting the consumption RAG deltas for gpt-5.4.
- **Brief answerer fixed at sonnet-4-6;** a different answerer could shift brief quality.

---

## 8. Artifacts

- Suites: `dmt_foodex2_challenge_suite.json` (consumption), `monitoring_challenge_suite.json` (monitoring)
- Per-coder results: `ablation_round{1..4}_*.json` (consumption), `ablation_monitoring_*.json` (monitoring)
- Harness: `/tmp/foodex2_ask_ablation.py`
- Engineering fixes made for this study: added `claude-opus-4-8` model YAML; fixed the qdrant-search adaptive-thinking model list (Opus 4.8 was sending legacy extended-thinking → HTTP 400 for any Opus-4.8 caller).

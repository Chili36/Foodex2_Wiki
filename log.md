---
title: "Wiki Log"
last_updated: "2026-07-04"
---

# Log

## [2026-07-05] diagnostic | Page-selection gold set + baseline eval

- Added a measurement layer for `/wiki/context-pack` page selection: deterministic scorer (`wiki_api/selection_scoring.py`), a 15-case reviewed gold set with must_have/acceptable/must_not labels (`evals/selection/`), and an eval runner (`scripts/selection_eval.py`). Plan: `docs/superpowers/plans/2026-07-05-page-selection-improvement.md`.
- Baseline (`reports/selection-evals/2026-07-05-baseline/`): mean must-have recall 0.73, precision 0.91, leak-free 0.93. Dominant failure is a whole-category miss of the validation layer — `term-type-facet-constraints.md` absent from 10/15 packs. Triage opens Phase 1 (deterministic category skeleton) as top priority; Phase 2 (candidate-aware selector) queued for two residual candidate-signal misses.
- This is a diagnostic baseline, not a guidance change; no wiki page semantics were altered.

## [2026-07-04] maintenance | Add model-facing wiki architecture orientation

- Added `WIKI_ARCHITECTURE_FOR_MODELS.md` as a first-class orientation page for models and maintainers that need the full architecture, structure, runtime endpoints, retrieval modes, source tiers, Qdrant role, and maintenance philosophy in one place.
- Registered the page in the wiki store and index so it is served by the local wiki and checked by the deterministic doctor.
- Linked the page from `README.md` and `SCHEMA.md` so future handoffs can use it as the canonical architecture briefing instead of reconstructing the system from scattered files.

## [2026-06-10] guidance | Clarify VMPR blood-related biological sample default

- Tightened the VMPR non-food biological sample boundary so active VMPR biological-sample rows for blood, blood serum, and plasma default to `A0C60 Non-food animal-related matrices` with explicit `F01` source and `F02` part-nature.
- Documented whole blood as a structural grey area: FoodEx2 has food-chain blood terms, while maintenance 2021 added blood-related `F02` descriptors for ASF/WGS biological sample description. Preserve the normal edible-blood path for explicit food-chain rows, including `is_food=true`, edible products, blood ingredients, slaughterhouse food commodities, ordinary all-domain food matrices, or where VMPR biological-sample context is absent.
- Added the blood/serum/plasma `F02` descriptor signal: blood `F02.A06AL`, blood serum `F02.A0CEY`, plasma `F02.A0CEX`; source animals still come from catalogue evidence.

## [2026-06-07] maintenance | Update validator-rule guidance for MTX 17.1 and BR13/BR19/BR26

- Updated the validation layer for the sibling validator's MTX `17.1` status: imported 2026-06-06, `PUBLISHED MINOR`, 31,690 terms, last EFSA update 2026-04-28.
- Replaced broad "no F03 on raw" wording with the ICT-derived seven-code BR13 disintegration list: `A06JD`, `A06JE`, `A06JF`, `A06JG`, `A07Y2`, `A07Y3`, and `A07Y4`.
- Documented the BR19 stale-data problem: upstream `BR_Data.csv` is frozen at 2020-05-20, so the sibling validator can emit transparent `BR19+` extension warnings from `data/BR_Data.extension.csv` unless `STRICT_ICT_PARITY=1` is set.
- Added the BR26 known-divergence note: stock ICT and the sibling validator are effectively silent in the observed state, though for different implementation causes, so process-composition guidance should not rely on BR26 firing.

## [2026-05-30] service | Add Qdrant-backed ask endpoint for DMT A/B tests

- Added `POST /wiki/ask-rag` as a compact guidance endpoint backed by Qdrant retrieval.
- Kept `/wiki/ask` unchanged as the service-owned page-selector synthesis path.
- Documented the DMT four-condition test contract: ask off, ask + wiki, ask + wiki RAG, and ask + source RAG.
- Added mocked API tests for both `wiki` and `source` retrieval modes.

## [2026-04-05] ingest | Initial FoodEx2 guidance compilation

- Created the first topic-oriented markdown pages under `raw/efsa-guidance/` from the EFSA FoodEx2 revision 2 guide, training materials, and chemical monitoring guidance.
- Seeded pages for overview, base-term selection, facet rules, implicit vs explicit facets, code-string format, process facets, and ingredient facets.
- Kept the source PDFs unchanged in `foodex2_docs/`.

## [2026-04-05] maintenance | Remove discontinued Smart Coding App references

- Deleted the standalone Smart Coding App page after confirming the app is discontinued.
- Re-checked the wiki layer to ensure no remaining `Smart Coding App` references remained.

## [2026-04-05] maintenance | Add repo context and wiki navigation

- Added `PROJECT_CONTEXT.md` to record what the project is building and why.
- Added `README.md` for repo-level orientation.
- Added `index.md` and `log.md` to support wiki navigation and chronological tracking.

## [2026-04-05] ingest | Add annual maintenance layer

- Added a cross-year maintenance timeline page.
- Added dedicated wiki pages for the annual maintenance reports covering 2015, 2016-2018, 2019, 2020, 2021, 2022, 2023 and 2024.
- Updated the index so the annual maintenance PDFs are now represented in the wiki layer instead of being left only in `foodex2_docs/`.

## [2026-04-05] ingest | Add Chemical Monitoring overlay

- Added a small page for the FoodEx2-specific rules embedded in the 2025 and 2026 Chemical Monitoring Reporting Guidance.
- Kept it separate from the core FoodEx2 guidance pages so reporting-workflow constraints do not get mixed with the base FoodEx2 model.

## [2026-04-05] ingest | Add validator rule layer

- Added dedicated wiki pages for structural validation, `BR01-BR31` overview, term-type facet constraints, process-rule conflicts, and domain-specific validation.
- Used the sibling `Foodex2 Code Validator` project as the source for the operational rule engine that had previously lived only in the coding prompt.
- Updated the index so the wiki now represents both EFSA guidance and the validator policy layer.

## [2026-04-05] ingest | Add packaging facet guidance

- Added a dedicated packaging page for `F18 Packaging-format` and `F19 Packaging-material`.
- Captured the distinction between packaging descriptors and `F28` process descriptors, including the fact that a `jar` does not by itself prove `pasteurisation`.
- Used the 2015 FoodEx2 guide and 2026 Chemical Monitoring examples as source material.

## [2026-04-05] service | Add wiki retrieval API

- Added a local FastAPI service under `wiki_api/` so external applications can call this repo for page reads and policy-pack retrieval.
- Kept the retrieval logic owned by the wiki repo instead of pushing wiki selection logic into downstream clients.
- Added tests for health, page listing, page reads, and a packaging-sensitive policy-pack case.

## [2026-04-05] service | Switch policy-pack retrieval to LLM librarian

- Replaced the deterministic page selector inside the API path with an internal Anthropic-powered wiki librarian.
- Kept the API surface stable for clients, but changed `/wiki/policy-pack` so the wiki repo now performs an actual LLM-guided read of the wiki before returning context.
- Added mocked tests for the LLM-owned policy-pack flow and included tool traces in the response metadata.

## [2026-04-06] maintenance | Add guiding principles to the wiki index

- Added a compact `Guiding Principles` section to `index.md` so the high-level FoodEx2 worldview is always available without consuming a separate page slot.
- Captured the key framing ideas that FoodEx2 is a scientific reporting language, is modeled top-down rather than bottom-up, prefers modular facets over term proliferation, and separates detailed input coding from downstream analytical aggregation.

## [2026-04-06] maintenance | Clarify derivative source vs added-ingredient logic

- Updated the facet and term-type pages to state the underlying origin-modeling rule explicitly: `F27` on a derivative answers what primary commodity the derivative was obtained from, while later-added characterising ingredients belong in `F04`.
- Kept the update generic and ontology-level, without adding a case-specific worked example.

## [2026-04-06] maintenance | Clarify derivative-base examples are illustrative

- Tightened the base-term selection wording so the list of nature-changing processes is explicitly illustrative rather than exhaustive.
- Added a note that the processed-base precedence rule should not be overridden just because a more specific raw commodity term exists.

## [2026-04-07] service | Add small compiled policy layer

- Added a small always-on policy contract to the API responses for `policy-pack` and `solve`.
- The contract includes a constitution, ordered decision procedure, binding rules, tie-break rules, and one explicit anti-pattern for raw-plus-`F28` reconstruction of standard derivative groups.
- Updated the solver so it treats this contract as the authoritative control layer and the wiki prose as supporting knowledge.

## [2026-04-07] maintenance | Move policy source into markdown

- Added `raw/efsa-guidance/policy-contract.md` as the source-of-truth policy page for the schema/control layer.
- Updated the API so it loads the policy contract from markdown frontmatter instead of defining it in service code.
- Linked the policy page from `index.md` so the schema layer is visible as part of the knowledge base.

## [2026-04-07] ingest | Add CHEMMON12 acrylamide F33 rule from EFSA clarification

- Added CHEMMON12 business rule detail to `domain-specific-validation.md`: paramCode trigger (`RF-00000410-ORG`), legal basis (Commission Regulation (EU) 2017/2158, Recommendation (EU) 2019/1888), and the implicit-override requirement.
- Added the implicit-facet exception to `implicit-vs-explicit-facets.md`: explicit `F33` is mandatory for acrylamide even when the base term already carries an implicit `F33`.
- Added a worked example to `chemical-monitoring-foodex2.md`: french fries `A0BYV#F33.A169H` with legislative class mapping.
- Source: EFSA official clarification on the ChemMon reporting channel, referencing CHEMMON12 and ChemMon 2026 guidance.

## [2026-04-08] maintenance | Add formal ingest workflow playbook

- Added `INGEST_WORKFLOW.md` as the concrete playbook for future document ingest.
- Captured the actual working method used in this repo: structure scan first, topic-map updates second, durable-rule extraction third, and gap-patching later.
- Linked the workflow from `README.md` and `index.md` so future maintenance work has an explicit reference process.

## [2026-04-08] maintenance | Strengthen inline cross-linking on core guidance pages

- Added body-level `[[...]]` cross-links to the main rule hubs so the model-facing API sees the same knowledge graph that humans infer from frontmatter and the viewer.
- Focused the pass on `base-term-selection.md`, `process-facets.md`, `ingredient-facets.md`, `implicit-vs-explicit-facets.md`, `term-type-facet-constraints.md`, `facet-coding-rules.md`, `process-validation-rules.md`, and `chemical-monitoring-foodex2.md`.
- Kept the links procedural rather than decorative: decision pages now point directly to adjacent rule pages for term type, origin-chain, process, validation, and ChemMon exceptions.

## [2026-04-08] service | Always include policy-contract.md in API page content

- Updated all three wiki API endpoints (context-pack, policy-pack, solve) to always include `policy-contract.md` in the `pages_used` list and `pages` content.
- The policy contract was already returned as structured data but its page content was not included unless the page selector happened to pick it. Now the constitution, binding rules, tie-break rules, and anti-patterns are always visible to the consuming model.

## [2026-04-08] maintenance | Add F27 narrowing rule for broad derivative groups

- Added a general rule to `implicit-vs-explicit-facets.md`: when a derivative base term carries a broad implicit F27, narrow it with an explicit F27 to the specific source commodity instead of abandoning the derivative and reconstructing from raw + F28.
- Added a corresponding row to the "When To Add An Explicit Facet" table for the broad-group derivative case.

## [2026-04-08] maintenance | Add related project links to README

- Added direct GitHub links in `README.md` to the sibling FoodEx2 validator project, the ChemMon wiki, and DMT.
- Made the repo-level orientation clearer for readers arriving without the surrounding project context.

## [2026-04-08] maintenance | Expand the policy contract with core coding ground rules

- Strengthened `raw/efsa-guidance/policy-contract.md` so the schema layer now carries more of the real FoodEx2 coding policy instead of only a thin constitutional shell.
- Added explicit policy rules for avoiding hierarchy terms, choosing the correct origin facet family by food type, and rejecting explicit facets that merely repeat implicit base-term properties.
- Bumped the policy version so API consumers can tell they are receiving the fuller contract.

## [2026-04-08] maintenance | Add operational coding rules to the policy contract

- Expanded `policy-contract.md` again with scope-note checking, processed-term priority, term-type-specific facet focus, descriptive facet guidance, process-ordinal constraints, single-cardinality limits, F27 refinement, F03/F01 restrictions, code syntax, SSD2 length limit, and monitoring-flag carry-through.
- Kept the rules in both forms: structured frontmatter for the machine-readable API contract and a readable "Operational Rules" section for humans consuming the page directly.
- Bumped the policy version from `v0.3` to `v0.4`.

## [2026-04-08] maintenance | Make the policy page body canonical and return it first

- Removed policy-specific frontmatter from `policy-contract.md` and moved the machine-readable rule sections into the visible markdown body so ordinary wiki consumers and API consumers now read the same policy text.
- Updated the policy loader to parse the body sections instead of relying on frontmatter-only rule data.
- Changed wiki API page ordering so `policy-contract.md` is always returned first in `pages_used` and `pages`.

## [2026-04-08] service | Tighten page-selector routing cues

- Expanded the wiki page selector prompt so it now treats candidate term types, monitoring flags, packaging clues, and raw-vs-derivative ambiguity as first-class routing signals rather than relying mostly on the user query text.
- Strengthened the relevant `index.md` summaries so domain and validation pages advertise VMPR/VETDRUG, raw-vs-derivative process conflicts, and ingredient-characterisation keywords more explicitly.

## [2026-04-09] ingest | Add cleaned validator business-rules source markdown

- Added `foodex2_docs/business_rules.md` as a cleaned source-layer markdown version of the validator's `BR01-BR31` rule set.
- Kept the content source-oriented and comprehensive, but stripped repeated severity boilerplate and formatting noise so future wiki ingests can work from a denser validator-policy artifact.

## [2026-04-09] maintenance | Add canonical business-rules wiki page and BR backlink workflow

- Added `raw/efsa-guidance/business-rules.md` as the canonical wiki target for `BR01`-`BR31`.
- Updated `index.md` so the validation layer now exposes that page directly.
- Updated `INGEST_WORKFLOW.md` to make business-rule backlinking mandatory for operational pages during ingest.
- Seeded `Relevant Business Rules` sections on the main validation pages so the pattern exists in the wiki itself, not just in process docs.

## [2026-04-09] maintenance | Backfill policy and business-rule traceability across all pages

- Added `Relevant Policy` sections across the full `raw/efsa-guidance/` set so every page now states which parts of `policy-contract.md` actually govern its use.
- Expanded `Relevant Business Rules` coverage across the full page set, including explicit "no single BRxx governs this page" language on conceptual and historical pages where that is the honest answer.
- Updated `INGEST_WORKFLOW.md` so future ingests must backfill both policy and business-rule relevance, not just validator-rule backlinks on operational pages.

## [2026-04-09] maintenance | Make the policy page prompt-first

- Removed service-layer and machine-readable framing from the top of `raw/efsa-guidance/policy-contract.md` so the first tokens seen by a downstream model are operational instructions rather than implementation notes.
- Kept the parseable policy sections intact so the API can still extract the policy contract while the visible markdown stays cleaner and more prompt-efficient.

## [2026-04-10] maintenance | Add runtime and schema layer documents

- Added `RUNTIME_RULES.md` as the compact prompt-facing rules file attached by `context-pack`.
- Added `SCHEMA.md` to define page types, frontmatter fields, section conventions, and the practical layer model for the repo.
- Updated `index.md` and `README.md` so the runtime layer and schema layer are visible as first-class parts of the knowledge base.

## [2026-04-10] service | Make context-pack runtime-first

- Changed `context-pack` page ordering so `RUNTIME_RULES.md` is returned first instead of `policy-contract.md`.
- Kept `context-pack` on the adaptive LLM page-selector path because page choice still needs to vary by case.
- Kept `policy-pack` and `solve` on the richer LLM-driven path, while updating retrieval tests for the runtime-first alpha `context-pack` flow.

## [2026-04-10] service | Clarify context-pack selector budget wording

- Replaced the opaque selector prompt wording about `non-index pages` with direct wording: the index is already provided, so the selector should request only the additional wiki pages it needs.
- Changed the default `context-pack` selector budget from 5 additional pages to 6 additional pages, which yields the intended default of up to 8 returned pages once `index.md` and `RUNTIME_RULES.md` are included.
- Kept the page budget request-scoped through `max_pages`, so it can be tuned later if runtime or cost proves worse than expected.

## [2026-04-11] maintenance | Document the wiki relationship model

- Added an explicit relationship-model section to `SCHEMA.md` so the wiki now documents how pages relate to each other without pretending there is a separate graph database.
- Recorded the current edge types as `related` frontmatter, inline `[[...]]` links, `Relevant Policy`, `Relevant Business Rules`, and `index.md` as the hub node.
- Added a short README note so outside readers can understand that the wiki is graph-like even though it is still authored as markdown pages.

## [2026-04-11] service | Add generated graph and backlink views

- Added wiki graph extraction in `wiki_store.py`, derived from frontmatter `related`, inline links, policy references, business-rule references, and `index.md` catalog links.
- Added `GET /wiki/graph` for a generated adjacency map and `GET /wiki/pages/{page_name}/backlinks` for per-page incoming links.
- Kept the markdown files as the source of truth; the graph views are generated artifacts rather than a new manual layer.

## [2026-04-11] service | Add compact graph endpoint for visualization

- Added `GET /wiki/graph/compact` as a frontend-friendly graph view with node id, label, category, and link counts plus stripped-down edges.
- Derived compact node categories from the existing page families so browser clients can color and group the wiki without extra hard-coded logic.
- Kept the compact endpoint generated from the same markdown graph model as the full adjacency map.

## [2026-04-22] ingest | Add VMPR legislative mapping overlay

- Added `raw/efsa-guidance/vmpr-legislative-mapping.md` from the new EFSA VMPR guidance PDF to capture the downstream ETL / LLDB mapping from `sampMatCode` into `Game`, `Wild`, `FoodClassVMPR`, and `FoodClassVMPR_report`.
- Patched `chemical-monitoring-foodex2.md` and `domain-specific-validation.md` so the existing VMPR overlay pages now explain why `F21`, `F23`, `F20`, and `F33` matter for downstream legislative classification, not only for validation.
- Updated `index.md` so the new VMPR mapping page is visible to selectors and human readers as a first-class domain-overlay page.
- Updated the compact graph category mapping so the new VMPR page is emitted as `domain_overlay`, with uncategorized guidance pages now falling back to `guidance` instead of `unknown`.

## [2026-04-22] service | Add macOS LaunchAgent template for persistent wiki API

- Added `deploy/launchd/com.chili36.foodex2-wiki.plist` so the wiki API can run under `launchd` instead of a transient foreground Codex process.
- Documented the install, reload, health-check, and log-inspection commands in `README.md`.
- This is intended to keep `127.0.0.1:8010` alive independently of interactive Codex sessions.

## [2026-05-09] maintenance | Split chemical-monitoring reporting-domain overlays

- Added conditional domain pages for pesticide residues, contaminants, VMPR, and additives/flavourings so domain-specific FoodEx2 rules are retrieved only when the reporting context or candidate set activates them.
- Updated the chemical-monitoring entry page to route to those domain pages and state that default FoodEx2 coding remains all-domain when no reporting domain is known.
- Registered the new pages in the wiki index, schema, viewer quick links, and API page categories as `domain_overlay`.

## [2026-05-14] maintenance | Consolidate GitHub cleanup branch

- Consolidated the stale VMPR legislative-mapping PR, LaunchAgent PR, and local chemical-monitoring overlay commit onto a fresh branch from `main`.
- Replaced hard-coded local LaunchAgent paths with a rendered template installer so the service definition works across checkout locations.
- Added minimal GitHub Actions coverage for the Python test suite and ignored local Codex/Claude experiment artifacts that should not be committed.
- Normalized VMPR mapping inline citation prefixes so model-facing page cleaning strips source boilerplate correctly.

## [2026-05-14] architecture | Define knowledge architecture stance

- Added `KNOWLEDGE_ARCHITECTURE.md` to capture the repo's compiled-wiki, markdown-graph, and long-source ingest strategy.
- Recorded that separate vector or graph infrastructure should wait for observed retrieval failures, because FoodEx2 source additions are rare and source interpretation needs deliberate review.
- Registered the architecture page in the wiki index, schema, API catalog, graph categories, and tests.

## [2026-05-18] guidance | Add facet category reference

- Added a compact `Facet Category Reference` table to `facet-coding-rules.md` so prompt contexts can map facet descriptor candidates to `Fxx` families without carrying a full descriptor catalog.
- Clarified that greenhouse or under-glass growing descriptors belong under `F21` production method or growing condition, while exact descriptor membership still comes from candidate or validator metadata.
- Linked `packaging-facets.md` from the facet page because the reference table now includes `F18` and `F19`.

## [2026-05-19] ingest | Add domoic acid scallop reporting overlay

- Added the EFSA/IDATA scallop matrix workbook `Reportable Scallops list of FoodEx2 codes - MTX.xlsx` as immutable source material and generated `domoic_acid_scallops_mtx.csv` as the normalised lookup extract.
- Created `domoic-acid-scallops.md` as a contaminants-domain overlay for domoic acid in scallops, including the source-provided `sampMatCode` / `sampMatText` matrix table and the FAREA `origFishAreaCode` recommendation.
- Routed domoic-acid/scallop signals through the chemical-monitoring, contaminants, domain-validation, index, schema, README, and API page-category layers.

## [2026-05-23] maintenance | Add wiki doctor and maintenance loop

- Added `wiki_api.doctor` for deterministic wiki health checks covering index registration, page-category registration, link resolution, prompt projection, graph orphans, and source-reference warnings.
- Added scheduled and manual GitHub Actions coverage for the wiki doctor so maintenance drift is reported outside normal feature work.
- Added `MAINTENANCE_WORKFLOW.md` to document deterministic checks, supervised LLM lint, and the maintainer loop.

## [2026-05-23] service | Add deterministic wiki find

- Added `GET /wiki/search` as a non-LLM text finder over served wiki pages, with quoted phrase support, page categories, and snippets.
- Added a Find panel to `/wiki/view` so users can verify whether a claimed rule or phrase exists in the wiki before asking an LLM to interpret it.

## [2026-05-24] maintenance | Add supervised LLM lint runner

- Added `python -m wiki_api.llm_lint` for manual, supervised semantic review of selected wiki pages or the full served wiki.
- The lint runner combines wiki-doctor output, index/log context, graph summary, prompt-projection policy, page backlinks, raw page text, and prompt-projected text into one LLM report payload.
- Reports are written under `reports/wiki-lint-*.md` by default and are intentionally ignored so lint findings remain review artifacts unless promoted into a deliberate PR.

## [2026-05-29] documentation | Document wiki guidance and page-evidence modes

- Updated the project documentation to treat `POST /wiki/ask` as a first-class compact guidance endpoint alongside `POST /wiki/context-pack`.
- Clarified that `/wiki/ask` is useful for short strategy briefs and "what should I think about?" questions, while `/wiki/context-pack` remains the page-evidence path for downstream classifier prompts.
- Added `WIKI_ANSWERER_MODEL` to the documented environment overrides and updated the endpoint list, response summaries, architecture flow guidance, schema runtime serving rules, and index summaries.
- Recorded the practical downstream flow distinction: quick guidance can come before candidate retrieval, while full page context should be reserved for auditability, domain-sensitive cases, facet-heavy cases, or validation-sensitive prompts.

## [2026-05-30] service | Add ask model overrides

- Added optional per-request `selector_model` and `answerer_model` fields to `POST /wiki/ask`.
- Kept the existing environment-driven defaults unchanged when callers omit the override fields.
- Updated the request contract documentation so callers can choose the cost, latency, and accuracy point for broad wiki guidance without changing service configuration.
- Added `scripts/wiki_ask_model_sweep.py` to compare `/wiki/ask` responses, citations, token totals, and timings across model choices.
- Extended `/wiki/ask` overrides beyond Anthropic so `gpt*` models route through OpenAI and `gemini*` models route through the Gemini API.

## [2026-05-30] retrieval | Add markdown Qdrant A/B index

- Added `scripts/index_wiki_qdrant.py` to build `foodex2_wiki_markdown_v1` from the curated markdown wiki using Voyage contextualized embeddings.
- Created the local Qdrant collection with 32 pages, 250 section-aware chunks, cosine vectors at 1024 dimensions, and keyword payload indexes for page/category/section filtering.
- Added `scripts/search_wiki_qdrant.py` so retrieval experiments can probe the markdown vector index before wiring it into any API path.
- Documented that the Qdrant collection is a derived A/B testing artifact; markdown remains the authored source of truth.

## [2026-05-30] retrieval | Add raw source Qdrant index

- Added `scripts/index_source_qdrant.py` to build `foodex2_source_docs_v1` from immutable source files under `foodex2_docs/`.
- Indexed 18 source files into 913 chunks using Voyage contextualized embeddings at 1024 dimensions, with keyword payload indexes for source file, source path, suffix, and location.
- Kept the source collection separate from the markdown collection so A/B tests can distinguish curated guidance retrieval from raw-source evidence retrieval.
- Updated the Qdrant probe script to display either wiki-page metadata or source-document metadata.

## [2026-05-31] maintenance | Add deterministic wiki RAG drift checks

- Added `GET /wiki/rag/status` and `scripts/wiki_rag_status.py` to compare the current markdown-derived wiki chunks with the live `foodex2_wiki_markdown_v1` Qdrant collection.
- Added optional `python -m wiki_api.doctor --check-rag-index` coverage so missing, stale, orphaned, malformed, or embedding-mismatched chunks can fail maintenance checks when Qdrant is available.
- Extended the markdown indexer with `--delete-orphans` and `--manifest-path` so incremental rebuilds can remove stale chunks and write a reproducible manifest for the derived index.

## [2026-06-06] policy | Treat wiki pages as coding evidence

- Updated `RUNTIME_RULES.md` so downstream classifiers treat returned wiki pages as coding knowledge, not merely background text.
- Kept the anti-invention guard by allowing only codes explicitly present in candidates, returned wiki pages, catalogue data, or validator evidence.
- Clarified that when the wiki establishes a required concept but no explicit code is present in returned evidence, the classifier should mark the candidate set incomplete instead of forcing a misleading near-match.

## [2026-06-06] guidance | Clarify VMPR non-food blood matrices

- Strengthened `vmpr-foodex2.md` so blood, blood serum, and plasma taken as VMPR non-food biological samples are routed to `A0C60 Non-food animal-related matrices` with explicit `F01` and `F02`, while preserving the ordinary FoodEx2 workflow for edible blood products outside VMPR non-food sampling.
- Grounded the rule in ChemMon 2025/2026 examples: non-food matrices use `A0C60`, and sheep blood serum is shown as `A0C60#F01.A0CDE$F02.A0CEY`.
- Updated the ChemMon overview and wiki index summary so retrieval exposes the blood/serum/plasma boundary without applying it to ordinary all-domain food coding.

## [2026-06-11] source | Add source-tier metadata and ANSES guidance intake

- Added optional `source_tier` page metadata with deterministic doctor validation for `authoritative_rule`, `expert_guidance`, `local_policy`, and `diagnostic`.
- Added `FoodEx2 codification guidance_2025_12_v3.pdf` to `foodex2_docs/` and created `anses-codification-guidance.md` as an `expert_guidance` source note.
- Documented that ANSES guidance can support workflow, examples, conventions, and interpretation, but should not silently override EFSA catalogue data, business rules, ChemMon reporting obligations, or validator behaviour.

## [2026-06-12] ingest | Extract ANSES expert guidance into operational pages

- OCR-extracted the ANSES FoodEx2 codification guidance v3 because the embedded PDF text layer omitted much of the body text.
- Expanded `anses-codification-guidance.md` from a source note into an extracted `expert_guidance` page covering base-term workflow, facet workflow, missing-term conventions, mixed products, range values, and dataset QC checks.
- Patched the core operational pages where ANSES adds reusable guidance: type-before-origin base selection, browser-order caveats, implicit facets as narrowing evidence, range-value handling for single-cardinality numeric facets, flavouring/ingredient review, and practical batch-validation filters.
- Added a sparse-PDF OCR fallback to the source Qdrant indexer so raw-source retrieval can index the ANSES PDF body text rather than the incomplete embedded text layer.
- Kept authority boundaries explicit: ANSES guidance informs conventions and examples, while current EFSA catalogue data, business rules, ChemMon/domain guidance, and validator behaviour remain higher-authority sources.

## [2026-06-12] ingest | Add retroactive ANSES source impact report

- Updated `INGEST_WORKFLOW.md` so future source ingests include a source impact report before operational page edits.
- Added `reports/source-intake/anses-codification-guidance-2025-12-v3.md` as a retroactive report for the ANSES document, covering novelty, overlap, conflicts, ingest risks, justified wiki changes, and candidate regression cases.
- Linked the report from `anses-codification-guidance.md` so the expert-guidance page keeps its intake rationale visible.

## [2026-06-13] maintenance | Enable thinking for offline lint and source intake

- Added Anthropic adaptive thinking support to the supervised LLM lint runner, enabled by default for offline semantic review and disabled with `--no-thinking` or `WIKI_LINT_THINKING=0`.
- Added `python -m wiki_api.source_intake` for LLM-assisted source impact reports before ingest, using `WIKI_INTAKE_MODEL` and adaptive thinking by default.
- Kept runtime wiki endpoints unchanged: `/wiki/ask`, `/wiki/context-pack`, and `/wiki/ask-rag` do not enable thinking by default.

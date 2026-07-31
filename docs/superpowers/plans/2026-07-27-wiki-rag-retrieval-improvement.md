# Wiki RAG Retrieval and Grounding Improvement Plan

> **For agentic workers:** Implement this plan phase by phase. Do not change the
> embedding model, answerer model, or production collection in place without
> David's approval. Every phase has an evidence gate; stop when the gate is met
> rather than automatically rebuilding the index.

**Goal:** Make `POST /wiki/ask-rag` retrieve a diverse, policy-compatible evidence
set and produce answers whose material claims are supported by that evidence,
while preserving local operation and interactive latency.

**Architecture:** Keep Qdrant as the topical candidate retriever, but separate
candidate retrieval from final context assembly. Retrieve a larger candidate
pool, select unique and complementary pages, reject conflicting domain overlays,
and add policy-required foundations for explicit coding requests. Give the
answerer merged page evidence with claim-level citations and deterministic checks
for unsupported FoodEx2 identifiers. Change chunking or embeddings only if this
retrieval-only work fails its evaluation gate.

**Tech stack:** Python 3, FastAPI, Qdrant, Voyage contextual embeddings, pytest,
the existing markdown wiki and selection policy, and the existing local/hosted
answerer adapters.

## Why This Work Is Needed

The 2026-07-26 diagnostic found:

- The wiki index is structurally healthy: 33 expected/indexed pages, 266
  expected/indexed chunks, and no missing, stale, orphaned, duplicate-ID, model,
  or dimension drift.
- Current search asks Qdrant for exactly `limit` nearest chunks. For wiki mode,
  `limit=7` therefore means seven chunks, not seven unique pages.
- `pages_used` is deduplicated only after retrieval. Duplicate chunks are not
  replaced with the next-best distinct page, and all duplicate chunks are still
  sent to the answerer.
- The table-grapes test returned seven chunks but only two unique pages. Several
  slots came from `pesticides-foodex2.md`; a semantically similar contrast
  section also leaked `contaminants-foodex2.md`.
- Against the current context-pack page labels, the diagnostic retrieval run
  produced 33.1% mean must-have page recall, 67.1% precision, 48.7% leak-free
  cases, zero fully covered cases, and six zero-recall cases. This is a
  diagnostic, not a direct answer-accuracy score, because the labels were
  designed for comprehensive context packs.
- Qdrant itself was fast: about 38 ms mean search time and about 348 ms mean
  embedding-plus-search time. Retrieval quality, not vector-database latency, is
  the immediate constraint.
- Local GPT-OSS answers demonstrated both outcomes: correctly grounded answers
  when the relevant page was present, and unsupported or misstated rules when
  evidence was missing or the model overreached.

## Diagnosis

The current evidence points to a retrieval-assembly problem before it points to
bad wiki prose or failed ingestion:

1. Repeated chunks from one page crowd out complementary pages.
2. Generic but operationally required pages are less similar to food-specific
   questions than topical domain pages.
3. No metadata policy excludes incompatible domain overlays.
4. No reranking step evaluates coverage of the evidence set as a whole.
5. The answer contract lists citations globally; it does not connect individual
   claims to supporting pages.
6. Repeated title, summary, and category text in every chunk may amplify
   same-page clustering, but this should be tested only after assembly is fixed.

## Scope and Non-Goals

### In scope

- Wiki-mode retrieval for `POST /wiki/ask-rag`.
- A retrieval-only evaluation and a separate end-to-end answer evaluation.
- Candidate oversampling, page diversity, metadata filtering, policy backfill,
  context budgeting, and grounding checks.
- Trace changes that make every retrieval decision auditable.
- Versioned index experiments if the no-reindex phases do not meet their gates.

### Initially out of scope

- Rewriting or consolidating wiki pages.
- Replacing Qdrant.
- Replacing Voyage embeddings.
- Changing the production model defaults.
- Changing source-document RAG behavior. Source mode must remain backward
  compatible while wiki mode is improved.
- Treating context-pack page recall as a complete measure of answer quality.

## Success Criteria

All criteria apply to the reviewed wiki-RAG evaluation set.

### Retrieval

- Mean unique pages delivered is at least 6 when `limit=7`, unless fewer than six
  candidates pass policy filters.
- Duplicate-slot waste is at most 10%.
- Explicit-domain overlay leak rate is at most 2%.
- Coding requests receive base-term, facet, and validation coverage in at least
  90% of cases.
- Retrieval-only page recall improves materially over the 33.1% diagnostic
  baseline; target at least 75% before considering re-indexing.
- P95 embedding plus Qdrant plus assembly latency remains below 1 second on the
  current environment.

### Answers

- Every material bullet has at least one valid citation.
- Every FoodEx2 code or facet identifier in an answer is present in its cited
  evidence or the answer explicitly labels it as unavailable.
- No citations refer to evidence absent from the final context.
- At least 90% of reviewed answers are acceptable for a cautious advisory brief.
- Warm local end-to-end P95 latency remains below 15 seconds with the selected
  local answerer.

## Phase Map

| Phase | Deliverable | Evidence gate |
| --- | --- | --- |
| 0 | Dedicated retrieval and answer evaluations | Baseline is reproducible and separates retrieval from generation |
| 1 | Oversampling, unique-page assembly, merged evidence | Diversity improves without re-indexing or breaking source mode |
| 2 | Domain filtering and policy-required foundations | Overlay leaks and foundational misses meet targets |
| 3 | Optional reranking and context budgeting | Coverage target is met within latency/token budget |
| 4 | Claim-level grounding and identifier checks | Unsupported identifiers are blocked and citation coverage meets target |
| 5 | Versioned chunk/index experiments | Only enter if Phases 1–4 plateau below retrieval target |
| 6 | Production rollout, monitoring, and documentation | Repeated eval passes are stable and rollback is tested |

---

## Phase 0: Build the Right Evaluation

The existing selection gold set remains useful as a retrieval diagnostic, but it
must not be presented as direct RAG answer accuracy.

### Task 0.1: Create pure retrieval scoring

**Files:**

- Create: `wiki_api/rag_scoring.py`
- Create: `tests/test_rag_scoring.py`

Implement pure functions for:

- unique page recall and precision;
- duplicate-slot waste;
- unique-page count;
- explicit-domain overlay leaks;
- required-role coverage;
- citation validity;
- unsupported FoodEx2 identifier detection;
- aggregate mean, median, P95, and case-count metrics.

Tests must cover:

- seven chunks from two pages;
- duplicate chunks that do not inflate unique-page recall;
- a pesticides request containing a contaminants overlay;
- no-domain requests containing any exclusive overlay;
- allowed citations, missing citations, and fabricated citations;
- identifiers present and absent from cited evidence.

Run:

```bash
.venv/bin/python -m pytest tests/test_rag_scoring.py -v
```

### Task 0.2: Create a retrieval-only runner

**Files:**

- Create: `scripts/wiki_rag_retrieval_eval.py`
- Create: `evals/wiki-rag/retrieval_cases.json`
- Create: `evals/wiki-rag/README.md`
- Output: `reports/wiki-rag-evals/<date>-<label>/retrieval-results.json`

Seed the retrieval cases from the current 39 selection cases, but add explicit
RAG metadata:

```json
{
  "id": "RAG-RET-0001",
  "question": "Bordsdruvor – färsk frukt; reporting domain: pesticides",
  "context": {
    "purpose": "code_construction",
    "reporting_domain": "pesticides"
  },
  "labels": {
    "must_have_pages": [
      "base-term-selection.md",
      "pesticides-foodex2.md",
      "term-type-facet-constraints.md"
    ],
    "acceptable_pages": [],
    "must_not_pages": [
      "contaminants-foodex2.md",
      "vmpr-foodex2.md"
    ],
    "required_roles": ["base_term", "validation", "domain_overlay"]
  }
}
```

The runner must call retrieval without invoking an answerer and record:

- raw candidate chunks and ranks;
- candidate and final unique-page counts;
- final chunks/pages;
- retrieval scores;
- role coverage and leaks;
- embedding, Qdrant, and assembly timings;
- configuration and collection manifest identity.

Support `--repeats`, `--limit`, `--candidate-limit`, `--only-reviewed`, and a
call-budget guard.

### Task 0.3: Create a reviewed end-to-end answer set

**Files:**

- Create: `evals/wiki-rag/answer_cases.json`
- Create: `scripts/wiki_rag_answer_eval.py`
- Output: `reports/wiki-rag-evals/<date>-<label>/answer-results.json`

Start with 12–15 cases covering:

- plain raw commodity;
- pesticides, contaminants, VMPR, and additives;
- mixed/composite food;
- processing and process validation;
- packaging;
- duplicate/single-cardinality validation;
- a question the evidence cannot answer exactly;
- a maintenance or orientation question that must not receive coding-policy
  backfill.

Each case defines:

- required claims;
- forbidden claims;
- whether exact codes are allowed;
- identifiers permitted by evidence;
- expected citation pages;
- an explicit insufficiency expectation where appropriate;
- human-review fields for correctness, support, caveats, and acceptability.

Do not make an LLM judge the sole release gate. An optional grader may assist
triage, but deterministic checks and human review remain authoritative.

### Phase 0 evidence gate

- Baseline numbers reproduce within expected retrieval variance.
- Retrieval and answer metrics are reported separately.
- The report captures enough raw data to explain every miss.

---

## Phase 1: Fix Diversity Without Re-Indexing

### Task 1.1: Separate candidate count from final page limit

**Files:**

- Modify: `wiki_api/qdrant_ask.py`
- Modify: `wiki_api/app.py`
- Create: `tests/test_qdrant_ask.py`
- Modify: `tests/test_wiki_api.py`

For `retrieval_mode="wiki"`:

- Treat request `limit` as the final unique-page limit.
- Retrieve a larger candidate pool, initially
  `candidate_limit = max(30, limit * 5)`, with a safe upper bound.
- Preserve current source-mode semantics.
- Add `candidate_limit` and `final_page_limit` to the trace.

Do not expose internal candidate chunks as returned pages.

### Task 1.2: Add deterministic page-diverse assembly

Create a pure assembler that:

1. accepts ranked raw chunks;
2. groups chunks by `page_name`;
3. ranks pages by their highest-scoring chunk;
4. chooses up to `limit` unique pages;
5. retains up to two useful chunks per selected page;
6. merges retained chunks into one `answerer_page` and one `page_summary` per
   page;
7. respects a total character/token-oriented context budget;
8. records dropped duplicate chunks and budget drops in the trace.

The first implementation should be deterministic. Do not add an LLM reranker in
this task.

Required tests:

- seven top-ranked chunks from one page no longer consume seven final slots;
- final `pages_used`, `pages`, and answerer inputs contain unique pages;
- the next-best distinct pages replace duplicate slots;
- chunk order inside a merged page is stable;
- source mode is unchanged;
- context-budget trimming is deterministic and traceable.

### Phase 1 evidence gate

Run the retrieval eval against baseline and require:

- duplicate-slot waste at or below 10%;
- mean unique pages at least 6 for `limit=7`;
- no material latency regression;
- no source-mode test regression.

If page recall remains below target, continue to Phase 2. Do not re-index yet.

---

## Phase 2: Add Metadata Policy and Foundational Coverage

### Task 2.1: Add explicit request context

**Files:**

- Modify: `wiki_api/app.py`
- Modify: `README.md`
- Modify: `tests/test_wiki_api.py`

Extend `AskRagRequest` with optional structured context:

```json
{
  "purpose": "code_construction",
  "reporting_domain": "pesticides"
}
```

Use explicit caller context when present. Do not guess a domain from weak keyword
matches. A narrowly defined fallback may recognize an explicit phrase such as
`reporting domain: pesticides`, but the trace must label inferred versus supplied
context.

### Task 2.2: Put RAG policy in markdown

**Files:**

- Modify: `raw/efsa-guidance/selection-policy.md`
- Modify: `wiki_api/selection_policy.py`
- Modify: `wiki_api/doctor.py`
- Modify: corresponding tests

Add a machine-readable RAG policy block defining:

- exclusive domain overlays and their reporting domains;
- pages never eligible for ordinary coding asks;
- role members for base-term, facet, and validation coverage;
- defaults allowed only for `purpose=code_construction`.

Keep policy in markdown and enforcement in code. The doctor must verify that
every referenced page exists and has the expected served category.

### Task 2.3: Filter incompatible overlays

Before final page assembly:

- If an explicit reporting domain exists, remove exclusive overlays belonging to
  other domains.
- If a code-construction request explicitly has no domain, remove all exclusive
  overlays.
- Do not remove umbrella or cross-domain pages unless policy marks them
  exclusive.
- Record every removal with page, chunk rank, score, and reason.

### Task 2.4: Add policy-required foundational pages

For `purpose=code_construction` only:

- inspect the diversified page set for base-term, facet, and validation roles;
- add the policy default for an uncovered role;
- prefer a retrieved role member over a default;
- keep the final page cap strict by dropping the lowest-priority non-required
  page;
- load injected page content from the wiki store and clearly mark it as
  `policy_injected` in the trace.

This is a safety backstop, not case-specific routing. Packaging, ingredients,
processing, and niche topic choices remain retrieval/reranking decisions.

### Phase 2 evidence gate

Require:

- explicit-domain overlay leak rate at or below 2%;
- required-role coverage at or above 90%;
- retrieval diagnostic recall at or above 75%;
- transparent backfill rate and reasons;
- no policy injection for maintenance/orientation asks.

---

## Phase 3: Improve Complementary Coverage and Context Budgeting

Enter this phase only if diversified, policy-aware retrieval still misses
case-specific pages such as ingredients, packaging, process validation, or
structural validation.

### Task 3.1: Add a deterministic coverage reranker

Score candidate pages using:

- highest vector score;
- category/role novelty relative to already selected pages;
- explicit request metadata;
- exact heading/title matches;
- penalties for repeated categories or near-duplicate headings;
- curated `related` links as a small tie-breaker, not an automatic inclusion.

Use a greedy maximum-marginal-coverage algorithm with tested weights in one
configuration object. Report component scores in the trace.

Do not add food-specific keyword-to-page rules.

### Task 3.2: Evaluate an optional local reranker

Only after the deterministic reranker has a baseline, evaluate a local model as a
reranker over the 15–25 candidate page summaries. It may choose or reorder
candidates but may not invent page names.

Compare:

- deterministic reranker;
- GPT-OSS page reranker;
- no reranker.

Include recall, precision, leakage, latency, tokens, and repeat stability. Keep
the deterministic policy layer after any model reranker.

### Task 3.3: Make the context budget explicit

Add configuration and trace fields for:

- final page limit;
- chunks per page;
- maximum evidence characters or estimated tokens;
- characters/tokens retained per page;
- budget-related drops.

Prefer losing a second chunk from a page over losing a required unique page.

### Phase 3 evidence gate

Choose the smallest/fastest approach that meets retrieval targets. An LLM
reranker is optional, not presumed.

---

## Phase 4: Strengthen Answer Grounding

### Task 4.1: Require claim-level citations

**Files:**

- Modify: `wiki_api/librarian.py`
- Modify: `wiki_api/app.py`
- Modify: answerer tests

Change the internal answerer JSON contract to return a list of concise claims,
each with its supporting page filenames. Preserve the public `answer` and
`citations` response fields for backward compatibility by rendering the claims
and aggregating their citations.

Reject citations not present in the final evidence set.

### Task 4.2: Add deterministic identifier support checks

Extract FoodEx2-like base codes, facet families, and descriptor identifiers from
each answer claim. Require each atomic identifier to appear in the cited
evidence. If an identifier is absent:

- do not silently return the unsupported claim;
- replace it with a clear insufficiency statement, or fail the answer validation
  so the endpoint can return a conservative response;
- record the unsupported identifier and claim in the trace.

Do not require a fully assembled code string to appear verbatim if all of its
atomic components and assembly rule are separately supported.

### Task 4.3: Add evidence-aware insufficiency behavior

The prompt and tests must require the answerer to state that evidence is
insufficient when:

- the retrieved pages do not provide an exact requested code;
- a required rule or descriptor is absent;
- retrieved pages conflict without a policy-supported resolution.

Add regression cases for the observed `F03`, `F28`, and exact-code errors.

### Phase 4 evidence gate

- No unsupported identifiers in the reviewed eval.
- Every material claim has a valid citation.
- Human reviewers judge at least 90% of answers acceptable.
- Local latency remains within the target.

---

## Phase 5: Run Versioned Ingestion Experiments Only If Needed

Do not mutate `foodex2_wiki_markdown_v1` in place. Each experiment gets a new
collection and manifest.

### Candidate experiments

1. Chunk sizes around 1,200, 1,800, and 2,800 characters.
2. Remove repeated full page summaries from section-chunk embedding text while
   keeping metadata in payload.
3. Embed page `select_when` text alongside title and heading.
4. Compare contextual page embeddings with independent chunk embeddings.
5. Add a page-level summary vector collection for first-stage page retrieval,
   followed by section retrieval within selected pages.
6. Evaluate hybrid lexical/vector retrieval for exact rule names and identifiers.

### Required experimental discipline

- Same reviewed cases, query text, final page limit, reranker, and answerer.
- At least three retrieval repeats where the provider can vary.
- Record collection manifest, chunk counts, latency, and embedding cost.
- Promote only a statistically and operationally meaningful improvement.
- Keep the prior collection available for rollback.

### Phase 5 evidence gate

Adopt a new index only if it materially improves retrieval or answer quality
beyond Phases 1–4 without unacceptable latency or maintenance cost.

---

## Phase 6: Rollout and Monitoring

### Task 6.1: Add a feature flag

Introduce a retrieval strategy setting with at least:

- `legacy_topk`;
- `diverse_policy`;
- optional `diverse_policy_reranked`.

The response trace must report the active strategy. This provides an immediate
rollback path.

### Task 6.2: Add operational metrics

Log and aggregate:

- candidate chunks;
- unique candidate and final pages;
- duplicate-slot waste;
- domain-filter drops;
- policy injections;
- context-budget drops;
- citation count and unsupported identifiers;
- embedding, Qdrant, assembly, reranker, answerer, and total latency.

Never log secrets or raw credentials.

### Task 6.3: Update documentation

**Files:**

- Modify: `README.md`
- Modify: `WIKI_ARCHITECTURE_FOR_MODELS.md`
- Modify: `.env.example`

Document:

- what `limit` means in wiki and source modes;
- optional request context;
- candidate retrieval versus final evidence assembly;
- deterministic policy behavior;
- trace fields;
- local model expectations;
- index version and rollback procedure.

### Task 6.4: Final verification

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m wiki_api.doctor --check-rag-index
.venv/bin/python scripts/wiki_rag_retrieval_eval.py \
  --base-url http://127.0.0.1:8010 \
  --label diverse-policy-final \
  --repeats 3
.venv/bin/python scripts/wiki_rag_answer_eval.py \
  --base-url http://127.0.0.1:8010 \
  --label local-answerer-final
```

Conduct human review of the answer set before making the new strategy the
default.

## Recommended Implementation Order

1. Phase 0 evaluation.
2. Phase 1 oversampling and page diversity.
3. Re-evaluate.
4. Phase 2 domain filtering and foundational policy.
5. Re-evaluate.
6. Phase 3 reranking only for remaining case-specific misses.
7. Phase 4 grounding.
8. Re-evaluate end to end with the intended local answerer.
9. Enter Phase 5 only if retrieval remains below target.
10. Roll out behind a strategy flag.

## Expected Outcome

The likely winning design does not replace the curated wiki or Qdrant. It uses:

- Qdrant for fast topical candidate discovery;
- deterministic assembly for page diversity and explicit policy;
- an optional reranker for complementary case-specific coverage;
- a local answerer constrained to claim-level evidence.

This aligns the retrieval layer with the role-oriented wiki architecture already
in place, while keeping re-indexing and wiki restructuring as evidence-driven
options rather than assumptions.

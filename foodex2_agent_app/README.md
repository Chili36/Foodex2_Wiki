# FoodEx2 Agent App

Tool-using FoodEx2 coding agent.

This app is intentionally separate from the wiki API. The agent emulates a human FoodEx2 coder by using tools against authoritative APIs:

- FoodEx2 catalogue/database API for terms, scope notes, hierarchy, facets, and implicit facets.
- Qdrant-backed semantic search for fuzzy candidate recall.
- FoodEx2 wiki API for guidance pages and rule context.
- FoodEx2 validator API for final code validation and repair signals.

It should not use vector matches as the source of truth. Semantic search proposes candidates; the catalogue, wiki, and validator provide the authority.

## Run

```bash
cd foodex2_agent_app
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn foodex2_agent.app:app --reload --port 8020
```

Open:

```text
http://127.0.0.1:8020/
```

## Configuration

Required:

- `OPENAI_API_KEY`
- `FOODEX2_CATALOG_API_URL`
- `FOODEX2_VALIDATOR_API_URL`

Optional:

- `FOODEX2_WIKI_API_URL`, default `http://127.0.0.1:8010`
- `FOODEX2_CATALOG_API_URL`, default `http://localhost:5178`
- `FOODEX2_VALIDATOR_API_URL`, default `http://localhost:5178`
- `FOODEX2_SEMANTIC_SEARCH_URL`, default `http://127.0.0.1:8001/search`
- `FOODEX2_SEMANTIC_COLLECTION`, default `mtx_monitoring_openai_current`
- `OPENAI_MODEL`, default `gpt-5.5`
- `AGENT_MAX_TOOL_ROUNDS`, default `12`
- `AGENT_TOOL_MODEL_MAX_ITEMS`, default `12`; caps list results sent back to the model
- `AGENT_TOOL_TRACE_MAX_ITEMS`, default `8`; caps list results shown in the UI trace
- `AGENT_RUN_LOG_DIR`, default `logs`; stores full JSONL run logs outside git

The default catalogue and validator paths target the local FoodEx2 Code Validator app:
`/api/search`, `/api/term/{code}`, and `/api/validate`. The child-term endpoint is left blank because the validator app does not currently expose one; the agent still gets hierarchy memberships and implicit facets from `/api/term/{code}`.

## Run Logs And Trace

Each agent run writes a JSONL log file under `foodex2_agent_app/logs/`. The UI response includes the `runId` and `logFile`.

The UI trace is intentionally compact: catalogue and facet search results are capped and long strings are shortened. The full raw tool result is in the JSONL log, while the model receives a bounded tool output so one broad database query cannot fill the whole reasoning loop.

## Agent Contract

The agent must:

1. Build a mission-level coding strategy before searching for building blocks.
2. Use semantic search for fuzzy candidate recall.
3. Inspect promising candidates in the authoritative catalogue.
4. Ask the wiki for a policy pack, using the source term and small verified candidate set.
5. Draft a code only from returned catalogue terms/facets.
6. Validate the draft.
7. Repair and revalidate if needed.
8. Return final JSON plus a trace of tool calls.

Every FoodEx2 factual claim should be traceable to one of:

- catalogue/database tool output
- wiki tool output
- validator tool output

## Future Modeling Notes

These are deliberately only partly wired into the first version of the agent:

- Qdrant/vector search is available as a recall helper for query planning, synonyms, and finding likely catalogue terms. It should not become the authority for the final FoodEx2 facts.
- A deconstructor step can be added before catalogue lookup to split difficult source text into base food, process, medium, ingredient, source species, domain hints, and numeric/qualitative descriptors.
- If added, deconstructor output should be treated as a hypothesis. The agent must verify each extracted claim against catalogue terms, wiki rules, and validator results.
- The useful experiment is to compare modes: direct catalogue search only, deconstructed catalogue search, vector-assisted search, and vector plus deconstruction. The trace should make clear which tool produced each candidate and which tool verified it.

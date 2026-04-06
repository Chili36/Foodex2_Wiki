# LLM Knowledge Base

This repository contains a structured markdown knowledge base for EFSA FoodEx2 guidance and FoodEx2 validation policy.

It follows the "LLM wiki" pattern: raw source documents stay immutable, while an LLM incrementally builds and maintains a topic-oriented markdown layer that is easier to read, search, cite, and update over time.

See [PROJECT_CONTEXT.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/PROJECT_CONTEXT.md) for the project rationale and the connection to Andrej Karpathy's `llm-wiki` gist.

## Current Status

Yes: the wiki layer has been created.

At the moment, the repository contains:

- Immutable source PDFs in [foodex2_docs](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/foodex2_docs)
- LLM-maintained topic pages in [raw/efsa-guidance](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance)
- A content index in [index.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/index.md)
- A chronological wiki log in [log.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/log.md)
- A validator-rule layer distilled from the sibling `Foodex2 Code Validator` project
- A local FastAPI retrieval service in `wiki_api/` so client applications can request an LLM-built policy pack from this repo instead of owning wiki navigation themselves

The current wiki pages include:

- [foodex2-overview.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/foodex2-overview.md)
- [base-term-selection.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/base-term-selection.md)
- [facet-coding-rules.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/facet-coding-rules.md)
- [implicit-vs-explicit-facets.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/implicit-vs-explicit-facets.md)
- [code-string-format.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/code-string-format.md)
- [process-facets.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/process-facets.md)
- [ingredient-facets.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/ingredient-facets.md)
- [packaging-facets.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/packaging-facets.md)
- [validation-rules.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/validation-rules.md)
- [structural-validation.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/structural-validation.md)
- [term-type-facet-constraints.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/term-type-facet-constraints.md)
- [process-validation-rules.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/process-validation-rules.md)
- [domain-specific-validation.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/domain-specific-validation.md)
- [maintenance-history.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/maintenance-history.md)
- [maintenance-2015.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/maintenance-2015.md)
- [maintenance-2016-2018.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/maintenance-2016-2018.md)
- [maintenance-2019.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/maintenance-2019.md)
- [maintenance-2020.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/maintenance-2020.md)
- [maintenance-2021.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/maintenance-2021.md)
- [maintenance-2022.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/maintenance-2022.md)
- [maintenance-2023.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/maintenance-2023.md)
- [maintenance-2024.md](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/raw/efsa-guidance/maintenance-2024.md)

Still not added:

- A formal ingest workflow document

## Directory Layout

```text
foodex2_docs/
  Raw EFSA PDF sources

raw/efsa-guidance/
  Topic-oriented markdown knowledge pages derived from the PDFs,
  including guidance pages, validator-rule pages, and annual maintenance pages

wiki_api/
  FastAPI service exposing the wiki catalog, raw page reads, and
  an LLM-driven policy-pack retrieval endpoint for external clients such as DMT
```

## Page Conventions

Each wiki page should:

- Use YAML frontmatter
- List source PDFs
- Include related-page links
- Keep source-page comments such as `<!-- Source: ... -->`
- Stay concise and scannable
- Attribute claims to source pages or sections
- Prefer topic pages over document dumps

## How This Is Intended To Work

1. Add new EFSA or related source files to `foodex2_docs/`.
2. Read those sources and extract durable rules, examples, and terminology.
3. Update or create topic pages under `raw/efsa-guidance/`.
4. Keep the markdown layer as the default working surface for future FoodEx2 coding questions.
5. Use the PDFs and validator sources as the source of truth whenever a claim needs verification.

## Wiki API

This repo now owns the wiki retrieval surface. Client applications should call this service instead of re-implementing wiki selection logic elsewhere.

Create and use the repo-local environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Then edit [`.env.example`](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/.env.example) into a local `.env`, or edit the generated [`.env`](/Users/davidfoster/Dev/LLM%20Knowledge%20Base/.env) directly:

```bash
cp .env.example .env
```

Set at least:

```bash
ANTHROPIC_API_KEY=...
WIKI_LIBRARIAN_MODEL=claude-3-7-sonnet-latest
```

Run it locally with:

```bash
. .venv/bin/activate
uvicorn wiki_api.app:app --reload
```

The policy-pack endpoint is LLM-driven and currently uses Anthropic internally. The wiki API loads `ANTHROPIC_API_KEY` and `WIKI_LIBRARIAN_MODEL` automatically from `.env`.
The service injects `index.md` into the first librarian prompt so the model can choose and batch follow-up wiki page reads without spending a separate LLM turn just to fetch the catalog.

Main endpoints:

- `GET /health`: service health check
- `GET /wiki/index`: raw `index.md`
- `GET /wiki/pages`: page catalog with titles and summaries
- `GET /wiki/pages/{page_name}`: one wiki page
- `POST /wiki/policy-pack`: runs the internal wiki librarian, returns selected pages plus a compact policy pack for a coding case

Example `POST /wiki/policy-pack` body:

```json
{
  "search_term": "Tomato basil and garlic sauce in a glass jar",
  "deconstructed_query": {
    "raw_query": "Tomato basil and garlic sauce in a glass jar",
    "base_term": "tomato basil and garlic sauce",
    "components": [
      {"text": "sauce", "kind": "PROCESS"},
      {"text": "glass jar", "kind": "PACKAGING"}
    ]
  },
  "candidates": [
    {"code": "A044C", "name": "Tomato-containing cooked sauces", "termType": "s"},
    {"code": "A07NN", "name": "Jar", "termType": "f"},
    {"code": "A07PF", "name": "Glass", "termType": "f"}
  ],
  "context": {},
  "max_pages": 6,
  "include_page_content": true
}
```

The response includes:

- `pages_used`: selected wiki pages
- `pages`: selected page metadata plus optional markdown content
- `query_classification`: inferred food type, domain, and signals
- `candidate_focus`: promising codes and rejected patterns
- `policy_pack`: compact rules grouped into base-term, facet, validation, domain, and construction buckets
- `trace`: retrieval metadata including the internal page-read trace, token summary, and timing summary

Run tests with:

```bash
. .venv/bin/activate
pytest -q
```

## Scope Notes

- The discontinued Smart Coding App is intentionally not included in this wiki.
- The current emphasis is FoodEx2 coding guidance plus validation logic, not full EFSA data-submission workflow coverage.

# Local MCP pilot

The read-only `foodex2-knowledge` MCP server forwards four tools to the existing
Wiki API. It uses the official Python MCP SDK, pinned to the tested 2.3.0 release,
and communicates with its host over stdio. The adapter opens no listening port.

## Tools

| Tool | Existing API | Model use |
| --- | --- | --- |
| `search_guidance(query, limit=10)` | `GET /wiki/search` | None; literal text/phrase search |
| `get_guidance_page(page_name)` | `GET /wiki/pages/{page_name}` | None; full Markdown and source references |
| `get_coding_context(search_term, candidate_hints=[], context={}, deconstructed_query={}, max_pages=7)` | `POST /wiki/context-pack` | Configured page selector |
| `ask_guidance(question, max_pages=7)` | `POST /wiki/ask` | Configured selector and answerer |

For a coding case, start with `get_coding_context` and reason from the returned
runtime rules, policy contract and guidance. Supply known candidates only, and
specify `context.reporting_domain` only when the reporting domain is explicit.
For a particular rule or phrase, search and then fetch the relevant page. Choose
`ask_guidance` when a concise prepared brief is useful. It returns citation and
source metadata; fetch cited pages when full evidence is needed.

These tools provide guidance and evidence. Catalogue search, code construction,
and final validation remain the caller's responsibility. The pilot does not expose
editing, indexing, maintenance, experimental solvers, or model overrides.

## Install and launch

From the repository root, install the optional adapter dependencies into the
existing environment:

```bash
.venv/bin/python -m pip install -r requirements-mcp.txt
```

Run the Wiki API as described in the main README. If an older service is already
running, restart it after updating the code to load the revision metadata.
The API retains its existing provider credentials and model configuration; the
adapter does not load `.env` or require provider keys of its own.

Launch the adapter with:

```bash
.venv/bin/python scripts/run_wiki_mcp.py
```

A stdio server waits for an MCP host; it is not an interactive command prompt.

For Codex, the local setup uses a connection named `foodex2_knowledge`, with
absolute paths and a 150-second tool timeout. It is registered in the user-level
`~/.codex/config.toml` for access across projects, with matching project settings
in this checkout's `.codex/config.toml` (ignored by Git). Reload the MCP server in
the app's MCP settings to load it.
Codex reads project settings only for trusted projects; see the
[official MCP configuration guide](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).
For another checkout, add the following to its `.codex/config.toml` and replace
the paths:

```toml
[mcp_servers.foodex2_knowledge]
command = "/absolute/path/to/LLM Knowledge Base/.venv/bin/python"
args = ["/absolute/path/to/LLM Knowledge Base/scripts/run_wiki_mcp.py"]
startup_timeout_sec = 15
tool_timeout_sec = 150

[mcp_servers.foodex2_knowledge.tools.get_coding_context]
output_token_limit = 24000
```

Configure a stdio-capable host to launch the interpreter and script using absolute
paths. The launcher works regardless of the host's working directory. For hosts
that use the common `mcpServers` JSON format:

```json
{
  "mcpServers": {
    "foodex2_knowledge": {
      "command": "/absolute/path/to/LLM Knowledge Base/.venv/bin/python",
      "args": ["/absolute/path/to/LLM Knowledge Base/scripts/run_wiki_mcp.py"]
    }
  }
}
```

### Claude Code

Claude Code needs its own registration; it does not inherit Codex's server list.
To make the knowledge base available across Claude Code projects, run this with
the actual checkout paths:

```bash
claude mcp add --scope user --transport stdio foodex2_knowledge -- \
  "/absolute/path/to/LLM Knowledge Base/.venv/bin/python" \
  "/absolute/path/to/LLM Knowledge Base/scripts/run_wiki_mcp.py"
claude mcp get foodex2_knowledge
```

Start a fresh Claude Code session and use `/mcp` to inspect the connection and
available tools. See the [Claude Code MCP guide](https://code.claude.com/docs/en/mcp).

### Claude Desktop

Claude Desktop has a separate server configuration. On macOS, merge the
`foodex2_knowledge` entry from the JSON example above into `mcpServers` in
`~/Library/Application Support/Claude/claude_desktop_config.json`, preserving other
servers and settings. Fully quit and reopen Claude Desktop to load it. See the
[local MCP setup guide](https://modelcontextprotocol.io/docs/develop/connect-local-servers).

### Prompt for Claude

After the connection is available, use this instruction in a conversation or in
the relevant Claude Code project's `CLAUDE.md`:

> Use the `foodex2_knowledge` MCP server for FoodEx2 guidance. For a coding case,
> call `get_coding_context` before making a recommendation. For specific rules,
> use `search_guidance` and `get_guidance_page`; use `ask_guidance` for a cited
> brief. Cite the returned pages and sources. Do not invent FoodEx2 codes or
> treat guidance as final catalogue validation. If the server is unavailable,
> say so rather than claiming to have consulted it.

## Runtime settings

The default API origin is `http://127.0.0.1:8010`. Override it using `--api-url`
or `WIKI_MCP_API_URL`; only loopback HTTP origins are accepted in this pilot.
Set `--timeout` or `WIKI_MCP_TIMEOUT_SECONDS` to change the 120-second HTTP timeout
(allowed range: 1–600 seconds). Configure the host's tool-call timeout slightly
longer than the adapter timeout. Logs go to stderr, leaving stdout for MCP.

Search results are capped at 20, context packs at 4–10 pages including runtime
rules, and guidance briefs at 1–10 pages. Unknown page names and invalid inputs
produce tool errors. Connection, timeout, and backend failures produce actionable
errors without forwarding upstream exception bodies. Calls are not automatically
retried: a timed-out model request may still be running in the API.

## Evidence and revisions

Successful tool results preserve the API JSON as MCP structured content and a
JSON text block, including sources, source tiers, citations and usage traces where
the endpoint provides them. Missing source tiers remain null, not inferred.

The four underlying API endpoints now include `knowledge_revision`, a SHA-256
fingerprint of all served Markdown filenames and contents at response assembly.
This includes uncommitted edits and changes when a served page is added, removed
or edited. It excludes raw PDFs, model settings and derived indexes. It is a
content identifier, not a Git commit, immutable snapshot, or guarantee of identical
model output. Avoid editing the corpus during a reproducibility run; restart the
API after catalogue changes so cached catalogue metadata is refreshed.

## Verification

Offline protocol and API contract tests use real wiki pages with stubbed model
responses, exercise actual stdio launches from another directory, and cover both
current and legacy MCP negotiation:

```bash
.venv/bin/pytest -q tests/test_wiki_mcp.py tests/test_wiki_api.py tests/test_wiki_store_catalog.py tests/test_jev_selector.py
```

With the API running, check real stdio discovery, search and page retrieval without
model calls:

```bash
.venv/bin/python scripts/check_wiki_mcp.py
```

To also exercise the configured providers, run the bounded live check below. It
makes four context selections using reviewed questions plus one guidance request
(which invokes both selector and answerer), and can incur provider charges:

```bash
.venv/bin/python scripts/check_wiki_mcp.py --with-models --output reports/mcp-pilot/live-check.json
```

The report records latency, revisions, selected pages, citations and usage traces.
Reference-page recall is informational: those labels were reviewed for the ask
evaluation, not specifically for context packs. This checks transport, contracts
and basic retrieval behavior; it does not evaluate a host model's tool choices or
establish answer-quality improvement. Hosted multi-user access and authentication
are outside the local pilot.

SDK reference: [official MCP Python SDK](https://py.sdk.modelcontextprotocol.io/).

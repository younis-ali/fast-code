# Fast Code

An open-source AI coding assistant: a **FastAPI** backend with a **LangGraph** agent, **tool execution**, **streaming** responses (Server-Sent Events), and a **web UI**. It talks to **Anthropic** and **OpenAI** APIs, runs Bash and file tools against a configurable working directory, and stores conversations in **SQLite**.

## Demo


1. Configure `.env` with a valid API key, then run: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
2. Open **http://localhost:8000** in your browser.
3. Show a short flow: e.g. new chat → send a message → watch streaming text and tool cards (toggle theme or mode if you want extra polish).
![fast-code](https://github.com/user-attachments/assets/7b9b58f8-261c-4adb-8e23-866e5b68eb6a)



---

## Features

### Agent and streaming

- **LangGraph agent** — The model runs in a graph with an LLM node and a tools node; tool calls can require approval before execution. Responses stream to the client as SSE so you see text and tool activity in real time.
- **Multi-provider models** — Choose a model in the UI or in the JSON body; the server picks the right provider from the model id (and optional `provider` override).

### Chat modes

| Mode | Purpose |
|------|--------|
| **Agent** | Full tool set: read/write files, Bash, web, sub-agents (**Agent**, **Coder**), notebooks, todos, etc. |
| **Ask** | Read-only exploration: **Read**, **Glob**, **Grep**, **WebFetch**, **WebSearch** — no edits, shell, or sub-agents. |
| **Plan** | Same read-only tools as Ask, plus **TodoWrite** after the plan. The model explores the repo, writes a plan, then records implementation steps as todos. The UI shows an **editable plan** panel and **Build plan**, which switches to **Agent** mode and sends an implementation prompt. |

### Web UI

- **Conversation sidebar** — List of chats; **hover a row** to reveal **delete** (trash). Deletion uses a **confirmation dialog**; if the chat is open while streaming, the stream is aborted first. Theme preference is stored in `localStorage`.
- **Dark / light theme** — **Theme** button in the header (sun / moon) toggles appearance; choice persists across visits.
- **Model and mode** — Dropdowns for model and chat mode (Agent / Ask / Plan).
- **Auto-approve tools** — When enabled, tools that would normally ask for approval run without prompting.
- **Tool cards** — Chronological tool calls with expandable inputs/outputs and status badges.
- **File autocomplete** — Type **`/`** in the message box to search paths under the configured working directory.
- **Plan workflow** — After a Plan-mode reply, edit the plan in the panel and click **Build plan** to run implementation in Agent mode.

### Built-in tools

| Tool | Role |
|------|------|
| **Bash** | Shell commands (timeout, optional approval) |
| **Read** | Read files (line numbers, images, binary hint) |
| **Write** | Create/overwrite files |
| **Edit** | Exact string replace in files |
| **Glob** | Find files by glob |
| **Grep** | Content search (ripgrep when available) |
| **WebFetch** | Fetch URL as text |
| **WebSearch** | Web search (DuckDuckGo) |
| **NotebookEdit** | Jupyter notebook cells |
| **TodoWrite** | In-memory task list (server process scope) |
| **Agent** | Nested sub-agent with the same tool surface (respects parent chat mode) |
| **Coder** | Coding sub-agent with a restricted tool set (no nested agents) |

### Safety and configuration

- **Tool approval** — Destructive or sensitive tools can pause until the user approves in the UI (`POST /api/tool-approve`).
- **Working directory** — Set **`WORK_DIR`** so file tools and `/` autocomplete resolve to your project root.
- **Conversation storage** — SQLite stores threads, messages, model, and token counts.

### Optional: MCP explorer

A separate **MCP** package can browse a codebase over STDIO or HTTP. See [MCP Explorer](#mcp-explorer) below.

---

## Quick start

### Prerequisites

- Python 3.11+
- At least one of: **Anthropic** API key, **OpenAI** API key

### Install

**Option A — uv (recommended)** — uses the pinned **`uv.lock`** for reproducible installs:

```bash
cd fast-code
uv sync                 # runtime deps from uv.lock
uv sync --extra dev     # include dev deps (pytest, ruff, …) for contributing
```

**Option B — pip**

```bash
cd fast-code
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# or: pip install -e ".[dev]"
```

The **`uv.lock`** file **should be committed** to Git (see [Contributing](#contributing)). It records exact dependency versions; after changing `pyproject.toml`, run `uv lock` and commit the updated lockfile.

### Configure

```bash
cp .env.example .env
# Set ANTHROPIC_API_KEY and/or OPENAI_API_KEY, optional WORK_DIR, etc.
```

### Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** for the web UI.

### Docker

```bash
export ANTHROPIC_API_KEY=sk-ant-...
docker compose up --build
```

---

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Status, default models, configured keys |
| GET | `/` | Web UI |
| POST | `/api/chat` | Streaming chat (SSE). Body includes `messages`, optional `model`, `conversation_id`, `mode` (`ask` \| `agent` \| `plan`), `auto_approve`, etc. |
| POST | `/api/tool-approve` | Resolve pending tool approvals |
| GET | `/api/files/list` | Directory listing for UI autocomplete |
| GET | `/api/conversations` | List conversations |
| POST | `/api/conversations` | Create conversation |
| GET | `/api/conversations/{id}` | Load conversation + messages |
| DELETE | `/api/conversations/{id}` | **Delete** conversation (used by the UI trash control) |
| GET | `/api/tools` | List tool definitions |
| GET | `/docs` | OpenAPI (Swagger UI) |

### Chat request example

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "List Python files here"}],
    "model": "gpt-4o-mini",
    "mode": "agent",
    "stream": true
  }'
```

SSE event types include: `message_start` (may include `chat_mode`), `content_block_delta`, `tool_use_start`, `tool_use_end`, `tool_approval_request`, `tool_execution_start`, `tool_result`, `tool_denied`, `message_stop`, `error`, and a final `[DONE]`.

---

## Environment variables

See **`.env.example`** for the full list. Common entries:

| Variable | Meaning |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude models |
| `OPENAI_API_KEY` | OpenAI models |
| `WORK_DIR` | Default project root for tools and UI `/` paths |
| `DATABASE_URL` | Async SQLite URL for conversations (see `.env.example`) |
| `AUTH_TOKEN` | Optional bearer token for API/UI access |

---

## Contributing

Issues and pull requests are welcome. For larger changes, opening an issue first helps align on direction.

### Dependency lock file

- **Commit `uv.lock` to Git.** It pins exact package versions so CI and contributors get the same dependency graph when using **uv**.
- If you add or bump dependencies in **`pyproject.toml`**, run **`uv lock`** (or **`uv sync`**, which updates the lockfile as needed) and **include the updated `uv.lock`** in your PR.
- People who install with **pip** + **`requirements.txt`** are unaffected by `uv.lock`; both flows are documented in [Install](#install).

### Testing

Run the suite before submitting a PR:

```bash
# Using uv (uses locked versions from uv.lock)
uv sync --extra dev
uv run pytest tests/ -q
```

```bash
# Using pip + editable install
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest tests/ -q
```

Useful variants:

```bash
pytest tests/ -v --tb=short          # verbose, shorter tracebacks
pytest tests/test_chat.py -q        # single file
pytest tests/ -k "chat_modes" -q    # tests whose name contains chat_modes
```

Most tests do **not** call real LLM APIs; they use the in-memory ASGI client or unit assertions. If a test fails only with network or keys, check **`AUTH_TOKEN`** / env and that nothing in `.env` overrides expected defaults.

---

## Project layout

```
fast-code/
├── app/
│   ├── main.py              # FastAPI app, lifespan, routes
│   ├── config.py
│   ├── dependencies.py
│   ├── agent/               # LangGraph graph, LLM, streaming, tools bridge
│   ├── api/                 # chat, sessions, files, …
│   ├── core/                # prompts, chat modes, approval, registry
│   ├── llm/                 # Provider routing
│   ├── tools/               # Bash, Read, Write, Agent, Coder, …
│   ├── services/            # SQLite store
│   └── models/
├── docs/                    # e.g. demo.gif for README
├── mcp_explorer/            # Optional MCP server
├── web/                     # Static UI (HTML, CSS, JS)
├── tests/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── uv.lock                  # Pin dependencies (commit this; use with uv)
└── requirements.txt
```

Runtime artifacts (e.g. local DB, `data/` workspace files, `.venv`) should stay untracked; see **`.gitignore`**.

### Security before you publish

- **Never commit** `.env` — it is listed in `.gitignore`; keep API keys only on your machine or in CI secrets.
- If a key was ever pasted into a tracked file or a public issue, **revoke it** in the provider dashboard and create a new one.
- Optional: run `git log --all --full-history -- .env` (and `git log -p -- path`) before the first public push to confirm `.env` never entered history.
- Set **`AUTH_TOKEN`** in production if the API is exposed beyond localhost.

---

## MCP Explorer

Optional codebase exploration over MCP:

```bash
python -m mcp_explorer.stdio
# or HTTP/SSE: python -m mcp_explorer.http
```

Set **`SRC_ROOT`** to the tree you want to expose.

---

## License

MIT

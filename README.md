# Sub-Agent MCP

Production-ready Python MCP server for **LLM delegation and sub-agent orchestration**. A main LLM connects to this server, discovers configured sub-agents, and delegates work via `spawn_agent`.

Each sub-agent is defined in YAML with its own LLM, system prompt, and connected MCP tool servers.

## Features

- Streamable HTTP transport only (no stdio / legacy SSE)
- YAML-driven agent definitions with strict Pydantic validation
- LangChain 1.x `create_agent` runtime with OpenAI-compatible LLMs
- Per-agent MCP server connections with tool allowlist filtering
- Exposed MCP tools: `list_agents`, `spawn_agent`
- Structured logging, Docker support, GitHub Actions CI

## Quick Start

### Local development

```bash
# Install (uv recommended)
uv sync --dev
# or: pip install -e ".[dev]"

# Copy and edit agent config
cp config/agents.example.yaml config/agents.yaml
export OPENAI_API_KEY=sk-...

# Run the server
python -m sub_agent_mcp.main
```

Server listens at `http://0.0.0.0:8000/mcp`.

### Docker Compose

```bash
export OPENAI_API_KEY=sk-...
docker compose up --build
```

This starts the sub-agent server plus mock `filesystem-mcp` and `search-mcp` servers.

## Cursor MCP Client Config

Add to your Cursor MCP settings:

```json
{
  "mcpServers": {
    "sub-agent-mcp": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## Agent Configuration

Agents are loaded from `config/agents.yaml` (override with `AGENTS_CONFIG_PATH`).

```yaml
agents:
  - id: researcher
    title: Research Agent
    description: "Agent specialized in research tasks"
    llm:
      base_uri: https://api.openai.com/v1
      api_key: ${OPENAI_API_KEY}
      model_id: gpt-4.1-mini
    system_prompt: |
      You are a helpful research assistant.
    mcp_servers:
      - name: filesystem
        transport: streamable_http
        url: http://filesystem-mcp:8001/mcp
      - name: search
        transport: streamable_http
        url: http://search-mcp:8002/mcp
    tool_allowlist:
      - filesystem.read_file
      - search.web_search
```

### Schema reference

| Field | Description |
|-------|-------------|
| `id` | Unique slug (`a-z`, digits, `-`, `_`) |
| `title` | Human-readable name |
| `description` | Agent purpose |
| `llm.base_uri` | OpenAI-compatible API base URL |
| `llm.api_key` | API key (supports `${ENV_VAR}` substitution) |
| `llm.model_id` | Model identifier |
| `system_prompt` | System message injected into the agent |
| `mcp_servers` | Remote MCP servers (`transport` must be `streamable_http`) |
| `tool_allowlist` | Optional list of `server.tool` names; omit to allow all |

Environment variable substitution supports `${VAR}` and `${VAR:-default}`.

## MCP Tools

### `list_agents`

Returns all configured agents with model info, MCP servers, and available tools (after allowlist filtering). API keys are never exposed.

### `spawn_agent`

| Parameter | Description |
|-----------|-------------|
| `agent_id` | Agent id from config |
| `prompt` | User prompt for the sub-agent |

Returns `{ "response": "..." }` on success or `{ "error": "..." }` on failure.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTS_CONFIG_PATH` | `config/agents.yaml` | Path to agents YAML |
| `HOST` | `0.0.0.0` | Server bind host |
| `PORT` | `8000` | Server bind port |
| `LOG_LEVEL` | `INFO` | Log level |
| `MCP_CLIENT_TIMEOUT` | `30` | MCP client timeout (seconds) |
| `AGENT_RECURSION_LIMIT` | `25` | Max agent tool-loop steps |

## Development

```bash
pytest -v
ruff check src tests
```

## Docker Image

Published to GitHub Container Registry on push to `main`:

```
ghcr.io/<owner>/sub-agent-mcp:latest
```

## Architecture

```
Main LLM → Sub-Agent MCP Server → LangChain Agent → OpenAI-compatible LLM
                                 ↘ MCP Tool Servers (per agent)
```

## License

MIT

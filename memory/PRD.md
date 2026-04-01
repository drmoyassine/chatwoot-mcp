# PRD - MCP Hub

## Original Problem Statement
Build a complete MCP (Model Context Protocol) server for Chatwoot Application APIs. Evolved into a multi-MCP platform ("MCP Hub") with authentication, per-app API keys, tool customization, and a dashboard for managing installed MCP servers.

## Long-Term Vision
A no-code MCP server development platform. Users point to a Swagger/OpenAPI spec -> parse endpoints -> select tools & categories -> auto-generate MCP server -> configure auth -> serve at `/api/{app_name}/mcp/sse`.

## Architecture
- **Backend**: FastAPI (Python) with JWT auth, per-app API key management, FastMCP server, MongoDB
- **Frontend**: React + Tailwind + Shadcn UI — Login -> Dashboard Hub -> App-specific dashboards
- **MCP Transports**: SSE (namespaced at `/api/{app_name}/mcp/sse`) + stdio
- **Database**: MongoDB (config, API keys, webhook events, tool overrides, custom tools)
- **Auth**: JWT for dashboard, per-app API keys for external access

## Route Structure
```
/login                          -> Login page
/dashboard                      -> MCP Hub (list of installed servers)
/dashboard/chatwoot             -> Chatwoot control room

/api/auth/login|me|logout       -> Dashboard authentication
/api/apps                       -> List installed MCP apps
/api/apps/{name}/keys           -> API key CRUD
/api/chatwoot/*                 -> Chatwoot-specific endpoints
/api/chatwoot/mcp/sse           -> MCP SSE transport
```

## What's Been Implemented

### Core (2026-03-28)
- 55 MCP Tools across 12+ categories (Chatwoot API coverage)
- Discovery tools: `start_here`, `list_tools`, `search_tools` with TOON compression
- Frontend: Tool Explorer, Test Terminal (Live Testing + API Docs tabs), Filter Builder, Webhook Events
- File attachment support, webhook SSE streaming, Docker deployment

### Auth & Platform (2026-03-29)
- Dashboard Authentication: Admin email/password from env vars -> JWT
- Login page, Dashboard Hub, route protection
- Per-app API keys: Create, list (masked), revoke via UI and REST API
- Dual auth on MCP endpoints: JWT OR API key
- Route namespacing: `/api/chatwoot/*`

### Tool Customization (2026-04-01)
- **Edit existing tool parameters**: Pencil icon on hover (both ToolExplorer and TestTerminal), modal with name/type/required/description/default/enum options
- **Add new parameters**: + button in parameter sections, same modal for creation
- **Create new tools**: "+ New Tool" button -> paste cURL/JSON schema -> auto-parse -> preview & configure -> save
- **Tool on/off toggle**: Switch on every tool in ToolExplorer to enable/disable exposure
- **cURL parser**: Extracts method, path, path params, body params, strips auth/account_id automatically
- **Enum support**: Dropdown rendering in TestTerminal for enum-type params
- **Persistence**: tool_overrides collection (param edits on builtin tools), custom_tools collection (fully new tools)

### Docker Fixes (2026-04-01)
- Fixed Easypanel env var injection: Added ADMIN_EMAIL/ADMIN_PASSWORD/JWT_SECRET to docker-compose.yml environment section
- Auto-generated JWT_SECRET if not set (with warning log)
- Graceful startup when MongoDB is unavailable

## Key DB Collections
- `mcp_config`: Chatwoot connection config
- `api_keys`: Per-app API keys with active/revoked status
- `webhook_events`: Webhook event history
- `tool_overrides`: Parameter edits/additions on builtin tools
- `custom_tools`: Fully custom tool definitions

## Code Architecture
```
/app/
├── backend/
│   ├── auth.py                 # JWT helpers, API key verification
│   ├── chatwoot_client.py      # HTTPX Async client for Chatwoot APIs
│   ├── mcp_tools.py            # FastMCP server, tool definitions, TOON
│   ├── server.py               # FastAPI app, auth/apps/chatwoot routers, tool CRUD, MCP SSE
│   ├── tests/                  # Pytest tests
│   ├── requirements.txt
│   └── requirements.docker.txt
├── frontend/
│   ├── src/
│   │   ├── App.js              # Router with auth guards
│   │   ├── contexts/AuthContext.js
│   │   ├── pages/Login.js, DashboardHub.js, ChatwootDashboard.js
│   │   └── components/
│   │       ├── ApiKeyManager.js, ParamEditModal.js, CreateToolModal.js
│   │       ├── ProtectedRoute.js, Sidebar.js, ToolExplorer.js
│   │       ├── TestTerminal.js, FilterBuilder.js, WebhookEvents.js
├── Dockerfile, docker-compose.yml, .env.example
```

## Prioritized Backlog

### P1 (Important)
- Bulk operations (assign multiple conversations)
- Claude Desktop / Cursor integration guide

### P2 (Nice to Have)
- Dashboard analytics (tool usage stats, response times)
- Export/import tool configurations
- Multiple admin users

### P3 (Long-term Vision)
- Swagger/OpenAPI spec parser -> auto-generate MCP servers
- No-code wizard workflow for new MCP server creation
- Multi-app support (dynamic router registration)

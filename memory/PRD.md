# PRD - MCP Hub

## Original Problem Statement
Build a complete MCP (Model Context Protocol) server for Chatwoot Application APIs. Evolved into a multi-MCP platform ("MCP Hub") with authentication, per-app API keys, tool customization, and a dashboard for managing installed MCP servers. Users can dynamically add external MCP servers via GitHub repository URLs, with credentials encrypted at rest.

## Long-Term Vision
A no-code MCP server development platform. Users point to a Swagger/OpenAPI spec -> parse endpoints -> select tools & categories -> auto-generate MCP server -> configure auth -> serve at `/api/{app_name}/mcp/sse`.

## Architecture
- **Backend**: FastAPI (Python) with JWT auth, per-app API key management, FastMCP server, MongoDB
- **Frontend**: React + Tailwind + Shadcn UI — Login -> Dashboard Hub -> App-specific dashboards
- **MCP Transports**: SSE (namespaced at `/api/{app_name}/mcp/sse`) + stdio
- **Database**: MongoDB (config, API keys, webhook events, tool overrides, custom tools, mcp_servers, server_credentials)
- **Auth**: JWT for dashboard, per-app API keys for external access
- **Encryption**: Fernet (AES) for all 3rd-party credentials at rest

## Route Structure
```
/login                          -> Login page
/dashboard                      -> MCP Hub (list of installed servers)
/dashboard/chatwoot             -> Chatwoot control room

/api/auth/login|me|logout       -> Dashboard authentication
/api/apps                       -> List installed MCP apps (builtin + dynamic)
/api/apps/{name}/keys           -> API key CRUD
/api/chatwoot/*                 -> Chatwoot-specific endpoints
/api/chatwoot/mcp/sse           -> MCP SSE transport
/api/servers/parse-github       -> Parse GitHub URL for MCP server info
/api/servers/add                -> Install & register new MCP server
/api/servers/{name}             -> Get/Delete server
/api/servers/{name}/credentials -> Save/Get encrypted credentials
/api/servers/{name}/start|stop  -> Manage server subprocess
/api/servers/{name}/toggle      -> Enable/disable server
/api/servers/{name}/tools       -> List tools from running server
/api/servers/{name}/tools/execute -> Execute tool on running server
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
- Edit existing tool parameters, add new parameters, create new tools via JSON/cURL
- Tool on/off toggle, cURL parser, enum support
- Persistence: tool_overrides and custom_tools collections

### Docker Fixes (2026-04-01)
- Fixed Easypanel env var injection in docker-compose.yml

### Multi-Server MCP Hub (2026-04-01 - 2026-04-02)
- **Backend infrastructure**: Node.js runtime in Dockerfile, `crypto.py` (Fernet AES encryption), `mcp_manager.py` (subprocess lifecycle management via MCP stdio client)
- **GitHub URL parser**: Parses `github.com/org/repo/tree/branch/path` to detect npm/pip packages and run commands
- **Server CRUD API**: Full REST API for adding, configuring, starting, stopping, and removing dynamic MCP servers
- **Encrypted credentials**: All 3rd-party API keys encrypted at rest in `server_credentials` collection
- **Frontend - AddServerModal**: Multi-step modal (URL input -> preview detected package -> install -> configure credentials)
- **Frontend - DashboardHub wiring**: "+ Add MCP Server" button, dynamic server cards with status badges (Running/Stopped/Not configured), runtime tags, and start/stop/delete action buttons
- **Auto-start**: Enabled servers with credentials auto-start on application startup

## Key DB Collections
- `mcp_config`: Chatwoot connection config
- `api_keys`: Per-app API keys with active/revoked status
- `webhook_events`: Webhook event history
- `tool_overrides`: Parameter edits/additions on builtin tools
- `custom_tools`: Fully custom tool definitions
- `mcp_servers`: Registered dynamic MCP servers (name, runtime, command, args, credentials_schema)
- `server_credentials`: Encrypted credential storage per server

## Code Architecture
```
/app/
├── backend/
│   ├── auth.py                 # JWT helpers, API key verification
│   ├── chatwoot_client.py      # HTTPX Async client for Chatwoot APIs
│   ├── crypto.py               # Fernet AES encryption for credentials
│   ├── mcp_manager.py          # MCP subprocess manager + GitHub URL parser
│   ├── mcp_tools.py            # FastMCP server, tool definitions, TOON
│   ├── server.py               # FastAPI app, all routers, MCP SSE
│   ├── tests/                  # Pytest tests
│   ├── requirements.txt
│   └── requirements.docker.txt
├── frontend/
│   ├── src/
│   │   ├── App.js              # Router with auth guards
│   │   ├── contexts/AuthContext.js
│   │   ├── pages/Login.js, DashboardHub.js, ChatwootDashboard.js
│   │   └── components/
│   │       ├── AddServerModal.js  # Multi-step GitHub URL -> install flow
│   │       ├── ApiKeyManager.js, ParamEditModal.js, CreateToolModal.js
│   │       ├── ProtectedRoute.js, Sidebar.js, ToolExplorer.js
│   │       ├── TestTerminal.js, FilterBuilder.js, WebhookEvents.js
├── Dockerfile, docker-compose.yml
```

## Prioritized Backlog

### P1 (Important)
- Detail/management page for dynamic MCP servers (view tools, manage credentials, start/stop, API keys)
- Claude Desktop / Cursor integration guide

### P2 (Nice to Have)
- Dashboard analytics (tool usage stats, response times)
- Bulk operations (assign multiple conversations)
- Export/import tool configurations
- Multiple admin users

### P3 (Long-term Vision)
- Swagger/OpenAPI spec parser -> auto-generate MCP servers
- No-code wizard workflow for new MCP server creation
- Smart crawler/parser (Firecrawl) for APIs without official MCP repos

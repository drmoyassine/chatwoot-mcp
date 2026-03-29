# PRD - MCP Hub (formerly Chatwoot MCP Server)

## Original Problem Statement
Build a complete MCP (Model Context Protocol) server for Chatwoot Application APIs. Evolved into a multi-MCP platform ("MCP Hub") with authentication, per-app API keys, and a dashboard for managing installed MCP servers.

## Long-Term Vision
A no-code MCP server development platform. Users point to a Swagger/OpenAPI spec → parse endpoints → select tools & categories → auto-generate MCP server → configure auth → serve at `/api/{app_name}/mcp/sse`.

## Architecture
- **Backend**: FastAPI (Python) with JWT auth, per-app API key management, FastMCP server, MongoDB
- **Frontend**: React + Tailwind + Shadcn UI — Login → Dashboard Hub → App-specific dashboards
- **MCP Transports**: SSE (namespaced at `/api/{app_name}/mcp/sse`) + stdio
- **Database**: MongoDB (config, API keys, webhook events)
- **Auth**: JWT (httpOnly cookie + Bearer header) for dashboard, per-app API keys for external access

## Route Structure
```
/login                          → Login page
/dashboard                      → MCP Hub (list of installed servers)
/dashboard/chatwoot             → Chatwoot control room

/api/auth/login|me|logout       → Dashboard authentication
/api/apps                       → List installed MCP apps
/api/apps/{name}/keys           → API key CRUD (create, list, revoke)
/api/chatwoot/*                 → Chatwoot-specific endpoints (tools, config, webhooks, MCP)
/api/chatwoot/mcp/sse           → MCP SSE transport
```

## What's Been Implemented

### Core (2026-03-28)
- **55 MCP Tools** across 12+ categories (Chatwoot API coverage)
- Discovery tools: `start_here`, `list_tools`, `search_tools` with TOON compression
- Frontend: Tool Explorer, Test Terminal (Live Testing + API Docs tabs), Filter Builder, Webhook Events
- File attachment support, webhook SSE streaming, Docker deployment

### Auth & Platform (2026-03-29)
- **Dashboard Authentication**: Admin email/password from env vars → JWT session
- **Login page** at `/login` with error handling
- **Dashboard Hub** at `/dashboard` showing installed MCP servers as cards
- **Route protection**: All dashboard/app routes require valid JWT
- **Per-app API keys**: Create, list (masked), revoke via UI and REST API
- **Dual auth on MCP endpoints**: Accept JWT (dashboard) OR API key (external clients like n8n)
- **Route namespacing**: All chatwoot endpoints under `/api/chatwoot/*`
- **API Key Manager UI**: Full CRUD in the chatwoot dashboard's "API Keys" tab
- **Sidebar updates**: Back to hub button, logout button
- `.env.example` updated with auth vars

## Prioritized Backlog

### P0 (Done)
- All core Chatwoot API tools
- Dashboard auth + route protection
- Per-app API key management
- Route namespacing under `/api/chatwoot/*`

### P1 (Important)
- Bulk operations (assign multiple conversations)
- Claude Desktop / Cursor integration guide with JSON config

### P2 (Nice to Have)
- Dashboard analytics (tool usage stats, response times)
- Export/import configuration
- Multiple admin users (currently env-based single admin)

### P3 (Long-term Vision)
- Swagger/OpenAPI spec parser → auto-generate MCP servers
- No-code wizard workflow for new MCP server creation
- Multi-app support in backend (dynamic router registration)

## Code Architecture
```
/app/
├── backend/
│   ├── auth.py                 # JWT helpers, API key verification
│   ├── chatwoot_client.py      # HTTPX Async client for Chatwoot APIs
│   ├── mcp_tools.py            # FastMCP server, tool definitions, TOON
│   ├── server.py               # FastAPI app, auth/apps/chatwoot routers, MCP SSE
│   ├── requirements.txt
│   └── requirements.docker.txt
├── frontend/
│   ├── src/
│   │   ├── App.js              # Router with auth guards
│   │   ├── contexts/
│   │   │   └── AuthContext.js  # Auth state management
│   │   ├── pages/
│   │   │   ├── Login.js
│   │   │   ├── DashboardHub.js
│   │   │   └── ChatwootDashboard.js
│   │   └── components/
│   │       ├── ApiKeyManager.js
│   │       ├── ProtectedRoute.js
│   │       ├── Sidebar.js
│   │       ├── ToolExplorer.js
│   │       ├── TestTerminal.js
│   │       ├── FilterBuilder.js
│   │       └── WebhookEvents.js
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Key DB Collections
- `mcp_config`: Chatwoot connection config
- `api_keys`: Per-app API keys with active/revoked status
- `webhook_events`: Webhook event history

## Next Tasks
- None pending. All user-requested features implemented.

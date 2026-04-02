# PRD - MCP Hub

## Original Problem Statement
Build a complete MCP (Model Context Protocol) server for Chatwoot Application APIs. Evolved into a multi-MCP platform ("MCP Hub") with authentication, per-app API keys, tool customization, a dashboard for managing installed MCP servers, a marketplace of curated + community servers, and per-server management dashboards.

## Long-Term Vision
A no-code MCP server development platform. Users point to a Swagger/OpenAPI spec -> parse endpoints -> select tools & categories -> auto-generate MCP server -> configure auth -> serve at `/api/{app_name}/mcp/sse`.

## Architecture
- **Backend**: FastAPI (Python) with JWT auth, per-app API key management, FastMCP server, MongoDB
- **Frontend**: React + Tailwind + Shadcn UI — Login -> Dashboard Hub (Installed + Marketplace) -> App-specific dashboards
- **MCP Transports**: SSE (namespaced at `/api/{app_name}/mcp/sse`) + stdio
- **Database**: MongoDB (config, API keys, webhook events, tool overrides, custom tools, mcp_servers, server_credentials, marketplace)
- **Auth**: JWT for dashboard, per-app API keys for external access
- **Encryption**: Fernet (AES) for all 3rd-party credentials at rest

## Route Structure
```
/login                          -> Login page
/dashboard                      -> MCP Hub (Installed tab + Marketplace tab)
/dashboard/chatwoot             -> Chatwoot control room
/dashboard/:serverName          -> Dynamic server dashboard (tools, creds, API keys)

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
/api/marketplace/catalog        -> List curated + community servers
/api/marketplace/publish        -> Share installed server to community
/api/marketplace/{slug}         -> Remove from marketplace
```

## What's Been Implemented

### Core (2026-03-28)
- 55 MCP Tools across 12+ categories (Chatwoot API coverage)
- Discovery tools, Filter Builder, Webhook Events, File attachments

### Auth & Platform (2026-03-29)
- JWT admin auth, per-app API keys, route protection, dual auth on MCP endpoints

### Tool Customization (2026-04-01)
- Edit/add params, create tools via JSON/cURL, toggle on/off

### Multi-Server MCP Hub (2026-04-01 - 2026-04-02)
- Backend: Node.js runtime, `crypto.py` encryption, `mcp_manager.py` subprocess manager
- GitHub URL parser, server CRUD API, encrypted credentials
- AddServerModal (multi-step: URL -> preview -> install -> credentials)
- DashboardHub wiring with dynamic server cards (status badges, start/stop/delete)

### Server Dashboard (2026-04-02)
- `/dashboard/:serverName` route with `ServerDashboard.js`
- Sidebar: server info, status, start/stop/restart controls, credential management
- Main area: discovered tools list with test terminal, API key management
- Tool execution against running MCP subprocess

### Marketplace (2026-04-02)
- 12 curated MCP servers: GitHub, GitLab, Slack, PostgreSQL, Brave Search, Filesystem, Memory, Fetch, Puppeteer, Google Drive, Sentry, SQLite
- Category filtering (developer, communication, database, search, utility, automation, storage, monitoring)
- Search functionality
- One-click install from marketplace
- "Installed" badge on already-installed servers
- Community sharing: "Share to Marketplace" button on dynamic servers
- Publish/unpublish API endpoints

## Key DB Collections
- `mcp_config`: Chatwoot connection config
- `api_keys`: Per-app API keys with active/revoked status
- `webhook_events`: Webhook event history
- `tool_overrides`: Parameter edits/additions on builtin tools
- `custom_tools`: Fully custom tool definitions
- `mcp_servers`: Registered dynamic MCP servers
- `server_credentials`: Encrypted credential storage per server
- `marketplace`: Community-published server entries

## Code Architecture
```
/app/
├── backend/
│   ├── auth.py                 # JWT helpers, API key verification
│   ├── chatwoot_client.py      # HTTPX Async client for Chatwoot APIs
│   ├── crypto.py               # Fernet AES encryption
│   ├── mcp_manager.py          # MCP subprocess manager + GitHub URL parser
│   ├── mcp_tools.py            # FastMCP server, tool definitions
│   ├── server.py               # FastAPI app, all routers, marketplace catalog
│   └── tests/                  # Pytest tests
├── frontend/src/
│   ├── App.js                  # Router (login, hub, chatwoot, :serverName)
│   ├── pages/
│   │   ├── Login.js
│   │   ├── DashboardHub.js     # Installed + Marketplace tabs
│   │   ├── ChatwootDashboard.js
│   │   └── ServerDashboard.js  # Dynamic server management
│   └── components/
│       ├── AddServerModal.js   # GitHub URL install flow
│       ├── Marketplace.js      # Catalog grid with search/filter/install
│       ├── ApiKeyManager.js    # Reusable API key CRUD
│       ├── ToolExplorer.js, TestTerminal.js, FilterBuilder.js
│       ├── ParamEditModal.js, CreateToolModal.js
│       ├── WebhookEvents.js, Sidebar.js, ProtectedRoute.js
```

## Prioritized Backlog

### P1 (Important)
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

# PRD - MCP Hub

## Original Problem Statement
Build a complete MCP (Model Context Protocol) server for Chatwoot Application APIs. Evolved into a multi-MCP platform ("MCP Hub") with authentication, per-app API keys, tool customization, dashboard management, marketplace of curated + community servers, and per-server dashboards with editable environment variable schemas.

## Architecture
- **Backend**: FastAPI (Python) with JWT auth, per-app API key management, FastMCP server, MongoDB
- **Frontend**: React + Tailwind + Shadcn UI — Login -> Dashboard Hub (Installed + Marketplace) -> App-specific dashboards
- **MCP Transports**: SSE (namespaced at `/api/{app_name}/mcp/sse`) + stdio
- **Database**: MongoDB (config, API keys, webhook events, tool overrides, custom tools, mcp_servers, server_credentials, marketplace)
- **Auth**: JWT for dashboard, per-app API keys for external access
- **Encryption**: Fernet (AES) for all 3rd-party credentials at rest

## Route Structure
```
/login -> Login
/dashboard -> MCP Hub (Installed + Marketplace tabs)
/dashboard/chatwoot -> Chatwoot control room
/dashboard/:serverName -> Dynamic server dashboard

/api/auth/* -> Authentication
/api/apps -> List installed MCP apps
/api/apps/{name}/keys -> API key CRUD
/api/chatwoot/* -> Chatwoot endpoints
/api/servers/* -> Dynamic server CRUD, start/stop, credentials, tools
/api/marketplace/* -> Catalog, publish, unpublish
```

## What's Been Implemented
- 55 MCP Tools (Chatwoot), discovery tools, filter builder, webhooks, file attachments
- JWT auth, per-app API keys, dual auth on MCP endpoints
- Tool customization (edit/add/create/toggle via JSON/cURL)
- Multi-server infrastructure (Node.js, crypto, subprocess manager)
- GitHub URL parser, AddServerModal (multi-step install)
- **Editable environment variables** in AddServerModal preview + ServerDashboard post-install
- Server Dashboard at /dashboard/:serverName (tools, credentials, start/stop, API keys)
- Marketplace with 12 curated servers, category filtering, search, one-click install, community sharing

## Code Architecture
```
/app/backend/ -> server.py, auth.py, crypto.py, mcp_manager.py, mcp_tools.py, chatwoot_client.py
/app/frontend/src/pages/ -> Login, DashboardHub, ChatwootDashboard, ServerDashboard
/app/frontend/src/components/ -> AddServerModal, Marketplace, ApiKeyManager, ToolExplorer, TestTerminal, etc.
```

## Key DB Collections
mcp_config, api_keys, webhook_events, tool_overrides, custom_tools, mcp_servers, server_credentials, marketplace

## Prioritized Backlog
### P1
- Claude Desktop / Cursor integration guide
### P2
- Dashboard analytics, bulk operations, export/import configs, multiple admin users
### P3
- Swagger/OpenAPI spec -> auto-generate MCP servers, no-code wizard, Firecrawl smart crawler

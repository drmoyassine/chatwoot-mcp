# PRD - MCP Hub

## Original Problem Statement
Build a complete MCP (Model Context Protocol) server for Chatwoot Application APIs. Evolved into a multi-MCP platform ("MCP Hub") with authentication, per-app API keys, tool customization, dashboard management, marketplace, and smart GitHub repo parsing.

## Architecture
- **Backend**: FastAPI (Python), JWT auth, per-app API keys, FastMCP, MongoDB
- **Frontend**: React + Tailwind + Shadcn UI
- **MCP Transports**: SSE + stdio
- **Encryption**: Fernet (AES) for credentials at rest

## Route Structure
```
/login -> Login
/dashboard -> MCP Hub (Installed + Marketplace tabs)
/dashboard/chatwoot -> Chatwoot control room
/dashboard/:serverName -> Dynamic server dashboard
/api/auth/*, /api/apps/*, /api/chatwoot/*, /api/servers/*, /api/marketplace/*
```

## What's Been Implemented
- 55 Chatwoot MCP Tools, discovery, filter builder, webhooks, file attachments
- JWT auth, per-app API keys, dual auth on MCP endpoints
- Tool customization (edit/add/create/toggle)
- Multi-server infrastructure (Node.js, crypto, subprocess manager)
- **Smart GitHub URL parser**: Fetches actual `package.json` from repo to resolve real npm package names. README scanning for env var hints. Monorepo-aware (subpath isolation).
- **npm install fallback**: Registry → GitHub direct install
- **Editable environment variables** in AddServerModal + ServerDashboard
- Server Dashboard at `/dashboard/:serverName` (tools, credentials, start/stop, API keys)
- Marketplace with 12 curated servers, category filtering, search, one-click install, community sharing

## Code Architecture
```
/app/backend/ -> server.py, auth.py, crypto.py, mcp_manager.py, mcp_tools.py, chatwoot_client.py
/app/frontend/src/pages/ -> Login, DashboardHub, ChatwootDashboard, ServerDashboard
/app/frontend/src/components/ -> AddServerModal, Marketplace, ApiKeyManager, ToolExplorer, TestTerminal, etc.
```

## Prioritized Backlog
### P1
- Claude Desktop / Cursor integration guide
### P2
- Dashboard analytics, bulk operations, export/import configs, multiple admin users
### P3
- Swagger/OpenAPI spec → auto-generate MCP servers, no-code wizard

# PRD - Chatwoot MCP Server

## Original Problem Statement
Build a complete MCP (Model Context Protocol) server for Chatwoot Application APIs. The server should allow agents to process customer service requests via the APIs.

## Architecture
- **Backend**: FastAPI (Python) with MCP server (FastMCP), Chatwoot HTTP client, MongoDB for config persistence
- **Frontend**: React + Tailwind + Shadcn UI - 3-column dashboard (Config, Tool Explorer, Live Testing Terminal)
- **MCP Transports**: SSE (mounted on FastAPI at /api/mcp/sse) + stdio (standalone script)
- **Database**: MongoDB for configuration storage

## User Personas
1. **Support Agent** - Uses MCP tools via Claude Desktop/Cursor to manage conversations, contacts, messages
2. **Developer/Admin** - Uses the dashboard UI to configure, explore tools, and test live API calls

## Core Requirements
- [x] Complete Chatwoot Application API coverage (48 tools)
- [x] MCP SSE transport for remote clients
- [x] MCP stdio transport for local CLI
- [x] Frontend config panel with connection testing
- [x] Frontend tool explorer with category filtering and search
- [x] Frontend live testing terminal with JSON output

## What's Been Implemented (2026-03-28)
- **51 MCP Tools** across 12+ categories:
  - Account (get, update)
  - Agents (list, add, update, remove)
  - Contacts (list, create, get, update, delete, search, get conversations)
  - Conversations (list, create, get, filter, counts, toggle status, assign, labels)
  - Messages (get, create, delete, **create with attachment**)
  - Inboxes (list, get, create, update)
  - Teams (list, create, get, update, delete)
  - Labels (list, create, update, delete)
  - Canned Responses (list, create, update, delete)
  - Custom Attributes (list, create)
  - Webhooks (list, create, update, delete, **setup listener**)
  - Reports (get)
  - **Advanced Filters** (filter_conversations_advanced)
- **Discovery Tools**: `start_here`, `list_tools`, `search_tools` with TOON compression toggle
- **Frontend Dashboard** with 3 tabs: Tools, Filters, Webhooks
- **Conversation Filter Builder** - Visual UI with attribute/operator/value dropdowns, AND/OR logic, payload preview
- **File Attachment Support** - Upload files via URL or direct upload in messages
- **Webhook Event Streaming** - Real-time SSE stream + MongoDB persistence + LIVE feed
- **Dockerfile + docker-compose.yml** - Production deployment ready
- **SSE Transport** at /api/mcp/sse
- **stdio Transport** via `python mcp_stdio.py`
- **Config Persistence** in MongoDB

### Added (2026-03-29)
- **TestTerminal API Docs Tab** - Split terminal into "Live Testing" + "API Docs" tabs
  - Auto-generated REST endpoint URL, headers, request body schema
  - Parameter type reference table
  - Ready-to-copy cURL example with copy button
  - Supports both JSON (`/api/tools/execute`) and multipart (`/api/tools/execute-with-file`) endpoints

## Prioritized Backlog
### P0 (Critical) - Done
- All core Chatwoot API tools implemented
- Discovery tools with TOON compression
- API Docs tab in TestTerminal

### P1 (Important)
- Conversation filter tool with advanced payload building UI (DONE)
- File attachment support for messages (DONE)
- Bulk operations (assign multiple conversations, etc.)

### P2 (Nice to Have)
- Claude Desktop / Cursor integration guide with JSON config
- Webhook event listener for real-time updates (DONE)
- Dashboard analytics (tool usage stats, response times)
- Export/import configuration

## Next Tasks
- No pending tasks. All user-requested features implemented.

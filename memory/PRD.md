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
- **48 MCP Tools** across 12 categories:
  - Account (get, update)
  - Agents (list, add, update, remove)
  - Contacts (list, create, get, update, delete, search, get conversations)
  - Conversations (list, create, get, filter, counts, toggle status, assign, labels)
  - Messages (get, create, delete)
  - Inboxes (list, get, create, update)
  - Teams (list, create, get, update, delete)
  - Labels (list, create, update, delete)
  - Canned Responses (list, create, update, delete)
  - Custom Attributes (list, create)
  - Webhooks (list, create, update, delete)
  - Reports (get)
- **Frontend Dashboard** with Swiss/High-Contrast design, Control Room layout
- **SSE Transport** at /api/mcp/sse
- **stdio Transport** via `python mcp_stdio.py`
- **Config Persistence** in MongoDB

## Prioritized Backlog
### P0 (Critical) - Done
- All core Chatwoot API tools implemented

### P1 (Important)
- Conversation filter tool with advanced payload building UI
- File attachment support for messages
- Bulk operations (assign multiple conversations, etc.)

### P2 (Nice to Have)
- Claude Desktop / Cursor integration guide with JSON config
- Webhook event listener for real-time updates
- Dashboard analytics (tool usage stats, response times)
- Export/import configuration

## Next Tasks
1. Add Claude Desktop integration guide with copy-paste JSON config
2. Add more comprehensive error handling for API failures
3. Add conversation filter builder UI
4. Add webhook event streaming

# Chatwoot MCP Server

A complete [Model Context Protocol](https://modelcontextprotocol.io/) server that wraps **all** Chatwoot Application APIs into 51 MCP tools. Connect it to n8n, Claude Desktop, Cursor, or any MCP-compatible client to manage customer conversations, contacts, agents, and more through natural language.

Includes a built-in **dashboard UI** for configuration, tool exploration, and live testing.

---

## Features

- **51 MCP tools** covering every Chatwoot Application API endpoint
- **Dual transport** — SSE (HTTP, for n8n / remote clients) and stdio (for local CLI / Claude Desktop)
- **Dashboard UI** — configure credentials, browse all tools, and live-test from the browser
- **Conversation Filter Builder** — advanced multi-condition filtering with AND/OR logic
- **File attachments** — send files in messages via URL or direct upload
- **Webhook event streaming** — receive Chatwoot events in real-time via SSE
- **Docker-ready** — single `docker compose up` to deploy (API + UI + MongoDB)

---

## Quick Start

### 1. Clone & configure

```bash
cp .env.example .env
```

Edit `.env` with your Chatwoot credentials:

```
CHATWOOT_URL=https://app.chatwoot.com
CHATWOOT_API_TOKEN=your_access_token
CHATWOOT_ACCOUNT_ID=1
```

### 2. Run with Docker Compose

```bash
docker compose up --build -d
```

This starts:
- **MCP Server + Dashboard UI** on `http://localhost:8001`
- **MongoDB** on port 27017

Open `http://localhost:8001` in your browser to access the dashboard.

### 3. Run without Docker

```bash
# Backend
cd backend
pip install -r requirements.docker.txt
cp ../.env.example .env   # then edit with your credentials
uvicorn server:app --host 0.0.0.0 --port 8001

# Frontend (separate terminal, for development)
cd frontend
yarn install
REACT_APP_BACKEND_URL=http://localhost:8001 yarn start
```

---

## Accessing the Dashboard UI

| Deployment | URL |
|------------|-----|
| Docker Compose | `http://localhost:8001` |
| Without Docker (dev) | `http://localhost:3000` (React dev server) |

The dashboard has three tabs:

- **Tools** — Browse all 51 MCP tools by category, search, select and execute with the live testing terminal
- **Filters** — Visual conversation filter builder with attribute/operator/value dropdowns and AND/OR logic
- **Webhooks** — Real-time feed of incoming Chatwoot webhook events

---

## MCP Tools Reference

### Account (2)
| Tool | Description |
|------|-------------|
| `get_account` | Get account details (name, locale, features, settings) |
| `update_account` | Update account name or locale |

### Agents (4)
| Tool | Description |
|------|-------------|
| `list_agents` | List all agents (ID, name, email, role, availability) |
| `add_agent` | Add a new agent (name, email, role) |
| `update_agent` | Update agent name, role, or availability |
| `remove_agent` | Remove an agent by ID |

### Contacts (7)
| Tool | Description |
|------|-------------|
| `list_contacts` | List contacts with pagination and sorting |
| `create_contact` | Create a contact (name, email, phone, identifier) |
| `get_contact` | Get contact details by ID |
| `update_contact` | Update contact name, email, or phone |
| `delete_contact` | Delete a contact |
| `search_contacts` | Search by name, email, phone, or identifier |
| `get_contact_conversations` | Get all conversations for a contact |

### Conversations (9)
| Tool | Description |
|------|-------------|
| `list_conversations` | List with filters (assignee, status, inbox, team, search) |
| `create_conversation` | Create new conversation (inbox, contact, assignee, message) |
| `get_conversation` | Get conversation details by ID |
| `get_conversation_counts` | Get counts by status and assignee type |
| `toggle_conversation_status` | Set status: open, resolved, pending, snoozed |
| `assign_conversation` | Assign to agent and/or team |
| `get_conversation_labels` | Get labels on a conversation |
| `add_conversation_labels` | Set labels on a conversation |
| `filter_conversations_advanced` | Multi-condition filter (status, assignee, inbox, priority, etc.) |

### Messages (4)
| Tool | Description |
|------|-------------|
| `get_messages` | Get messages in a conversation (with pagination) |
| `create_message` | Send a text message (outgoing/incoming, private notes) |
| `delete_message` | Delete a message and its attachments |
| `create_message_with_attachment` | Send a message with a file attachment via URL |

### Inboxes (4)
| Tool | Description |
|------|-------------|
| `list_inboxes` | List all inboxes with channel details |
| `get_inbox` | Get inbox details by ID |
| `create_inbox` | Create inbox (web_widget, api, etc.) |
| `update_inbox` | Update inbox name or auto-assignment |

### Teams (5)
| Tool | Description |
|------|-------------|
| `list_teams` | List all teams |
| `create_team` | Create a team (name, description) |
| `get_team` | Get team details |
| `update_team` | Update team name or description |
| `delete_team` | Delete a team |

### Labels (4)
| Tool | Description |
|------|-------------|
| `list_labels` | List all labels |
| `create_label` | Create label (title, color, sidebar visibility) |
| `update_label` | Update label title, description, or color |
| `delete_label` | Delete a label |

### Canned Responses (4)
| Tool | Description |
|------|-------------|
| `list_canned_responses` | List pre-written message templates |
| `create_canned_response` | Create template (short_code + content) |
| `update_canned_response` | Update template short_code or content |
| `delete_canned_response` | Delete a template |

### Custom Attributes (2)
| Tool | Description |
|------|-------------|
| `list_custom_attributes` | List attribute definitions (conversation or contact) |
| `create_custom_attribute` | Create attribute (text, number, date, list, etc.) |

### Webhooks (5)
| Tool | Description |
|------|-------------|
| `list_webhooks` | List configured webhooks |
| `create_webhook` | Create webhook (URL + event subscriptions) |
| `update_webhook` | Update webhook URL or subscriptions |
| `delete_webhook` | Delete a webhook |
| `setup_webhook_listener` | Quick-setup: register a webhook for real-time events |

### Reports (1)
| Tool | Description |
|------|-------------|
| `get_account_reports` | Get analytics (account, agent, inbox, label, team) |

---

## Connecting to n8n

1. In n8n, add an **MCP Client** node
2. Set the SSE URL to:
   ```
   http://<your-server>:8001/api/mcp/sse
   ```
3. The node will auto-discover all 51 tools

---

## Connecting to Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "chatwoot": {
      "command": "python",
      "args": ["mcp_stdio.py"],
      "cwd": "/path/to/backend",
      "env": {
        "CHATWOOT_URL": "https://app.chatwoot.com",
        "CHATWOOT_API_TOKEN": "your_token",
        "CHATWOOT_ACCOUNT_ID": "1"
      }
    }
  }
}
```

Or use the SSE transport:

```json
{
  "mcpServers": {
    "chatwoot": {
      "url": "http://localhost:8001/api/mcp/sse"
    }
  }
}
```

---

## Webhook Events

To receive real-time Chatwoot events:

1. Register a webhook in Chatwoot (or use the `setup_webhook_listener` tool) pointing to:
   ```
   http://<your-server>:8001/api/webhooks/receive
   ```
2. Events are stored in MongoDB (last 500) and streamed via SSE at:
   ```
   GET /api/webhooks/events
   ```
3. View event history:
   ```
   GET /api/webhooks/events/history?limit=50
   ```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/config` | Get current configuration |
| `POST` | `/api/config` | Save Chatwoot configuration |
| `POST` | `/api/config/test` | Test Chatwoot connection |
| `GET` | `/api/tools` | List all 51 MCP tools with metadata |
| `POST` | `/api/tools/execute` | Execute a tool `{ tool_name, parameters }` |
| `POST` | `/api/tools/execute-with-file` | Execute tool with file upload (multipart) |
| `GET` | `/api/mcp/info` | MCP server status and transport info |
| `GET` | `/api/mcp/sse` | MCP SSE transport endpoint |
| `POST` | `/api/webhooks/receive` | Chatwoot webhook receiver |
| `GET` | `/api/webhooks/events` | SSE stream of webhook events |
| `GET` | `/api/webhooks/events/history` | Recent webhook events from DB |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CHATWOOT_URL` | Yes | Chatwoot instance URL (e.g. `https://app.chatwoot.com`) |
| `CHATWOOT_API_TOKEN` | Yes | API access token from Chatwoot |
| `CHATWOOT_ACCOUNT_ID` | Yes | Numeric account ID |
| `MONGO_URL` | Yes | MongoDB connection string |
| `DB_NAME` | No | Database name (default: `chatwoot_mcp`) |
| `CORS_ORIGINS` | No | Allowed CORS origins (default: `*`) |

---

## Project Structure

```
├── Dockerfile                        # Multi-stage build (Node + Python)
├── docker-compose.yml                # Docker Compose with MongoDB
├── .dockerignore                     # Docker build exclusions
├── .env.example                      # Environment variable template
├── backend/
│   ├── server.py                     # FastAPI app + REST API + MCP SSE + static file serving
│   ├── mcp_tools.py                  # 51 MCP tool definitions
│   ├── mcp_stdio.py                  # Standalone stdio transport entry point
│   ├── chatwoot_client.py            # Async HTTP client for Chatwoot APIs
│   ├── requirements.docker.txt       # Python dependencies (Docker)
│   └── .env                          # Local environment variables
└── frontend/
    ├── package.json                  # React dependencies
    └── src/
        ├── App.js                    # Main app with tab routing
        └── components/
            ├── Sidebar.js            # Config panel + MCP status + navigation
            ├── ToolExplorer.js       # Tool browser with categories and search
            ├── TestTerminal.js       # Live testing terminal (dark theme)
            ├── FilterBuilder.js      # Visual conversation filter builder
            └── WebhookEvents.js      # Real-time webhook event feed
```

---

## License

MIT

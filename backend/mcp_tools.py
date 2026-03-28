"""MCP Server with Chatwoot Application API tools."""
import os
import json
import logging
import httpx
from typing import Optional
from mcp.server.fastmcp import FastMCP
from chatwoot_client import ChatwootClient

logger = logging.getLogger(__name__)

mcp = FastMCP("chatwoot-mcp-server")

# Shared runtime config — set by server.py startup and UI saves
_runtime_config = {
    "chatwoot_url": "",
    "api_token": "",
    "account_id": 0,
}


def set_runtime_config(url: str, token: str, account_id: int):
    """Called by server.py when config is loaded or saved."""
    _runtime_config["chatwoot_url"] = url
    _runtime_config["api_token"] = token
    _runtime_config["account_id"] = account_id


async def _load_config_from_db():
    """Last-resort: load config directly from MongoDB if runtime config is empty."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "chatwoot_mcp")
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=3000)
        db = client[db_name]
        config = await db.mcp_config.find_one({"key": "chatwoot"}, {"_id": 0})
        client.close()
        if config and config.get("chatwoot_url"):
            set_runtime_config(
                config["chatwoot_url"],
                config.get("api_token", ""),
                config.get("account_id", 0),
            )
            logger.info(f"MCP tools loaded config from DB: {config['chatwoot_url']}")
            return True
    except Exception as e:
        logger.warning(f"Failed to load config from DB: {e}")
    return False


async def _get_client() -> ChatwootClient:
    """Get a ChatwootClient from runtime config, env vars, or MongoDB."""
    base_url = _runtime_config["chatwoot_url"] or os.environ.get("CHATWOOT_URL", "")
    api_token = _runtime_config["api_token"] or os.environ.get("CHATWOOT_API_TOKEN", "")
    account_id = _runtime_config["account_id"] or int(os.environ.get("CHATWOOT_ACCOUNT_ID", "0") or "0")

    # If still empty, try loading from MongoDB
    if not base_url or not api_token or not account_id:
        loaded = await _load_config_from_db()
        if loaded:
            base_url = _runtime_config["chatwoot_url"]
            api_token = _runtime_config["api_token"]
            account_id = _runtime_config["account_id"]

    if not base_url or not api_token or not account_id:
        raise ValueError(
            "Chatwoot not configured. Either:\n"
            "1. Set CHATWOOT_URL, CHATWOOT_API_TOKEN, CHATWOOT_ACCOUNT_ID env vars, or\n"
            "2. Open the dashboard UI and save your config there."
        )
    return ChatwootClient(base_url, api_token, account_id)


def _json(data) -> str:
    return json.dumps(data, indent=2, default=str)


# ── Tool registry for discovery ──
import inspect

TOOL_CATEGORIES = {
    "account": "Account management — get and update account details, settings, features",
    "agents": "Agent management — list, add, update, remove support agents",
    "contacts": "Contact management — CRUD, search, filter contacts and their conversations",
    "conversations": "Conversation management — list, create, filter, assign, toggle status, labels",
    "messages": "Message management — send, receive, delete messages and attachments",
    "inboxes": "Inbox management — list, create, update inboxes (web widget, API, email, etc.)",
    "teams": "Team management — create and manage teams of agents",
    "labels": "Label management — create and manage labels for organizing conversations",
    "canned_responses": "Canned responses — pre-written message templates with short codes",
    "custom_attributes": "Custom attributes — define custom fields for contacts and conversations",
    "webhooks": "Webhook management — configure real-time event notifications",
    "reports": "Reports and analytics — account, agent, inbox, label, team metrics",
    "discovery": "Server discovery — list tools, search capabilities, check status",
}


def _classify_tool(name: str) -> str:
    """Determine category from tool name."""
    if name.startswith(("list_tools", "describe_tool", "list_categories", "search_tools", "get_server", "check_connection")):
        return "discovery"
    for cat in ["canned_response", "custom_attribute", "webhook", "report", "agent", "contact",
                 "conversation", "message", "inbox", "team", "label", "account"]:
        if cat in name:
            key = cat.rstrip("s")
            if "canned" in name:
                return "canned_responses"
            if "custom_attribute" in name:
                return "custom_attributes"
            if "webhook" in name and "setup" in name:
                return "webhooks"
            if "webhook" in name:
                return "webhooks"
            if "report" in name:
                return "reports"
            if "assign" in name:
                return "conversations"
            # Pluralize
            for k in TOOL_CATEGORIES:
                if k.startswith(cat):
                    return k
    return "account"


def _get_all_tools_metadata() -> list:
    """Introspect all registered MCP tools and return metadata."""
    tool_manager = mcp._tool_manager
    tools = []
    for name, tool in tool_manager._tools.items():
        fn = tool.fn
        sig = inspect.signature(fn)
        params = []
        for pname, param in sig.parameters.items():
            if pname in ("self", "ctx"):
                continue
            ptype = "string"
            if hasattr(param.annotation, "__name__"):
                ptype = param.annotation.__name__
            elif param.annotation != inspect.Parameter.empty:
                ptype = str(param.annotation).replace("typing.", "")
            info = {"name": pname, "type": ptype, "required": param.default is inspect.Parameter.empty}
            if param.default is not inspect.Parameter.empty and param.default is not None:
                info["default"] = param.default
            params.append(info)
        tools.append({
            "name": name,
            "description": (tool.description or fn.__doc__ or "").strip(),
            "category": _classify_tool(name),
            "parameters": params,
        })
    return tools


# ═══════════════════════════════════════════════════════
# DISCOVERY & DOCUMENTATION TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def list_tools(category: Optional[str] = None) -> str:
    """List all available tools on this MCP server. Optionally filter by category. Returns tool name, description, and parameter summary for each tool.
    Available categories: account, agents, contacts, conversations, messages, inboxes, teams, labels, canned_responses, custom_attributes, webhooks, reports, discovery.
    Call with no arguments to see all tools. Use describe_tool for full parameter details."""
    all_tools = _get_all_tools_metadata()
    if category:
        cat = category.lower().strip()
        all_tools = [t for t in all_tools if t["category"] == cat]
        if not all_tools:
            return _json({"error": f"No tools in category '{category}'", "available_categories": list(TOOL_CATEGORIES.keys())})

    result = []
    for t in all_tools:
        result.append({
            "name": t["name"],
            "category": t["category"],
            "description": t["description"],
            "parameters": t["parameters"],
        })
    return _json({"tool_count": len(result), "tools": result})


@mcp.tool()
async def describe_tool(tool_name: str) -> str:
    """Get the full schema and documentation for a specific tool. Returns complete parameter definitions with types, defaults, and whether they're required. Use this before calling an unfamiliar tool."""
    all_tools = _get_all_tools_metadata()
    tool = next((t for t in all_tools if t["name"] == tool_name), None)
    if not tool:
        suggestions = [t["name"] for t in all_tools if tool_name.lower() in t["name"].lower()]
        return _json({"error": f"Tool '{tool_name}' not found", "did_you_mean": suggestions[:5]})
    return _json(tool)


@mcp.tool()
async def list_categories() -> str:
    """List all tool categories with descriptions and tool counts. Use this to understand what this server can do at a high level before diving into specific tools."""
    all_tools = _get_all_tools_metadata()
    cats = {}
    for t in all_tools:
        c = t["category"]
        if c not in cats:
            cats[c] = {"description": TOOL_CATEGORIES.get(c, ""), "tools": []}
        cats[c]["tools"].append(t["name"])
    result = []
    for name in sorted(cats):
        result.append({
            "category": name,
            "description": cats[name]["description"],
            "tool_count": len(cats[name]["tools"]),
            "tools": cats[name]["tools"],
        })
    return _json({"total_categories": len(result), "total_tools": len(all_tools), "categories": result})


@mcp.tool()
async def search_tools(query: str) -> str:
    """Search for tools by keyword. Searches tool names and descriptions. Use this when you know what you want to do but aren't sure which tool to use. Example queries: 'assign', 'search contact', 'webhook', 'status'."""
    all_tools = _get_all_tools_metadata()
    q = query.lower()
    matches = []
    for t in all_tools:
        score = 0
        if q in t["name"].lower():
            score += 2
        if q in t["description"].lower():
            score += 1
        if score > 0:
            matches.append({**t, "_score": score})
    matches.sort(key=lambda x: -x["_score"])
    for m in matches:
        del m["_score"]
    return _json({"query": query, "results_count": len(matches), "results": matches})


@mcp.tool()
async def get_server_info() -> str:
    """Get MCP server status, version, configuration state, and available transports. Use this as a health check or to understand the server setup."""
    config_set = bool(
        _runtime_config["chatwoot_url"]
        or os.environ.get("CHATWOOT_URL", "")
    )
    all_tools = _get_all_tools_metadata()
    cats = {}
    for t in all_tools:
        cats[t["category"]] = cats.get(t["category"], 0) + 1
    return _json({
        "server": "chatwoot-mcp-server",
        "protocol": "Model Context Protocol (MCP)",
        "chatwoot_configured": config_set,
        "chatwoot_url": _runtime_config.get("chatwoot_url", "")[:30] + "..." if _runtime_config.get("chatwoot_url") else "not set",
        "total_tools": len(all_tools),
        "categories": cats,
        "transports": {
            "sse": "Available at /api/mcp/sse",
            "stdio": "Run: python mcp_stdio.py",
        },
        "quickstart": "Call list_categories to see what's available, then list_tools with a category to explore.",
    })


@mcp.tool()
async def check_connection() -> str:
    """Test the connection to Chatwoot and return account details. Use this to verify credentials are working before running other tools."""
    try:
        client = await _get_client()
        result = await client.get_account()
        return _json({
            "status": "connected",
            "account_name": result.get("name", ""),
            "account_id": result.get("id", ""),
            "locale": result.get("locale", ""),
        })
    except ValueError as e:
        return _json({"status": "not_configured", "error": str(e)})
    except Exception as e:
        return _json({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════
# ACCOUNT TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def get_account() -> str:
    """Get details of the current Chatwoot account including name, locale, features, and settings."""
    client = await _get_client()
    result = await client.get_account()
    return _json(result)


@mcp.tool()
async def update_account(name: Optional[str] = None, locale: Optional[str] = None) -> str:
    """Update the current Chatwoot account details like name or locale."""
    client = await _get_client()
    result = await client.update_account(name=name, locale=locale)
    return _json(result)


# ═══════════════════════════════════════════════════════
# AGENT TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def list_agents() -> str:
    """List all agents in the Chatwoot account. Returns agent ID, name, email, role, availability."""
    client = await _get_client()
    result = await client.list_agents()
    return _json(result)


@mcp.tool()
async def add_agent(name: str, email: str, role: str = "agent") -> str:
    """Add a new agent to the Chatwoot account. Role can be 'agent' or 'administrator'."""
    client = await _get_client()
    result = await client.add_agent(name=name, email=email, role=role)
    return _json(result)


@mcp.tool()
async def update_agent(agent_id: int, name: Optional[str] = None,
                        role: Optional[str] = None,
                        availability: Optional[str] = None) -> str:
    """Update an existing agent's name, role, or availability status."""
    client = await _get_client()
    kwargs = {}
    if name:
        kwargs["name"] = name
    if role:
        kwargs["role"] = role
    if availability:
        kwargs["availability"] = availability
    result = await client.update_agent(agent_id, **kwargs)
    return _json(result)


@mcp.tool()
async def remove_agent(agent_id: int) -> str:
    """Remove an agent from the Chatwoot account by their ID."""
    client = await _get_client()
    result = await client.remove_agent(agent_id)
    return _json(result)


# ═══════════════════════════════════════════════════════
# CONTACT TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def list_contacts(page: int = 1, sort: Optional[str] = None) -> str:
    """List all contacts with pagination (15 per page). Sort by: name, email, phone_number, last_activity_at (prefix with - for descending)."""
    client = await _get_client()
    result = await client.list_contacts(page=page, sort=sort)
    return _json(result)


@mcp.tool()
async def create_contact(name: str, email: Optional[str] = None,
                          phone_number: Optional[str] = None,
                          identifier: Optional[str] = None) -> str:
    """Create a new contact in Chatwoot with name, email, phone number, or external identifier."""
    client = await _get_client()
    kwargs = {}
    if identifier:
        kwargs["identifier"] = identifier
    result = await client.create_contact(name=name, email=email, phone_number=phone_number, **kwargs)
    return _json(result)


@mcp.tool()
async def get_contact(contact_id: int) -> str:
    """Get detailed information about a specific contact by their ID."""
    client = await _get_client()
    result = await client.get_contact(contact_id)
    return _json(result)


@mcp.tool()
async def update_contact(contact_id: int, name: Optional[str] = None,
                          email: Optional[str] = None,
                          phone_number: Optional[str] = None) -> str:
    """Update an existing contact's name, email, or phone number."""
    client = await _get_client()
    kwargs = {}
    if name:
        kwargs["name"] = name
    if email:
        kwargs["email"] = email
    if phone_number:
        kwargs["phone_number"] = phone_number
    result = await client.update_contact(contact_id, **kwargs)
    return _json(result)


@mcp.tool()
async def delete_contact(contact_id: int) -> str:
    """Delete a contact from Chatwoot by their ID."""
    client = await _get_client()
    result = await client.delete_contact(contact_id)
    return _json(result)


@mcp.tool()
async def search_contacts(q: str, page: int = 1) -> str:
    """Search contacts by name, email, phone number, or identifier. Returns matching contacts with pagination."""
    client = await _get_client()
    result = await client.search_contacts(q=q, page=page)
    return _json(result)


@mcp.tool()
async def get_contact_conversations(contact_id: int) -> str:
    """Get all conversations associated with a specific contact."""
    client = await _get_client()
    result = await client.get_contact_conversations(contact_id)
    return _json(result)


# ═══════════════════════════════════════════════════════
# CONVERSATION TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def list_conversations(assignee_type: str = "all", status: str = "open",
                              page: int = 1, q: Optional[str] = None,
                              inbox_id: Optional[int] = None,
                              team_id: Optional[int] = None) -> str:
    """List conversations with filters. assignee_type: me/unassigned/all/assigned. status: all/open/resolved/pending/snoozed. Supports search query and inbox/team filtering."""
    client = await _get_client()
    result = await client.list_conversations(
        assignee_type=assignee_type, status=status, page=page,
        q=q, inbox_id=inbox_id, team_id=team_id,
    )
    return _json(result)


@mcp.tool()
async def create_conversation(inbox_id: int, contact_id: Optional[int] = None,
                               source_id: Optional[str] = None,
                               status: str = "open",
                               assignee_id: Optional[int] = None,
                               team_id: Optional[int] = None,
                               message: Optional[str] = None) -> str:
    """Create a new conversation in Chatwoot. Requires inbox_id. Optionally set contact, assignee, team, initial message, and status."""
    client = await _get_client()
    result = await client.create_conversation(
        inbox_id=inbox_id, contact_id=contact_id, source_id=source_id,
        status=status, assignee_id=assignee_id, team_id=team_id, message=message,
    )
    return _json(result)


@mcp.tool()
async def get_conversation(conversation_id: int) -> str:
    """Get details of a specific conversation by its ID, including messages, meta info, and status."""
    client = await _get_client()
    result = await client.get_conversation(conversation_id)
    return _json(result)


@mcp.tool()
async def get_conversation_counts() -> str:
    """Get conversation counts grouped by status (open, resolved, pending, etc.) and assignee type."""
    client = await _get_client()
    result = await client.get_conversation_counts()
    return _json(result)


@mcp.tool()
async def toggle_conversation_status(conversation_id: int, status: str) -> str:
    """Toggle a conversation's status. Status options: open, resolved, pending, snoozed."""
    client = await _get_client()
    result = await client.toggle_conversation_status(conversation_id, status)
    return _json(result)


@mcp.tool()
async def assign_conversation(conversation_id: int,
                               assignee_id: Optional[int] = None,
                               team_id: Optional[int] = None) -> str:
    """Assign a conversation to an agent and/or team. Pass assignee_id for agent, team_id for team."""
    client = await _get_client()
    result = await client.assign_conversation(conversation_id, assignee_id=assignee_id, team_id=team_id)
    return _json(result)


@mcp.tool()
async def get_conversation_labels(conversation_id: int) -> str:
    """Get all labels assigned to a specific conversation."""
    client = await _get_client()
    result = await client.get_conversation_labels(conversation_id)
    return _json(result)


@mcp.tool()
async def add_conversation_labels(conversation_id: int, labels: list) -> str:
    """Add or set labels on a conversation. Provide a list of label names."""
    client = await _get_client()
    result = await client.add_conversation_labels(conversation_id, labels)
    return _json(result)


# ═══════════════════════════════════════════════════════
# MESSAGE TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def get_messages(conversation_id: int, after: Optional[int] = None,
                        before: Optional[int] = None) -> str:
    """Get all messages in a conversation. Use 'after' to paginate forward, 'before' to paginate backward."""
    client = await _get_client()
    result = await client.get_messages(conversation_id, after=after, before=before)
    return _json(result)


@mcp.tool()
async def create_message(conversation_id: int, content: str,
                          message_type: str = "outgoing",
                          private: bool = False,
                          content_type: str = "text") -> str:
    """Send a new message in a conversation. message_type: outgoing/incoming. Set private=true for internal notes. content_type: text/input_email/cards/input_select/form/article."""
    client = await _get_client()
    result = await client.create_message(
        conversation_id, content, message_type=message_type,
        private=private, content_type=content_type,
    )
    return _json(result)


@mcp.tool()
async def delete_message(conversation_id: int, message_id: int) -> str:
    """Delete a specific message and its attachments from a conversation."""
    client = await _get_client()
    result = await client.delete_message(conversation_id, message_id)
    return _json(result)


# ═══════════════════════════════════════════════════════
# INBOX TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def list_inboxes() -> str:
    """List all inboxes in the account including their type, channel details, and configuration."""
    client = await _get_client()
    result = await client.list_inboxes()
    return _json(result)


@mcp.tool()
async def get_inbox(inbox_id: int) -> str:
    """Get details of a specific inbox by its ID."""
    client = await _get_client()
    result = await client.get_inbox(inbox_id)
    return _json(result)


@mcp.tool()
async def create_inbox(name: str, channel_type: str = "web_widget",
                        website_url: Optional[str] = None) -> str:
    """Create a new inbox. channel_type examples: web_widget, api. For web_widget, provide website_url."""
    client = await _get_client()
    channel = {"type": channel_type}
    if website_url:
        channel["website_url"] = website_url
    result = await client.create_inbox(name=name, channel=channel)
    return _json(result)


@mcp.tool()
async def update_inbox(inbox_id: int, name: Optional[str] = None,
                        enable_auto_assignment: Optional[bool] = None) -> str:
    """Update an inbox's name or auto-assignment setting."""
    client = await _get_client()
    kwargs = {}
    if name:
        kwargs["name"] = name
    if enable_auto_assignment is not None:
        kwargs["enable_auto_assignment"] = enable_auto_assignment
    result = await client.update_inbox(inbox_id, **kwargs)
    return _json(result)


# ═══════════════════════════════════════════════════════
# TEAM TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def list_teams() -> str:
    """List all teams in the Chatwoot account."""
    client = await _get_client()
    result = await client.list_teams()
    return _json(result)


@mcp.tool()
async def create_team(name: str, description: Optional[str] = None) -> str:
    """Create a new team with a name and optional description."""
    client = await _get_client()
    result = await client.create_team(name=name, description=description)
    return _json(result)


@mcp.tool()
async def get_team(team_id: int) -> str:
    """Get details of a specific team by its ID."""
    client = await _get_client()
    result = await client.get_team(team_id)
    return _json(result)


@mcp.tool()
async def update_team(team_id: int, name: Optional[str] = None,
                       description: Optional[str] = None) -> str:
    """Update a team's name or description."""
    client = await _get_client()
    kwargs = {}
    if name:
        kwargs["name"] = name
    if description:
        kwargs["description"] = description
    result = await client.update_team(team_id, **kwargs)
    return _json(result)


@mcp.tool()
async def delete_team(team_id: int) -> str:
    """Delete a team from the Chatwoot account."""
    client = await _get_client()
    result = await client.delete_team(team_id)
    return _json(result)


# ═══════════════════════════════════════════════════════
# LABEL TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def list_labels() -> str:
    """List all labels in the Chatwoot account."""
    client = await _get_client()
    result = await client.list_labels()
    return _json(result)


@mcp.tool()
async def create_label(title: str, description: Optional[str] = None,
                        color: Optional[str] = None,
                        show_on_sidebar: bool = True) -> str:
    """Create a new label with title, optional description, color (hex), and sidebar visibility."""
    client = await _get_client()
    result = await client.create_label(title=title, description=description,
                                        color=color, show_on_sidebar=show_on_sidebar)
    return _json(result)


@mcp.tool()
async def update_label(label_id: int, title: Optional[str] = None,
                        description: Optional[str] = None,
                        color: Optional[str] = None) -> str:
    """Update a label's title, description, or color."""
    client = await _get_client()
    kwargs = {}
    if title:
        kwargs["title"] = title
    if description:
        kwargs["description"] = description
    if color:
        kwargs["color"] = color
    result = await client.update_label(label_id, **kwargs)
    return _json(result)


@mcp.tool()
async def delete_label(label_id: int) -> str:
    """Delete a label from the Chatwoot account."""
    client = await _get_client()
    result = await client.delete_label(label_id)
    return _json(result)


# ═══════════════════════════════════════════════════════
# CANNED RESPONSE TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def list_canned_responses() -> str:
    """List all canned responses (pre-written message templates) in the account."""
    client = await _get_client()
    result = await client.list_canned_responses()
    return _json(result)


@mcp.tool()
async def create_canned_response(short_code: str, content: str) -> str:
    """Create a new canned response with a short_code trigger and message content."""
    client = await _get_client()
    result = await client.create_canned_response(short_code=short_code, content=content)
    return _json(result)


@mcp.tool()
async def update_canned_response(canned_response_id: int,
                                  short_code: Optional[str] = None,
                                  content: Optional[str] = None) -> str:
    """Update a canned response's short_code or content."""
    client = await _get_client()
    kwargs = {}
    if short_code:
        kwargs["short_code"] = short_code
    if content:
        kwargs["content"] = content
    result = await client.update_canned_response(canned_response_id, **kwargs)
    return _json(result)


@mcp.tool()
async def delete_canned_response(canned_response_id: int) -> str:
    """Delete a canned response from the account."""
    client = await _get_client()
    result = await client.delete_canned_response(canned_response_id)
    return _json(result)


# ═══════════════════════════════════════════════════════
# CUSTOM ATTRIBUTE TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def list_custom_attributes(attribute_model: str = "conversation_attribute") -> str:
    """List custom attribute definitions. attribute_model: conversation_attribute or contact_attribute."""
    client = await _get_client()
    result = await client.list_custom_attributes(attribute_model=attribute_model)
    return _json(result)


@mcp.tool()
async def create_custom_attribute(attribute_display_name: str,
                                   attribute_display_type: int,
                                   attribute_description: str,
                                   attribute_model: int,
                                   attribute_key: str) -> str:
    """Create a custom attribute definition. attribute_display_type: 0=text, 1=number, 2=currency, 3=percent, 4=link, 5=date, 6=list, 7=checkbox. attribute_model: 0=conversation, 1=contact."""
    client = await _get_client()
    result = await client.create_custom_attribute(
        attribute_display_name=attribute_display_name,
        attribute_display_type=attribute_display_type,
        attribute_description=attribute_description,
        attribute_model=attribute_model,
        attribute_key=attribute_key,
    )
    return _json(result)


# ═══════════════════════════════════════════════════════
# WEBHOOK TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def list_webhooks() -> str:
    """List all webhooks configured in the account."""
    client = await _get_client()
    result = await client.list_webhooks()
    return _json(result)


@mcp.tool()
async def create_webhook(url: str, subscriptions: Optional[list] = None) -> str:
    """Create a webhook. Subscriptions: message_created, message_updated, conversation_created, conversation_status_changed, conversation_updated, contact_created, contact_updated."""
    client = await _get_client()
    result = await client.create_webhook(url=url, subscriptions=subscriptions)
    return _json(result)


@mcp.tool()
async def update_webhook(webhook_id: int, url: Optional[str] = None,
                          subscriptions: Optional[list] = None) -> str:
    """Update a webhook's URL or subscriptions."""
    client = await _get_client()
    kwargs = {}
    if url:
        kwargs["url"] = url
    if subscriptions:
        kwargs["subscriptions"] = subscriptions
    result = await client.update_webhook(webhook_id, **kwargs)
    return _json(result)


@mcp.tool()
async def delete_webhook(webhook_id: int) -> str:
    """Delete a webhook from the account."""
    client = await _get_client()
    result = await client.delete_webhook(webhook_id)
    return _json(result)


# ═══════════════════════════════════════════════════════
# REPORT TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def get_account_reports(metric: str = "account",
                               report_type: str = "account",
                               since: Optional[str] = None,
                               until: Optional[str] = None) -> str:
    """Get account reports and analytics. metric/report_type: account, agent, inbox, label, team."""
    client = await _get_client()
    result = await client.get_account_reports(metric=metric, report_type=report_type,
                                               since=since, until=until)
    return _json(result)



# ═══════════════════════════════════════════════════════
# ADVANCED FILTER TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def filter_conversations_advanced(filters_json: str, page: int = 1) -> str:
    """Filter conversations using advanced criteria. Pass filters_json as a JSON string array of filter objects.
    Each filter: {"attribute_key": "<key>", "filter_operator": "<op>", "values": [<vals>], "query_operator": "AND"|"OR"|null}
    Available attribute_keys: status, assignee_id, inbox_id, team_id, labels, priority, browser_language, country_code, city, created_at, last_activity_at, referer, campaign_id, display_id, contact_identifier.
    Available filter_operators: equal_to, not_equal_to, contains, does_not_contain, is_present, is_not_present, is_greater_than, is_less_than, days_before.
    Status values: open, resolved, pending, snoozed.
    Priority values: none, low, medium, high, urgent.
    The last filter in the list should have query_operator as null.
    Example: [{"attribute_key":"status","filter_operator":"equal_to","values":["open"],"query_operator":"AND"},{"attribute_key":"assignee_id","filter_operator":"equal_to","values":[1],"query_operator":null}]"""
    client = await _get_client()
    try:
        payload = json.loads(filters_json)
    except json.JSONDecodeError as e:
        return _json({"error": f"Invalid JSON: {str(e)}"})
    result = await client.filter_conversations(payload=payload, page=page)
    return _json(result)


# ═══════════════════════════════════════════════════════
# ATTACHMENT TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def create_message_with_attachment(conversation_id: int, content: str,
                                          file_url: str,
                                          filename: Optional[str] = None,
                                          message_type: str = "outgoing",
                                          private: bool = False) -> str:
    """Send a message with a file attachment in a conversation. Provide file_url pointing to the file to attach (http/https URL). Optionally specify filename. message_type: outgoing/incoming. Set private=true for internal notes."""
    client = await _get_client()
    # Download the file
    async with httpx.AsyncClient(timeout=30) as http:
        file_resp = await http.get(file_url)
        file_resp.raise_for_status()
        file_data = file_resp.content
        ct = file_resp.headers.get("content-type", "application/octet-stream")
    if not filename:
        filename = file_url.split("/")[-1].split("?")[0] or "attachment"
    result = await client.create_message_with_attachment(
        conversation_id=conversation_id, content=content,
        file_data=file_data, filename=filename,
        content_type_file=ct, message_type=message_type, private=private,
    )
    return _json(result)


# ═══════════════════════════════════════════════════════
# WEBHOOK LISTENER TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def setup_webhook_listener(webhook_url: str,
                                  subscriptions: Optional[str] = None) -> str:
    """Register a webhook in Chatwoot to receive real-time events. Provide the URL that should receive webhook POST events.
    Optional subscriptions as comma-separated: message_created, message_updated, conversation_created, conversation_status_changed, conversation_updated, contact_created, contact_updated.
    If not specified, all events are subscribed."""
    client = await _get_client()
    subs = None
    if subscriptions:
        subs = [s.strip() for s in subscriptions.split(",")]
    result = await client.create_webhook(url=webhook_url, subscriptions=subs)
    return _json(result)

"""MCP Server with Chatwoot Application API tools."""
import os
import json
import logging
from typing import Optional
from mcp.server.fastmcp import FastMCP
from chatwoot_client import ChatwootClient

logger = logging.getLogger(__name__)

mcp = FastMCP("chatwoot-mcp-server")


def _get_client() -> ChatwootClient:
    """Get a ChatwootClient using environment variables."""
    base_url = os.environ.get("CHATWOOT_URL", "")
    api_token = os.environ.get("CHATWOOT_API_TOKEN", "")
    account_id = int(os.environ.get("CHATWOOT_ACCOUNT_ID", "0"))
    if not base_url or not api_token or not account_id:
        raise ValueError("Chatwoot configuration missing. Set CHATWOOT_URL, CHATWOOT_API_TOKEN, CHATWOOT_ACCOUNT_ID.")
    return ChatwootClient(base_url, api_token, account_id)


def _json(data) -> str:
    return json.dumps(data, indent=2, default=str)


# ═══════════════════════════════════════════════════════
# ACCOUNT TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def get_account() -> str:
    """Get details of the current Chatwoot account including name, locale, features, and settings."""
    client = _get_client()
    result = await client.get_account()
    return _json(result)


@mcp.tool()
async def update_account(name: Optional[str] = None, locale: Optional[str] = None) -> str:
    """Update the current Chatwoot account details like name or locale."""
    client = _get_client()
    result = await client.update_account(name=name, locale=locale)
    return _json(result)


# ═══════════════════════════════════════════════════════
# AGENT TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def list_agents() -> str:
    """List all agents in the Chatwoot account. Returns agent ID, name, email, role, availability."""
    client = _get_client()
    result = await client.list_agents()
    return _json(result)


@mcp.tool()
async def add_agent(name: str, email: str, role: str = "agent") -> str:
    """Add a new agent to the Chatwoot account. Role can be 'agent' or 'administrator'."""
    client = _get_client()
    result = await client.add_agent(name=name, email=email, role=role)
    return _json(result)


@mcp.tool()
async def update_agent(agent_id: int, name: Optional[str] = None,
                        role: Optional[str] = None,
                        availability: Optional[str] = None) -> str:
    """Update an existing agent's name, role, or availability status."""
    client = _get_client()
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
    client = _get_client()
    result = await client.remove_agent(agent_id)
    return _json(result)


# ═══════════════════════════════════════════════════════
# CONTACT TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def list_contacts(page: int = 1, sort: Optional[str] = None) -> str:
    """List all contacts with pagination (15 per page). Sort by: name, email, phone_number, last_activity_at (prefix with - for descending)."""
    client = _get_client()
    result = await client.list_contacts(page=page, sort=sort)
    return _json(result)


@mcp.tool()
async def create_contact(name: str, email: Optional[str] = None,
                          phone_number: Optional[str] = None,
                          identifier: Optional[str] = None) -> str:
    """Create a new contact in Chatwoot with name, email, phone number, or external identifier."""
    client = _get_client()
    kwargs = {}
    if identifier:
        kwargs["identifier"] = identifier
    result = await client.create_contact(name=name, email=email, phone_number=phone_number, **kwargs)
    return _json(result)


@mcp.tool()
async def get_contact(contact_id: int) -> str:
    """Get detailed information about a specific contact by their ID."""
    client = _get_client()
    result = await client.get_contact(contact_id)
    return _json(result)


@mcp.tool()
async def update_contact(contact_id: int, name: Optional[str] = None,
                          email: Optional[str] = None,
                          phone_number: Optional[str] = None) -> str:
    """Update an existing contact's name, email, or phone number."""
    client = _get_client()
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
    client = _get_client()
    result = await client.delete_contact(contact_id)
    return _json(result)


@mcp.tool()
async def search_contacts(q: str, page: int = 1) -> str:
    """Search contacts by name, email, phone number, or identifier. Returns matching contacts with pagination."""
    client = _get_client()
    result = await client.search_contacts(q=q, page=page)
    return _json(result)


@mcp.tool()
async def get_contact_conversations(contact_id: int) -> str:
    """Get all conversations associated with a specific contact."""
    client = _get_client()
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
    client = _get_client()
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
    client = _get_client()
    result = await client.create_conversation(
        inbox_id=inbox_id, contact_id=contact_id, source_id=source_id,
        status=status, assignee_id=assignee_id, team_id=team_id, message=message,
    )
    return _json(result)


@mcp.tool()
async def get_conversation(conversation_id: int) -> str:
    """Get details of a specific conversation by its ID, including messages, meta info, and status."""
    client = _get_client()
    result = await client.get_conversation(conversation_id)
    return _json(result)


@mcp.tool()
async def get_conversation_counts() -> str:
    """Get conversation counts grouped by status (open, resolved, pending, etc.) and assignee type."""
    client = _get_client()
    result = await client.get_conversation_counts()
    return _json(result)


@mcp.tool()
async def toggle_conversation_status(conversation_id: int, status: str) -> str:
    """Toggle a conversation's status. Status options: open, resolved, pending, snoozed."""
    client = _get_client()
    result = await client.toggle_conversation_status(conversation_id, status)
    return _json(result)


@mcp.tool()
async def assign_conversation(conversation_id: int,
                               assignee_id: Optional[int] = None,
                               team_id: Optional[int] = None) -> str:
    """Assign a conversation to an agent and/or team. Pass assignee_id for agent, team_id for team."""
    client = _get_client()
    result = await client.assign_conversation(conversation_id, assignee_id=assignee_id, team_id=team_id)
    return _json(result)


@mcp.tool()
async def get_conversation_labels(conversation_id: int) -> str:
    """Get all labels assigned to a specific conversation."""
    client = _get_client()
    result = await client.get_conversation_labels(conversation_id)
    return _json(result)


@mcp.tool()
async def add_conversation_labels(conversation_id: int, labels: list) -> str:
    """Add or set labels on a conversation. Provide a list of label names."""
    client = _get_client()
    result = await client.add_conversation_labels(conversation_id, labels)
    return _json(result)


# ═══════════════════════════════════════════════════════
# MESSAGE TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def get_messages(conversation_id: int, after: Optional[int] = None,
                        before: Optional[int] = None) -> str:
    """Get all messages in a conversation. Use 'after' to paginate forward, 'before' to paginate backward."""
    client = _get_client()
    result = await client.get_messages(conversation_id, after=after, before=before)
    return _json(result)


@mcp.tool()
async def create_message(conversation_id: int, content: str,
                          message_type: str = "outgoing",
                          private: bool = False,
                          content_type: str = "text") -> str:
    """Send a new message in a conversation. message_type: outgoing/incoming. Set private=true for internal notes. content_type: text/input_email/cards/input_select/form/article."""
    client = _get_client()
    result = await client.create_message(
        conversation_id, content, message_type=message_type,
        private=private, content_type=content_type,
    )
    return _json(result)


@mcp.tool()
async def delete_message(conversation_id: int, message_id: int) -> str:
    """Delete a specific message and its attachments from a conversation."""
    client = _get_client()
    result = await client.delete_message(conversation_id, message_id)
    return _json(result)


# ═══════════════════════════════════════════════════════
# INBOX TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def list_inboxes() -> str:
    """List all inboxes in the account including their type, channel details, and configuration."""
    client = _get_client()
    result = await client.list_inboxes()
    return _json(result)


@mcp.tool()
async def get_inbox(inbox_id: int) -> str:
    """Get details of a specific inbox by its ID."""
    client = _get_client()
    result = await client.get_inbox(inbox_id)
    return _json(result)


@mcp.tool()
async def create_inbox(name: str, channel_type: str = "web_widget",
                        website_url: Optional[str] = None) -> str:
    """Create a new inbox. channel_type examples: web_widget, api. For web_widget, provide website_url."""
    client = _get_client()
    channel = {"type": channel_type}
    if website_url:
        channel["website_url"] = website_url
    result = await client.create_inbox(name=name, channel=channel)
    return _json(result)


@mcp.tool()
async def update_inbox(inbox_id: int, name: Optional[str] = None,
                        enable_auto_assignment: Optional[bool] = None) -> str:
    """Update an inbox's name or auto-assignment setting."""
    client = _get_client()
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
    client = _get_client()
    result = await client.list_teams()
    return _json(result)


@mcp.tool()
async def create_team(name: str, description: Optional[str] = None) -> str:
    """Create a new team with a name and optional description."""
    client = _get_client()
    result = await client.create_team(name=name, description=description)
    return _json(result)


@mcp.tool()
async def get_team(team_id: int) -> str:
    """Get details of a specific team by its ID."""
    client = _get_client()
    result = await client.get_team(team_id)
    return _json(result)


@mcp.tool()
async def update_team(team_id: int, name: Optional[str] = None,
                       description: Optional[str] = None) -> str:
    """Update a team's name or description."""
    client = _get_client()
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
    client = _get_client()
    result = await client.delete_team(team_id)
    return _json(result)


# ═══════════════════════════════════════════════════════
# LABEL TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def list_labels() -> str:
    """List all labels in the Chatwoot account."""
    client = _get_client()
    result = await client.list_labels()
    return _json(result)


@mcp.tool()
async def create_label(title: str, description: Optional[str] = None,
                        color: Optional[str] = None,
                        show_on_sidebar: bool = True) -> str:
    """Create a new label with title, optional description, color (hex), and sidebar visibility."""
    client = _get_client()
    result = await client.create_label(title=title, description=description,
                                        color=color, show_on_sidebar=show_on_sidebar)
    return _json(result)


@mcp.tool()
async def update_label(label_id: int, title: Optional[str] = None,
                        description: Optional[str] = None,
                        color: Optional[str] = None) -> str:
    """Update a label's title, description, or color."""
    client = _get_client()
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
    client = _get_client()
    result = await client.delete_label(label_id)
    return _json(result)


# ═══════════════════════════════════════════════════════
# CANNED RESPONSE TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def list_canned_responses() -> str:
    """List all canned responses (pre-written message templates) in the account."""
    client = _get_client()
    result = await client.list_canned_responses()
    return _json(result)


@mcp.tool()
async def create_canned_response(short_code: str, content: str) -> str:
    """Create a new canned response with a short_code trigger and message content."""
    client = _get_client()
    result = await client.create_canned_response(short_code=short_code, content=content)
    return _json(result)


@mcp.tool()
async def update_canned_response(canned_response_id: int,
                                  short_code: Optional[str] = None,
                                  content: Optional[str] = None) -> str:
    """Update a canned response's short_code or content."""
    client = _get_client()
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
    client = _get_client()
    result = await client.delete_canned_response(canned_response_id)
    return _json(result)


# ═══════════════════════════════════════════════════════
# CUSTOM ATTRIBUTE TOOLS
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def list_custom_attributes(attribute_model: str = "conversation_attribute") -> str:
    """List custom attribute definitions. attribute_model: conversation_attribute or contact_attribute."""
    client = _get_client()
    result = await client.list_custom_attributes(attribute_model=attribute_model)
    return _json(result)


@mcp.tool()
async def create_custom_attribute(attribute_display_name: str,
                                   attribute_display_type: int,
                                   attribute_description: str,
                                   attribute_model: int,
                                   attribute_key: str) -> str:
    """Create a custom attribute definition. attribute_display_type: 0=text, 1=number, 2=currency, 3=percent, 4=link, 5=date, 6=list, 7=checkbox. attribute_model: 0=conversation, 1=contact."""
    client = _get_client()
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
    client = _get_client()
    result = await client.list_webhooks()
    return _json(result)


@mcp.tool()
async def create_webhook(url: str, subscriptions: Optional[list] = None) -> str:
    """Create a webhook. Subscriptions: message_created, message_updated, conversation_created, conversation_status_changed, conversation_updated, contact_created, contact_updated."""
    client = _get_client()
    result = await client.create_webhook(url=url, subscriptions=subscriptions)
    return _json(result)


@mcp.tool()
async def update_webhook(webhook_id: int, url: Optional[str] = None,
                          subscriptions: Optional[list] = None) -> str:
    """Update a webhook's URL or subscriptions."""
    client = _get_client()
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
    client = _get_client()
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
    client = _get_client()
    result = await client.get_account_reports(metric=metric, report_type=report_type,
                                               since=since, until=until)
    return _json(result)

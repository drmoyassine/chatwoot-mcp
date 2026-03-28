"""Async HTTP client for Chatwoot Application APIs."""
import httpx
from typing import Optional


class ChatwootClient:
    """Async client for interacting with Chatwoot Application APIs."""

    def __init__(self, base_url: str, api_token: str, account_id: int):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.account_id = account_id
        self.headers = {"api_access_token": api_token, "Content-Type": "application/json"}

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/v1/accounts/{self.account_id}{path}"

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(method, self._url(path), headers=self.headers, **kwargs)
            resp.raise_for_status()
            if resp.status_code == 204:
                return {"status": "success"}
            return resp.json()

    # ── Account ──
    async def get_account(self) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/accounts/{self.account_id}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def update_account(self, name: Optional[str] = None, locale: Optional[str] = None) -> dict:
        payload = {}
        if name:
            payload["name"] = name
        if locale:
            payload["locale"] = locale
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.patch(
                f"{self.base_url}/api/v1/accounts/{self.account_id}",
                headers=self.headers,
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    # ── Agents ──
    async def list_agents(self) -> dict:
        return await self._request("GET", "/agents")

    async def add_agent(self, name: str, email: str, role: str = "agent") -> dict:
        return await self._request("POST", "/agents", json={"name": name, "email": email, "role": role})

    async def update_agent(self, agent_id: int, **kwargs) -> dict:
        return await self._request("PATCH", f"/agents/{agent_id}", json=kwargs)

    async def remove_agent(self, agent_id: int) -> dict:
        return await self._request("DELETE", f"/agents/{agent_id}")

    # ── Contacts ──
    async def list_contacts(self, page: int = 1, sort: Optional[str] = None) -> dict:
        params = {"page": page}
        if sort:
            params["sort"] = sort
        return await self._request("GET", "/contacts", params=params)

    async def create_contact(self, name: str, email: Optional[str] = None,
                             phone_number: Optional[str] = None, **kwargs) -> dict:
        payload = {"name": name}
        if email:
            payload["email"] = email
        if phone_number:
            payload["phone_number"] = phone_number
        payload.update(kwargs)
        return await self._request("POST", "/contacts", json=payload)

    async def get_contact(self, contact_id: int) -> dict:
        return await self._request("GET", f"/contacts/{contact_id}")

    async def update_contact(self, contact_id: int, **kwargs) -> dict:
        return await self._request("PUT", f"/contacts/{contact_id}", json=kwargs)

    async def delete_contact(self, contact_id: int) -> dict:
        return await self._request("DELETE", f"/contacts/{contact_id}")

    async def search_contacts(self, q: str, page: int = 1) -> dict:
        return await self._request("GET", "/contacts/search", params={"q": q, "page": page})

    async def get_contact_conversations(self, contact_id: int) -> dict:
        return await self._request("GET", f"/contacts/{contact_id}/conversations")

    # ── Conversations ──
    async def list_conversations(self, assignee_type: str = "all", status: str = "open",
                                  page: int = 1, q: Optional[str] = None,
                                  inbox_id: Optional[int] = None,
                                  team_id: Optional[int] = None) -> dict:
        params = {"assignee_type": assignee_type, "status": status, "page": page}
        if q:
            params["q"] = q
        if inbox_id:
            params["inbox_id"] = inbox_id
        if team_id:
            params["team_id"] = team_id
        return await self._request("GET", "/conversations", params=params)

    async def create_conversation(self, inbox_id: int, contact_id: Optional[int] = None,
                                   source_id: Optional[str] = None, status: str = "open",
                                   assignee_id: Optional[int] = None,
                                   team_id: Optional[int] = None,
                                   message: Optional[str] = None) -> dict:
        payload = {"inbox_id": inbox_id, "status": status}
        if source_id:
            payload["source_id"] = source_id
        if contact_id:
            payload["contact_id"] = contact_id
        if assignee_id:
            payload["assignee_id"] = assignee_id
        if team_id:
            payload["team_id"] = team_id
        if message:
            payload["message"] = {"content": message}
        return await self._request("POST", "/conversations", json=payload)

    async def get_conversation(self, conversation_id: int) -> dict:
        return await self._request("GET", f"/conversations/{conversation_id}")

    async def filter_conversations(self, payload: list, page: int = 1) -> dict:
        return await self._request("POST", "/conversations/filter",
                                   json={"payload": payload}, params={"page": page})

    async def get_conversation_counts(self) -> dict:
        return await self._request("GET", "/conversations/meta")

    async def toggle_conversation_status(self, conversation_id: int, status: str) -> dict:
        return await self._request("POST", f"/conversations/{conversation_id}/toggle_status",
                                   json={"status": status})

    async def assign_conversation(self, conversation_id: int,
                                   assignee_id: Optional[int] = None,
                                   team_id: Optional[int] = None) -> dict:
        payload = {}
        if assignee_id is not None:
            payload["assignee_id"] = assignee_id
        if team_id is not None:
            payload["team_id"] = team_id
        return await self._request("POST", f"/conversations/{conversation_id}/assignments",
                                   json=payload)

    # ── Conversation Labels ──
    async def get_conversation_labels(self, conversation_id: int) -> dict:
        return await self._request("GET", f"/conversations/{conversation_id}/labels")

    async def add_conversation_labels(self, conversation_id: int, labels: list) -> dict:
        return await self._request("POST", f"/conversations/{conversation_id}/labels",
                                   json={"labels": labels})

    # ── Messages ──
    async def get_messages(self, conversation_id: int, after: Optional[int] = None,
                           before: Optional[int] = None) -> dict:
        params = {}
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        return await self._request("GET", f"/conversations/{conversation_id}/messages", params=params)

    async def create_message(self, conversation_id: int, content: str,
                              message_type: str = "outgoing", private: bool = False,
                              content_type: str = "text") -> dict:
        payload = {
            "content": content,
            "message_type": message_type,
            "private": private,
            "content_type": content_type,
        }
        return await self._request("POST", f"/conversations/{conversation_id}/messages",
                                   json=payload)

    async def delete_message(self, conversation_id: int, message_id: int) -> dict:
        return await self._request("DELETE", f"/conversations/{conversation_id}/messages/{message_id}")

    # ── Inboxes ──
    async def list_inboxes(self) -> dict:
        return await self._request("GET", "/inboxes")

    async def get_inbox(self, inbox_id: int) -> dict:
        return await self._request("GET", f"/inboxes/{inbox_id}")

    async def create_inbox(self, name: str, channel: dict) -> dict:
        return await self._request("POST", "/inboxes", json={"name": name, "channel": channel})

    async def update_inbox(self, inbox_id: int, **kwargs) -> dict:
        return await self._request("PATCH", f"/inboxes/{inbox_id}", json=kwargs)

    # ── Teams ──
    async def list_teams(self) -> dict:
        return await self._request("GET", "/teams")

    async def create_team(self, name: str, description: Optional[str] = None) -> dict:
        payload = {"name": name}
        if description:
            payload["description"] = description
        return await self._request("POST", "/teams", json=payload)

    async def get_team(self, team_id: int) -> dict:
        return await self._request("GET", f"/teams/{team_id}")

    async def update_team(self, team_id: int, **kwargs) -> dict:
        return await self._request("PATCH", f"/teams/{team_id}", json=kwargs)

    async def delete_team(self, team_id: int) -> dict:
        return await self._request("DELETE", f"/teams/{team_id}")

    # ── Labels ──
    async def list_labels(self) -> dict:
        return await self._request("GET", "/labels")

    async def create_label(self, title: str, description: Optional[str] = None,
                            color: Optional[str] = None, show_on_sidebar: bool = True) -> dict:
        payload = {"title": title, "show_on_sidebar": show_on_sidebar}
        if description:
            payload["description"] = description
        if color:
            payload["color"] = color
        return await self._request("POST", "/labels", json=payload)

    async def update_label(self, label_id: int, **kwargs) -> dict:
        return await self._request("PATCH", f"/labels/{label_id}", json=kwargs)

    async def delete_label(self, label_id: int) -> dict:
        return await self._request("DELETE", f"/labels/{label_id}")

    # ── Canned Responses ──
    async def list_canned_responses(self) -> dict:
        return await self._request("GET", "/canned_responses")

    async def create_canned_response(self, short_code: str, content: str) -> dict:
        return await self._request("POST", "/canned_responses",
                                   json={"short_code": short_code, "content": content})

    async def update_canned_response(self, cr_id: int, **kwargs) -> dict:
        return await self._request("PATCH", f"/canned_responses/{cr_id}", json=kwargs)

    async def delete_canned_response(self, cr_id: int) -> dict:
        return await self._request("DELETE", f"/canned_responses/{cr_id}")

    # ── Custom Attributes ──
    async def list_custom_attributes(self, attribute_model: str = "conversation_attribute") -> dict:
        return await self._request("GET", "/custom_attribute_definitions",
                                   params={"attribute_model": attribute_model})

    async def create_custom_attribute(self, attribute_display_name: str,
                                       attribute_display_type: int,
                                       attribute_description: str,
                                       attribute_model: int,
                                       attribute_key: str) -> dict:
        return await self._request("POST", "/custom_attribute_definitions", json={
            "attribute_display_name": attribute_display_name,
            "attribute_display_type": attribute_display_type,
            "attribute_description": attribute_description,
            "attribute_model": attribute_model,
            "attribute_key": attribute_key,
        })

    async def update_custom_attribute(self, attr_id: int, **kwargs) -> dict:
        return await self._request("PATCH", f"/custom_attribute_definitions/{attr_id}", json=kwargs)

    async def delete_custom_attribute(self, attr_id: int) -> dict:
        return await self._request("DELETE", f"/custom_attribute_definitions/{attr_id}")

    # ── Webhooks ──
    async def list_webhooks(self) -> dict:
        return await self._request("GET", "/webhooks")

    async def create_webhook(self, url: str, subscriptions: Optional[list] = None) -> dict:
        payload = {"url": url}
        if subscriptions:
            payload["subscriptions"] = subscriptions
        return await self._request("POST", "/webhooks", json=payload)

    async def update_webhook(self, webhook_id: int, **kwargs) -> dict:
        return await self._request("PATCH", f"/webhooks/{webhook_id}", json=kwargs)

    async def delete_webhook(self, webhook_id: int) -> dict:
        return await self._request("DELETE", f"/webhooks/{webhook_id}")

    # ── Reports ──
    async def get_account_reports(self, metric: str = "account", report_type: str = "account",
                                   since: Optional[str] = None, until: Optional[str] = None) -> dict:
        params = {"metric": metric, "type": report_type}
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        return await self._request("GET", "/reports", params=params)

    # ── Inbox Members (Agent Assignments to Inboxes) ──
    async def list_inbox_agents(self, inbox_id: int) -> dict:
        return await self._request("GET", f"/inbox_members/{inbox_id}")

    async def update_inbox_agents(self, inbox_id: int, user_ids: list) -> dict:
        return await self._request("POST", f"/inbox_members", json={"inbox_id": inbox_id, "user_ids": user_ids})

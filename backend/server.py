from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, UploadFile, File, Form, Depends
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.routing import Route
from mcp.server.sse import SseServerTransport
import os
import json
import logging
import inspect
import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel
from typing import Optional

ROOT_DIR = Path(__file__).parent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load .env files (for local dev; in Docker, env vars come from docker-compose)
_env_paths = [ROOT_DIR / '.env', Path('/app/.env'), Path.cwd() / '.env']
for _p in _env_paths:
    if _p.exists():
        load_dotenv(_p, override=True)
        logger.info(f"Loaded .env from: {_p}")
        break
else:
    load_dotenv(override=True)

STATIC_DIR = ROOT_DIR / "static"

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()

# In-memory event subscribers for SSE streaming
webhook_subscribers: list[asyncio.Queue] = []

# ── Auth imports ──
from auth import (
    create_access_token, verify_access_token, require_admin,
    get_token_from_request, get_api_key_from_request, generate_api_key,
)

# ── MCP imports ──
from mcp_tools import mcp as mcp_server_instance, set_runtime_config, set_output_format, _runtime_config
from chatwoot_client import ChatwootClient
from crypto import encrypt, decrypt, encrypt_dict, decrypt_dict
from mcp_manager import (
    start_server as start_mcp_server, stop_server as stop_mcp_server,
    get_running_server, list_running_servers, parse_github_url,
    install_server_package, restart_server as restart_mcp_server,
    enrich_from_github,
)
from platform_tools import (
    PLATFORM_TOOL_NAMES, get_platform_tools, execute_platform_tool,
)


# ══════════════════════════════════════════════════════════════════
#  Pydantic Models
# ══════════════════════════════════════════════════════════════════
class LoginPayload(BaseModel):
    email: str
    password: str

class ConfigPayload(BaseModel):
    chatwoot_url: str
    api_token: str
    account_id: int

class ToolExecutePayload(BaseModel):
    tool_name: str
    parameters: dict = {}

class CreateApiKeyPayload(BaseModel):
    label: str = "Default"

class ParamSchema(BaseModel):
    name: str
    type: str = "string"  # string, int, float, bool, enum, list, object
    required: bool = False
    description: str = ""
    default: Optional[str] = None
    enum_options: list = []  # For enum type

class UpdateToolPayload(BaseModel):
    description: Optional[str] = None
    category: Optional[str] = None
    enabled: Optional[bool] = None

class CreateToolPayload(BaseModel):
    name: str
    description: str = ""
    category: str = "custom"
    parameters: list = []
    source_schema: str = ""
    app_name: str = "chatwoot"
    method: str = ""
    path: str = ""
    base_url: str = ""

class AddServerPayload(BaseModel):
    github_url: str = ""
    name: str = ""
    display_name: str = ""
    description: str = ""
    runtime: str = "node"  # node or python
    command: str = ""
    args: list = []
    npm_package: str = ""
    pip_package: str = ""
    credentials_schema: list = []  # [{"key": "API_KEY", "label": "API Key", "required": true}]
    features: list = []  # ["filters", "webhooks", "file_upload"]

class SaveCredentialsPayload(BaseModel):
    credentials: dict = {}  # {"API_KEY": "value", ...}
    credentials_schema: list = []  # Optional: update the schema too


# ══════════════════════════════════════════════════════════════════
#  Routers
# ══════════════════════════════════════════════════════════════════
auth_router = APIRouter(prefix="/api/auth")
apps_router = APIRouter(prefix="/api/apps")
chatwoot_router = APIRouter(prefix="/api/chatwoot")
servers_router = APIRouter(prefix="/api/servers")
marketplace_router = APIRouter(prefix="/api/marketplace")
tools_router = APIRouter(prefix="/api/tools")


# ══════════════════════════════════════════════════════════════════
#  Auth Middleware for Chatwoot routes: accept JWT OR API key
# ══════════════════════════════════════════════════════════════════
async def require_jwt_or_api_key(request: Request):
    """Accept either a valid JWT (dashboard) or a valid API key (any server)."""
    token = get_token_from_request(request)
    if token:
        try:
            verify_access_token(token)
            return
        except HTTPException:
            pass
    api_key = get_api_key_from_request(request)
    if api_key:
        key_doc = await db.api_keys.find_one(
            {"key": api_key, "is_active": True},
            {"_id": 0}
        )
        if key_doc:
            return
    raise HTTPException(status_code=401, detail="Valid JWT or API key required")


# ══════════════════════════════════════════════════════════════════
#  AUTH ENDPOINTS  (/api/auth)
# ══════════════════════════════════════════════════════════════════
@auth_router.post("/login")
async def login(payload: LoginPayload, response: Response):
    admin_email = os.environ.get("ADMIN_EMAIL", "")
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    if not admin_email or not admin_password:
        raise HTTPException(status_code=500, detail="Admin credentials not configured")
    if payload.email.lower() != admin_email.lower() or payload.password != admin_password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(payload.email.lower())
    response.set_cookie(
        key="access_token", value=token, httponly=True,
        secure=False, samesite="lax", max_age=86400, path="/",
    )
    return {"email": payload.email.lower(), "token": token}


@auth_router.get("/me")
async def get_me(user=Depends(require_admin)):
    return {"email": user["sub"]}


@auth_router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"status": "logged_out"}


# ══════════════════════════════════════════════════════════════════
#  APPS ENDPOINTS  (/api/apps) — protected by JWT
# ══════════════════════════════════════════════════════════════════
@apps_router.get("", dependencies=[Depends(require_admin)])
async def list_apps():
    """List all installed MCP servers."""
    apps = []
    try:
        servers = await db.mcp_servers.find({}, {"_id": 0}).to_list(100)
    except Exception as e:
        logger.warning(f"Failed to fetch installed servers: {e}")
        return {"apps": []}
    for srv in servers:
        srv_name = srv.get("name", "")
        if not srv_name:
            continue
        try:
            srv_keys = await db.api_keys.count_documents({"app_name": srv_name, "is_active": True})
        except Exception:
            srv_keys = 0
        running = get_running_server(srv_name)
        apps.append({
            "name": srv_name,
            "display_name": srv.get("display_name", srv_name),
            "description": srv.get("description", ""),
            "configured": srv.get("configured", False),
            "tools_count": len(running.get_tools()) if running and running.is_connected else 0,
            "active_keys": srv_keys,
            "mcp_endpoint": f"/api/servers/{srv_name}/mcp/sse",
            "type": "dynamic",
            "runtime": srv.get("runtime", "node"),
            "enabled": srv.get("enabled", True),
            "status": "connected" if (running and running.is_connected) else "stopped",
            "github_url": srv.get("github_url", ""),
            "features": srv.get("features", []),
        })
    return {"apps": apps}


@apps_router.get("/{app_name}/keys", dependencies=[Depends(require_admin)])
async def list_api_keys(app_name: str):
    """List API keys for an app (key value masked)."""
    keys = await db.api_keys.find(
        {"app_name": app_name},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    for k in keys:
        full_key = k.get("key", "")
        k["key_preview"] = full_key[:8] + "..." + full_key[-4:] if len(full_key) > 12 else full_key
        del k["key"]
    return {"keys": keys}


@apps_router.post("/{app_name}/keys", dependencies=[Depends(require_admin)])
async def create_api_key(app_name: str, payload: CreateApiKeyPayload):
    """Create a new API key for an app. Returns the full key ONCE."""
    key = generate_api_key()
    key_id = f"{app_name}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{key[-6:]}"
    doc = {
        "key_id": key_id,
        "app_name": app_name,
        "key": key,
        "label": payload.label,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
    }
    await db.api_keys.insert_one(doc)
    return {"key_id": key_id, "key": key, "label": payload.label, "created_at": doc["created_at"]}


@apps_router.delete("/{app_name}/keys/{key_id}", dependencies=[Depends(require_admin)])
async def revoke_api_key(app_name: str, key_id: str):
    """Revoke an API key."""
    result = await db.api_keys.update_one(
        {"app_name": app_name, "key_id": key_id},
        {"$set": {"is_active": False, "revoked_at": datetime.now(timezone.utc).isoformat()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"status": "revoked", "key_id": key_id}


# ══════════════════════════════════════════════════════════════════
#  CHATWOOT HELPERS
# ══════════════════════════════════════════════════════════════════
def _get_chatwoot_config() -> dict:
    url = _runtime_config.get("chatwoot_url") or os.environ.get("CHATWOOT_URL", "") or ""
    token = _runtime_config.get("api_token") or os.environ.get("CHATWOOT_API_TOKEN", "") or ""
    account_id = _runtime_config.get("account_id") or 0
    if not account_id:
        try:
            account_id = int(os.environ.get("CHATWOOT_ACCOUNT_ID", "0") or "0")
        except (ValueError, TypeError):
            account_id = 0
    return {"chatwoot_url": url, "api_token": token, "account_id": account_id}


async def _ensure_config_loaded():
    if _runtime_config.get("chatwoot_url"):
        return
    config = await db.mcp_config.find_one({"key": "chatwoot"}, {"_id": 0})
    if config and config.get("chatwoot_url"):
        token = config.get("api_token", "")
        # Decrypt if encrypted
        if config.get("api_token_encrypted"):
            try:
                token = decrypt(token)
            except Exception:
                pass  # Legacy plaintext
        _set_chatwoot_config(config["chatwoot_url"], token, config.get("account_id", 0))
        logger.info(f"Lazy-loaded Chatwoot config from DB: {config['chatwoot_url']}")


def _set_chatwoot_config(url: str, token: str, account_id: int):
    os.environ["CHATWOOT_URL"] = url
    os.environ["CHATWOOT_API_TOKEN"] = token
    os.environ["CHATWOOT_ACCOUNT_ID"] = str(account_id)
    set_runtime_config(url, token, account_id)


async def _get_tool_definitions() -> list:
    """Get tool definitions, merging base tools with DB overrides."""
    # 1. Base tools from mcp_tools.py
    tools = []
    tool_manager = mcp_server_instance._tool_manager
    for name, tool in tool_manager._tools.items():
        params = []
        fn = tool.fn
        sig = inspect.signature(fn)
        for pname, param in sig.parameters.items():
            if pname in ("self", "ctx"):
                continue
            param_info = {
                "name": pname,
                "required": param.default is inspect.Parameter.empty,
                "type": str(param.annotation.__name__) if hasattr(param.annotation, '__name__') else str(param.annotation),
                "description": "",
                "enum_options": [],
            }
            if param.default is not inspect.Parameter.empty:
                param_info["default"] = param.default
            params.append(param_info)
        category = "account"
        for cat in ["agent", "contact", "conversation", "message", "inbox", "team",
                     "label", "canned", "custom_attribute", "webhook", "report"]:
            if cat in name:
                if "canned" in name:
                    category = "canned_responses"
                elif "custom_attribute" in name:
                    category = "custom_attributes"
                elif "webhook" in name:
                    category = "webhooks"
                elif "report" in name:
                    category = "reports"
                elif "agent" in name and "assign" not in name:
                    category = "agents"
                elif "contact" in name:
                    category = "contacts"
                elif "conversation" in name or "assign" in name:
                    category = "conversations"
                elif "message" in name:
                    category = "messages"
                elif "inbox" in name:
                    category = "inboxes"
                elif "team" in name:
                    category = "teams"
                elif "label" in name:
                    category = "labels"
                break
        tools.append({
            "name": name,
            "description": tool.description or fn.__doc__ or "",
            "parameters": params,
            "category": category,
            "source": "builtin",
            "enabled": True,
        })

    # 2. Apply DB overrides
    overrides = await db.tool_overrides.find({"app_name": "chatwoot"}, {"_id": 0}).to_list(500)
    override_map = {o["tool_name"]: o for o in overrides}

    for t in tools:
        ov = override_map.get(t["name"])
        if ov:
            if ov.get("description") is not None:
                t["description"] = ov["description"]
            if ov.get("category") is not None:
                t["category"] = ov["category"]
            if ov.get("enabled") is not None:
                t["enabled"] = ov["enabled"]
            # Merge parameter overrides
            if ov.get("param_overrides"):
                existing = {p["name"]: p for p in t["parameters"]}
                for po in ov["param_overrides"]:
                    if po["name"] in existing:
                        existing[po["name"]].update(po)
                    else:
                        t["parameters"].append(po)
                t["parameters"] = [existing.get(p["name"], p) for p in t["parameters"]]
                # Add new params not in original
                existing_names = {p["name"] for p in t["parameters"]}
                for po in ov["param_overrides"]:
                    if po["name"] not in existing_names:
                        t["parameters"].append(po)

    # 3. Add fully custom tools from DB
    custom_tools_cursor = db.custom_tools.find({"app_name": "chatwoot"}, {"_id": 0})
    custom_tools = await custom_tools_cursor.to_list(200)
    for ct in custom_tools:
        tools.append({
            "name": ct["name"],
            "description": ct.get("description", ""),
            "parameters": ct.get("parameters", []),
            "category": ct.get("category", "custom"),
            "source": "custom",
            "enabled": ct.get("enabled", True),
        })

    return tools


# ══════════════════════════════════════════════════════════════════
#  CHATWOOT ENDPOINTS  (/api/chatwoot) — protected by JWT or API key
# ══════════════════════════════════════════════════════════════════
@chatwoot_router.get("/config", dependencies=[Depends(require_jwt_or_api_key)])
async def get_config():
    await _ensure_config_loaded()
    config = _get_chatwoot_config()
    return {
        "chatwoot_url": config["chatwoot_url"],
        "api_token_set": bool(config["api_token"]),
        "api_token_masked": config["api_token"][:6] + "***" if config["api_token"] else "",
        "account_id": config["account_id"],
    }


@chatwoot_router.post("/config", dependencies=[Depends(require_jwt_or_api_key)])
async def save_config(payload: ConfigPayload):
    _set_chatwoot_config(payload.chatwoot_url, payload.api_token, payload.account_id)
    await db.mcp_config.update_one(
        {"key": "chatwoot"},
        {"$set": {
            "chatwoot_url": payload.chatwoot_url,
            "api_token": encrypt(payload.api_token),
            "api_token_encrypted": True,
            "account_id": payload.account_id,
        }},
        upsert=True,
    )
    return {"status": "saved"}


@chatwoot_router.post("/config/test", dependencies=[Depends(require_jwt_or_api_key)])
async def test_connection():
    await _ensure_config_loaded()
    config = _get_chatwoot_config()
    if not config["chatwoot_url"] or not config["api_token"] or not config["account_id"]:
        raise HTTPException(status_code=400, detail="Configuration incomplete")
    try:
        c = ChatwootClient(config["chatwoot_url"], config["api_token"], config["account_id"])
        result = await c.get_account()
        return {"status": "connected", "account_name": result.get("name", ""), "account_id": result.get("id", 0)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@chatwoot_router.get("/config/output-format", dependencies=[Depends(require_jwt_or_api_key)])
async def get_output_format():
    return {"output_format": _runtime_config.get("output_format", "json")}


@chatwoot_router.post("/config/output-format", dependencies=[Depends(require_jwt_or_api_key)])
async def save_output_format(payload: dict):
    fmt = payload.get("output_format", "json")
    if fmt not in ("json", "toon"):
        raise HTTPException(status_code=400, detail="Invalid format. Use 'json' or 'toon'.")
    set_output_format(fmt)
    await db.mcp_config.update_one({"key": "chatwoot"}, {"$set": {"output_format": fmt}}, upsert=True)
    return {"output_format": fmt}


@chatwoot_router.get("/tools", dependencies=[Depends(require_jwt_or_api_key)])
async def list_tools():
    tools = await _get_tool_definitions()
    return {"tools": tools}


@chatwoot_router.put("/tools/{tool_name}", dependencies=[Depends(require_admin)])
async def update_tool(tool_name: str, payload: UpdateToolPayload):
    """Update a tool's description, category, or enabled state."""
    update = {}
    if payload.description is not None:
        update["description"] = payload.description
    if payload.category is not None:
        update["category"] = payload.category
    if payload.enabled is not None:
        update["enabled"] = payload.enabled
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")
    await db.tool_overrides.update_one(
        {"app_name": "chatwoot", "tool_name": tool_name},
        {"$set": update},
        upsert=True,
    )
    return {"status": "updated", "tool_name": tool_name}


@chatwoot_router.put("/tools/{tool_name}/params/{param_name}", dependencies=[Depends(require_admin)])
async def update_tool_param(tool_name: str, param_name: str, param: ParamSchema):
    """Update or add a parameter to a tool."""
    param_dict = param.model_dump()
    # Upsert parameter in the overrides
    existing = await db.tool_overrides.find_one(
        {"app_name": "chatwoot", "tool_name": tool_name}, {"_id": 0}
    )
    if existing and existing.get("param_overrides"):
        # Update existing param or append
        found = False
        for i, p in enumerate(existing["param_overrides"]):
            if p["name"] == param_name:
                existing["param_overrides"][i] = param_dict
                found = True
                break
        if not found:
            existing["param_overrides"].append(param_dict)
        await db.tool_overrides.update_one(
            {"app_name": "chatwoot", "tool_name": tool_name},
            {"$set": {"param_overrides": existing["param_overrides"]}},
        )
    else:
        await db.tool_overrides.update_one(
            {"app_name": "chatwoot", "tool_name": tool_name},
            {"$set": {"param_overrides": [param_dict]}},
            upsert=True,
        )
    return {"status": "updated", "tool_name": tool_name, "param": param_dict}


@chatwoot_router.delete("/tools/{tool_name}/params/{param_name}", dependencies=[Depends(require_admin)])
async def delete_tool_param(tool_name: str, param_name: str):
    """Remove a parameter override from a tool."""
    await db.tool_overrides.update_one(
        {"app_name": "chatwoot", "tool_name": tool_name},
        {"$pull": {"param_overrides": {"name": param_name}}},
    )
    return {"status": "deleted", "tool_name": tool_name, "param_name": param_name}


@chatwoot_router.post("/tools/create", dependencies=[Depends(require_admin)])
async def create_custom_tool(payload: CreateToolPayload):
    """Create a fully custom tool."""
    # Check name doesn't conflict with builtins
    tool_manager = mcp_server_instance._tool_manager
    existing_custom = await db.custom_tools.find_one(
        {"app_name": "chatwoot", "name": payload.name}, {"_id": 0}
    )
    if payload.name in tool_manager._tools or existing_custom:
        raise HTTPException(status_code=409, detail=f"Tool '{payload.name}' already exists")
    doc = {
        "app_name": "chatwoot",
        "name": payload.name,
        "description": payload.description,
        "category": payload.category,
        "parameters": payload.parameters,
        "source_schema": payload.source_schema,
        "enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.custom_tools.insert_one(doc)
    return {"status": "created", "tool": {k: v for k, v in doc.items() if k != "_id"}}


@chatwoot_router.put("/tools/custom/{tool_name}", dependencies=[Depends(require_admin)])
async def update_custom_tool(tool_name: str, payload: dict):
    """Update a custom tool's full definition."""
    update = {}
    for field in ["name", "description", "category", "parameters", "enabled"]:
        if field in payload:
            update[field] = payload[field]
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.custom_tools.update_one(
        {"app_name": "chatwoot", "name": tool_name},
        {"$set": update},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Custom tool not found")
    return {"status": "updated", "tool_name": tool_name}


@chatwoot_router.delete("/tools/custom/{tool_name}", dependencies=[Depends(require_admin)])
async def delete_custom_tool(tool_name: str):
    """Delete a custom tool."""
    result = await db.custom_tools.delete_one({"app_name": "chatwoot", "name": tool_name})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Custom tool not found")
    return {"status": "deleted", "tool_name": tool_name}


@chatwoot_router.post("/tools/parse-schema", dependencies=[Depends(require_admin)])
async def parse_tool_schema(payload: dict):
    """Parse a cURL command or JSON schema into a tool definition."""
    schema_text = payload.get("schema", "").strip()
    if not schema_text:
        raise HTTPException(status_code=400, detail="Schema text required")
    try:
        tool_def = _parse_schema(schema_text)
        return {"tool": tool_def}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse schema: {str(e)}")


def _parse_schema(text: str) -> dict:
    """Parse cURL command or JSON body into a tool parameter definition."""
    import re
    import shlex

    tool = {"name": "", "description": "", "parameters": [], "method": "POST", "path": ""}

    # Try parsing as cURL
    if text.strip().startswith("curl"):
        # Normalize multiline
        text_clean = text.replace("\\\n", " ").replace("\\\r\n", " ")
        try:
            parts = shlex.split(text_clean)
        except ValueError:
            parts = text_clean.split()

        method = "GET"
        url = ""
        data_str = ""
        headers = {}

        i = 0
        while i < len(parts):
            p = parts[i]
            if p in ("-X", "--request") and i + 1 < len(parts):
                method = parts[i + 1].upper()
                i += 2
            elif p in ("-H", "--header") and i + 1 < len(parts):
                h = parts[i + 1]
                if ":" in h:
                    k, v = h.split(":", 1)
                    headers[k.strip().lower()] = v.strip()
                i += 2
            elif p in ("-d", "--data", "--data-raw") and i + 1 < len(parts):
                data_str = parts[i + 1]
                i += 2
            elif p.startswith("http"):
                url = p
                i += 1
            elif p == "--url" and i + 1 < len(parts):
                url = parts[i + 1]
                i += 2
            else:
                i += 1

        tool["method"] = method

        # Extract path — strip base URL and account_id pattern
        if url:
            # Remove protocol and domain
            path_match = re.search(r'/api/v\d+/accounts/\{?[^/}]+\}?(/.*)', url)
            if path_match:
                tool["path"] = path_match.group(1)
            else:
                path_match = re.search(r'(/.+)', url.split("//")[-1].split("/", 1)[-1] if "//" in url else url)
                if path_match:
                    tool["path"] = "/" + path_match.group(1).lstrip("/")

        # Infer tool name from path
        if tool["path"]:
            path_parts = [p for p in tool["path"].split("/") if p and not p.startswith("{")]
            method_prefix = {"GET": "get", "POST": "create", "PUT": "update", "PATCH": "update", "DELETE": "delete"}.get(method, "run")
            if path_parts:
                resource = path_parts[-1].rstrip("s") if len(path_parts[-1]) > 3 else path_parts[-1]
                tool["name"] = f"{method_prefix}_{resource}"

        # Parse JSON body for parameters
        if data_str:
            try:
                # Handle nested JSON
                data_str_clean = data_str.strip().strip("'\"")
                body = json.loads(data_str_clean)
                tool["parameters"] = _extract_params_from_json(body)
            except json.JSONDecodeError:
                pass

        # Extract path parameters like {id}
        if tool["path"]:
            path_params = re.findall(r'\{(\w+)\}', tool["path"])
            existing_names = {p["name"] for p in tool["parameters"]}
            for pp in path_params:
                if pp not in existing_names and pp != "account_id":
                    tool["parameters"].insert(0, {
                        "name": pp, "type": "int", "required": True,
                        "description": f"Path parameter: {pp}", "enum_options": [],
                    })

        # Strip auth-related params
        tool["parameters"] = [
            p for p in tool["parameters"]
            if p["name"] not in ("api_access_token", "api_key", "account_id")
        ]

    else:
        # Try parsing as raw JSON body
        try:
            body = json.loads(text)
            tool["parameters"] = _extract_params_from_json(body)
            tool["name"] = "new_tool"
        except json.JSONDecodeError:
            raise ValueError("Could not parse as cURL or JSON")

    return tool


def _extract_params_from_json(body: dict, prefix: str = "") -> list:
    """Extract parameter definitions from a JSON body example."""
    params = []
    for key, value in body.items():
        name = f"{prefix}{key}" if prefix else key
        param = {
            "name": name,
            "required": False,
            "description": "",
            "enum_options": [],
        }
        if isinstance(value, bool):
            param["type"] = "bool"
            param["default"] = str(value).lower()
        elif isinstance(value, int):
            param["type"] = "int"
        elif isinstance(value, float):
            param["type"] = "float"
        elif isinstance(value, list):
            param["type"] = "list"
        elif isinstance(value, dict):
            param["type"] = "object"
        elif isinstance(value, str):
            param["type"] = "string"
            if value.startswith("<") and value.endswith(">"):
                param["description"] = value[1:-1]
        else:
            param["type"] = "string"
        params.append(param)
    return params



@chatwoot_router.post("/tools/execute", dependencies=[Depends(require_jwt_or_api_key)])
async def execute_tool(payload: ToolExecutePayload):
    config = _get_chatwoot_config()
    if not config["chatwoot_url"] or not config["api_token"]:
        raise HTTPException(status_code=400, detail="Chatwoot not configured")

    # Check if it's a custom tool first
    custom_tool = await db.custom_tools.find_one(
        {"app_name": "chatwoot", "name": payload.tool_name}, {"_id": 0}
    )
    if custom_tool:
        # Execute custom tool via generic Chatwoot client
        c = ChatwootClient(config["chatwoot_url"], config["api_token"], config["account_id"])
        method = custom_tool.get("method", "GET").upper()
        path = custom_tool.get("path", "")
        # Substitute path params
        params = dict(payload.parameters)
        for key in list(params.keys()):
            placeholder = "{" + key + "}"
            if placeholder in path:
                path = path.replace(placeholder, str(params.pop(key)))
        try:
            if method in ("POST", "PUT", "PATCH"):
                result = await c._request(method, path, json=params)
            else:
                result = await c._request(method, path, params=params or None)
            return {"result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Builtin tool
    tool_manager = mcp_server_instance._tool_manager
    tool = tool_manager._tools.get(payload.tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{payload.tool_name}' not found")
    try:
        # Separate known params from extra (added via UI)
        sig = inspect.signature(tool.fn)
        known_params = set(sig.parameters.keys()) - {"self", "ctx"}
        fn_params = {k: v for k, v in payload.parameters.items() if k in known_params}
        extra_params = {k: v for k, v in payload.parameters.items() if k not in known_params}

        if extra_params:
            # Tool has extra params added via UI — inject them by wrapping the call
            # Pass known params normally; extra params need to be added to the
            # underlying HTTP request body
            result = await tool.fn(**fn_params)
            # TODO: Future enhancement — merge extra_params into the HTTP call
        else:
            result = await tool.fn(**fn_params)

        if isinstance(result, str):
            try:
                return {"result": json.loads(result)}
            except (json.JSONDecodeError, ValueError):
                return {"result": result}
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@chatwoot_router.post("/tools/execute-with-file", dependencies=[Depends(require_jwt_or_api_key)])
async def execute_tool_with_file(
    tool_name: str = Form(...),
    parameters: str = Form("{}"),
    file: Optional[UploadFile] = File(None),
):
    config = _get_chatwoot_config()
    if not config["chatwoot_url"] or not config["api_token"]:
        raise HTTPException(status_code=400, detail="Chatwoot not configured")
    params = json.loads(parameters)
    if tool_name == "create_message_with_attachment" and file:
        c = ChatwootClient(config["chatwoot_url"], config["api_token"], config["account_id"])
        file_data = await file.read()
        result = await c.create_message_with_attachment(
            conversation_id=int(params.get("conversation_id", 0)),
            content=params.get("content", ""),
            file_data=file_data,
            filename=file.filename or "attachment",
            content_type_file=file.content_type or "application/octet-stream",
            message_type=params.get("message_type", "outgoing"),
            private=params.get("private", False),
        )
        return {"result": result}
    tool_manager = mcp_server_instance._tool_manager
    tool = tool_manager._tools.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    try:
        result = await tool.fn(**params)
        if isinstance(result, str):
            try:
                return {"result": json.loads(result)}
            except (json.JSONDecodeError, ValueError):
                return {"result": result}
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Webhook receiver — no auth (Chatwoot sends events here)
@chatwoot_router.post("/webhooks/receive")
async def receive_webhook(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    event = {
        "event": body.get("event", "unknown"),
        "data": body,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.webhook_events.insert_one({**event, "_stored": True})
    count = await db.webhook_events.count_documents({})
    if count > 500:
        oldest = await db.webhook_events.find().sort("received_at", 1).limit(count - 500).to_list(count - 500)
        if oldest:
            ids = [o["_id"] for o in oldest]
            await db.webhook_events.delete_many({"_id": {"$in": ids}})
    for q in webhook_subscribers:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass
    logger.info(f"Webhook received: {event['event']}")
    return {"status": "received"}


@chatwoot_router.get("/webhooks/events", dependencies=[Depends(require_jwt_or_api_key)])
async def stream_webhook_events():
    queue = asyncio.Queue(maxsize=100)
    webhook_subscribers.append(queue)
    async def event_generator():
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            webhook_subscribers.remove(queue)
    return StreamingResponse(event_generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@chatwoot_router.get("/webhooks/events/history", dependencies=[Depends(require_jwt_or_api_key)])
async def get_webhook_history(limit: int = 50):
    events = await db.webhook_events.find({}, {"_id": 0, "_stored": 0}).sort("received_at", -1).limit(limit).to_list(limit)
    return {"events": events}


@chatwoot_router.get("/mcp/info", dependencies=[Depends(require_jwt_or_api_key)])
async def mcp_info():
    await _ensure_config_loaded()
    config = _get_chatwoot_config()
    tools = await _get_tool_definitions()
    return {
        "server_name": "chatwoot-mcp-server",
        "transport": {
            "sse": {"endpoint": "/api/chatwoot/mcp/sse", "messages_endpoint": "/api/chatwoot/mcp/messages/"},
            "stdio": {"command": "python mcp_stdio.py", "description": "Run locally for stdio transport"},
        },
        "tools_count": len(tools),
        "configured": bool(config["chatwoot_url"] and config["api_token"]),
    }



# ══════════════════════════════════════════════════════════════════
#  DYNAMIC MCP SERVERS  (/api/servers) — protected by JWT
# ══════════════════════════════════════════════════════════════════
@servers_router.post("/parse-github", dependencies=[Depends(require_admin)])
async def parse_github(payload: dict):
    """Parse a GitHub URL and return detected package info."""
    url = payload.get("github_url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="GitHub URL required")
    try:
        info = parse_github_url(url)
        # Enrich with actual package.json and README data from GitHub
        info = await enrich_from_github(info)
        return {"server_info": info}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@servers_router.post("/add", dependencies=[Depends(require_admin)])
async def add_server(payload: AddServerPayload):
    """Add a new MCP server — install package and register."""
    if not payload.name:
        raise HTTPException(status_code=400, detail="Server name required")

    # Check if already exists
    existing = await db.mcp_servers.find_one({"name": payload.name}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=409, detail=f"Server '{payload.name}' already exists")

    # Install the package — extract org/repo from github_url for fallback
    server_info = payload.model_dump()
    if payload.github_url:
        gh_match = re.match(r"https?://github\.com/([^/]+)/([^/]+)", payload.github_url)
        if gh_match:
            server_info["org"] = gh_match.group(1)
            server_info["repo"] = gh_match.group(2)
    try:
        install_result = await install_server_package(server_info)
        logger.info(f"Installed {payload.name}: {install_result.get('output', '')[:200]}")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Save to DB
    doc = {
        "name": payload.name,
        "display_name": payload.display_name or payload.name.replace("-", " ").title(),
        "description": payload.description,
        "runtime": payload.runtime,
        "command": payload.command,
        "args": payload.args,
        "npm_package": payload.npm_package,
        "pip_package": payload.pip_package,
        "github_url": payload.github_url,
        "credentials_schema": payload.credentials_schema,
        "features": payload.features,
        "configured": False,
        "enabled": True,
        "installed_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.mcp_servers.insert_one(doc)
    return {"status": "installed", "server": {k: v for k, v in doc.items() if k != "_id"}}


@servers_router.get("/{server_name}", dependencies=[Depends(require_admin)])
async def get_server(server_name: str):
    """Get server details."""
    srv = await db.mcp_servers.find_one({"name": server_name}, {"_id": 0})
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")
    running = get_running_server(server_name)
    srv["status"] = "connected" if (running and running.is_connected) else "stopped"
    srv["tools_count"] = len(running.get_tools()) if running and running.is_connected else 0
    # Check if credentials are saved
    creds = await db.server_credentials.find_one({"server_name": server_name}, {"_id": 0})
    srv["has_credentials"] = bool(creds and creds.get("credentials"))
    return srv


@servers_router.post("/{server_name}/credentials", dependencies=[Depends(require_admin)])
async def save_server_credentials(server_name: str, payload: SaveCredentialsPayload):
    """Save encrypted credentials for a server."""
    srv = await db.mcp_servers.find_one({"name": server_name}, {"_id": 0})
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")

    # Encrypt all credential values
    encrypted_creds = {k: encrypt(str(v)) for k, v in payload.credentials.items() if v}

    await db.server_credentials.update_one(
        {"server_name": server_name},
        {"$set": {
            "server_name": server_name,
            "credentials": encrypted_creds,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )

    # Mark as configured
    update_fields = {"configured": True}
    if payload.credentials_schema is not None:
        update_fields["credentials_schema"] = payload.credentials_schema
    await db.mcp_servers.update_one({"name": server_name}, {"$set": update_fields})
    return {"status": "saved"}


@servers_router.get("/{server_name}/credentials", dependencies=[Depends(require_admin)])
async def get_server_credentials(server_name: str):
    """Get credential keys (values masked) for a server."""
    creds = await db.server_credentials.find_one({"server_name": server_name}, {"_id": 0})
    if not creds or not creds.get("credentials"):
        return {"credentials": {}}
    # Return masked values
    masked = {}
    for k, v in creds["credentials"].items():
        try:
            decrypted = decrypt(v)
            masked[k] = decrypted[:4] + "***" + decrypted[-2:] if len(decrypted) > 6 else "***"
        except Exception:
            masked[k] = "***"
    return {"credentials": masked}


@servers_router.post("/{server_name}/start", dependencies=[Depends(require_admin)])
async def start_server_endpoint(server_name: str):
    """Start an MCP server process."""
    srv = await db.mcp_servers.find_one({"name": server_name}, {"_id": 0})
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")

    # Get decrypted credentials
    creds_doc = await db.server_credentials.find_one({"server_name": server_name}, {"_id": 0})
    env_vars = {}
    if creds_doc and creds_doc.get("credentials"):
        for k, v in creds_doc["credentials"].items():
            try:
                env_vars[k] = decrypt(v)
            except Exception:
                env_vars[k] = v

    server_config = {
        "name": server_name,
        "command": srv["command"],
        "args": srv.get("args", []),
        "env_vars": env_vars,
        "runtime": srv.get("runtime", "node"),
    }

    try:
        proc = await start_mcp_server(server_config)
        return {
            "status": "started",
            "tools_count": len(proc.get_tools()),
            "tools": proc.get_tools(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start: {str(e)}")


@servers_router.post("/{server_name}/stop", dependencies=[Depends(require_admin)])
async def stop_server_endpoint(server_name: str):
    """Stop an MCP server process."""
    await stop_mcp_server(server_name)
    return {"status": "stopped"}


@servers_router.post("/{server_name}/toggle", dependencies=[Depends(require_admin)])
async def toggle_server(server_name: str, payload: dict):
    """Toggle a server on/off."""
    enabled = payload.get("enabled", True)
    await db.mcp_servers.update_one({"name": server_name}, {"$set": {"enabled": enabled}})
    if enabled:
        # Try to start
        try:
            return await start_server_endpoint(server_name)
        except HTTPException:
            return {"status": "enabled_but_not_started"}
    else:
        await stop_mcp_server(server_name)
        return {"status": "stopped"}


@servers_router.get("/{server_name}/tools", dependencies=[Depends(require_jwt_or_api_key)])
async def list_server_tools(server_name: str):
    """List tools for a dynamic MCP server (discovered + custom)."""
    tools = []
    running = get_running_server(server_name)
    if running and running.is_connected:
        for t in running.get_tools():
            t["source"] = t.get("source", "builtin")
            tools.append(t)

    overrides = await db.tool_overrides.find({"app_name": server_name}, {"_id": 0}).to_list(500)
    override_map = {o["tool_name"]: o for o in overrides}
    for t in tools:
        ov = override_map.get(t["name"])
        if ov:
            if ov.get("description") is not None:
                t["description"] = ov["description"]
            if ov.get("category") is not None:
                t["category"] = ov["category"]
            if ov.get("enabled") is not None:
                t["enabled"] = ov["enabled"]
            if ov.get("param_overrides"):
                existing = {p["name"]: p for p in t["parameters"]}
                for po in ov["param_overrides"]:
                    if po["name"] in existing:
                        existing[po["name"]].update(po)
                    else:
                        t["parameters"].append(po)
                t["parameters"] = [existing.get(p["name"], p) for p in t["parameters"]]
                existing_names = {p["name"] for p in t["parameters"]}
                for po in ov["param_overrides"]:
                    if po["name"] not in existing_names:
                        t["parameters"].append(po)

    custom_tools = await db.custom_tools.find({"app_name": server_name}, {"_id": 0}).to_list(200)
    for ct in custom_tools:
        tools.append({
            "name": ct["name"],
            "description": ct.get("description", ""),
            "parameters": ct.get("parameters", []),
            "category": ct.get("category", "custom"),
            "source": "custom",
            "enabled": ct.get("enabled", True),
        })

    for pt in get_platform_tools():
        if not any(t["name"] == pt["name"] for t in tools):
            tools.append(pt)

    if not tools:
        raise HTTPException(status_code=400, detail=f"Server '{server_name}' is not running and has no custom tools")
    return {"tools": tools}


@servers_router.post("/{server_name}/tools/execute", dependencies=[Depends(require_jwt_or_api_key)])
async def execute_server_tool(server_name: str, payload: ToolExecutePayload):
    """Execute a tool on a dynamic MCP server (platform, subprocess, or custom)."""
    if payload.tool_name in PLATFORM_TOOL_NAMES:
        running = get_running_server(server_name)
        is_connected = bool(running and running.is_connected)
        all_tools = []
        if is_connected:
            all_tools = running.get_tools()
        custom = await db.custom_tools.find({"app_name": server_name}, {"_id": 0}).to_list(200)
        for ct in custom:
            all_tools.append({
                "name": ct["name"], "description": ct.get("description", ""),
                "parameters": ct.get("parameters", []),
                "category": ct.get("category", "custom"), "source": "custom",
            })
        try:
            result = await execute_platform_tool(
                payload.tool_name, payload.parameters, server_name, all_tools, is_connected,
            )
            return {"result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    custom_tool = await db.custom_tools.find_one(
        {"app_name": server_name, "name": payload.tool_name}, {"_id": 0}
    )
    if custom_tool:
        return await universal_execute_custom_tool(
            server_name, payload.tool_name, {"parameters": payload.parameters}
        )

    running = get_running_server(server_name)
    if not running or not running.is_connected:
        raise HTTPException(status_code=400, detail=f"Server '{server_name}' is not running")
    try:
        result = await running.call_tool(payload.tool_name, payload.parameters)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@servers_router.put("/{server_name}/tools/{tool_name}/params/{param_name}", dependencies=[Depends(require_admin)])
async def update_server_tool_param(server_name: str, tool_name: str, param_name: str, param: ParamSchema):
    param_dict = param.model_dump()
    existing = await db.tool_overrides.find_one(
        {"app_name": server_name, "tool_name": tool_name}, {"_id": 0}
    )
    if existing and existing.get("param_overrides"):
        found = False
        for i, p in enumerate(existing["param_overrides"]):
            if p["name"] == param_name:
                existing["param_overrides"][i] = param_dict
                found = True
                break
        if not found:
            existing["param_overrides"].append(param_dict)
        await db.tool_overrides.update_one(
            {"app_name": server_name, "tool_name": tool_name},
            {"$set": {"param_overrides": existing["param_overrides"]}},
        )
    else:
        await db.tool_overrides.update_one(
            {"app_name": server_name, "tool_name": tool_name},
            {"$set": {"param_overrides": [param_dict]}},
            upsert=True,
        )
    return {"status": "updated", "tool_name": tool_name, "param": param_dict}


@servers_router.delete("/{server_name}/tools/{tool_name}/params/{param_name}", dependencies=[Depends(require_admin)])
async def delete_server_tool_param(server_name: str, tool_name: str, param_name: str):
    await db.tool_overrides.update_one(
        {"app_name": server_name, "tool_name": tool_name},
        {"$pull": {"param_overrides": {"name": param_name}}},
    )
    return {"status": "deleted", "tool_name": tool_name, "param_name": param_name}


@servers_router.get("/{server_name}/output-format", dependencies=[Depends(require_admin)])
async def get_server_output_format(server_name: str):
    srv = await db.mcp_servers.find_one({"name": server_name}, {"_id": 0, "output_format": 1})
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"output_format": srv.get("output_format", "json")}


@servers_router.post("/{server_name}/output-format", dependencies=[Depends(require_admin)])
async def save_server_output_format(server_name: str, payload: dict):
    fmt = payload.get("output_format", "json")
    if fmt not in ("json", "toon"):
        raise HTTPException(status_code=400, detail="Invalid format. Use 'json' or 'toon'.")
    result = await db.mcp_servers.update_one(
        {"name": server_name}, {"$set": {"output_format": fmt}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"output_format": fmt}


@servers_router.delete("/{server_name}", dependencies=[Depends(require_admin)])
async def remove_server(server_name: str):
    """Remove a server and clean up."""
    try:
        await stop_mcp_server(server_name)
    except Exception as e:
        logger.warning(f"Failed to stop server process '{server_name}': {e}")
    await db.mcp_servers.delete_one({"name": server_name})
    await db.server_credentials.delete_one({"server_name": server_name})
    await db.api_keys.delete_many({"app_name": server_name})
    return {"status": "removed"}


@servers_router.post("/{server_name}/webhooks/receive")
async def receive_server_webhook(server_name: str, request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    event = {
        "server_name": server_name,
        "event": body.get("event", "unknown"),
        "data": body,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.webhook_events.insert_one({**event, "_stored": True})
    count = await db.webhook_events.count_documents({"server_name": server_name})
    if count > 500:
        oldest = await db.webhook_events.find({"server_name": server_name}).sort("received_at", 1).limit(count - 500).to_list(count - 500)
        if oldest:
            ids = [o["_id"] for o in oldest]
            await db.webhook_events.delete_many({"_id": {"$in": ids}})
    for q in webhook_subscribers:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass
    logger.info(f"Webhook received for {server_name}: {event['event']}")
    return {"status": "received"}


@servers_router.get("/{server_name}/webhooks/events", dependencies=[Depends(require_jwt_or_api_key)])
async def stream_server_webhook_events(server_name: str):
    queue = asyncio.Queue(maxsize=100)
    webhook_subscribers.append(queue)
    async def event_generator():
        try:
            while True:
                event = await queue.get()
                if event.get("server_name", server_name) == server_name:
                    yield f"data: {json.dumps(event, default=str)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            webhook_subscribers.remove(queue)
    return StreamingResponse(event_generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@servers_router.get("/{server_name}/webhooks/events/history", dependencies=[Depends(require_jwt_or_api_key)])
async def get_server_webhook_history(server_name: str, limit: int = 50):
    events = await db.webhook_events.find(
        {"server_name": server_name}, {"_id": 0, "_stored": 0}
    ).sort("received_at", -1).limit(limit).to_list(limit)
    return {"events": events}



# ══════════════════════════════════════════════════════════════════
#  UNIVERSAL CUSTOM TOOLS  (/api/tools) — works for any server
# ══════════════════════════════════════════════════════════════════

def _parse_schema_universal(text: str) -> dict:
    import shlex

    tool = {"name": "", "description": "", "parameters": [], "method": "POST", "path": "", "base_url": ""}

    if text.strip().startswith("curl"):
        text_clean = text.replace("\\\n", " ").replace("\\\r\n", " ")
        try:
            parts = shlex.split(text_clean)
        except ValueError:
            parts = text_clean.split()

        method = "GET"
        url = ""
        data_str = ""

        i = 0
        while i < len(parts):
            p = parts[i]
            if p in ("-X", "--request") and i + 1 < len(parts):
                method = parts[i + 1].upper()
                i += 2
            elif p in ("-H", "--header") and i + 1 < len(parts):
                i += 2
            elif p in ("-d", "--data", "--data-raw") and i + 1 < len(parts):
                data_str = parts[i + 1]
                i += 2
            elif p.startswith("http"):
                url = p
                i += 1
            elif p == "--url" and i + 1 < len(parts):
                url = parts[i + 1]
                i += 2
            else:
                i += 1

        tool["method"] = method

        if url:
            tool["base_url"] = url

            from urllib.parse import urlparse
            parsed = urlparse(url)
            path = parsed.path
            if path:
                tool["path"] = path

            path_parts = [p for p in path.split("/") if p and not p.startswith("{")]
            method_prefix = {"GET": "get", "POST": "create", "PUT": "update", "PATCH": "update", "DELETE": "delete"}.get(method, "run")
            if path_parts:
                resource = path_parts[-1].rstrip("s") if len(path_parts[-1]) > 3 else path_parts[-1]
                tool["name"] = f"{method_prefix}_{resource}"

        if data_str:
            try:
                data_str_clean = data_str.strip().strip("'\"")
                body = json.loads(data_str_clean)
                tool["parameters"] = _extract_params_from_json(body)
            except json.JSONDecodeError:
                pass

        if tool["path"]:
            path_params = re.findall(r'\{(\w+)\}', tool["path"])
            existing_names = {p["name"] for p in tool["parameters"]}
            for pp in path_params:
                if pp not in existing_names:
                    tool["parameters"].insert(0, {
                        "name": pp, "type": "string", "required": True,
                        "description": f"Path parameter: {pp}", "enum_options": [],
                    })
    else:
        try:
            body = json.loads(text)
            tool["parameters"] = _extract_params_from_json(body)
            tool["name"] = "new_tool"
        except json.JSONDecodeError:
            raise ValueError("Could not parse as cURL or JSON")

    return tool


@tools_router.post("/parse-schema", dependencies=[Depends(require_admin)])
async def universal_parse_schema(payload: dict):
    schema_text = payload.get("schema", "").strip()
    if not schema_text:
        raise HTTPException(status_code=400, detail="Schema text required")
    try:
        tool_def = _parse_schema_universal(schema_text)
        return {"tool": tool_def}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse schema: {str(e)}")


@tools_router.post("/{app_name}/create", dependencies=[Depends(require_admin)])
async def universal_create_custom_tool(app_name: str, payload: CreateToolPayload):
    existing_custom = await db.custom_tools.find_one(
        {"app_name": app_name, "name": payload.name}, {"_id": 0}
    )
    if app_name == "chatwoot":
        tool_manager = mcp_server_instance._tool_manager
        if payload.name in tool_manager._tools or existing_custom:
            raise HTTPException(status_code=409, detail=f"Tool '{payload.name}' already exists")
    elif existing_custom:
        raise HTTPException(status_code=409, detail=f"Tool '{payload.name}' already exists")

    doc = {
        "app_name": app_name,
        "name": payload.name,
        "description": payload.description,
        "category": payload.category,
        "parameters": payload.parameters,
        "source_schema": payload.source_schema,
        "method": payload.method or "POST",
        "path": payload.path or "",
        "base_url": payload.base_url or "",
        "enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.custom_tools.insert_one(doc)
    return {"status": "created", "tool": {k: v for k, v in doc.items() if k != "_id"}}


@tools_router.get("/{app_name}", dependencies=[Depends(require_admin)])
async def universal_list_custom_tools(app_name: str):
    custom_tools = await db.custom_tools.find({"app_name": app_name}, {"_id": 0}).to_list(200)
    tools = []
    for ct in custom_tools:
        tools.append({
            "name": ct["name"],
            "description": ct.get("description", ""),
            "parameters": ct.get("parameters", []),
            "category": ct.get("category", "custom"),
            "source": "custom",
            "enabled": ct.get("enabled", True),
            "method": ct.get("method", ""),
            "path": ct.get("path", ""),
            "base_url": ct.get("base_url", ""),
        })
    return {"tools": tools}


@tools_router.put("/{app_name}/{tool_name}", dependencies=[Depends(require_admin)])
async def universal_update_custom_tool(app_name: str, tool_name: str, payload: dict):
    update = {}
    for field in ["name", "description", "category", "parameters", "enabled", "method", "path", "base_url"]:
        if field in payload:
            update[field] = payload[field]
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.custom_tools.update_one(
        {"app_name": app_name, "name": tool_name},
        {"$set": update},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Custom tool not found")
    return {"status": "updated", "tool_name": tool_name}


@tools_router.delete("/{app_name}/{tool_name}", dependencies=[Depends(require_admin)])
async def universal_delete_custom_tool(app_name: str, tool_name: str):
    result = await db.custom_tools.delete_one({"app_name": app_name, "name": tool_name})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Custom tool not found")
    return {"status": "deleted", "tool_name": tool_name}


@tools_router.post("/{app_name}/{tool_name}/execute", dependencies=[Depends(require_jwt_or_api_key)])
async def universal_execute_custom_tool(app_name: str, tool_name: str, payload: dict):
    custom_tool = await db.custom_tools.find_one(
        {"app_name": app_name, "name": tool_name}, {"_id": 0}
    )
    if not custom_tool:
        raise HTTPException(status_code=404, detail=f"Custom tool '{tool_name}' not found")

    base_url = custom_tool.get("base_url", "")
    method = custom_tool.get("method", "GET").upper()
    path = custom_tool.get("path", "")
    parameters = payload.get("parameters", {})

    if base_url:
        import httpx
        url = base_url
        params = dict(parameters)
        for key in list(params.keys()):
            placeholder = "{" + key + "}"
            if placeholder in url:
                url = url.replace(placeholder, str(params.pop(key)))
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method in ("POST", "PUT", "PATCH"):
                    resp = await client.request(method, url, json=params)
                else:
                    resp = await client.request(method, url, params=params if params else None)
                try:
                    return {"result": resp.json()}
                except Exception:
                    return {"result": resp.text}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    elif app_name == "chatwoot":
        config = _get_chatwoot_config()
        if not config["chatwoot_url"] or not config["api_token"]:
            raise HTTPException(status_code=400, detail="Chatwoot not configured")
        c = ChatwootClient(config["chatwoot_url"], config["api_token"], config["account_id"])
        params = dict(parameters)
        for key in list(params.keys()):
            placeholder = "{" + key + "}"
            if placeholder in path:
                path = path.replace(placeholder, str(params.pop(key)))
        try:
            if method in ("POST", "PUT", "PATCH"):
                result = await c._request(method, path, json=params)
            else:
                result = await c._request(method, path, params=params or None)
            return {"result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=400, detail="Custom tool has no base_url configured")


# ══════════════════════════════════════════════════════════════════
#  MARKETPLACE  (/api/marketplace)
# ══════════════════════════════════════════════════════════════════

# Curated catalog of popular MCP servers
CURATED_SERVERS = [
    {
        "slug": "chatwoot",
        "name": "Chatwoot MCP",
        "description": "Complete Chatwoot API coverage via MCP. Manage conversations, contacts, messages, agents, inboxes, teams, labels, and more.",
        "github_url": "",
        "runtime": "python",
        "pip_package": "",
        "command": "python",
        "args": ["mcp_stdio.py"],
        "category": "communication",
        "credentials_schema": [
            {"key": "CHATWOOT_URL", "label": "Instance URL", "required": True, "hint": "e.g. https://app.chatwoot.com"},
            {"key": "CHATWOOT_API_TOKEN", "label": "API Token", "required": True, "hint": "Your Chatwoot user access token"},
            {"key": "CHATWOOT_ACCOUNT_ID", "label": "Account ID", "required": True, "hint": "Numeric account ID"},
        ],
        "features": ["filters", "webhooks"],
        "source": "curated",
    },
    {
        "slug": "github",
        "name": "GitHub",
        "description": "Manage repositories, issues, pull requests, and more via the GitHub API",
        "github_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/github",
        "runtime": "node",
        "npm_package": "@modelcontextprotocol/server-github",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "category": "developer",
        "credentials_schema": [
            {"key": "GITHUB_PERSONAL_ACCESS_TOKEN", "label": "GitHub Personal Access Token", "required": True, "hint": "Create at github.com/settings/tokens"}
        ],
        "source": "curated",
    },
    {
        "slug": "gitlab",
        "name": "GitLab",
        "description": "Interact with GitLab projects, merge requests, issues, and CI/CD pipelines",
        "github_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/gitlab",
        "runtime": "node",
        "npm_package": "@modelcontextprotocol/server-gitlab",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-gitlab"],
        "category": "developer",
        "credentials_schema": [
            {"key": "GITLAB_PERSONAL_ACCESS_TOKEN", "label": "GitLab Access Token", "required": True},
            {"key": "GITLAB_API_URL", "label": "GitLab API URL", "required": False},
        ],
        "source": "curated",
    },
    {
        "slug": "slack",
        "name": "Slack",
        "description": "Send messages, manage channels, and interact with Slack workspaces",
        "github_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/slack",
        "runtime": "node",
        "npm_package": "@modelcontextprotocol/server-slack",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-slack"],
        "category": "communication",
        "credentials_schema": [
            {"key": "SLACK_BOT_TOKEN", "label": "Slack Bot Token", "required": True},
            {"key": "SLACK_TEAM_ID", "label": "Slack Team ID", "required": True},
        ],
        "source": "curated",
    },
    {
        "slug": "postgres",
        "name": "PostgreSQL",
        "description": "Query and manage PostgreSQL databases with read-only access",
        "github_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/postgres",
        "runtime": "node",
        "npm_package": "@modelcontextprotocol/server-postgres",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres"],
        "category": "database",
        "credentials_schema": [
            {"key": "POSTGRES_CONNECTION_STRING", "label": "PostgreSQL Connection String", "required": True},
        ],
        "source": "curated",
    },
    {
        "slug": "brave-search",
        "name": "Brave Search",
        "description": "Web and local search powered by the Brave Search API",
        "github_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/brave-search",
        "runtime": "node",
        "npm_package": "@modelcontextprotocol/server-brave-search",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-brave-search"],
        "category": "search",
        "credentials_schema": [
            {"key": "BRAVE_API_KEY", "label": "Brave Search API Key", "required": True},
        ],
        "source": "curated",
    },
    {
        "slug": "filesystem",
        "name": "Filesystem",
        "description": "Secure file operations with configurable access controls",
        "github_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem",
        "runtime": "node",
        "npm_package": "@modelcontextprotocol/server-filesystem",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem"],
        "category": "utility",
        "credentials_schema": [
            {"key": "ALLOWED_DIRECTORIES", "label": "Allowed Directories (comma-separated)", "required": True},
        ],
        "source": "curated",
    },
    {
        "slug": "memory",
        "name": "Memory",
        "description": "Knowledge graph-based persistent memory for AI agents",
        "github_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/memory",
        "runtime": "node",
        "npm_package": "@modelcontextprotocol/server-memory",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "category": "utility",
        "credentials_schema": [],
        "source": "curated",
    },
    {
        "slug": "fetch",
        "name": "Fetch",
        "description": "Fetch and convert web content for AI consumption",
        "github_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/fetch",
        "runtime": "node",
        "npm_package": "@modelcontextprotocol/server-fetch",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-fetch"],
        "category": "utility",
        "credentials_schema": [],
        "source": "curated",
    },
    {
        "slug": "puppeteer",
        "name": "Puppeteer",
        "description": "Browser automation and web scraping via headless Chrome",
        "github_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/puppeteer",
        "runtime": "node",
        "npm_package": "@modelcontextprotocol/server-puppeteer",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
        "category": "automation",
        "credentials_schema": [],
        "source": "curated",
    },
    {
        "slug": "google-drive",
        "name": "Google Drive",
        "description": "Search, read, and manage files in Google Drive",
        "github_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/gdrive",
        "runtime": "node",
        "npm_package": "@modelcontextprotocol/server-gdrive",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-gdrive"],
        "category": "storage",
        "credentials_schema": [
            {"key": "GOOGLE_DRIVE_CREDENTIALS", "label": "Google Service Account JSON", "required": True},
        ],
        "source": "curated",
    },
    {
        "slug": "sentry",
        "name": "Sentry",
        "description": "Retrieve and analyze error reports and issues from Sentry",
        "github_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/sentry",
        "runtime": "node",
        "npm_package": "@modelcontextprotocol/server-sentry",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sentry"],
        "category": "monitoring",
        "credentials_schema": [
            {"key": "SENTRY_AUTH_TOKEN", "label": "Sentry Auth Token", "required": True},
            {"key": "SENTRY_ORGANIZATION", "label": "Sentry Organization Slug", "required": True},
        ],
        "source": "curated",
    },
    {
        "slug": "sqlite",
        "name": "SQLite",
        "description": "Query and analyze SQLite databases with business intelligence features",
        "github_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite",
        "runtime": "node",
        "npm_package": "@modelcontextprotocol/server-sqlite",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sqlite"],
        "category": "database",
        "credentials_schema": [
            {"key": "SQLITE_DB_PATH", "label": "SQLite Database Path", "required": True},
        ],
        "source": "curated",
    },
    {
        "slug": "firecrawl",
        "name": "Firecrawl",
        "description": "Web scraping and crawling API — turn websites into LLM-ready markdown data",
        "github_url": "https://github.com/mendableai/firecrawl-mcp-server",
        "runtime": "node",
        "npm_package": "firecrawl-mcp",
        "command": "npx",
        "args": ["-y", "firecrawl-mcp"],
        "category": "search",
        "credentials_schema": [
            {"key": "FIRECRAWL_API_KEY", "label": "Firecrawl API Key", "required": True, "hint": "Get your key at firecrawl.dev"},
        ],
        "source": "curated",
    },
]


@marketplace_router.get("/catalog")
async def list_catalog(category: str = "", search: str = ""):
    """List all marketplace servers (curated + community)."""
    community = []
    try:
        community = await db.marketplace.find({}, {"_id": 0}).to_list(200)
    except Exception as e:
        logger.warning(f"Failed to fetch community marketplace entries: {e}")

    installed_names = set()
    try:
        installed_servers = await db.mcp_servers.find({}, {"_id": 0, "name": 1}).to_list(200)
        for s in installed_servers:
            name = s.get("name", "")
            if name:
                installed_names.add(name)
    except Exception as e:
        logger.warning(f"Failed to fetch installed servers: {e}")

    all_entries = []
    for entry in CURATED_SERVERS:
        e = {**entry, "installed": entry["slug"] in installed_names}
        all_entries.append(e)

    for entry in community:
        e = {**entry, "installed": entry.get("slug", entry.get("name", "")) in installed_names}
        all_entries.append(e)

    if category:
        all_entries = [e for e in all_entries if e.get("category", "") == category]
    if search:
        q = search.lower()
        all_entries = [e for e in all_entries if q in e.get("name", "").lower() or q in e.get("description", "").lower() or q in e.get("slug", "").lower()]

    seen = set()
    unique = []
    for e in all_entries:
        slug = e.get("slug", e.get("name", ""))
        if slug not in seen:
            seen.add(slug)
            unique.append(e)

    return {"catalog": unique, "categories": sorted(set(e.get("category", "other") for e in unique))}


@marketplace_router.post("/publish", dependencies=[Depends(require_admin)])
async def publish_to_marketplace(payload: dict):
    """Publish an installed server to the community marketplace."""
    server_name = payload.get("server_name", "").strip()
    if not server_name:
        raise HTTPException(status_code=400, detail="server_name required")

    srv = await db.mcp_servers.find_one({"name": server_name}, {"_id": 0})
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found in your installations")

    # Check not already published
    existing = await db.marketplace.find_one({"slug": server_name}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=409, detail="Already published to marketplace")

    entry = {
        "slug": server_name,
        "name": srv.get("display_name", server_name),
        "description": payload.get("description", srv.get("description", "")),
        "github_url": srv.get("github_url", ""),
        "runtime": srv.get("runtime", "node"),
        "npm_package": srv.get("npm_package", ""),
        "pip_package": srv.get("pip_package", ""),
        "command": srv.get("command", ""),
        "args": srv.get("args", []),
        "category": payload.get("category", "community"),
        "credentials_schema": srv.get("credentials_schema", []),
        "source": "community",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "installs": 0,
    }
    await db.marketplace.insert_one(entry)
    return {"status": "published", "slug": server_name}


@marketplace_router.delete("/{slug}", dependencies=[Depends(require_admin)])
async def unpublish_from_marketplace(slug: str):
    """Remove a server from the community marketplace."""
    result = await db.marketplace.delete_one({"slug": slug})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found in marketplace")
    return {"status": "removed"}



# ══════════════════════════════════════════════════════════════════
#  MCP SSE Transport (namespaced under chatwoot)
# ══════════════════════════════════════════════════════════════════
sse_transport = SseServerTransport("/api/chatwoot/mcp/messages/")


async def handle_sse(request):
    """MCP SSE handler — validates API key before allowing connection."""
    api_key = get_api_key_from_request(request)
    if api_key:
        key_doc = await db.api_keys.find_one(
            {"app_name": "chatwoot", "key": api_key, "is_active": True}, {"_id": 0}
        )
        if not key_doc:
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
    else:
        token = get_token_from_request(request)
        if not token:
            return JSONResponse(status_code=401, content={"detail": "API key or JWT required"})
        try:
            verify_access_token(token)
        except HTTPException:
            return JSONResponse(status_code=401, content={"detail": "Invalid JWT"})

    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        await mcp_server_instance._mcp_server.run(
            read_stream, write_stream,
            mcp_server_instance._mcp_server.create_initialization_options(),
        )


# ══════════════════════════════════════════════════════════════════
#  Root API
# ══════════════════════════════════════════════════════════════════
@app.get("/api")
@app.get("/api/")
async def api_root():
    return {"message": "MCP Hub API", "version": "1.0"}


# ══════════════════════════════════════════════════════════════════
#  Mount routers and SSE
# ══════════════════════════════════════════════════════════════════
app.include_router(auth_router)
app.include_router(apps_router)
app.include_router(chatwoot_router)
app.include_router(servers_router)
app.include_router(tools_router)
app.include_router(marketplace_router)

app.router.routes.append(Route("/api/chatwoot/mcp/sse", endpoint=handle_sse))
app.mount("/api/chatwoot/mcp/messages/", app=sse_transport.handle_post_message)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve built frontend (Docker deployment) ──
if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR / "static")), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        file_path = STATIC_DIR / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(STATIC_DIR / "index.html"))


@app.on_event("startup")
async def startup():
    # Create indexes (non-blocking)
    try:
        await db.api_keys.create_index("key_id", unique=True)
        await db.api_keys.create_index([("app_name", 1), ("is_active", 1)])
        await db.mcp_servers.create_index("name", unique=True)
        await db.server_credentials.create_index("server_name", unique=True)
        await db.marketplace.create_index("slug", unique=True)
    except Exception as e:
        logger.warning(f"Index creation deferred: {e}")

    # Load chatwoot config (with decryption support)
    try:
        config = await db.mcp_config.find_one({"key": "chatwoot"}, {"_id": 0})
        if config:
            if config.get("output_format"):
                set_output_format(config["output_format"])
            if config.get("chatwoot_url"):
                token = config.get("api_token", "")
                if config.get("api_token_encrypted"):
                    try:
                        token = decrypt(token)
                    except Exception:
                        pass
                _set_chatwoot_config(config["chatwoot_url"], token, config.get("account_id", 0))
                logger.info(f"Loaded Chatwoot config from DB: {config['chatwoot_url']}")
        else:
            url = os.environ.get("CHATWOOT_URL", "")
            token = os.environ.get("CHATWOOT_API_TOKEN", "")
            account_id = int(os.environ.get("CHATWOOT_ACCOUNT_ID", "0") or "0")
            if url and token:
                set_runtime_config(url, token, account_id)
                logger.info(f"Using Chatwoot config from env: {url}")
    except Exception as e:
        logger.warning(f"Config loading deferred: {e}")
        url = os.environ.get("CHATWOOT_URL", "")
        token = os.environ.get("CHATWOOT_API_TOKEN", "")
        account_id = int(os.environ.get("CHATWOOT_ACCOUNT_ID", "0") or "0")
        if url and token:
            set_runtime_config(url, token, account_id)

    # Auto-start enabled dynamic MCP servers (staggered to reduce CPU spike)
    try:
        servers = await db.mcp_servers.find({"enabled": True}, {"_id": 0}).to_list(50)
        started = 0
        for srv in servers:
            if not srv.get("configured"):
                continue
            try:
                srv_name = srv.get("name", "")
                if not srv_name:
                    continue
                creds_doc = await db.server_credentials.find_one(
                    {"server_name": srv_name}, {"_id": 0}
                )
                env_vars = {}
                if creds_doc and creds_doc.get("credentials"):
                    for k, v in creds_doc["credentials"].items():
                        try:
                            env_vars[k] = decrypt(v)
                        except Exception:
                            env_vars[k] = v
                server_config = {
                    "name": srv_name,
                    "command": srv.get("command", ""),
                    "args": srv.get("args", []),
                    "env_vars": env_vars,
                    "runtime": srv.get("runtime", "node"),
                }
                await start_mcp_server(server_config)
                started += 1
                if started < len(servers):
                    await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"Failed to auto-start {srv.get('name', '?')}: {e}")
    except Exception as e:
        logger.warning(f"Server auto-start deferred: {e}")

    logger.info(f"Admin email: {os.environ.get('ADMIN_EMAIL', 'NOT SET')}")


@app.on_event("shutdown")
async def shutdown_db_client():
    # Stop all dynamic servers
    for name in list_running_servers():
        try:
            await stop_mcp_server(name)
        except Exception:
            pass
    client.close()

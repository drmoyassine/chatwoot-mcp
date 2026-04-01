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
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel
from typing import Optional

ROOT_DIR = Path(__file__).parent
# Load .env: try working dir first (Easypanel creates .env here), then backend dir as fallback
# override=True so .env file values win over empty Docker ENV defaults
load_dotenv(override=True)
load_dotenv(ROOT_DIR / '.env', override=False)

STATIC_DIR = ROOT_DIR / "static"

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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


# ══════════════════════════════════════════════════════════════════
#  Routers
# ══════════════════════════════════════════════════════════════════
auth_router = APIRouter(prefix="/api/auth")
apps_router = APIRouter(prefix="/api/apps")
chatwoot_router = APIRouter(prefix="/api/chatwoot")


# ══════════════════════════════════════════════════════════════════
#  Auth Middleware for Chatwoot routes: accept JWT OR API key
# ══════════════════════════════════════════════════════════════════
async def require_jwt_or_api_key(request: Request):
    """Accept either a valid JWT (dashboard) or a valid API key (external)."""
    # Try JWT first
    token = get_token_from_request(request)
    if token:
        try:
            verify_access_token(token)
            return
        except HTTPException:
            pass
    # Try API key
    api_key = get_api_key_from_request(request)
    if api_key:
        key_doc = await db.api_keys.find_one(
            {"app_name": "chatwoot", "key": api_key, "is_active": True},
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
    """List all installed MCP apps."""
    await _ensure_config_loaded()
    chatwoot_config = _get_chatwoot_config()
    key_count = await db.api_keys.count_documents({"app_name": "chatwoot", "is_active": True})
    apps = [
        {
            "name": "chatwoot",
            "display_name": "Chatwoot",
            "description": "Customer support & engagement platform",
            "configured": bool(chatwoot_config.get("chatwoot_url") and chatwoot_config.get("api_token")),
            "tools_count": len(_get_tool_definitions()),
            "active_keys": key_count,
            "mcp_endpoint": "/api/chatwoot/mcp/sse",
        }
    ]
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
        _set_chatwoot_config(config["chatwoot_url"], config.get("api_token", ""), config.get("account_id", 0))
        logger.info(f"Lazy-loaded Chatwoot config from DB: {config['chatwoot_url']}")


def _set_chatwoot_config(url: str, token: str, account_id: int):
    os.environ["CHATWOOT_URL"] = url
    os.environ["CHATWOOT_API_TOKEN"] = token
    os.environ["CHATWOOT_ACCOUNT_ID"] = str(account_id)
    set_runtime_config(url, token, account_id)


def _get_tool_definitions() -> list:
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
            "api_token": payload.api_token,
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
    return {"tools": _get_tool_definitions()}


@chatwoot_router.post("/tools/execute", dependencies=[Depends(require_jwt_or_api_key)])
async def execute_tool(payload: ToolExecutePayload):
    config = _get_chatwoot_config()
    if not config["chatwoot_url"] or not config["api_token"]:
        raise HTTPException(status_code=400, detail="Chatwoot not configured")
    tool_manager = mcp_server_instance._tool_manager
    tool = tool_manager._tools.get(payload.tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{payload.tool_name}' not found")
    try:
        result = await tool.fn(**payload.parameters)
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
    return {
        "server_name": "chatwoot-mcp-server",
        "transport": {
            "sse": {"endpoint": "/api/chatwoot/mcp/sse", "messages_endpoint": "/api/chatwoot/mcp/messages/"},
            "stdio": {"command": "python mcp_stdio.py", "description": "Run locally for stdio transport"},
        },
        "tools_count": len(_get_tool_definitions()),
        "configured": bool(config["chatwoot_url"] and config["api_token"]),
    }


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
    # Create indexes (non-blocking — skip if MongoDB isn't ready yet)
    try:
        await db.api_keys.create_index("key_id", unique=True)
        await db.api_keys.create_index([("app_name", 1), ("is_active", 1)])
    except Exception as e:
        logger.warning(f"Index creation deferred (MongoDB may not be ready): {e}")

    # Load chatwoot config
    try:
        config = await db.mcp_config.find_one({"key": "chatwoot"}, {"_id": 0})
        if config:
            if config.get("output_format"):
                set_output_format(config["output_format"])
                logger.info(f"Output format: {config['output_format']}")
            if config.get("chatwoot_url"):
                _set_chatwoot_config(config["chatwoot_url"], config.get("api_token", ""), config.get("account_id", 0))
                logger.info(f"Loaded Chatwoot config from DB: {config['chatwoot_url']}")
        else:
            url = os.environ.get("CHATWOOT_URL", "")
            token = os.environ.get("CHATWOOT_API_TOKEN", "")
            account_id = int(os.environ.get("CHATWOOT_ACCOUNT_ID", "0") or "0")
            if url and token:
                set_runtime_config(url, token, account_id)
                logger.info(f"Using Chatwoot config from env: {url}")
            else:
                logger.warning("No Chatwoot config found. Configure via UI or set env vars.")
    except Exception as e:
        logger.warning(f"Config loading deferred (MongoDB may not be ready): {e}")
        # Fall back to env vars
        url = os.environ.get("CHATWOOT_URL", "")
        token = os.environ.get("CHATWOOT_API_TOKEN", "")
        account_id = int(os.environ.get("CHATWOOT_ACCOUNT_ID", "0") or "0")
        if url and token:
            set_runtime_config(url, token, account_id)
            logger.info(f"Using Chatwoot config from env (DB unavailable): {url}")

    logger.info(f"Admin email: {os.environ.get('ADMIN_EMAIL', 'NOT SET')}")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

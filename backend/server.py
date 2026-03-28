from fastapi import FastAPI, APIRouter, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.routing import Mount, Route
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
load_dotenv(ROOT_DIR / '.env', override=True)

# Path to built frontend (populated in Docker)
STATIC_DIR = ROOT_DIR / "static"

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# In-memory event subscribers for SSE streaming
webhook_subscribers: list[asyncio.Queue] = []


# ── Pydantic models ──
class ConfigPayload(BaseModel):
    chatwoot_url: str
    api_token: str
    account_id: int


class ToolExecutePayload(BaseModel):
    tool_name: str
    parameters: dict = {}


# ── Import MCP server and client ──
from mcp_tools import mcp as mcp_server_instance, set_runtime_config  # noqa: E402
from chatwoot_client import ChatwootClient  # noqa: E402


def _get_chatwoot_config() -> dict:
    """Get current Chatwoot config from env."""
    return {
        "chatwoot_url": os.environ.get("CHATWOOT_URL", ""),
        "api_token": os.environ.get("CHATWOOT_API_TOKEN", ""),
        "account_id": int(os.environ.get("CHATWOOT_ACCOUNT_ID", "0")),
    }


def _set_chatwoot_config(url: str, token: str, account_id: int):
    """Set Chatwoot config in env (runtime) and sync to MCP tools."""
    os.environ["CHATWOOT_URL"] = url
    os.environ["CHATWOOT_API_TOKEN"] = token
    os.environ["CHATWOOT_ACCOUNT_ID"] = str(account_id)
    set_runtime_config(url, token, account_id)


# ── Configuration API ──
@api_router.get("/config")
async def get_config():
    config = _get_chatwoot_config()
    return {
        "chatwoot_url": config["chatwoot_url"],
        "api_token_set": bool(config["api_token"]),
        "api_token_masked": config["api_token"][:6] + "***" if config["api_token"] else "",
        "account_id": config["account_id"],
    }


@api_router.post("/config")
async def save_config(payload: ConfigPayload):
    _set_chatwoot_config(payload.chatwoot_url, payload.api_token, payload.account_id)
    # Persist to MongoDB
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


@api_router.post("/config/test")
async def test_connection():
    config = _get_chatwoot_config()
    if not config["chatwoot_url"] or not config["api_token"] or not config["account_id"]:
        raise HTTPException(status_code=400, detail="Configuration incomplete")
    try:
        c = ChatwootClient(config["chatwoot_url"], config["api_token"], config["account_id"])
        result = await c.get_account()
        return {"status": "connected", "account_name": result.get("name", ""), "account_id": result.get("id", 0)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Tools Listing API ──
def _get_tool_definitions() -> list:
    """Extract all registered MCP tools with their metadata."""
    tools = []
    # Get tools from the FastMCP server
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

        # Determine category from tool name
        category = "account"
        for cat in ["agent", "contact", "conversation", "message", "inbox", "team",
                     "label", "canned", "custom_attribute", "webhook", "report"]:
            if cat in name:
                category = cat.replace("_", " ").title().replace(" ", "")
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


@api_router.get("/tools")
async def list_tools():
    return {"tools": _get_tool_definitions()}


@api_router.post("/tools/execute")
async def execute_tool(payload: ToolExecutePayload):
    """Execute an MCP tool directly (for the testing UI)."""
    config = _get_chatwoot_config()
    if not config["chatwoot_url"] or not config["api_token"]:
        raise HTTPException(status_code=400, detail="Chatwoot not configured")

    tool_manager = mcp_server_instance._tool_manager
    tool = tool_manager._tools.get(payload.tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{payload.tool_name}' not found")

    try:
        result = await tool.fn(**payload.parameters)
        return {"result": json.loads(result) if isinstance(result, str) else result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Webhook Receiver & Event Stream ──
@api_router.post("/webhooks/receive")
async def receive_webhook(request: Request):
    """Endpoint for Chatwoot to POST webhook events to."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    event = {
        "event": body.get("event", "unknown"),
        "data": body,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    # Store in MongoDB (keep last 500 events)
    await db.webhook_events.insert_one({**event, "_stored": True})
    count = await db.webhook_events.count_documents({})
    if count > 500:
        oldest = await db.webhook_events.find().sort("received_at", 1).limit(count - 500).to_list(count - 500)
        if oldest:
            ids = [o["_id"] for o in oldest]
            await db.webhook_events.delete_many({"_id": {"$in": ids}})
    # Notify all SSE subscribers
    for q in webhook_subscribers:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass
    logger.info(f"Webhook received: {event['event']}")
    return {"status": "received"}


@api_router.get("/webhooks/events")
async def stream_webhook_events():
    """SSE endpoint to stream webhook events to the frontend in real-time."""
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


@api_router.get("/webhooks/events/history")
async def get_webhook_history(limit: int = 50):
    """Get recent webhook events from the database."""
    events = await db.webhook_events.find({}, {"_id": 0, "_stored": 0}).sort("received_at", -1).limit(limit).to_list(limit)
    return {"events": events}


@api_router.post("/tools/execute-with-file")
async def execute_tool_with_file(
    tool_name: str = Form(...),
    parameters: str = Form("{}"),
    file: Optional[UploadFile] = File(None),
):
    """Execute an MCP tool with optional file upload (for attachment tools)."""
    config = _get_chatwoot_config()
    if not config["chatwoot_url"] or not config["api_token"]:
        raise HTTPException(status_code=400, detail="Chatwoot not configured")

    params = json.loads(parameters)

    # If it's the attachment tool and we have a file, handle it specially
    if tool_name == "create_message_with_attachment" and file:
        from chatwoot_client import ChatwootClient
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

    # Regular tool execution
    tool_manager = mcp_server_instance._tool_manager
    tool = tool_manager._tools.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    try:
        result = await tool.fn(**params)
        return {"result": json.loads(result) if isinstance(result, str) else result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── MCP SSE Transport ──
sse_transport = SseServerTransport("/api/mcp/messages/")


async def handle_sse(request):
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        await mcp_server_instance._mcp_server.run(
            read_stream,
            write_stream,
            mcp_server_instance._mcp_server.create_initialization_options(),
        )


# ── MCP Info Endpoint ──
@api_router.get("/mcp/info")
async def mcp_info():
    config = _get_chatwoot_config()
    return {
        "server_name": "chatwoot-mcp-server",
        "transport": {
            "sse": {
                "endpoint": "/api/mcp/sse",
                "messages_endpoint": "/api/mcp/messages/",
            },
            "stdio": {
                "command": "python mcp_stdio.py",
                "description": "Run locally for stdio transport",
            },
        },
        "tools_count": len(_get_tool_definitions()),
        "configured": bool(config["chatwoot_url"] and config["api_token"]),
    }


# ── Root ──
@api_router.get("/")
async def root():
    return {"message": "Chatwoot MCP Server API"}


# Include the router and mount MCP SSE
app.include_router(api_router)

# Mount SSE routes
app.router.routes.append(Route("/api/mcp/sse", endpoint=handle_sse))
app.mount("/api/mcp/messages/", app=sse_transport.handle_post_message)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve built frontend (Docker deployment) ──
if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    # Serve static assets (JS, CSS, images)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR / "static")), name="frontend-assets")

    # SPA catch-all: serve index.html for any non-API route
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Don't intercept API or MCP routes
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        # Serve actual static files if they exist (favicon, manifest, etc.)
        file_path = STATIC_DIR / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        # Everything else → index.html (SPA routing)
        return FileResponse(str(STATIC_DIR / "index.html"))


@app.on_event("startup")
async def startup():
    # Load config from MongoDB if available
    config = await db.mcp_config.find_one({"key": "chatwoot"}, {"_id": 0})
    if config and config.get("chatwoot_url"):
        _set_chatwoot_config(
            config.get("chatwoot_url", ""),
            config.get("api_token", ""),
            config.get("account_id", 0),
        )
        logger.info(f"Loaded Chatwoot config from DB: {config.get('chatwoot_url', '')}")
    else:
        # Use env vars (from .env file or Docker env)
        url = os.environ.get("CHATWOOT_URL", "")
        token = os.environ.get("CHATWOOT_API_TOKEN", "")
        account_id = int(os.environ.get("CHATWOOT_ACCOUNT_ID", "0") or "0")
        if url and token:
            set_runtime_config(url, token, account_id)
            logger.info(f"Using Chatwoot config from env: {url}")
        else:
            logger.warning("No Chatwoot config found. Configure via UI or set env vars.")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

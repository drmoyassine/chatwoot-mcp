"""MCP Server Process Manager — spawns, monitors, and proxies to child MCP servers."""
import asyncio
import os
import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from crypto import encrypt, decrypt, encrypt_dict, decrypt_dict

logger = logging.getLogger(__name__)

# ── In-memory registry of running MCP server processes ──
_running_servers: dict[str, "MCPServerProcess"] = {}


class MCPServerProcess:
    """Manages a single MCP server subprocess."""

    def __init__(self, server_config: dict):
        self.name = server_config["name"]
        self.command = server_config["command"]
        self.args = server_config.get("args", [])
        self.env_vars = server_config.get("env_vars", {})  # Decrypted
        self.runtime = server_config.get("runtime", "node")  # node or python
        self.session: Optional[ClientSession] = None
        self._read_stream = None
        self._write_stream = None
        self._client_cm = None
        self._session_cm = None
        self._tools_cache = []
        self._connected = False
        self._lock = asyncio.Lock()

    @property
    def is_connected(self):
        return self._connected

    async def start(self):
        """Start the subprocess and connect via stdio."""
        async with self._lock:
            if self._connected:
                return
            try:
                # Build environment: inherit current + server-specific vars
                env = dict(os.environ)
                env.update(self.env_vars)

                server_params = StdioServerParameters(
                    command=self.command,
                    args=self.args,
                    env=env,
                )

                # Open the stdio transport
                self._client_cm = stdio_client(server_params)
                streams = await self._client_cm.__aenter__()
                self._read_stream, self._write_stream = streams

                # Create and initialize session
                self._session_cm = ClientSession(self._read_stream, self._write_stream)
                self.session = await self._session_cm.__aenter__()
                await self.session.initialize()

                # Discover tools
                tools_result = await self.session.list_tools()
                self._tools_cache = [
                    {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": _extract_tool_params(t),
                        "category": "general",
                        "source": "mcp",
                        "enabled": True,
                    }
                    for t in tools_result.tools
                ]

                self._connected = True
                logger.info(f"[{self.name}] Connected — {len(self._tools_cache)} tools discovered")

            except Exception as e:
                logger.error(f"[{self.name}] Failed to start: {e}")
                await self._cleanup()
                raise

    async def stop(self):
        """Stop the subprocess."""
        async with self._lock:
            await self._cleanup()
            logger.info(f"[{self.name}] Stopped")

    async def _cleanup(self):
        self._connected = False
        self.session = None
        try:
            if self._session_cm:
                await self._session_cm.__aexit__(None, None, None)
        except Exception:
            pass
        try:
            if self._client_cm:
                await self._client_cm.__aexit__(None, None, None)
        except Exception:
            pass
        self._session_cm = None
        self._client_cm = None

    def get_tools(self) -> list:
        return self._tools_cache

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call a tool on the child MCP server."""
        if not self._connected or not self.session:
            raise RuntimeError(f"Server '{self.name}' is not connected")
        result = await self.session.call_tool(tool_name, arguments=arguments)
        # Convert result content to serializable format
        content_parts = []
        for part in result.content:
            if hasattr(part, "text"):
                content_parts.append(part.text)
            elif hasattr(part, "data"):
                content_parts.append(part.data)
            else:
                content_parts.append(str(part))

        combined = "\n".join(content_parts) if len(content_parts) > 1 else (content_parts[0] if content_parts else "")
        # Try to parse as JSON
        try:
            return json.loads(combined)
        except (json.JSONDecodeError, TypeError):
            return combined


def _extract_tool_params(tool) -> list:
    """Extract parameter definitions from an MCP tool schema."""
    params = []
    schema = getattr(tool, "inputSchema", None) or {}
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    for name, prop in properties.items():
        param = {
            "name": name,
            "type": prop.get("type", "string"),
            "required": name in required,
            "description": prop.get("description", ""),
            "enum_options": prop.get("enum", []),
        }
        if "default" in prop:
            param["default"] = prop["default"]
        params.append(param)
    return params


# ── Public API ──

def get_running_server(name: str) -> Optional[MCPServerProcess]:
    return _running_servers.get(name)


async def start_server(server_config: dict) -> MCPServerProcess:
    """Start an MCP server process and register it."""
    name = server_config["name"]
    if name in _running_servers and _running_servers[name].is_connected:
        return _running_servers[name]
    proc = MCPServerProcess(server_config)
    await proc.start()
    _running_servers[name] = proc
    return proc


async def stop_server(name: str):
    """Stop a running MCP server process."""
    proc = _running_servers.pop(name, None)
    if proc:
        await proc.stop()


async def restart_server(server_config: dict) -> MCPServerProcess:
    """Restart an MCP server process."""
    await stop_server(server_config["name"])
    return await start_server(server_config)


def list_running_servers() -> list[str]:
    return [name for name, proc in _running_servers.items() if proc.is_connected]


# ── GitHub URL Parser ──

def parse_github_url(url: str) -> dict:
    """Parse a GitHub repo URL and detect the MCP package info."""
    url = url.strip().rstrip("/")

    # Patterns: 
    # https://github.com/org/repo
    # https://github.com/org/repo/tree/main/src/some-server
    match = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)(?:/tree/[^/]+/(.+))?",
        url,
    )
    if not match:
        raise ValueError("Invalid GitHub URL format")

    org, repo, subpath = match.group(1), match.group(2), match.group(3)

    result = {
        "github_url": url,
        "org": org,
        "repo": repo,
        "subpath": subpath or "",
    }

    # Try to infer package name and runtime
    # Common MCP server naming: @org/server-name or just package-name
    if subpath:
        # Subpath like src/github → likely an npm package
        parts = subpath.rstrip("/").split("/")
        server_name = parts[-1]
        result["name"] = server_name
        result["runtime"] = "node"
        # Convention for official MCP servers: @modelcontextprotocol/server-{name}
        if org == "modelcontextprotocol" and repo == "servers":
            result["npm_package"] = f"@modelcontextprotocol/server-{server_name}"
            result["command"] = "npx"
            result["args"] = ["-y", f"@modelcontextprotocol/server-{server_name}"]
        else:
            result["npm_package"] = f"@{org}/{server_name}"
            result["command"] = "npx"
            result["args"] = ["-y", f"@{org}/{server_name}"]
    else:
        result["name"] = repo.replace("mcp-server-", "").replace("-mcp-server", "").replace("-mcp", "")
        # Check if it looks like a Python or Node project
        if "python" in repo.lower() or "py" in repo.lower():
            result["runtime"] = "python"
            result["pip_package"] = repo
            result["command"] = "python"
            result["args"] = ["-m", repo.replace("-", "_")]
        else:
            result["runtime"] = "node"
            result["npm_package"] = repo
            result["command"] = "npx"
            result["args"] = ["-y", repo]

    return result


async def install_server_package(server_info: dict) -> dict:
    """Install an MCP server package. Returns install result."""
    runtime = server_info.get("runtime", "node")
    name = server_info["name"]

    if runtime == "node":
        package = server_info.get("npm_package", "").strip()
        if not package:
            # No package to install - skip installation
            logger.info(f"No npm_package specified for {name}, skipping installation")
            return {"status": "skipped", "package": "", "output": "No package specified"}
        logger.info(f"Installing npm package: {package}")
        proc = await asyncio.create_subprocess_exec(
            "npm", "install", "-g", package,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            error_msg = stderr.decode().strip() or stdout.decode().strip()
            raise RuntimeError(f"npm install failed: {error_msg}")
        return {"status": "installed", "package": package, "output": stdout.decode().strip()}

    elif runtime == "python":
        package = server_info.get("pip_package", "").strip()
        if not package:
            # No package to install - skip installation
            logger.info(f"No pip_package specified for {name}, skipping installation")
            return {"status": "skipped", "package": "", "output": "No package specified"}
        logger.info(f"Installing pip package: {package}")
        proc = await asyncio.create_subprocess_exec(
            "pip", "install", package,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            error_msg = stderr.decode().strip() or stdout.decode().strip()
            raise RuntimeError(f"pip install failed: {error_msg}")
        return {"status": "installed", "package": package, "output": stdout.decode().strip()}

    else:
        raise ValueError(f"Unsupported runtime: {runtime}")

"""MCP Server Process Manager — spawns, monitors, and proxies to child MCP servers."""
import asyncio
import os
import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from typing import Optional

import httpx
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
        session_cm = self._session_cm
        client_cm = self._client_cm
        self._session_cm = None
        self._client_cm = None

        async def _do_exit():
            try:
                if session_cm:
                    await session_cm.__aexit__(None, None, None)
            except Exception:
                pass
            try:
                if client_cm:
                    await client_cm.__aexit__(None, None, None)
            except Exception:
                pass

        try:
            await asyncio.wait_for(
                asyncio.shield(_do_exit()),
                timeout=5.0,
            )
        except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
            pass

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

async def _fetch_github_package_json(org: str, repo: str, subpath: str = "") -> dict | None:
    """Fetch package.json from a GitHub repo to get the real npm package name."""
    paths_to_try = []
    if subpath:
        # Only try the subpath — don't fall back to root for monorepos
        paths_to_try.append(f"https://raw.githubusercontent.com/{org}/{repo}/main/{subpath}/package.json")
        paths_to_try.append(f"https://raw.githubusercontent.com/{org}/{repo}/master/{subpath}/package.json")
    else:
        paths_to_try.append(f"https://raw.githubusercontent.com/{org}/{repo}/main/package.json")
        paths_to_try.append(f"https://raw.githubusercontent.com/{org}/{repo}/master/package.json")

    async with httpx.AsyncClient(timeout=10) as client:
        for url in paths_to_try:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                continue
    return None


async def _fetch_github_readme(org: str, repo: str, subpath: str = "") -> str | None:
    """Fetch README from a GitHub repo for credential hints."""
    paths_to_try = []
    if subpath:
        # For monorepos, ONLY try subpath README — root README has noise from other servers
        paths_to_try.append(f"https://raw.githubusercontent.com/{org}/{repo}/main/{subpath}/README.md")
        paths_to_try.append(f"https://raw.githubusercontent.com/{org}/{repo}/master/{subpath}/README.md")
    else:
        paths_to_try.append(f"https://raw.githubusercontent.com/{org}/{repo}/main/README.md")
        paths_to_try.append(f"https://raw.githubusercontent.com/{org}/{repo}/master/README.md")

    async with httpx.AsyncClient(timeout=10) as client:
        for url in paths_to_try:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.text
            except Exception:
                continue
    return None


def _extract_env_vars_from_readme(readme: str) -> list[dict]:
    """Scan README for environment variable references."""
    env_vars = []
    seen = set()
    # Match patterns like FIRECRAWL_API_KEY, GITHUB_TOKEN etc.
    for m in re.finditer(r'\b([A-Z][A-Z0-9_]{2,})\b', readme):
        key = m.group(1)
        # Filter out common non-env words and generic placeholders
        skip = {"README", "HTTP", "HTTPS", "JSON", "POST", "GET", "PUT", "DELETE",
                "HEAD", "OPTIONS", "PATCH", "MCP", "API", "URL", "MIT", "NPM",
                "CLI", "SSE", "TCP", "UDP", "SSH", "SSL", "TLS", "ENV", "NODE",
                "CORS", "REST", "HTML", "CSS", "TYPE", "TRUE", "FALSE", "NULL",
                "NOTE", "TODO", "FIXME", "WARNING", "ERROR", "DEBUG", "INFO",
                "IMPORTANT", "OPTIONAL", "REQUIRED", "DEFAULT", "EXAMPLE",
                "USAGE", "INSTALL", "CONFIG", "CONFIGURATION", "SETUP",
                "DOCKER", "COMPOSE", "PYTHON", "JAVASCRIPT", "TYPESCRIPT",
                "YOUR_API_KEY", "YOUR_API_KEY_HERE", "YOUR_TOKEN", "YOUR_SECRET",
                "KEY", "TOKEN", "SECRET", "CURSOR", "VSC", "IDE"}
        if key in skip or key in seen:
            continue
        # Must contain an underscore (real env vars almost always do)
        if "_" not in key:
            continue
        # Skip generic placeholders
        if key.startswith("YOUR_") or key.startswith("MY_") or key.startswith("EXAMPLE_"):
            continue
        seen.add(key)
        # Determine if likely required based on surrounding context
        context = readme[max(0, m.start()-150):m.end()+150].lower()
        required = "required" in context and "optional" not in context
        env_vars.append({
            "key": key,
            "label": key.replace("_", " ").title(),
            "required": required,
        })
    return env_vars


def parse_github_url(url: str) -> dict:
    """Parse a GitHub repo URL and detect the MCP package info (sync wrapper)."""
    url = url.strip().rstrip("/")

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

    if subpath:
        parts = subpath.rstrip("/").split("/")
        server_name = parts[-1]
        result["name"] = server_name
        result["runtime"] = "node"
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


async def enrich_from_github(server_info: dict) -> dict:
    """Enrich parsed server info by fetching package.json and README from GitHub."""
    org = server_info.get("org", "")
    repo = server_info.get("repo", "")
    subpath = server_info.get("subpath", "")

    if not org or not repo:
        return server_info

    # Fetch package.json to get the real npm package name
    pkg_found_at_subpath = False
    if subpath:
        # For monorepos — only try the subpath package.json, not root
        pkg = await _fetch_github_package_json(org, repo, subpath)
        if not pkg:
            pkg = None  # Don't fall back to root for monorepo subpaths
    else:
        # For standalone repos — fetch root package.json
        pkg = await _fetch_github_package_json(org, repo, "")

    if pkg and server_info.get("runtime") == "node":
        real_name = pkg.get("name", "")
        if real_name:
            server_info["npm_package"] = real_name
            server_info["command"] = "npx"
            server_info["args"] = ["-y", real_name]
            logger.info(f"Resolved npm package from package.json: {real_name}")
        if pkg.get("description"):
            server_info["description"] = pkg["description"]

    # Fetch README for env var hints
    readme = await _fetch_github_readme(org, repo, subpath)
    if readme:
        env_vars = _extract_env_vars_from_readme(readme)
        if env_vars:
            existing_keys = {cs["key"] for cs in server_info.get("credentials_schema", [])}
            for ev in env_vars:
                if ev["key"] not in existing_keys:
                    server_info.setdefault("credentials_schema", []).append(ev)

    return server_info


async def install_server_package(server_info: dict) -> dict:
    """Install an MCP server package. Falls back to GitHub install if registry fails."""
    runtime = server_info.get("runtime", "node")
    name = server_info["name"]

    if runtime == "node":
        package = server_info.get("npm_package", "").strip()
        if not package:
            logger.info(f"No npm_package specified for {name}, skipping installation")
            return {"status": "skipped", "package": "", "output": "No package specified"}

        # Try 1: Install from npm registry
        logger.info(f"Installing npm package: {package}")
        proc = await asyncio.create_subprocess_exec(
            "npm", "install", "-g", package,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            return {"status": "installed", "package": package, "output": stdout.decode().strip()}

        npm_error = stderr.decode().strip() or stdout.decode().strip()
        logger.warning(f"npm registry install failed for {package}: {npm_error}")

        # Try 2: Install directly from GitHub repo URL
        org = server_info.get("org", "")
        repo = server_info.get("repo", "")
        if org and repo:
            github_ref = f"github:{org}/{repo}"
            logger.info(f"Falling back to GitHub install: {github_ref}")
            proc2 = await asyncio.create_subprocess_exec(
                "npm", "install", "-g", github_ref,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout2, stderr2 = await proc2.communicate()

            if proc2.returncode == 0:
                # Update the server_info command to use the installed binary
                return {
                    "status": "installed",
                    "package": github_ref,
                    "output": stdout2.decode().strip(),
                    "install_method": "github",
                }

            github_error = stderr2.decode().strip() or stdout2.decode().strip()
            logger.warning(f"GitHub install also failed: {github_error}")

            # Combine error messages
            raise RuntimeError(
                f"npm registry install failed ({package}): {npm_error}\n\n"
                f"GitHub fallback also failed ({github_ref}): {github_error}"
            )

        raise RuntimeError(f"npm install failed: {npm_error}")

    elif runtime == "python":
        package = server_info.get("pip_package", "").strip()
        if not package:
            logger.info(f"No pip_package specified for {name}, skipping installation")
            return {"status": "skipped", "package": "", "output": "No package specified"}

        # Try 1: pip install from PyPI
        logger.info(f"Installing pip package: {package}")
        proc = await asyncio.create_subprocess_exec(
            "pip", "install", package,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            return {"status": "installed", "package": package, "output": stdout.decode().strip()}

        pip_error = stderr.decode().strip() or stdout.decode().strip()

        # Try 2: Install from GitHub
        org = server_info.get("org", "")
        repo = server_info.get("repo", "")
        if org and repo:
            github_url = f"git+https://github.com/{org}/{repo}.git"
            logger.info(f"Falling back to pip install from GitHub: {github_url}")
            proc2 = await asyncio.create_subprocess_exec(
                "pip", "install", github_url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout2, stderr2 = await proc2.communicate()
            if proc2.returncode == 0:
                return {"status": "installed", "package": github_url, "output": stdout2.decode().strip(), "install_method": "github"}

            github_error = stderr2.decode().strip() or stdout2.decode().strip()
            raise RuntimeError(
                f"pip install failed ({package}): {pip_error}\n\n"
                f"GitHub fallback also failed: {github_error}"
            )

        raise RuntimeError(f"pip install failed: {pip_error}")

    else:
        raise ValueError(f"Unsupported runtime: {runtime}")

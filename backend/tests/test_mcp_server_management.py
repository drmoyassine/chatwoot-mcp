"""
Test MCP Server Management Endpoints
Tests for: parse-github, add, credentials, start, stop, delete, and /api/apps
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

def get_unique_name():
    """Generate unique server name for test isolation"""
    return f"test-srv-{uuid.uuid4().hex[:8]}"


class TestMCPServerManagement:
    """MCP Server Management endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: login and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.created_servers = []
        
        # Login
        resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@mcphub.local",
            "password": "McpHub2026!"
        })
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        self.token = resp.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        yield
        
        # Cleanup: remove all test servers created
        for name in self.created_servers:
            try:
                self.session.post(f"{BASE_URL}/api/servers/{name}/stop")
                self.session.delete(f"{BASE_URL}/api/servers/{name}")
            except:
                pass
    
    def add_test_server(self, name, **kwargs):
        """Helper to add a server and track for cleanup"""
        defaults = {
            "name": name,
            "display_name": f"Test {name}",
            "runtime": "node",
            "command": "echo",
            "args": ["test"]
        }
        defaults.update(kwargs)
        resp = self.session.post(f"{BASE_URL}/api/servers/add", json=defaults, timeout=60)
        if resp.status_code == 200:
            self.created_servers.append(name)
        return resp
    
    # ── Parse GitHub URL Tests ──
    
    def test_parse_github_url_with_subpath(self):
        """Parse GitHub URL with subpath (official MCP servers format)"""
        resp = self.session.post(f"{BASE_URL}/api/servers/parse-github", json={
            "github_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/github"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "server_info" in data
        info = data["server_info"]
        assert info["name"] == "github"
        assert info["runtime"] == "node"
        assert info["npm_package"] == "@modelcontextprotocol/server-github"
        assert info["command"] == "npx"
        assert "-y" in info["args"]
        assert "@modelcontextprotocol/server-github" in info["args"]
    
    def test_parse_github_url_simple_repo(self):
        """Parse simple GitHub repo URL"""
        resp = self.session.post(f"{BASE_URL}/api/servers/parse-github", json={
            "github_url": "https://github.com/some-org/mcp-server-test"
        })
        assert resp.status_code == 200
        data = resp.json()
        info = data["server_info"]
        assert info["name"] == "test"
        assert info["npm_package"] == "mcp-server-test"
    
    def test_parse_github_url_invalid(self):
        """Invalid GitHub URL returns 400"""
        resp = self.session.post(f"{BASE_URL}/api/servers/parse-github", json={
            "github_url": "not-a-valid-url"
        })
        assert resp.status_code == 400
        assert "Invalid GitHub URL" in resp.json()["detail"]
    
    def test_parse_github_url_empty(self):
        """Empty GitHub URL returns 400"""
        resp = self.session.post(f"{BASE_URL}/api/servers/parse-github", json={
            "github_url": ""
        })
        assert resp.status_code == 400
    
    # ── Add Server Tests ──
    
    def test_add_server_success(self):
        """Add a new MCP server"""
        name = get_unique_name()
        resp = self.add_test_server(
            name,
            github_url="https://github.com/modelcontextprotocol/servers/tree/main/src/memory",
            display_name="Test GitHub Server",
            description="A test server for testing",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-memory"],
            npm_package="@modelcontextprotocol/server-memory",
            credentials_schema=[{"key": "TEST_TOKEN", "label": "Test Token", "required": True}]
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "installed"
        assert data["server"]["name"] == name
        assert data["server"]["configured"] == False
        assert data["server"]["enabled"] == True
    
    def test_add_server_duplicate(self):
        """Adding duplicate server returns 409"""
        name = get_unique_name()
        # First add
        self.add_test_server(name)
        
        # Second add should fail
        resp = self.session.post(f"{BASE_URL}/api/servers/add", json={
            "name": name,
            "display_name": "Test Duplicate",
            "runtime": "node",
            "command": "echo",
            "args": ["test"]
        })
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]
    
    def test_add_server_no_name(self):
        """Adding server without name returns 400"""
        resp = self.session.post(f"{BASE_URL}/api/servers/add", json={
            "display_name": "No Name Server",
            "runtime": "node",
            "command": "echo"
        })
        assert resp.status_code == 400
    
    # ── Get Server Tests ──
    
    def test_get_server_details(self):
        """Get server details"""
        name = get_unique_name()
        self.add_test_server(name, display_name="Test Server")
        
        resp = self.session.get(f"{BASE_URL}/api/servers/{name}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == name
        assert data["status"] == "stopped"
        assert data["has_credentials"] == False
    
    def test_get_server_not_found(self):
        """Get non-existent server returns 404"""
        resp = self.session.get(f"{BASE_URL}/api/servers/nonexistent-server-xyz")
        assert resp.status_code == 404
    
    # ── Credentials Tests ──
    
    def test_save_credentials(self):
        """Save encrypted credentials"""
        name = get_unique_name()
        self.add_test_server(name)
        
        # Save credentials
        resp = self.session.post(f"{BASE_URL}/api/servers/{name}/credentials", json={
            "credentials": {"API_KEY": "secret-key-12345", "OTHER_KEY": "other-value"}
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "saved"
        
        # Verify server is now configured
        srv_resp = self.session.get(f"{BASE_URL}/api/servers/{name}")
        assert srv_resp.json()["configured"] == True
        assert srv_resp.json()["has_credentials"] == True
    
    def test_get_credentials_masked(self):
        """Get credentials returns masked values"""
        name = get_unique_name()
        self.add_test_server(name)
        self.session.post(f"{BASE_URL}/api/servers/{name}/credentials", json={
            "credentials": {"API_KEY": "secret-key-12345"}
        })
        
        # Get credentials
        resp = self.session.get(f"{BASE_URL}/api/servers/{name}/credentials")
        assert resp.status_code == 200
        creds = resp.json()["credentials"]
        assert "API_KEY" in creds
        assert "***" in creds["API_KEY"]  # Should be masked
        assert "secret-key-12345" not in creds["API_KEY"]  # Full value not exposed
    
    def test_save_credentials_server_not_found(self):
        """Save credentials for non-existent server returns 404"""
        resp = self.session.post(f"{BASE_URL}/api/servers/nonexistent-xyz/credentials", json={
            "credentials": {"KEY": "value"}
        })
        assert resp.status_code == 404
    
    # ── Start/Stop Tests ──
    
    def test_start_server(self):
        """Start an MCP server"""
        name = get_unique_name()
        self.add_test_server(
            name,
            display_name="Test Memory",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-memory"],
            npm_package="@modelcontextprotocol/server-memory"
        )
        
        # Start
        resp = self.session.post(f"{BASE_URL}/api/servers/{name}/start", timeout=30)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "started"
        assert data["tools_count"] > 0
        assert "tools" in data
    
    def test_stop_server(self):
        """Stop a running MCP server"""
        name = get_unique_name()
        self.add_test_server(
            name,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-memory"]
        )
        self.session.post(f"{BASE_URL}/api/servers/{name}/start", timeout=30)
        
        # Stop
        resp = self.session.post(f"{BASE_URL}/api/servers/{name}/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "stopped"
        
        # Verify status via GET
        srv_resp = self.session.get(f"{BASE_URL}/api/servers/{name}")
        assert srv_resp.status_code == 200
        assert srv_resp.json()["status"] == "stopped"
    
    def test_start_server_not_found(self):
        """Start non-existent server returns 404"""
        resp = self.session.post(f"{BASE_URL}/api/servers/nonexistent-xyz/start")
        assert resp.status_code == 404
    
    # ── Delete Tests ──
    
    def test_delete_server(self):
        """Delete an MCP server"""
        name = get_unique_name()
        self.add_test_server(name)
        
        # Delete
        resp = self.session.delete(f"{BASE_URL}/api/servers/{name}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "removed"
        
        # Remove from cleanup list since already deleted
        self.created_servers.remove(name)
        
        # Verify gone
        get_resp = self.session.get(f"{BASE_URL}/api/servers/{name}")
        assert get_resp.status_code == 404
    
    # ── Apps List Tests ──
    
    def test_apps_list_includes_builtin(self):
        """GET /api/apps includes Chatwoot as builtin"""
        resp = self.session.get(f"{BASE_URL}/api/apps")
        assert resp.status_code == 200
        apps = resp.json()["apps"]
        chatwoot = next((a for a in apps if a["name"] == "chatwoot"), None)
        assert chatwoot is not None
        assert chatwoot["type"] == "builtin"
        assert chatwoot["tools_count"] > 0
    
    def test_apps_list_includes_dynamic(self):
        """GET /api/apps includes dynamic servers"""
        name = get_unique_name()
        self.add_test_server(
            name,
            display_name="Test Dynamic",
            description="A dynamic test server"
        )
        
        resp = self.session.get(f"{BASE_URL}/api/apps")
        assert resp.status_code == 200
        apps = resp.json()["apps"]
        
        dynamic = next((a for a in apps if a["name"] == name), None)
        assert dynamic is not None
        assert dynamic["type"] == "dynamic"
        assert dynamic["runtime"] == "node"
        assert dynamic["status"] == "stopped"
        assert dynamic["configured"] == False
    
    def test_apps_list_dynamic_status_running(self):
        """Dynamic server shows 'connected' status when running"""
        name = get_unique_name()
        self.add_test_server(
            name,
            display_name="Test Running",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-memory"]
        )
        self.session.post(f"{BASE_URL}/api/servers/{name}/start", timeout=30)
        
        resp = self.session.get(f"{BASE_URL}/api/apps")
        apps = resp.json()["apps"]
        dynamic = next((a for a in apps if a["name"] == name), None)
        assert dynamic is not None
        assert dynamic["status"] == "connected"
        assert dynamic["tools_count"] > 0


class TestMCPServerManagementAuth:
    """Test auth requirements for MCP server endpoints"""
    
    def test_parse_github_requires_auth(self):
        """parse-github requires authentication"""
        resp = requests.post(f"{BASE_URL}/api/servers/parse-github", json={
            "github_url": "https://github.com/test/repo"
        })
        assert resp.status_code == 401
    
    def test_add_server_requires_auth(self):
        """add server requires authentication"""
        resp = requests.post(f"{BASE_URL}/api/servers/add", json={
            "name": "test",
            "runtime": "node",
            "command": "echo"
        })
        assert resp.status_code == 401
    
    def test_apps_requires_auth(self):
        """GET /api/apps requires authentication"""
        resp = requests.get(f"{BASE_URL}/api/apps")
        assert resp.status_code == 401

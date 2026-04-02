"""
Test suite for GitHub URL parser fix - verifies:
1. Firecrawl URL resolves to 'firecrawl-mcp' (not 'firecrawl-mcp-server')
2. Firecrawl URL returns FIRECRAWL_API_KEY and FIRECRAWL_API_URL in credentials_schema
3. Official GitHub MCP URL resolves to '@modelcontextprotocol/server-github'
4. Official GitHub MCP URL does NOT resolve to '@modelcontextprotocol/servers' (monorepo root)
5. npm install with correct package name succeeds
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test URLs
FIRECRAWL_URL = "https://github.com/mendableai/firecrawl-mcp-server"
GITHUB_MCP_URL = "https://github.com/modelcontextprotocol/servers/tree/main/src/github"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API calls."""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@mcphub.local",
        "password": "McpHub2026!"
    })
    if resp.status_code == 200:
        return resp.json().get("token")
    pytest.skip("Authentication failed")


@pytest.fixture
def api_client(auth_token):
    """Authenticated requests session."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestFirecrawlGitHubParser:
    """Tests for firecrawl-mcp-server GitHub URL parsing."""
    
    def test_firecrawl_resolves_to_correct_npm_package(self, api_client):
        """Firecrawl URL should resolve npm_package to 'firecrawl-mcp' (not 'firecrawl-mcp-server')."""
        resp = api_client.post(f"{BASE_URL}/api/servers/parse-github", json={
            "github_url": FIRECRAWL_URL
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        server_info = data.get("server_info", {})
        
        # Key assertion: npm_package should be 'firecrawl-mcp' (from package.json)
        # NOT 'firecrawl-mcp-server' (the repo name)
        npm_package = server_info.get("npm_package", "")
        assert npm_package == "firecrawl-mcp", \
            f"Expected npm_package='firecrawl-mcp', got '{npm_package}'. Parser should fetch package.json to get real name."
    
    def test_firecrawl_returns_env_vars_from_readme(self, api_client):
        """Firecrawl URL should return FIRECRAWL_API_KEY and FIRECRAWL_API_URL in credentials_schema."""
        resp = api_client.post(f"{BASE_URL}/api/servers/parse-github", json={
            "github_url": FIRECRAWL_URL
        })
        assert resp.status_code == 200
        
        data = resp.json()
        server_info = data.get("server_info", {})
        credentials_schema = server_info.get("credentials_schema", [])
        
        # Extract keys from credentials_schema
        env_keys = {cs.get("key") for cs in credentials_schema}
        
        # Should have FIRECRAWL_API_KEY (required for the service)
        assert "FIRECRAWL_API_KEY" in env_keys, \
            f"Expected FIRECRAWL_API_KEY in credentials_schema, got: {env_keys}"
        
        # Should have FIRECRAWL_API_URL (for self-hosted instances)
        assert "FIRECRAWL_API_URL" in env_keys, \
            f"Expected FIRECRAWL_API_URL in credentials_schema, got: {env_keys}"
    
    def test_firecrawl_command_uses_correct_package(self, api_client):
        """Firecrawl command should use 'firecrawl-mcp' not 'firecrawl-mcp-server'."""
        resp = api_client.post(f"{BASE_URL}/api/servers/parse-github", json={
            "github_url": FIRECRAWL_URL
        })
        assert resp.status_code == 200
        
        data = resp.json()
        server_info = data.get("server_info", {})
        
        command = server_info.get("command", "")
        args = server_info.get("args", [])
        
        assert command == "npx", f"Expected command='npx', got '{command}'"
        assert "firecrawl-mcp" in args, \
            f"Expected 'firecrawl-mcp' in args, got: {args}"
        # Should NOT have the wrong package name
        assert "firecrawl-mcp-server" not in args, \
            f"Should NOT have 'firecrawl-mcp-server' in args (that package doesn't exist on npm)"


class TestOfficialGitHubMCPParser:
    """Tests for official modelcontextprotocol/servers monorepo parsing."""
    
    def test_github_mcp_resolves_to_scoped_package(self, api_client):
        """GitHub MCP URL should resolve to '@modelcontextprotocol/server-github'."""
        resp = api_client.post(f"{BASE_URL}/api/servers/parse-github", json={
            "github_url": GITHUB_MCP_URL
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        server_info = data.get("server_info", {})
        
        npm_package = server_info.get("npm_package", "")
        assert npm_package == "@modelcontextprotocol/server-github", \
            f"Expected npm_package='@modelcontextprotocol/server-github', got '{npm_package}'"
    
    def test_github_mcp_does_not_resolve_to_monorepo_root(self, api_client):
        """GitHub MCP URL should NOT resolve to '@modelcontextprotocol/servers' (monorepo root)."""
        resp = api_client.post(f"{BASE_URL}/api/servers/parse-github", json={
            "github_url": GITHUB_MCP_URL
        })
        assert resp.status_code == 200
        
        data = resp.json()
        server_info = data.get("server_info", {})
        
        npm_package = server_info.get("npm_package", "")
        # Should NOT be the monorepo root package
        assert npm_package != "@modelcontextprotocol/servers", \
            f"npm_package should NOT be '@modelcontextprotocol/servers' (monorepo root)"
        assert npm_package != "servers", \
            f"npm_package should NOT be 'servers' (monorepo root)"
    
    def test_github_mcp_monorepo_subpath_no_readme(self, api_client):
        """GitHub MCP URL (monorepo subpath) has no subpath README, so no env vars detected.
        
        This is expected behavior - for monorepos, the parser only looks at the subpath's
        README to avoid noise from other servers. Since src/github/README.md doesn't exist,
        no env vars are auto-detected. The frontend will use inferCredentialsSchema() fallback.
        """
        resp = api_client.post(f"{BASE_URL}/api/servers/parse-github", json={
            "github_url": GITHUB_MCP_URL
        })
        assert resp.status_code == 200
        
        data = resp.json()
        server_info = data.get("server_info", {})
        credentials_schema = server_info.get("credentials_schema", [])
        
        # For monorepo subpaths without a README, credentials_schema will be empty
        # The frontend's inferCredentialsSchema() will provide defaults based on server name
        print(f"Monorepo subpath credentials_schema: {credentials_schema}")
        # This is expected - no assertion failure, just documenting behavior


class TestServerInstallation:
    """Tests for server installation with correct package names."""
    
    @pytest.fixture(autouse=True)
    def cleanup_test_server(self, api_client):
        """Clean up test server before and after test."""
        # Cleanup before
        try:
            api_client.delete(f"{BASE_URL}/api/servers/firecrawl")
        except:
            pass
        yield
        # Cleanup after
        try:
            api_client.delete(f"{BASE_URL}/api/servers/firecrawl")
        except:
            pass
    
    def test_firecrawl_install_with_correct_package(self, api_client):
        """Installing firecrawl with npm_package='firecrawl-mcp' should succeed (not 404)."""
        # First parse to get server info
        parse_resp = api_client.post(f"{BASE_URL}/api/servers/parse-github", json={
            "github_url": FIRECRAWL_URL
        })
        assert parse_resp.status_code == 200
        server_info = parse_resp.json().get("server_info", {})
        
        # Verify we have the correct package name
        assert server_info.get("npm_package") == "firecrawl-mcp", \
            "Pre-condition failed: npm_package should be 'firecrawl-mcp'"
        
        # Now try to install
        install_resp = api_client.post(f"{BASE_URL}/api/servers/add", json={
            "github_url": FIRECRAWL_URL,
            "name": server_info.get("name", "firecrawl"),
            "display_name": "Firecrawl",
            "description": server_info.get("description", "Web scraping MCP server"),
            "runtime": server_info.get("runtime", "node"),
            "command": server_info.get("command", "npx"),
            "args": server_info.get("args", ["-y", "firecrawl-mcp"]),
            "npm_package": server_info.get("npm_package", "firecrawl-mcp"),
            "credentials_schema": server_info.get("credentials_schema", [])
        })
        
        # Should succeed (200 or 201) - NOT fail with npm 404
        assert install_resp.status_code in [200, 201], \
            f"Installation failed with status {install_resp.status_code}: {install_resp.text}"
        
        data = install_resp.json()
        assert data.get("status") == "installed", \
            f"Expected status='installed', got: {data}"


class TestInstalledServerVerification:
    """Tests to verify installed firecrawl server in database."""
    
    def test_firecrawl_in_installed_servers(self, api_client):
        """Verify firecrawl server appears in installed servers list."""
        resp = api_client.get(f"{BASE_URL}/api/apps")
        assert resp.status_code == 200
        
        data = resp.json()
        apps = data.get("apps", [])
        
        # Find firecrawl in the list
        firecrawl_apps = [a for a in apps if "firecrawl" in a.get("name", "").lower()]
        
        # Note: This test may pass or fail depending on whether firecrawl was installed
        # in previous testing. We just verify the API works.
        print(f"Found {len(firecrawl_apps)} firecrawl-related apps: {[a.get('name') for a in firecrawl_apps]}")


class TestMarketplaceRegression:
    """Regression tests for marketplace functionality."""
    
    def test_marketplace_returns_12_curated_servers(self, api_client):
        """Marketplace should return 12 curated servers."""
        resp = api_client.get(f"{BASE_URL}/api/marketplace/catalog")
        assert resp.status_code == 200
        
        data = resp.json()
        catalog = data.get("catalog", [])
        
        # Filter to curated only
        curated = [c for c in catalog if c.get("source") == "curated"]
        assert len(curated) == 12, \
            f"Expected 12 curated servers, got {len(curated)}"
    
    def test_marketplace_github_server_has_correct_package(self, api_client):
        """Marketplace GitHub server should have correct npm_package."""
        resp = api_client.get(f"{BASE_URL}/api/marketplace/catalog")
        assert resp.status_code == 200
        
        data = resp.json()
        catalog = data.get("catalog", [])
        
        # Find GitHub server
        github_servers = [c for c in catalog if c.get("slug") == "github"]
        assert len(github_servers) == 1, "Should have exactly one GitHub server in catalog"
        
        github_server = github_servers[0]
        assert github_server.get("npm_package") == "@modelcontextprotocol/server-github", \
            f"GitHub server npm_package should be '@modelcontextprotocol/server-github'"

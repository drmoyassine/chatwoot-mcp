"""
Backend tests for MCP Hub Authentication and API Key Management
Tests: Login, JWT auth, API key CRUD, protected routes, chatwoot endpoints with auth
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Admin credentials from env
ADMIN_EMAIL = "admin@mcphub.local"
ADMIN_PASSWORD = "McpHub2026!"


class TestAuthEndpoints:
    """Authentication endpoint tests - /api/auth/*"""
    
    def test_login_success(self):
        """Test successful login returns token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "token" in data, "Response should contain token"
        assert "email" in data, "Response should contain email"
        assert data["email"] == ADMIN_EMAIL.lower()
        assert len(data["token"]) > 0, "Token should not be empty"
        print(f"SUCCESS: Login returned token for {data['email']}")
    
    def test_login_invalid_credentials(self):
        """Test login with wrong credentials returns 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data
        print(f"SUCCESS: Invalid credentials returned 401 with detail: {data['detail']}")
    
    def test_login_wrong_password(self):
        """Test login with correct email but wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("SUCCESS: Wrong password returns 401")
    
    def test_get_me_without_token(self):
        """Test /api/auth/me without token returns 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        print("SUCCESS: /api/auth/me without token returns 401")
    
    def test_get_me_with_valid_token(self):
        """Test /api/auth/me with valid token returns user info"""
        # First login
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_resp.json()["token"]
        
        # Then get me
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert data["email"] == ADMIN_EMAIL.lower()
        print(f"SUCCESS: /api/auth/me returned email: {data['email']}")
    
    def test_logout(self):
        """Test logout endpoint"""
        # Login first
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_resp.json()["token"]
        
        # Logout
        response = requests.post(
            f"{BASE_URL}/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "logged_out"
        print("SUCCESS: Logout returned status: logged_out")


class TestAppsEndpoints:
    """Apps endpoint tests - /api/apps/*"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_apps_without_auth(self):
        """Test /api/apps without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/apps")
        assert response.status_code == 401
        print("SUCCESS: /api/apps without auth returns 401")
    
    def test_list_apps_with_auth(self):
        """Test /api/apps with auth returns apps list"""
        response = requests.get(f"{BASE_URL}/api/apps", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "apps" in data
        assert isinstance(data["apps"], list)
        assert len(data["apps"]) > 0, "Should have at least one app (chatwoot)"
        
        # Check chatwoot app structure
        chatwoot = next((a for a in data["apps"] if a["name"] == "chatwoot"), None)
        assert chatwoot is not None, "Chatwoot app should be in list"
        assert "display_name" in chatwoot
        assert "tools_count" in chatwoot
        assert "active_keys" in chatwoot
        assert "mcp_endpoint" in chatwoot
        assert chatwoot["mcp_endpoint"] == "/api/chatwoot/mcp/sse"
        print(f"SUCCESS: Listed {len(data['apps'])} apps, chatwoot has {chatwoot['tools_count']} tools")


class TestApiKeyManagement:
    """API Key CRUD tests - /api/apps/{app_name}/keys"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.created_key_ids = []
    
    def teardown_method(self):
        """Cleanup created keys"""
        for key_id in self.created_key_ids:
            try:
                requests.delete(
                    f"{BASE_URL}/api/apps/chatwoot/keys/{key_id}",
                    headers=self.headers
                )
            except:
                pass
    
    def test_create_api_key(self):
        """Test creating a new API key"""
        response = requests.post(
            f"{BASE_URL}/api/apps/chatwoot/keys",
            headers=self.headers,
            json={"label": "TEST_pytest_key"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "key_id" in data
        assert "key" in data
        assert "label" in data
        assert data["label"] == "TEST_pytest_key"
        assert data["key"].startswith("mcp_"), "Key should start with mcp_"
        
        self.created_key_ids.append(data["key_id"])
        print(f"SUCCESS: Created API key with id: {data['key_id']}, key preview: {data['key'][:12]}...")
        return data
    
    def test_list_api_keys(self):
        """Test listing API keys (values should be masked)"""
        # Create a key first
        create_resp = requests.post(
            f"{BASE_URL}/api/apps/chatwoot/keys",
            headers=self.headers,
            json={"label": "TEST_list_key"}
        )
        key_id = create_resp.json()["key_id"]
        self.created_key_ids.append(key_id)
        
        # List keys
        response = requests.get(
            f"{BASE_URL}/api/apps/chatwoot/keys",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "keys" in data
        assert isinstance(data["keys"], list)
        
        # Find our key
        our_key = next((k for k in data["keys"] if k["key_id"] == key_id), None)
        assert our_key is not None, "Created key should be in list"
        assert "key_preview" in our_key, "Key should have preview"
        assert "key" not in our_key, "Full key should NOT be in list response"
        assert "..." in our_key["key_preview"], "Key preview should be masked"
        print(f"SUCCESS: Listed {len(data['keys'])} keys, key preview: {our_key['key_preview']}")
    
    def test_revoke_api_key(self):
        """Test revoking an API key"""
        # Create a key first
        create_resp = requests.post(
            f"{BASE_URL}/api/apps/chatwoot/keys",
            headers=self.headers,
            json={"label": "TEST_revoke_key"}
        )
        key_id = create_resp.json()["key_id"]
        
        # Revoke it
        response = requests.delete(
            f"{BASE_URL}/api/apps/chatwoot/keys/{key_id}",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "revoked"
        assert data.get("key_id") == key_id
        print(f"SUCCESS: Revoked key {key_id}")
        
        # Verify it's marked as inactive
        list_resp = requests.get(
            f"{BASE_URL}/api/apps/chatwoot/keys",
            headers=self.headers
        )
        keys = list_resp.json()["keys"]
        revoked_key = next((k for k in keys if k["key_id"] == key_id), None)
        assert revoked_key is not None
        assert revoked_key["is_active"] == False
        print("SUCCESS: Verified key is marked as inactive")
    
    def test_revoke_nonexistent_key(self):
        """Test revoking a non-existent key returns 404"""
        response = requests.delete(
            f"{BASE_URL}/api/apps/chatwoot/keys/nonexistent_key_id",
            headers=self.headers
        )
        assert response.status_code == 404
        print("SUCCESS: Revoking non-existent key returns 404")


class TestChatwootEndpointsAuth:
    """Chatwoot endpoint auth tests - /api/chatwoot/*"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and create API key for tests"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Create an API key for testing
        key_resp = requests.post(
            f"{BASE_URL}/api/apps/chatwoot/keys",
            headers=self.headers,
            json={"label": "TEST_chatwoot_auth"}
        )
        self.api_key = key_resp.json()["key"]
        self.api_key_id = key_resp.json()["key_id"]
    
    def teardown_method(self):
        """Cleanup API key"""
        try:
            requests.delete(
                f"{BASE_URL}/api/apps/chatwoot/keys/{self.api_key_id}",
                headers=self.headers
            )
        except:
            pass
    
    def test_chatwoot_tools_without_auth(self):
        """Test /api/chatwoot/tools without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/chatwoot/tools")
        assert response.status_code == 401
        print("SUCCESS: /api/chatwoot/tools without auth returns 401")
    
    def test_chatwoot_tools_with_jwt(self):
        """Test /api/chatwoot/tools with JWT token"""
        response = requests.get(
            f"{BASE_URL}/api/chatwoot/tools",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "tools" in data
        assert len(data["tools"]) > 0
        print(f"SUCCESS: /api/chatwoot/tools with JWT returned {len(data['tools'])} tools")
    
    def test_chatwoot_tools_with_api_key_header(self):
        """Test /api/chatwoot/tools with X-API-Key header"""
        response = requests.get(
            f"{BASE_URL}/api/chatwoot/tools",
            headers={"X-API-Key": self.api_key}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "tools" in data
        print(f"SUCCESS: /api/chatwoot/tools with X-API-Key returned {len(data['tools'])} tools")
    
    def test_chatwoot_tools_with_bearer_api_key(self):
        """Test /api/chatwoot/tools with Bearer API key"""
        response = requests.get(
            f"{BASE_URL}/api/chatwoot/tools",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "tools" in data
        print(f"SUCCESS: /api/chatwoot/tools with Bearer API key returned {len(data['tools'])} tools")
    
    def test_chatwoot_tools_with_invalid_api_key(self):
        """Test /api/chatwoot/tools with invalid API key returns 401"""
        response = requests.get(
            f"{BASE_URL}/api/chatwoot/tools",
            headers={"X-API-Key": "invalid_key_12345"}
        )
        assert response.status_code == 401
        print("SUCCESS: Invalid API key returns 401")
    
    def test_chatwoot_config_with_jwt(self):
        """Test /api/chatwoot/config with JWT"""
        response = requests.get(
            f"{BASE_URL}/api/chatwoot/config",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "chatwoot_url" in data
        assert "api_token_set" in data
        print(f"SUCCESS: /api/chatwoot/config returned url: {data['chatwoot_url']}")
    
    def test_chatwoot_mcp_info_with_api_key(self):
        """Test /api/chatwoot/mcp/info with API key"""
        response = requests.get(
            f"{BASE_URL}/api/chatwoot/mcp/info",
            headers={"X-API-Key": self.api_key}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "server_name" in data
        assert "transport" in data
        assert data["transport"]["sse"]["endpoint"] == "/api/chatwoot/mcp/sse"
        print(f"SUCCESS: MCP info returned server: {data['server_name']}")


class TestWebhookEndpoint:
    """Webhook endpoint tests - no auth required for receive"""
    
    def test_webhook_receive_no_auth(self):
        """Test /api/chatwoot/webhooks/receive accepts events without auth"""
        response = requests.post(
            f"{BASE_URL}/api/chatwoot/webhooks/receive",
            json={"event": "test_event", "data": {"test": True}}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "received"
        print("SUCCESS: Webhook receive accepts events without auth")
    
    def test_webhook_history_requires_auth(self):
        """Test /api/chatwoot/webhooks/events/history requires auth"""
        response = requests.get(f"{BASE_URL}/api/chatwoot/webhooks/events/history")
        assert response.status_code == 401
        print("SUCCESS: Webhook history requires auth")


class TestProtectedRouteRedirects:
    """Test that protected routes require authentication"""
    
    def test_apps_endpoint_requires_auth(self):
        """Test /api/apps requires auth"""
        response = requests.get(f"{BASE_URL}/api/apps")
        assert response.status_code == 401
        print("SUCCESS: /api/apps requires auth")
    
    def test_api_keys_endpoint_requires_auth(self):
        """Test /api/apps/chatwoot/keys requires auth"""
        response = requests.get(f"{BASE_URL}/api/apps/chatwoot/keys")
        assert response.status_code == 401
        print("SUCCESS: /api/apps/chatwoot/keys requires auth")
    
    def test_chatwoot_config_requires_auth(self):
        """Test /api/chatwoot/config requires auth"""
        response = requests.get(f"{BASE_URL}/api/chatwoot/config")
        assert response.status_code == 401
        print("SUCCESS: /api/chatwoot/config requires auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

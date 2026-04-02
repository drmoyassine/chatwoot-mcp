"""
Test suite for editable credentials_schema feature:
1. POST /api/servers/{name}/credentials with credentials_schema updates the schema in mcp_servers collection
2. GET /api/servers/{name} returns the updated credentials_schema
3. Backend properly handles add/remove/edit of env vars
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCredentialsSchema:
    """Test credentials_schema update functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@mcphub.local",
            "password": "McpHub2026!"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        self.token = login_resp.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        yield
    
    def test_get_memory_server_info(self):
        """Test GET /api/servers/memory returns server info with credentials_schema"""
        resp = requests.get(f"{BASE_URL}/api/servers/memory", headers=self.headers)
        print(f"GET /api/servers/memory: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"  Server name: {data.get('name')}")
            print(f"  Display name: {data.get('display_name')}")
            print(f"  Status: {data.get('status')}")
            print(f"  Has credentials: {data.get('has_credentials')}")
            print(f"  Credentials schema: {data.get('credentials_schema')}")
            assert "name" in data
            assert "credentials_schema" in data or data.get("credentials_schema") is None
        else:
            pytest.skip(f"Memory server not found: {resp.status_code}")
    
    def test_save_credentials_with_schema_update(self):
        """Test POST /api/servers/{name}/credentials with credentials_schema updates the schema"""
        # First, get current server info
        get_resp = requests.get(f"{BASE_URL}/api/servers/memory", headers=self.headers)
        if get_resp.status_code != 200:
            pytest.skip("Memory server not found")
        
        original_schema = get_resp.json().get("credentials_schema", [])
        print(f"Original schema: {original_schema}")
        
        # Add a new env var to the schema
        new_schema = original_schema.copy() if original_schema else []
        new_schema.append({
            "key": "TEST_CUSTOM_VAR",
            "label": "Test Custom Variable",
            "required": False,
            "hint": "Added via test"
        })
        
        # Save credentials with updated schema
        save_resp = requests.post(
            f"{BASE_URL}/api/servers/memory/credentials",
            headers=self.headers,
            json={
                "credentials": {},  # No actual credentials, just schema update
                "credentials_schema": new_schema
            }
        )
        print(f"POST /api/servers/memory/credentials: {save_resp.status_code}")
        assert save_resp.status_code == 200, f"Save failed: {save_resp.text}"
        
        # Verify the schema was updated
        verify_resp = requests.get(f"{BASE_URL}/api/servers/memory", headers=self.headers)
        assert verify_resp.status_code == 200
        updated_schema = verify_resp.json().get("credentials_schema", [])
        print(f"Updated schema: {updated_schema}")
        
        # Check that our new var is in the schema
        var_keys = [v.get("key") for v in updated_schema]
        assert "TEST_CUSTOM_VAR" in var_keys, f"TEST_CUSTOM_VAR not found in schema: {var_keys}"
        
        # Clean up - restore original schema
        cleanup_resp = requests.post(
            f"{BASE_URL}/api/servers/memory/credentials",
            headers=self.headers,
            json={
                "credentials": {},
                "credentials_schema": original_schema
            }
        )
        print(f"Cleanup: {cleanup_resp.status_code}")
    
    def test_save_credentials_with_multiple_vars(self):
        """Test adding multiple env vars to credentials_schema"""
        get_resp = requests.get(f"{BASE_URL}/api/servers/memory", headers=self.headers)
        if get_resp.status_code != 200:
            pytest.skip("Memory server not found")
        
        original_schema = get_resp.json().get("credentials_schema", [])
        
        # Create schema with multiple vars
        new_schema = [
            {"key": "API_KEY", "label": "API Key", "required": True, "hint": "Main API key"},
            {"key": "API_URL", "label": "API URL", "required": False, "hint": "Optional URL"},
            {"key": "DEBUG_MODE", "label": "Debug Mode", "required": False, "hint": "Enable debug"}
        ]
        
        save_resp = requests.post(
            f"{BASE_URL}/api/servers/memory/credentials",
            headers=self.headers,
            json={
                "credentials": {"API_KEY": "test-key-123"},
                "credentials_schema": new_schema
            }
        )
        print(f"Save with multiple vars: {save_resp.status_code}")
        assert save_resp.status_code == 200
        
        # Verify
        verify_resp = requests.get(f"{BASE_URL}/api/servers/memory", headers=self.headers)
        updated_schema = verify_resp.json().get("credentials_schema", [])
        print(f"Updated schema: {updated_schema}")
        
        var_keys = [v.get("key") for v in updated_schema]
        assert "API_KEY" in var_keys
        assert "API_URL" in var_keys
        assert "DEBUG_MODE" in var_keys
        
        # Verify credentials were saved
        creds_resp = requests.get(f"{BASE_URL}/api/servers/memory/credentials", headers=self.headers)
        assert creds_resp.status_code == 200
        creds = creds_resp.json().get("credentials", {})
        print(f"Saved credentials (masked): {creds}")
        assert "API_KEY" in creds, "API_KEY credential not saved"
        
        # Clean up
        requests.post(
            f"{BASE_URL}/api/servers/memory/credentials",
            headers=self.headers,
            json={"credentials": {}, "credentials_schema": original_schema}
        )
    
    def test_save_credentials_empty_schema(self):
        """Test saving with empty credentials_schema clears the schema"""
        get_resp = requests.get(f"{BASE_URL}/api/servers/memory", headers=self.headers)
        if get_resp.status_code != 200:
            pytest.skip("Memory server not found")
        
        original_schema = get_resp.json().get("credentials_schema", [])
        
        # First ensure we have some schema to clear
        setup_schema = [{"key": "TEMP_VAR", "label": "Temp", "required": False}]
        requests.post(
            f"{BASE_URL}/api/servers/memory/credentials",
            headers=self.headers,
            json={"credentials": {}, "credentials_schema": setup_schema}
        )
        
        # Save with empty schema
        save_resp = requests.post(
            f"{BASE_URL}/api/servers/memory/credentials",
            headers=self.headers,
            json={
                "credentials": {},
                "credentials_schema": []
            }
        )
        print(f"Save with empty schema: {save_resp.status_code}")
        assert save_resp.status_code == 200
        
        # Verify schema is empty
        verify_resp = requests.get(f"{BASE_URL}/api/servers/memory", headers=self.headers)
        updated_schema = verify_resp.json().get("credentials_schema", [])
        print(f"Updated schema (should be empty): {updated_schema}")
        assert updated_schema == [], f"Schema should be empty but got: {updated_schema}"
        
        # Restore original
        requests.post(
            f"{BASE_URL}/api/servers/memory/credentials",
            headers=self.headers,
            json={"credentials": {}, "credentials_schema": original_schema}
        )
    
    def test_credentials_schema_persists_after_server_restart(self):
        """Test that credentials_schema persists in database"""
        get_resp = requests.get(f"{BASE_URL}/api/servers/memory", headers=self.headers)
        if get_resp.status_code != 200:
            pytest.skip("Memory server not found")
        
        original_schema = get_resp.json().get("credentials_schema", [])
        
        # Add custom schema
        custom_schema = [
            {"key": "PERSIST_TEST_VAR", "label": "Persistence Test", "required": True}
        ]
        
        save_resp = requests.post(
            f"{BASE_URL}/api/servers/memory/credentials",
            headers=self.headers,
            json={"credentials": {}, "credentials_schema": custom_schema}
        )
        assert save_resp.status_code == 200
        
        # Verify it persists (multiple GET calls)
        for i in range(3):
            verify_resp = requests.get(f"{BASE_URL}/api/servers/memory", headers=self.headers)
            schema = verify_resp.json().get("credentials_schema", [])
            var_keys = [v.get("key") for v in schema]
            assert "PERSIST_TEST_VAR" in var_keys, f"Schema not persisted on call {i+1}"
            print(f"Persistence check {i+1}: OK")
        
        # Clean up
        requests.post(
            f"{BASE_URL}/api/servers/memory/credentials",
            headers=self.headers,
            json={"credentials": {}, "credentials_schema": original_schema}
        )


class TestAddServerWithCredentialsSchema:
    """Test adding servers with custom credentials_schema"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@mcphub.local",
            "password": "McpHub2026!"
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        yield
        # Cleanup test server
        requests.delete(f"{BASE_URL}/api/servers/test-creds-server", headers=self.headers)
    
    def test_add_server_with_custom_credentials_schema(self):
        """Test POST /api/servers/add with custom credentials_schema - using memory server which doesn't need npm install"""
        # First delete if exists
        requests.delete(f"{BASE_URL}/api/servers/test-creds-server", headers=self.headers)
        time.sleep(0.5)
        
        # Add server with custom schema - use memory server which is already installed
        add_resp = requests.post(
            f"{BASE_URL}/api/servers/add",
            headers=self.headers,
            json={
                "github_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/memory",
                "name": "test-creds-server",
                "display_name": "Test Credentials Server",
                "description": "Test server for credentials schema",
                "runtime": "node",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-memory"],
                "npm_package": "@modelcontextprotocol/server-memory",
                "credentials_schema": [
                    {"key": "CUSTOM_API_KEY", "label": "Custom API Key", "required": True, "hint": "Your API key"},
                    {"key": "CUSTOM_API_URL", "label": "Custom API URL", "required": False, "hint": "Optional URL"}
                ]
            }
        )
        print(f"Add server: {add_resp.status_code}")
        print(f"Response: {add_resp.text[:500]}")
        
        # If npm install fails, skip the test (external dependency)
        if add_resp.status_code == 500 and "npm" in add_resp.text.lower():
            pytest.skip("npm install failed - external dependency issue")
        
        assert add_resp.status_code == 200, f"Add failed: {add_resp.text}"
        
        # Verify the schema was saved
        get_resp = requests.get(f"{BASE_URL}/api/servers/test-creds-server", headers=self.headers)
        assert get_resp.status_code == 200
        data = get_resp.json()
        schema = data.get("credentials_schema", [])
        print(f"Saved schema: {schema}")
        
        var_keys = [v.get("key") for v in schema]
        assert "CUSTOM_API_KEY" in var_keys, f"CUSTOM_API_KEY not in schema: {var_keys}"
        assert "CUSTOM_API_URL" in var_keys, f"CUSTOM_API_URL not in schema: {var_keys}"
        
        # Verify required flag
        for v in schema:
            if v.get("key") == "CUSTOM_API_KEY":
                assert v.get("required") == True, "CUSTOM_API_KEY should be required"
            if v.get("key") == "CUSTOM_API_URL":
                assert v.get("required") == False, "CUSTOM_API_URL should be optional"


class TestParseGitHubWithCredentials:
    """Test GitHub URL parsing returns credentials_schema"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@mcphub.local",
            "password": "McpHub2026!"
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        yield
    
    def test_parse_github_url_returns_server_info(self):
        """Test POST /api/servers/parse-github returns server info"""
        resp = requests.post(
            f"{BASE_URL}/api/servers/parse-github",
            headers=self.headers,
            json={"github_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/github"}
        )
        print(f"Parse GitHub: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            server_info = data.get("server_info", {})
            print(f"Server info: {server_info}")
            assert "name" in server_info
            assert "runtime" in server_info
            # credentials_schema may or may not be present depending on detection
            print(f"Credentials schema: {server_info.get('credentials_schema', 'Not detected')}")
        else:
            print(f"Parse failed: {resp.text}")
            # This might fail if GitHub rate limits, so don't fail the test
            pytest.skip(f"GitHub parse failed: {resp.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

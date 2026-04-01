"""
Test suite for MCP Hub Tool Customization System
Tests: parse-schema, create tool, update tool, param CRUD, toggle tools
"""
import pytest
import requests
import os
import json
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@mcphub.local"
ADMIN_PASSWORD = "McpHub2026!"


class TestSetup:
    """Setup and basic connectivity tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get JWT token for authenticated requests"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        return resp.json()["token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Headers with JWT auth"""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_api_root(self):
        """Test API is accessible"""
        resp = requests.get(f"{BASE_URL}/api/")
        assert resp.status_code == 200
        assert "MCP Hub API" in resp.json().get("message", "")
        print("✓ API root accessible")
    
    def test_login_success(self):
        """Test login with valid credentials"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["email"] == ADMIN_EMAIL.lower()
        print("✓ Login successful")


class TestToolsList:
    """Test GET /api/chatwoot/tools endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return {"Authorization": f"Bearer {resp.json()['token']}", "Content-Type": "application/json"}
    
    def test_tools_list_requires_auth(self):
        """Tools list requires authentication"""
        resp = requests.get(f"{BASE_URL}/api/chatwoot/tools")
        assert resp.status_code == 401
        print("✓ Tools list requires auth")
    
    def test_tools_list_with_auth(self, auth_headers):
        """Tools list returns tools with auth"""
        resp = requests.get(f"{BASE_URL}/api/chatwoot/tools", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data
        assert isinstance(data["tools"], list)
        assert len(data["tools"]) > 0
        # Verify tool structure
        tool = data["tools"][0]
        assert "name" in tool
        assert "description" in tool
        assert "parameters" in tool
        assert "category" in tool
        assert "enabled" in tool
        print(f"✓ Tools list returned {len(data['tools'])} tools")


class TestParseSchema:
    """Test POST /api/chatwoot/tools/parse-schema endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return {"Authorization": f"Bearer {resp.json()['token']}", "Content-Type": "application/json"}
    
    def test_parse_schema_requires_auth(self):
        """Parse schema requires admin auth"""
        resp = requests.post(f"{BASE_URL}/api/chatwoot/tools/parse-schema", json={
            "schema": "curl -X GET https://example.com/api"
        })
        assert resp.status_code == 401
        print("✓ Parse schema requires auth")
    
    def test_parse_curl_put_request(self, auth_headers):
        """Parse cURL PUT request with JSON body"""
        curl_cmd = """curl --request PUT \\
  --url https://app.chatwoot.com/api/v1/accounts/{account_id}/contacts/{id} \\
  --header 'Content-Type: application/json' \\
  --data '{"name": "Alice", "email": "alice@acme.inc"}'"""
        
        resp = requests.post(
            f"{BASE_URL}/api/chatwoot/tools/parse-schema",
            headers=auth_headers,
            json={"schema": curl_cmd}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "tool" in data
        tool = data["tool"]
        assert tool["method"] == "PUT"
        assert "contact" in tool["name"].lower() or "update" in tool["name"].lower()
        # Should have id param from path and name/email from body
        param_names = [p["name"] for p in tool["parameters"]]
        assert "id" in param_names
        assert "name" in param_names
        assert "email" in param_names
        # account_id should be stripped
        assert "account_id" not in param_names
        print(f"✓ Parsed cURL PUT: {tool['name']} with params {param_names}")
    
    def test_parse_curl_post_request(self, auth_headers):
        """Parse cURL POST request"""
        curl_cmd = """curl -X POST 'https://app.chatwoot.com/api/v1/accounts/{account_id}/conversations' \\
  -H 'Content-Type: application/json' \\
  -d '{"inbox_id": 1, "contact_id": 123, "message": {"content": "Hello"}}'"""
        
        resp = requests.post(
            f"{BASE_URL}/api/chatwoot/tools/parse-schema",
            headers=auth_headers,
            json={"schema": curl_cmd}
        )
        assert resp.status_code == 200
        tool = resp.json()["tool"]
        assert tool["method"] == "POST"
        param_names = [p["name"] for p in tool["parameters"]]
        assert "inbox_id" in param_names
        assert "contact_id" in param_names
        print(f"✓ Parsed cURL POST: {tool['name']}")
    
    def test_parse_json_body(self, auth_headers):
        """Parse raw JSON body"""
        json_body = '{"phone_number": "+1234567890", "custom_attributes": {"plan": "premium"}}'
        
        resp = requests.post(
            f"{BASE_URL}/api/chatwoot/tools/parse-schema",
            headers=auth_headers,
            json={"schema": json_body}
        )
        assert resp.status_code == 200
        tool = resp.json()["tool"]
        param_names = [p["name"] for p in tool["parameters"]]
        assert "phone_number" in param_names
        assert "custom_attributes" in param_names
        print(f"✓ Parsed JSON body with params {param_names}")
    
    def test_parse_empty_schema_fails(self, auth_headers):
        """Empty schema returns 400"""
        resp = requests.post(
            f"{BASE_URL}/api/chatwoot/tools/parse-schema",
            headers=auth_headers,
            json={"schema": ""}
        )
        assert resp.status_code == 400
        print("✓ Empty schema returns 400")
    
    def test_parse_invalid_schema_fails(self, auth_headers):
        """Invalid schema returns 400"""
        resp = requests.post(
            f"{BASE_URL}/api/chatwoot/tools/parse-schema",
            headers=auth_headers,
            json={"schema": "not a valid curl or json"}
        )
        assert resp.status_code == 400
        print("✓ Invalid schema returns 400")


class TestCreateCustomTool:
    """Test POST /api/chatwoot/tools/create endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return {"Authorization": f"Bearer {resp.json()['token']}", "Content-Type": "application/json"}
    
    def test_create_tool_requires_auth(self):
        """Create tool requires admin auth"""
        resp = requests.post(f"{BASE_URL}/api/chatwoot/tools/create", json={
            "name": "test_tool",
            "description": "Test tool"
        })
        assert resp.status_code == 401
        print("✓ Create tool requires auth")
    
    def test_create_custom_tool(self, auth_headers):
        """Create a new custom tool"""
        tool_name = f"TEST_custom_tool_{int(time.time())}"
        resp = requests.post(
            f"{BASE_URL}/api/chatwoot/tools/create",
            headers=auth_headers,
            json={
                "name": tool_name,
                "description": "A test custom tool for testing",
                "category": "custom",
                "parameters": [
                    {"name": "param1", "type": "string", "required": True, "description": "First param"},
                    {"name": "param2", "type": "int", "required": False, "description": "Second param"}
                ],
                "source_schema": "curl -X POST https://example.com/api"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"
        assert data["tool"]["name"] == tool_name
        assert len(data["tool"]["parameters"]) == 2
        print(f"✓ Created custom tool: {tool_name}")
        
        # Verify tool appears in list
        list_resp = requests.get(f"{BASE_URL}/api/chatwoot/tools", headers=auth_headers)
        tools = list_resp.json()["tools"]
        tool_names = [t["name"] for t in tools]
        assert tool_name in tool_names
        
        # Find the tool and verify source is "custom"
        created_tool = next(t for t in tools if t["name"] == tool_name)
        assert created_tool["source"] == "custom"
        print(f"✓ Custom tool appears in tools list with source='custom'")
        
        # Cleanup - delete the custom tool
        del_resp = requests.delete(
            f"{BASE_URL}/api/chatwoot/tools/custom/{tool_name}",
            headers=auth_headers
        )
        assert del_resp.status_code == 200
        print(f"✓ Cleaned up custom tool: {tool_name}")
    
    def test_create_duplicate_tool_fails(self, auth_headers):
        """Cannot create tool with existing name"""
        # Get an existing builtin tool name
        list_resp = requests.get(f"{BASE_URL}/api/chatwoot/tools", headers=auth_headers)
        existing_tool = list_resp.json()["tools"][0]["name"]
        
        resp = requests.post(
            f"{BASE_URL}/api/chatwoot/tools/create",
            headers=auth_headers,
            json={
                "name": existing_tool,
                "description": "Duplicate tool"
            }
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]
        print(f"✓ Duplicate tool name rejected: {existing_tool}")


class TestUpdateTool:
    """Test PUT /api/chatwoot/tools/{tool_name} endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return {"Authorization": f"Bearer {resp.json()['token']}", "Content-Type": "application/json"}
    
    @pytest.fixture(scope="class")
    def test_tool_name(self, auth_headers):
        """Get a builtin tool name for testing"""
        resp = requests.get(f"{BASE_URL}/api/chatwoot/tools", headers=auth_headers)
        tools = resp.json()["tools"]
        # Find a builtin tool
        builtin = next((t for t in tools if t.get("source") != "custom"), tools[0])
        return builtin["name"]
    
    def test_update_tool_requires_auth(self, test_tool_name):
        """Update tool requires admin auth"""
        resp = requests.put(
            f"{BASE_URL}/api/chatwoot/tools/{test_tool_name}",
            json={"enabled": False}
        )
        assert resp.status_code == 401
        print("✓ Update tool requires auth")
    
    def test_toggle_tool_off(self, auth_headers, test_tool_name):
        """Toggle tool enabled state to false"""
        resp = requests.put(
            f"{BASE_URL}/api/chatwoot/tools/{test_tool_name}",
            headers=auth_headers,
            json={"enabled": False}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"
        
        # Verify tool is disabled in list
        list_resp = requests.get(f"{BASE_URL}/api/chatwoot/tools", headers=auth_headers)
        tool = next(t for t in list_resp.json()["tools"] if t["name"] == test_tool_name)
        assert tool["enabled"] == False
        print(f"✓ Tool {test_tool_name} disabled")
    
    def test_toggle_tool_on(self, auth_headers, test_tool_name):
        """Toggle tool enabled state back to true"""
        resp = requests.put(
            f"{BASE_URL}/api/chatwoot/tools/{test_tool_name}",
            headers=auth_headers,
            json={"enabled": True}
        )
        assert resp.status_code == 200
        
        # Verify tool is enabled
        list_resp = requests.get(f"{BASE_URL}/api/chatwoot/tools", headers=auth_headers)
        tool = next(t for t in list_resp.json()["tools"] if t["name"] == test_tool_name)
        assert tool["enabled"] == True
        print(f"✓ Tool {test_tool_name} re-enabled")
    
    def test_update_tool_description(self, auth_headers, test_tool_name):
        """Update tool description"""
        new_desc = "TEST_Updated description for testing"
        resp = requests.put(
            f"{BASE_URL}/api/chatwoot/tools/{test_tool_name}",
            headers=auth_headers,
            json={"description": new_desc}
        )
        assert resp.status_code == 200
        
        # Verify description updated
        list_resp = requests.get(f"{BASE_URL}/api/chatwoot/tools", headers=auth_headers)
        tool = next(t for t in list_resp.json()["tools"] if t["name"] == test_tool_name)
        assert tool["description"] == new_desc
        print(f"✓ Tool description updated")
    
    def test_update_empty_payload_fails(self, auth_headers, test_tool_name):
        """Update with no fields returns 400"""
        resp = requests.put(
            f"{BASE_URL}/api/chatwoot/tools/{test_tool_name}",
            headers=auth_headers,
            json={}
        )
        assert resp.status_code == 400
        print("✓ Empty update payload rejected")


class TestParamCRUD:
    """Test parameter CRUD operations"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return {"Authorization": f"Bearer {resp.json()['token']}", "Content-Type": "application/json"}
    
    @pytest.fixture(scope="class")
    def test_tool_name(self, auth_headers):
        """Get a builtin tool name with parameters"""
        resp = requests.get(f"{BASE_URL}/api/chatwoot/tools", headers=auth_headers)
        tools = resp.json()["tools"]
        # Find a tool with parameters
        tool_with_params = next((t for t in tools if len(t.get("parameters", [])) > 0), tools[0])
        return tool_with_params["name"]
    
    def test_add_new_param(self, auth_headers, test_tool_name):
        """Add a new parameter to existing tool"""
        new_param_name = f"TEST_new_param_{int(time.time())}"
        resp = requests.put(
            f"{BASE_URL}/api/chatwoot/tools/{test_tool_name}/params/{new_param_name}",
            headers=auth_headers,
            json={
                "name": new_param_name,
                "type": "string",
                "required": False,
                "description": "A test parameter",
                "enum_options": []
            }
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"
        
        # Verify param appears in tool
        list_resp = requests.get(f"{BASE_URL}/api/chatwoot/tools", headers=auth_headers)
        tool = next(t for t in list_resp.json()["tools"] if t["name"] == test_tool_name)
        param_names = [p["name"] for p in tool["parameters"]]
        assert new_param_name in param_names
        print(f"✓ Added new param {new_param_name} to {test_tool_name}")
        
        # Cleanup - delete the param
        del_resp = requests.delete(
            f"{BASE_URL}/api/chatwoot/tools/{test_tool_name}/params/{new_param_name}",
            headers=auth_headers
        )
        assert del_resp.status_code == 200
        print(f"✓ Cleaned up param {new_param_name}")
    
    def test_update_existing_param(self, auth_headers, test_tool_name):
        """Update an existing parameter"""
        # Get existing param
        list_resp = requests.get(f"{BASE_URL}/api/chatwoot/tools", headers=auth_headers)
        tool = next(t for t in list_resp.json()["tools"] if t["name"] == test_tool_name)
        existing_param = tool["parameters"][0]
        param_name = existing_param["name"]
        
        # Update the param
        resp = requests.put(
            f"{BASE_URL}/api/chatwoot/tools/{test_tool_name}/params/{param_name}",
            headers=auth_headers,
            json={
                "name": param_name,
                "type": "string",
                "required": True,
                "description": "TEST_Updated description",
                "enum_options": []
            }
        )
        assert resp.status_code == 200
        
        # Verify update
        list_resp = requests.get(f"{BASE_URL}/api/chatwoot/tools", headers=auth_headers)
        tool = next(t for t in list_resp.json()["tools"] if t["name"] == test_tool_name)
        updated_param = next(p for p in tool["parameters"] if p["name"] == param_name)
        assert updated_param["description"] == "TEST_Updated description"
        print(f"✓ Updated param {param_name}")
    
    def test_add_enum_param(self, auth_headers, test_tool_name):
        """Add parameter with enum options"""
        enum_param_name = f"TEST_enum_param_{int(time.time())}"
        resp = requests.put(
            f"{BASE_URL}/api/chatwoot/tools/{test_tool_name}/params/{enum_param_name}",
            headers=auth_headers,
            json={
                "name": enum_param_name,
                "type": "enum",
                "required": False,
                "description": "Status enum",
                "enum_options": ["open", "resolved", "pending"]
            }
        )
        assert resp.status_code == 200
        
        # Verify enum options
        list_resp = requests.get(f"{BASE_URL}/api/chatwoot/tools", headers=auth_headers)
        tool = next(t for t in list_resp.json()["tools"] if t["name"] == test_tool_name)
        enum_param = next(p for p in tool["parameters"] if p["name"] == enum_param_name)
        assert enum_param["type"] == "enum"
        assert enum_param["enum_options"] == ["open", "resolved", "pending"]
        print(f"✓ Added enum param with options")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/chatwoot/tools/{test_tool_name}/params/{enum_param_name}",
            headers=auth_headers
        )
    
    def test_delete_param(self, auth_headers, test_tool_name):
        """Delete a parameter override"""
        # First add a param
        temp_param = f"TEST_temp_param_{int(time.time())}"
        requests.put(
            f"{BASE_URL}/api/chatwoot/tools/{test_tool_name}/params/{temp_param}",
            headers=auth_headers,
            json={"name": temp_param, "type": "string", "required": False, "description": "Temp", "enum_options": []}
        )
        
        # Delete it
        resp = requests.delete(
            f"{BASE_URL}/api/chatwoot/tools/{test_tool_name}/params/{temp_param}",
            headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"
        print(f"✓ Deleted param {temp_param}")


class TestMCPInfo:
    """Test MCP info endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return {"Authorization": f"Bearer {resp.json()['token']}", "Content-Type": "application/json"}
    
    def test_mcp_info_requires_auth(self):
        """MCP info requires auth"""
        resp = requests.get(f"{BASE_URL}/api/chatwoot/mcp/info")
        assert resp.status_code == 401
        print("✓ MCP info requires auth")
    
    def test_mcp_info_returns_data(self, auth_headers):
        """MCP info returns server info"""
        resp = requests.get(f"{BASE_URL}/api/chatwoot/mcp/info", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "server_name" in data
        assert "transport" in data
        assert "tools_count" in data
        assert isinstance(data["tools_count"], int)
        assert data["tools_count"] > 0
        print(f"✓ MCP info: {data['server_name']} with {data['tools_count']} tools")


class TestCustomToolCRUD:
    """Test full CRUD for custom tools"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return {"Authorization": f"Bearer {resp.json()['token']}", "Content-Type": "application/json"}
    
    def test_custom_tool_full_lifecycle(self, auth_headers):
        """Create, update, and delete a custom tool"""
        tool_name = f"TEST_lifecycle_tool_{int(time.time())}"
        
        # CREATE
        create_resp = requests.post(
            f"{BASE_URL}/api/chatwoot/tools/create",
            headers=auth_headers,
            json={
                "name": tool_name,
                "description": "Initial description",
                "category": "custom",
                "parameters": [{"name": "input", "type": "string", "required": True, "description": "Input", "enum_options": []}]
            }
        )
        assert create_resp.status_code == 200
        print(f"✓ Created custom tool: {tool_name}")
        
        # READ - verify in list
        list_resp = requests.get(f"{BASE_URL}/api/chatwoot/tools", headers=auth_headers)
        tool = next((t for t in list_resp.json()["tools"] if t["name"] == tool_name), None)
        assert tool is not None
        assert tool["source"] == "custom"
        print(f"✓ Custom tool found in list")
        
        # UPDATE
        update_resp = requests.put(
            f"{BASE_URL}/api/chatwoot/tools/custom/{tool_name}",
            headers=auth_headers,
            json={"description": "Updated description", "enabled": False}
        )
        assert update_resp.status_code == 200
        
        # Verify update
        list_resp = requests.get(f"{BASE_URL}/api/chatwoot/tools", headers=auth_headers)
        tool = next(t for t in list_resp.json()["tools"] if t["name"] == tool_name)
        assert tool["description"] == "Updated description"
        assert tool["enabled"] == False
        print(f"✓ Custom tool updated")
        
        # DELETE
        del_resp = requests.delete(
            f"{BASE_URL}/api/chatwoot/tools/custom/{tool_name}",
            headers=auth_headers
        )
        assert del_resp.status_code == 200
        
        # Verify deleted
        list_resp = requests.get(f"{BASE_URL}/api/chatwoot/tools", headers=auth_headers)
        tool_names = [t["name"] for t in list_resp.json()["tools"]]
        assert tool_name not in tool_names
        print(f"✓ Custom tool deleted")
    
    def test_delete_nonexistent_custom_tool(self, auth_headers):
        """Delete nonexistent custom tool returns 404"""
        resp = requests.delete(
            f"{BASE_URL}/api/chatwoot/tools/custom/nonexistent_tool_xyz",
            headers=auth_headers
        )
        assert resp.status_code == 404
        print("✓ Delete nonexistent tool returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

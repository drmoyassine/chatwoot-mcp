#!/usr/bin/env python3
"""
Comprehensive backend API testing for Chatwoot MCP Server
Tests all required endpoints and tool execution functionality
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, Any, List

class ChatwootMCPTester:
    def __init__(self, base_url: str = "https://gracious-dewdney-2.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    {details}")
        
        if success:
            self.tests_passed += 1
        else:
            self.failed_tests.append({"name": name, "details": details})

    def test_api_endpoint(self, method: str, endpoint: str, expected_status: int = 200, 
                         data: Dict[str, Any] = None, test_name: str = None) -> Dict[str, Any]:
        """Test a single API endpoint"""
        if not test_name:
            test_name = f"{method} {endpoint}"
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if success:
                try:
                    result = response.json()
                    self.log_test(test_name, True, f"{details} - Response received")
                    return result
                except json.JSONDecodeError:
                    self.log_test(test_name, True, f"{details} - Non-JSON response")
                    return {"status": "success", "text": response.text}
            else:
                error_msg = f"Expected {expected_status}, got {response.status_code}"
                try:
                    error_detail = response.json().get('detail', '')
                    if error_detail:
                        error_msg += f" - {error_detail}"
                except:
                    pass
                self.log_test(test_name, False, error_msg)
                return {}
                
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            return {}

    def test_config_endpoints(self):
        """Test configuration endpoints"""
        print("\n🔧 Testing Configuration Endpoints...")
        
        # Test GET /api/config
        config = self.test_api_endpoint('GET', '/config', test_name="GET /api/config - Get current configuration")
        
        # Test POST /api/config/test
        test_result = self.test_api_endpoint('POST', '/config/test', test_name="POST /api/config/test - Test Chatwoot connection")
        
        # Verify connection test returns expected data
        if test_result and 'status' in test_result:
            if test_result['status'] == 'connected' and test_result.get('account_name') == 'Studygram Inc':
                self.log_test("Connection test returns correct account", True, f"Account: {test_result.get('account_name')}")
            else:
                self.log_test("Connection test returns correct account", False, f"Got: {test_result}")
        
        return config, test_result

    def test_tools_endpoints(self):
        """Test tools endpoints"""
        print("\n🛠️  Testing Tools Endpoints...")
        
        # Test GET /api/tools
        tools_response = self.test_api_endpoint('GET', '/tools', test_name="GET /api/tools - Get all MCP tools")
        
        tools = []
        if tools_response and 'tools' in tools_response:
            tools = tools_response['tools']
            
            # Verify we have 48 tools
            if len(tools) == 48:
                self.log_test("Tools count verification", True, f"Found {len(tools)} tools")
            else:
                self.log_test("Tools count verification", False, f"Expected 48 tools, got {len(tools)}")
            
            # Verify tools have required fields
            if tools:
                sample_tool = tools[0]
                required_fields = ['name', 'description', 'parameters', 'category']
                missing_fields = [field for field in required_fields if field not in sample_tool]
                
                if not missing_fields:
                    self.log_test("Tool structure verification", True, "All required fields present")
                else:
                    self.log_test("Tool structure verification", False, f"Missing fields: {missing_fields}")
        
        return tools

    def test_tool_execution(self, tools: List[Dict[str, Any]]):
        """Test tool execution endpoints"""
        print("\n⚡ Testing Tool Execution...")
        
        # Test specific tools mentioned in requirements
        test_tools = [
            {'name': 'get_account', 'params': {}},
            {'name': 'list_agents', 'params': {}},
            {'name': 'list_contacts', 'params': {}},
            {'name': 'list_conversations', 'params': {}},
            {'name': 'list_inboxes', 'params': {}}
        ]
        
        for tool_test in test_tools:
            tool_name = tool_test['name']
            params = tool_test['params']
            
            # Check if tool exists in the tools list
            tool_exists = any(tool['name'] == tool_name for tool in tools)
            if not tool_exists:
                self.log_test(f"Tool execution: {tool_name}", False, "Tool not found in tools list")
                continue
            
            # Execute the tool
            execution_data = {
                'tool_name': tool_name,
                'parameters': params
            }
            
            result = self.test_api_endpoint('POST', '/tools/execute', data=execution_data, 
                                          test_name=f"Execute tool: {tool_name}")
            
            # Verify result structure
            if result and 'result' in result:
                self.log_test(f"Tool {tool_name} returns result", True, "Result field present")
            elif result:
                self.log_test(f"Tool {tool_name} returns result", False, f"No result field in response: {list(result.keys())}")

    def test_mcp_info_endpoint(self):
        """Test MCP info endpoint"""
        print("\n📡 Testing MCP Info Endpoint...")
        
        mcp_info = self.test_api_endpoint('GET', '/mcp/info', test_name="GET /api/mcp/info - Get MCP server info")
        
        if mcp_info:
            # Verify transport details
            if 'transport' in mcp_info:
                transport = mcp_info['transport']
                
                # Check SSE transport
                if 'sse' in transport and 'endpoint' in transport['sse']:
                    expected_endpoint = '/api/mcp/sse'
                    actual_endpoint = transport['sse']['endpoint']
                    if actual_endpoint == expected_endpoint:
                        self.log_test("SSE endpoint verification", True, f"Endpoint: {actual_endpoint}")
                    else:
                        self.log_test("SSE endpoint verification", False, f"Expected {expected_endpoint}, got {actual_endpoint}")
                
                # Check STDIO transport
                if 'stdio' in transport and 'command' in transport['stdio']:
                    expected_command = 'python mcp_stdio.py'
                    actual_command = transport['stdio']['command']
                    if actual_command == expected_command:
                        self.log_test("STDIO command verification", True, f"Command: {actual_command}")
                    else:
                        self.log_test("STDIO command verification", False, f"Expected {expected_command}, got {actual_command}")
            
            # Check tools count
            if 'tools_count' in mcp_info:
                tools_count = mcp_info['tools_count']
                if tools_count == 48:
                    self.log_test("MCP tools count verification", True, f"Tools count: {tools_count}")
                else:
                    self.log_test("MCP tools count verification", False, f"Expected 48, got {tools_count}")
        
        return mcp_info

    def test_category_distribution(self, tools: List[Dict[str, Any]]):
        """Test that tools are properly categorized"""
        print("\n📊 Testing Tool Categories...")
        
        expected_categories = [
            'account', 'agents', 'contacts', 'conversations', 'messages', 
            'inboxes', 'teams', 'labels', 'canned_responses', 'custom_attributes', 
            'webhooks', 'reports'
        ]
        
        # Count tools by category
        category_counts = {}
        for tool in tools:
            category = tool.get('category', 'unknown')
            category_counts[category] = category_counts.get(category, 0) + 1
        
        print(f"    Category distribution: {category_counts}")
        
        # Verify all expected categories are present
        missing_categories = [cat for cat in expected_categories if cat not in category_counts]
        if not missing_categories:
            self.log_test("All expected categories present", True, f"Found {len(category_counts)} categories")
        else:
            self.log_test("All expected categories present", False, f"Missing: {missing_categories}")

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Chatwoot MCP Server Backend Tests")
        print(f"Testing against: {self.base_url}")
        print("=" * 60)
        
        # Test configuration endpoints
        config, test_result = self.test_config_endpoints()
        
        # Test tools endpoints
        tools = self.test_tools_endpoints()
        
        # Test tool execution
        if tools:
            self.test_tool_execution(tools)
            self.test_category_distribution(tools)
        
        # Test MCP info endpoint
        mcp_info = self.test_mcp_info_endpoint()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {len(self.failed_tests)}")
        print(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in self.failed_tests:
                print(f"  - {test['name']}: {test['details']}")
        
        return {
            'total_tests': self.tests_run,
            'passed_tests': self.tests_passed,
            'failed_tests': self.failed_tests,
            'success_rate': self.tests_passed/self.tests_run if self.tests_run > 0 else 0
        }

def main():
    """Main test execution"""
    tester = ChatwootMCPTester()
    results = tester.run_all_tests()
    
    # Exit with error code if tests failed
    if results['failed_tests']:
        sys.exit(1)
    else:
        print("\n🎉 All tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()
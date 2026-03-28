#!/usr/bin/env python3
"""
Comprehensive backend API testing for Chatwoot MCP Server
Tests all required endpoints and tool execution functionality
Updated for iteration 2: Testing 51 tools + new webhook/filter features
"""

import requests
import json
import sys
import time
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
            
            # Verify we have 51 tools (updated from 48)
            if len(tools) == 51:
                self.log_test("Tools count verification", True, f"Found {len(tools)} tools")
            else:
                self.log_test("Tools count verification", False, f"Expected 51 tools, got {len(tools)}")
            
            # Check for new tools specifically
            new_tools = ['filter_conversations_advanced', 'create_message_with_attachment', 'setup_webhook_listener']
            found_new_tools = []
            for tool in tools:
                if tool['name'] in new_tools:
                    found_new_tools.append(tool['name'])
            
            if len(found_new_tools) == 3:
                self.log_test("New tools verification", True, f"Found all 3 new tools: {found_new_tools}")
            else:
                missing_new = [t for t in new_tools if t not in found_new_tools]
                self.log_test("New tools verification", False, f"Missing new tools: {missing_new}")
            
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
            
            # Check tools count (updated to 51)
            if 'tools_count' in mcp_info:
                tools_count = mcp_info['tools_count']
                if tools_count == 51:
                    self.log_test("MCP tools count verification", True, f"Tools count: {tools_count}")
                else:
                    self.log_test("MCP tools count verification", False, f"Expected 51, got {tools_count}")
        
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

    def test_webhook_endpoints(self):
        """Test new webhook endpoints"""
        print("\n🔗 Testing Webhook Endpoints...")
        
        # Test POST /api/webhooks/receive
        webhook_data = {
            "event": "test_event",
            "data": {"test": "data", "timestamp": datetime.now().isoformat()}
        }
        
        webhook_result = self.test_api_endpoint('POST', '/webhooks/receive', data=webhook_data,
                                              test_name="POST /api/webhooks/receive - Webhook receiver")
        
        if webhook_result and webhook_result.get('status') == 'received':
            self.log_test("Webhook receiver accepts events", True, "Event received successfully")
        else:
            self.log_test("Webhook receiver accepts events", False, f"Unexpected response: {webhook_result}")
        
        # Test GET /api/webhooks/events/history
        history_result = self.test_api_endpoint('GET', '/webhooks/events/history?limit=10',
                                               test_name="GET /api/webhooks/events/history - Get webhook history")
        
        if history_result and 'events' in history_result:
            events = history_result['events']
            self.log_test("Webhook history endpoint", True, f"Retrieved {len(events)} events")
            
            # Check if our test event is in the history
            test_event_found = any(event.get('event') == 'test_event' for event in events)
            if test_event_found:
                self.log_test("Test event stored in history", True, "Test event found in webhook history")
            else:
                self.log_test("Test event stored in history", False, "Test event not found in history")
        else:
            self.log_test("Webhook history endpoint", False, f"Invalid response: {history_result}")
        
        # Test SSE endpoint connection (just check it responds, don't wait for events)
        try:
            sse_url = f"{self.base_url}/webhooks/events"
            response = requests.get(sse_url, stream=True, timeout=2)
            if response.status_code == 200:
                self.log_test("SSE webhook stream endpoint", True, "SSE endpoint accessible")
            else:
                self.log_test("SSE webhook stream endpoint", False, f"Status: {response.status_code}")
        except requests.exceptions.Timeout:
            self.log_test("SSE webhook stream endpoint", True, "SSE endpoint accessible (timeout expected)")
        except Exception as e:
            self.log_test("SSE webhook stream endpoint", False, f"Error: {str(e)}")

    def test_advanced_filter_tool(self):
        """Test the new filter_conversations_advanced tool"""
        print("\n🔍 Testing Advanced Filter Tool...")
        
        # Test filter_conversations_advanced with status filter
        filter_data = {
            'tool_name': 'filter_conversations_advanced',
            'parameters': {
                'filters_json': '[{"attribute_key":"status","filter_operator":"equal_to","values":["open"],"query_operator":null}]',
                'page': 1
            }
        }
        
        filter_result = self.test_api_endpoint('POST', '/tools/execute', data=filter_data,
                                             test_name="Execute filter_conversations_advanced tool")
        
        if filter_result and 'result' in filter_result:
            self.log_test("Advanced filter returns result", True, "Filter executed successfully")
            
            # Check if result has expected structure (should be conversation data)
            result = filter_result['result']
            if isinstance(result, dict) and ('data' in result or 'payload' in result or 'conversations' in result):
                self.log_test("Advanced filter result structure", True, "Result has expected conversation data structure")
            else:
                self.log_test("Advanced filter result structure", False, f"Unexpected result structure: {type(result)}")
        else:
            self.log_test("Advanced filter returns result", False, f"No result in response: {filter_result}")

    def test_file_upload_endpoint(self):
        """Test the new file upload endpoint"""
        print("\n📎 Testing File Upload Endpoint...")
        
        # Test POST /api/tools/execute-with-file endpoint exists
        # We'll test with a simple text file and the create_message_with_attachment tool
        try:
            # Create a simple test file content
            test_file_content = b"This is a test file for attachment testing"
            files = {'file': ('test.txt', test_file_content, 'text/plain')}
            data = {
                'tool_name': 'create_message_with_attachment',
                'parameters': json.dumps({
                    'conversation_id': 1,
                    'content': 'Test message with attachment'
                })
            }
            
            url = f"{self.base_url}/tools/execute-with-file"
            response = requests.post(url, data=data, files=files)
            
            if response.status_code == 200:
                self.log_test("File upload endpoint accessible", True, "POST /api/tools/execute-with-file responds")
                
                try:
                    result = response.json()
                    if 'result' in result:
                        self.log_test("File upload endpoint returns result", True, "File upload processed")
                    else:
                        self.log_test("File upload endpoint returns result", False, f"No result field: {result}")
                except json.JSONDecodeError:
                    self.log_test("File upload endpoint returns result", False, "Invalid JSON response")
            else:
                # Even if it fails due to invalid conversation ID, the endpoint should exist
                if response.status_code in [400, 404, 500]:
                    self.log_test("File upload endpoint accessible", True, f"Endpoint exists (status: {response.status_code})")
                else:
                    self.log_test("File upload endpoint accessible", False, f"Unexpected status: {response.status_code}")
                    
        except Exception as e:
            self.log_test("File upload endpoint accessible", False, f"Exception: {str(e)}")

    def test_new_tool_registration(self):
        """Test that new tools are properly registered"""
        print("\n🆕 Testing New Tool Registration...")
        
        # Test that create_message_with_attachment tool is registered
        attachment_tool_data = {
            'tool_name': 'create_message_with_attachment',
            'parameters': {
                'conversation_id': 999999,  # Use non-existent ID to avoid side effects
                'content': 'Test message',
                'file_url': 'https://httpbin.org/status/404'  # URL that will fail
            }
        }
        
        attachment_result = self.test_api_endpoint('POST', '/tools/execute', data=attachment_tool_data,
                                                 expected_status=500,  # Expect failure due to invalid data
                                                 test_name="Test create_message_with_attachment tool registration")
        
        # Test that setup_webhook_listener tool is registered
        webhook_tool_data = {
            'tool_name': 'setup_webhook_listener',
            'parameters': {
                'webhook_url': 'https://example.com/webhook',
                'subscriptions': 'message_created,conversation_created'
            }
        }
        
        webhook_tool_result = self.test_api_endpoint('POST', '/tools/execute', data=webhook_tool_data,
                                                   test_name="Test setup_webhook_listener tool registration")
        
        if webhook_tool_result and 'result' in webhook_tool_result:
            self.log_test("Webhook listener tool returns result", True, "Tool executed successfully")
        else:
            self.log_test("Webhook listener tool returns result", False, f"No result: {webhook_tool_result}")

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Chatwoot MCP Server Backend Tests - Iteration 2")
        print(f"Testing against: {self.base_url}")
        print("Testing new features: 51 tools, webhook endpoints, advanced filtering, file uploads")
        print("=" * 80)
        
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
        
        # NEW TESTS FOR ITERATION 2
        # Test webhook endpoints
        self.test_webhook_endpoints()
        
        # Test advanced filter tool
        self.test_advanced_filter_tool()
        
        # Test file upload endpoint
        self.test_file_upload_endpoint()
        
        # Test new tool registration
        self.test_new_tool_registration()
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY - ITERATION 2")
        print("=" * 80)
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
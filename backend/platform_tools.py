import json
import logging

logger = logging.getLogger(__name__)

PLATFORM_TOOL_NAMES = {"start_here", "list_tools", "search_tools", "check_connection"}

PLATFORM_TOOLS = [
    {
        "name": "start_here",
        "description": "START HERE. Call this first to understand what this MCP server can do. Returns a concise overview of the server, all categories, tool counts, and connection status.",
        "parameters": [],
        "category": "platform",
        "source": "platform",
        "enabled": True,
    },
    {
        "name": "list_tools",
        "description": "List and inspect MCP tools. Use ONE of the optional filters: - category: filter by category - tool_name: get full schema for a specific tool (name, description, parameters with types/defaults/required). Call with no arguments to list all tools.",
        "parameters": [
            {"name": "category", "type": "string", "required": False, "description": "Filter tools by category", "enum_options": []},
            {"name": "tool_name", "type": "string", "required": False, "description": "Get full schema for a specific tool", "enum_options": []},
        ],
        "category": "platform",
        "source": "platform",
        "enabled": True,
    },
    {
        "name": "search_tools",
        "description": "Search for tools by keyword. Searches tool names and descriptions. Example queries: 'assign', 'search contact', 'webhook', 'status'.",
        "parameters": [
            {"name": "query", "type": "string", "required": True, "description": "Search keyword", "enum_options": []},
        ],
        "category": "platform",
        "source": "platform",
        "enabled": True,
    },
    {
        "name": "check_connection",
        "description": "Test the connection to this MCP server and return status details. Use this to verify the server is running and credentials are working.",
        "parameters": [],
        "category": "platform",
        "source": "platform",
        "enabled": True,
    },
]


def get_platform_tools():
    return [dict(t) for t in PLATFORM_TOOLS]


async def execute_platform_tool(tool_name, parameters, server_name, server_tools, is_connected):
    if tool_name == "start_here":
        return _execute_start_here(server_name, server_tools, is_connected)
    elif tool_name == "list_tools":
        return _execute_list_tools(server_tools, parameters)
    elif tool_name == "search_tools":
        return _execute_search_tools(server_tools, parameters)
    elif tool_name == "check_connection":
        return _execute_check_connection(server_name, server_tools, is_connected)
    raise ValueError(f"Unknown platform tool: {tool_name}")


def _execute_start_here(server_name, tools, is_connected):
    cats = {}
    for t in tools:
        c = t.get("category", "general")
        if c == "platform":
            continue
        if c not in cats:
            cats[c] = {"tool_count": 0, "tools": []}
        cats[c]["tool_count"] += 1
        cats[c]["tools"].append(t["name"])
    non_platform = [t for t in tools if t.get("source") != "platform"]
    return {
        "server": server_name,
        "connected": is_connected,
        "total_tools": len(non_platform),
        "categories": {k: v for k, v in sorted(cats.items())},
        "usage": {
            "browse": "list_tools(category='<category_name>')",
            "lookup": "list_tools(tool_name='<tool_name>')",
            "search": "search_tools(query='<keyword>')",
            "verify": "check_connection()",
        },
    }


def _execute_list_tools(tools, parameters):
    category = parameters.get("category")
    tool_name = parameters.get("tool_name")
    non_platform = [t for t in tools if t.get("source") != "platform"]

    if tool_name:
        tool = next((t for t in non_platform if t["name"] == tool_name), None)
        if not tool:
            suggestions = [t["name"] for t in non_platform if tool_name.lower() in t["name"].lower()][:5]
            return {"error": f"Tool '{tool_name}' not found", "did_you_mean": suggestions}
        return tool

    if category:
        cat = category.lower().strip()
        non_platform = [t for t in non_platform if t.get("category") == cat]
        if not non_platform:
            all_cats = sorted(set(t.get("category", "general") for t in tools if t.get("source") != "platform"))
            return {"error": f"No tools in category '{category}'", "available_categories": all_cats}

    return {
        "tool_count": len(non_platform),
        "tools": [{"name": t["name"], "description": t.get("description", ""), "category": t.get("category", "general")} for t in non_platform],
    }


def _execute_search_tools(tools, parameters):
    query = parameters.get("query", "")
    q = query.lower()
    non_platform = [t for t in tools if t.get("source") != "platform"]
    matches = []
    for t in non_platform:
        score = 0
        if q in t["name"].lower():
            score += 2
        if q in t.get("description", "").lower():
            score += 1
        if score > 0:
            matches.append({**t, "_score": score})
    matches.sort(key=lambda x: -x["_score"])
    for m in matches:
        del m["_score"]
    return {"query": query, "results_count": len(matches), "results": matches}


def _execute_check_connection(server_name, tools, is_connected):
    non_platform = [t for t in tools if t.get("source") != "platform"]
    if is_connected:
        return {
            "status": "connected",
            "server": server_name,
            "tools_available": len(non_platform),
        }
    return {
        "status": "disconnected",
        "server": server_name,
        "tools_available": 0,
    }

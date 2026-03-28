#!/usr/bin/env python3
"""Standalone MCP server entry point for stdio transport.

Usage:
    python mcp_stdio.py

Configure via environment variables:
    CHATWOOT_URL - Your Chatwoot instance URL (e.g., https://app.chatwoot.com)
    CHATWOOT_API_TOKEN - Your API access token
    CHATWOOT_ACCOUNT_ID - Your account ID
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_tools import mcp  # noqa: E402


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

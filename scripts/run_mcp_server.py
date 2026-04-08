#!/usr/bin/env python3
"""Wrapper to run the Hermes Coding MCP server with SSE transport."""
import sys
sys.path.insert(0, '/root/.hermes/mcp/hermes-coding-mcp')
from server import mcp
mcp.run(transport='sse', mount_path='/mcp')

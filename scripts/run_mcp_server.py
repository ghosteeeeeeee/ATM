#!/usr/bin/env python3
"""Wrapper to run the Hermes Coding MCP server.

Uses SSE transport for systemd service integration.
Respects SSE_PORT / SSE_HOST / SSE_MOUNT_PATH env vars.
"""
import os
import sys
sys.path.insert(0, '/root/.hermes/mcp/hermes-coding-mcp')
from server import mcp

mcp.settings.port = int(os.environ.get('SSE_PORT', 8000))
mcp.settings.host = os.environ.get('SSE_HOST', '127.0.0.1')
mcp.run(transport='sse', mount_path=os.environ.get('SSE_MOUNT_PATH', '/mcp'))

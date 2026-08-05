#!/bin/bash
# Port 4099 avoids conflict with interactive opencode sessions on default port
# Timeout: 5 minutes (300s) — CEO should be fast, not comprehensive
timeout 300 cat /root/.hermes/automation/ceo_prompt.md | /root/.opencode/bin/opencode run --port 4099

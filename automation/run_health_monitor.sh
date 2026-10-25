#!/bin/bash
cat /root/.hermes/automation/health_monitor_prompt.md | timeout 1100 /root/.opencode/bin/opencode run --port 4099

#!/bin/bash
cat /root/.hermes/automation/upgrade_implementer_prompt.md | timeout 120 /root/.opencode/bin/opencode run --port 4099


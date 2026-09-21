#!/bin/bash
# Brain Auditor — runs via opencode, same pattern as auto_1hr
# Queries session brain + trade data, generates recommendations + creative improvements

PROMPT_FILE="/root/.hermes/automation/brain-auditor/brain_auditor_prompt.md"
cat "$PROMPT_FILE" | timeout 600 /root/.opencode/bin/opencode run --port 4099

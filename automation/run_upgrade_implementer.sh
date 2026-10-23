#!/bin/bash
# ponytail: 1800s (was 900) — typical run ~10min, task on 2026-10-23 needed >15min; matches unit TimeoutStartSec
cat /root/.hermes/automation/upgrade_implementer_prompt.md | timeout 1800 /root/.opencode/bin/opencode run --port 4099


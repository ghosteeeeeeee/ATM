#!/bin/bash
# run_ceo.sh — CEO STATUS run (reworked 2026-10-12).
#
# This is the FREQUENT, BOUNDED, READ-ONLY path. It was previously the only
# entrypoint and it ran the full Step 0-5 audit + Monday MoE inline in one
# process — which cannot finish in any timeout (5 timed-out runs on 2026-10-11).
# Now:
#   - status = this script. ~3 min, read-only, one bounded session.
#   - deep   = run_ceo_deep.sh  (weekly / on-flag, detached, subagent sessions)
#   - moe    = run_ceo_moe.sh   (Monday only, detached, 6 parallel experts)
#
# Design basis: CEO decision 2026-10-12 (automation/ceo/ceo_report.md).

set -uo pipefail
cd /root/.hermes || exit 1
source /root/.hermes/automation/ceo/ceo_lib.sh

TS=$(date -u +%Y%m%dT%H%M%SZ)
BASE="$CEO_DIR/ceo_prompt_base.md"
STATUS="$CEO_DIR/ceo_prompt_status.md"
TASK="$CEO_DIR/ceo_task_${TS}.md"
REPORT="$CEO_DIR/ceo_report.md"

# ── Session lock notice (status run is READ-ONLY; check but never take) ─────
LOCK_NOTE=""
if [ -f "$LOCK_FILE" ]; then
    age=$(( $(date +%s) - $(stat -c %Y "$LOCK_FILE" 2>/dev/null || echo 0) ))
    if [ "$age" -lt "$LOCK_TTL" ]; then
        LOCK_NOTE="Note: a human session is active (${age}s old). You are READ-ONLY this run regardless."
    fi
fi

# ── Monday guard: MoE is handled by its own script, never inline ────────────
DOW=$(date -u +%u)   # 1=Mon .. 7=Sun
MOE_NOTE=""
if [ "$DOW" -eq 1 ]; then
    MOE_NOTE="It is Monday (UTC). The weekly MoE panel is handled SEPARATELY by run_ceo_moe.sh — do NOT run it here. Do not dispatch the 6 experts in this session."
fi

# ── Hand off flagged deep work to the deep script (never inline) ────────────
DEEP_NOTE=""
if grep -qiE 'DEEP_RUN_REQUESTED|NEEDS_DEEP_RUN' "$REPORT" 2>/dev/null; then
    DEEP_NOTE="A deep-run flag is set in ceo_report.md. Deep work is handled by run_ceo_deep.sh — do NOT edit live-trading files in this status session. If you confirm a problem, write a one-line recommendation and STOP."
fi

# ── Build this run's task (the bounded status brief) ────────────────────────
cat > "$TASK" <<TASK
# STATUS RUN ${TS} (UTC)

You are running the BOUNDED, READ-ONLY status check. Base persona/rules follow after this block.

${LOCK_NOTE}
${MOE_NOTE}
${DEEP_NOTE}

## Do EXACTLY this, then stop
1. cat CURRENT.md ; head -20 automation/ceo/ceo_kanban.md
2. ONE SQL batch (24h totals, 7d totals, open positions) — queries are in the status template.
3. systemctl is-active hermes-pipeline ; systemctl is-active hermes-hl-sync-guardian ; tail -20 automation/error_alerts.md
4. Answer ONE rotating proactive question (today's UTC date-of-month mod the PROACTIVE table row count). Do not answer all.
5. Append a dated "## CEO Status — ${TS}" section to automation/ceo/ceo_report.md. Max 200 words. Lead with state.

## HARD LIMITS
- READ-ONLY. Do NOT edit any file EXCEPT appending your report to automation/ceo/ceo_report.md.
- No param/flag/blacklist changes. No signal development or tuning. No subagents. No MoE panel.
- If something needs fixing: write ONE recommendation line and stop.
TASK

# ── Run: status runs IN-PROCESS (short, bounded). Hard timeout is intentional:
#    a timeout here means a regression, because status must finish <3 min.
PROMPT_FILE="$CEO_LOG_DIR/status-${TS}.prompt"
cat "$STATUS" > "$PROMPT_FILE"
printf '\n\n--- BASE PERSONA ---\n\n' >> "$PROMPT_FILE"
cat "$BASE" >> "$PROMPT_FILE"
printf '\n\n--- TASK ---\n\n' >> "$PROMPT_FILE"
cat "$TASK" >> "$PROMPT_FILE"

# Abort if the persona failed to load. Status is read-only so nothing can be
# edited blind, but an unguarded report is still a bad report — and consistency
# with deep/moe means one rule to reason about, not three. (ceo_lib.sh.)
if ! ceo_assert_prompt "$PROMPT_FILE" "$CEO_PERSONA_MARKER" "status"; then
    echo "[CEO] prompt integrity check FAILED — not launching." >&2
    rm -f "$PROMPT_FILE" "$TASK"
    exit 5
fi

echo "[CEO] status run ${TS} starting (bounded, read-only)"
# Prompt is passed on STDIN as the positional message. (--file only ATTACHES files,
# it does not supply the message — verified by smoke test 2026-10-12.)
timeout 300 "$OPENCODE" run --format json < "$PROMPT_FILE" \
    >> "$CEO_LOG_DIR/status-${TS}.jsonl" 2>&1
rc=$?
echo "$rc" > "$CEO_LOG_DIR/status-${TS}.exit"

if [ "$rc" -eq 124 ]; then
    echo "[CEO] ⚠️ status run TIMED OUT (300s) — REGRESSION (status must be <3min)."
    echo "[CEO]    inspect $CEO_LOG_DIR/status-${TS}.jsonl"
elif [ "$rc" -ne 0 ]; then
    echo "[CEO] ⚠️ status run exited rc=$rc — inspect $CEO_LOG_DIR/status-${TS}.jsonl"
else
    echo "[CEO] status run complete — report appended to $REPORT"
fi

rm -f "$TASK"
exit "$rc"

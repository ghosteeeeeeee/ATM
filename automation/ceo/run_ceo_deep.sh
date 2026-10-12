#!/bin/bash
# run_ceo_deep.sh — CEO DEEP run (weekly / on-flag). DETACHED.
#
# Expensive improvement path. Runs the deep template, which mandates:
#   - checkpoint-to-disk BEFORE any edit
#   - edits dispatched to FRESH single-goal subagent sessions (never a resumed
#     compacted mega-session — that edits files from a summary, not evidence)
#   - ACQUIRES the session lock before dispatching any editor
#   - single-writer (flock) for ceo_report.md / ceo_kanban.md
#
# Triggered: manually, by a DEEP_RUN_REQUESTED flag in ceo_report.md, or by the
# weekly schedule (this script does NOT self-schedule; the systemd deep unit does).
#
# Design basis: CEO decision 2026-10-12 (automation/ceo/ceo_report.md).

set -uo pipefail
cd /root/.hermes || exit 1
source /root/.hermes/automation/ceo/ceo_lib.sh

TS=$(date -u +%Y%m%dT%H%M%SZ)
BASE="$CEO_DIR/ceo_prompt_base.md"
DEEP="$CEO_DIR/ceo_prompt_deep.md"
TASK="$CEO_DIR/ceo_task_deep_${TS}.md"

# ── ACQUIRE the session lock (deep runs CAN edit; this is the collision guard) ──
# The lock is acquired by the DETACHED child (below), not this parent: the child
# outlives the parent, so it must own the lock and release it on its own exit. The
# child sets its EXIT trap BEFORE calling ceo_acquire_lock; acquire sees an
# existing trap and does not set its own, so the child's single trap fires the
# release on any exit path (normal, timeout, or signal).
if [ -f "$LOCK_FILE" ]; then
    _age=$(( $(date +%s) - $(stat -c %Y "$LOCK_FILE" 2>/dev/null || echo 0) ))
    if [ "$_age" -lt "$LOCK_TTL" ]; then
        echo "[CEO-DEEP] human/other session active (${_age}s < ${LOCK_TTL}s) — refusing to edit. Set a recommendation only. Stopping."
        exit 2
    fi
    echo "[CEO-DEEP] stale lock (${_age}s) — removing"
    rm -f "$LOCK_FILE"
fi

# ── Build the bounded deep task ─────────────────────────────────────────────
cat > "$TASK" <<TASK
# DEEP RUN ${TS} (UTC)

You are running the WEEKLY DEEP IMPROVEMENT run. Base persona/rules follow after this block.

## MANDATORY FIRST ACTION
Before ANY analysis that leads to an edit, and BEFORE dispatching any subagent, write:
  automation/ceo/checkpoints/${TS}-decision.md
containing Decision, Evidence, Plan, Files-to-touch, Rollback. This is the surviving artifact if you are killed.

## CONCURRENCY
- Any subagent that will edit hermes_constants.py or a signal file must ACQUIRE
  /tmp/hermes-session-active.lock before its first edit (this runner already holds it).
- ceo_report.md and ceo_kanban.md are written by ONE aggregator under flock — NOT by subagents.
- Each subagent writes ONLY its own file: automation/ceo/checkpoints/${TS}-result-<n>.md

## SCOPE (at most TWO work items)
1. Verify the headline numbers yourself (base prompt SQL). Find the single biggest bleeding point.
2. Regime-aware analysis: before disabling anything, find the signal's WINNING regime. Do not blanket-kill.
3. Pick at most TWO items: (a) ONE signal tune / param fix; (b) ONE new-signal or coin_tracker task.
   Checkpoint each, then dispatch each to its OWN fresh single-goal subagent session.
4. Assemble results from the subagent result files into the report under flock.

## OUTPUT
Append "## CEO Deep Run — ${TS}" to automation/ceo/ceo_report.md (single writer, under flock):
Decision, Evidence, Work items dispatched, Result files, Metric checkpoint (measure in 7d).
Store a one-paragraph summary to OpenMemory.

## HARD RULE
Do NOT do all of Step 0-5 in your own context. Analyze + decide + checkpoint + DISPATCH.
TASK

PROMPT_FILE="$CEO_LOG_DIR/deep-${TS}.prompt"
cat "$DEEP" > "$PROMPT_FILE"
printf '\n\n--- BASE PERSONA ---\n\n' >> "$PROMPT_FILE"
cat "$BASE" >> "$PROMPT_FILE"
printf '\n\n--- TASK ---\n\n' >> "$PROMPT_FILE"
cat "$TASK" >> "$PROMPT_FILE"

echo "[CEO-DEEP] run ${TS} starting (detached)"
jsonl="$CEO_LOG_DIR/deep-${TS}.jsonl"
exitf="$CEO_LOG_DIR/deep-${TS}.exit"

# Run FOREGROUND inside a detached process tree so the EXIT trap (lock release)
# fires only AFTER the opencode call actually finishes. `timeout 1800` bounds it;
# a timeout is inspectable via the .exit file, and the lock still releases cleanly
# because this subshell exits when the bounded run returns.
nohup bash -c '
    source /root/.hermes/automation/ceo/ceo_lib.sh
    # Always release the lock on ANY exit path (normal, timeout, or signal) — an
    # explicit call after `timeout` would be skipped if timeout is killed.
    trap "ceo_release_lock" EXIT
    ceo_acquire_lock "ceo-deep" || { echo "[CEO-DEEP] child could not acquire lock; aborting." >&2; echo 3 > "$3"; exit 3; }
    timeout 1800 "$OPENCODE" run --format json < "$1" >> "$2" 2>&1
    echo $? > "$3"
' _ "$PROMPT_FILE" "$jsonl" "$exitf" >/dev/null 2>&1 &
pid=$!
echo "[CEO-DEEP] detached pid=$pid — poll $exitf (budget 1800s). Lock held until the run exits."
rm -f "$TASK"
exit 0

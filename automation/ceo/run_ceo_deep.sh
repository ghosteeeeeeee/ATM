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
# Triggered: manually, or by a DEEP_RUN_REQUESTED / NEEDS_DEEP_RUN flag in
# ceo_report.md. This script does NOT self-schedule — no systemd timer exists for
# it yet (only run_ceo.sh is on a timer). Wire a hermes-ceo-deep.timer before
# relying on it firing automatically.
#
# Design basis: CEO decision 2026-10-12 (automation/ceo/ceo_report.md).

set -uo pipefail

# Resolve an optional brief argument to an ABSOLUTE path BEFORE cd'ing. A
# relative path would otherwise be re-interpreted against /root/.hermes and
# spuriously fail the existence test below — every relative-path invocation
# aborted with "brief not found" even when the file existed. (Found 2026-10-12
# while testing the persona guard.)
#
# Then CANONICALIZE it (strip `.`/`..`/symlinks). Without this the /tmp ban
# below is a string-prefix match on a non-canonical path and is both bypassable
# (`/root/../tmp/brief.md` slips past it and the session dies mid-run on the
# auto-reject the ban exists to prevent) and falsely-triggerable
# (`/tmp/../root/.../brief.md` wrongly rejects a legitimate in-repo brief).
INJECTED_BRIEF="${1:-}"
if [ -n "$INJECTED_BRIEF" ]; then
    case "$INJECTED_BRIEF" in
        /*) : ;;                                   # already absolute
        *) INJECTED_BRIEF="$(pwd)/$INJECTED_BRIEF" ;;  # caller-relative -> absolute
    esac
    if _canon=$(realpath -m -- "$INJECTED_BRIEF" 2>/dev/null) && [ -n "$_canon" ]; then
        INJECTED_BRIEF="$_canon"
    elif _canon=$(readlink -f -- "$INJECTED_BRIEF" 2>/dev/null) && [ -n "$_canon" ]; then
        INJECTED_BRIEF="$_canon"                   # fallback if realpath is absent
    fi
    # If neither exists we keep the absolute-but-uncanonicalized path: the
    # existence test below still applies, and a miss fails closed.
    unset _canon
fi

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

# ── Optional directed brief (task injection) ────────────────────────────────
# A caller with a specific question can pass a brief WITHOUT patching this script:
#   run_ceo_deep.sh /path/to/brief.md
# The brief is appended to the prompt AFTER the generic scope, and it REPLACES the
# "at most TWO work items" default — the agent works YOUR question instead of
# picking its own. Put the brief INSIDE the repo (e.g. under automation/), NOT in
# /tmp: opencode auto-rejects /tmp/* reads and the session dies mid-run.
# (INJECTED_BRIEF was resolved to an absolute path at the top of this script,
# before the cd — do not reassign it from $1 here or relative paths break again.)
INJECT_BLOCK=""
if [ -n "$INJECTED_BRIEF" ]; then
    if [ ! -f "$INJECTED_BRIEF" ]; then
        echo "[CEO-DEEP] brief not found: $INJECTED_BRIEF — stopping (caller error)." >&2
        exit 4
    fi
    case "$INJECTED_BRIEF" in
        /tmp/*|/var/tmp/*)
            _bdir=$(dirname "$INJECTED_BRIEF")
            echo "[CEO-DEEP] brief is in $_bdir — opencode auto-rejects that path and the session will die mid-run. Move the brief into the repo (e.g. automation/)." >&2
            exit 4 ;;
    esac
    INJECT_BLOCK=$(cat "$INJECTED_BRIEF")
    echo "[CEO-DEEP] directed brief attached: $INJECTED_BRIEF"
fi

# ── Build the bounded deep task ─────────────────────────────────────────────
# Branch in SHELL (before the heredoc) and emit only the chosen scope text. A
# shell if/else written inside the heredoc would be emitted as literal prose for
# the agent to read — that bug shipped once and leaked the default scope even
# when a directed brief was passed.
if [ -n "$INJECTED_BRIEF" ]; then
    SCOPE_BLOCK="Work the DIRECTED BRIEF below — it REPLACES the default \"pick your own items\" scope. Answer the brief's question with verified numbers, checkpoint the decision, then dispatch edits as needed.
--- DIRECTED BRIEF ---
$INJECT_BLOCK
--- END BRIEF ---"
else
    SCOPE_BLOCK="Default scope (no brief was passed):
1. Verify the headline numbers yourself (base prompt SQL). Find the single biggest bleeding point.
2. Regime-aware analysis: before disabling anything, find the signal's WINNING regime. Do not blanket-kill.
3. Pick at most TWO items: (a) ONE signal tune / param fix; (b) ONE new-signal or coin_tracker task.
   Checkpoint each, then dispatch each to its OWN fresh single-goal subagent session.
4. Assemble results from the subagent result files into the report under flock."
fi

cat > "$TASK" <<TASK
# DEEP RUN ${TS} (UTC)

You are running the WEEKLY DEEP IMPROVEMENT run. Base persona/rules follow after this block.

## MANDATORY FIRST ACTION
Before ANY analysis that leads to an edit, and BEFORE dispatching any subagent, write:
  automation/ceo/checkpoints/${TS}-decision.md
containing Decision, Evidence, Plan, Files-to-touch, Rollback. This is the surviving artifact if you are killed.

## CONCURRENCY
- The session lock (/tmp/hermes-session-active.lock) is ALREADY held by the runner that launched you. Do NOT read, write, or reference it yourself — opencode auto-rejects /tmp/* access and a single /tmp read will kill this session mid-run. Just proceed; the lock is handled for you.
- ceo_report.md and ceo_kanban.md are written by ONE aggregator under flock — NOT by subagents.
- Each subagent writes ONLY its own file: automation/ceo/checkpoints/${TS}-result-<n>.md

## SCOPE
$SCOPE_BLOCK

## OUTPUT
Append "## CEO Deep Run — ${TS}" to automation/ceo/ceo_report.md (single writer, under flock):
Decision, Evidence, Work items dispatched, Result files, Metric checkpoint (measure in 7d).
Store a one-paragraph summary to OpenMemory.

## HARD RULE
Do NOT do all of Step 0-5 in your own context. Analyze + decide + checkpoint + DISPATCH.
TASK

PROMPT_FILE="$CEO_LOG_DIR/deep-${TS}.prompt"
# Check EACH source before assembling. `cat` on a missing file fails to stderr
# but `>` has already truncated the target, so assembly would quietly produce a
# base+task prompt that still carries the persona marker — launching a deep run
# with no checkpoint-before-edit / single-writer / fresh-subagent discipline.
# Fail closed here instead. (ceo_lib.sh; found 2026-10-12 by bug_hunter.)
ceo_assert_template "$DEEP" "deep" || { rm -f "$TASK"; exit 5; }
ceo_assert_template "$BASE" "base" || { rm -f "$TASK"; exit 5; }
cat "$DEEP" > "$PROMPT_FILE"
printf '\n\n--- BASE PERSONA ---\n\n' >> "$PROMPT_FILE"
cat "$BASE" >> "$PROMPT_FILE"
printf '\n\n--- TASK ---\n\n' >> "$PROMPT_FILE"
cat "$TASK" >> "$PROMPT_FILE"

# Abort BEFORE taking the lock if the persona failed to load. A deep run with no
# protected-flags context could edit live-trading files blind — the one failure
# mode that must never launch. (Live test 2026-10-12 hit exactly this via an
# ad-hoc pipeline; the runners had the same latent weakness, now closed.)
if ! ceo_assert_prompt "$PROMPT_FILE" "$CEO_PERSONA_MARKER" "deep"; then
    echo "[CEO-DEEP] prompt integrity check FAILED — not launching, not locking." >&2
    rm -f "$PROMPT_FILE" "$TASK"
    exit 5
fi

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
    ceo_acquire_lock "ceo-deep-$(date -u +%Y%m%dT%H%M%SZ)-$$" || { echo "[CEO-DEEP] child could not acquire lock; aborting." >&2; echo "failed rc=3" > "$3"; exit 3; }
    timeout 1800 "$OPENCODE" run --format json < "$1" >> "$2" 2> "$4"
    rc=$?
    # opencode exits 0 even when the agent died mid-run (e.g. a permission
    # auto-reject), so classify by jsonl evidence, not the bare exit code.
    # Keep rc alongside the class so a timeout (124) stays visible — a
    # budget-exhausted run must not read as a clean "ok".
    echo "$(ceo_classify_run "$2") rc=$rc" > "$3"
' _ "$PROMPT_FILE" "$jsonl" "$exitf" "$CEO_LOG_DIR/deep-${TS}.err" 2>> "$CEO_LOG_DIR/deep-${TS}.err" &
pid=$!
echo "[CEO-DEEP] detached pid=$pid — poll $exitf (budget 1800s). Lock held until the run exits."
echo "[CEO-DEEP] NOTE: $exitf contains a CLASS plus rc (e.g. 'ok rc=0', 'failed rc=0', 'silent rc=124'), not a bare exit code — opencode exits 0 even when the agent dies mid-run. Do not treat exit-0 as success; read the class. Child stderr: $CEO_LOG_DIR/deep-${TS}.err"
rm -f "$TASK"
exit 0

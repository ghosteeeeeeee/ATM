#!/bin/bash
# ceo_lib.sh — shared helpers for the reworked CEO runners (2026-10-12 rework).
#
# Design basis: CEO decision 2026-10-12 (automation/ceo/ceo_report.md).
#  - Detach + stream: run opencode in background, tee --format json to a log,
#    capture exit code to a .exit file. A timeout becomes a signal to inspect,
#    not a data-loss event.
#  - Ephemeral port: each run gets its own port so concurrent runs don't collide.
#  - Session lock: implementation runs ACQUIRE /tmp/hermes-session-active.lock
#    before dispatching any editor (was a read-only check before -> collision risk).
#  - compaction.auto=false: impl/deep/moe sessions FAIL LOUDLY on context
#    overflow instead of silently summarizing mid-edit.
#  - Checkpoints: the FIRST action of any deep/moe run is a checkpoint file, so a
#    hard kill leaves the decision + plan on disk.

CEO_DIR="/root/.hermes/automation/ceo"
CEO_LOG_DIR="/root/.hermes/logs/ceo"
CHECKPOINT_DIR="$CEO_DIR/checkpoints"
OPENCODE="/root/.opencode/bin/opencode"
LOCK_FILE="/tmp/hermes-session-active.lock"
LOCK_TTL=3600
CEO_LOCK_OWNER=""   # tag written into the lock; release only removes OUR lock

mkdir -p "$CEO_LOG_DIR" "$CHECKPOINT_DIR"

# ── Port ────────────────────────────────────────────────────────────────────
# opencode run already defaults to a RANDOM free port when --port is omitted,
# so concurrent detached runs never collide. We pass --port only for runs that
# must be reachable at a stable address (none currently).
ceo_ephemeral_port() { :; }

# ── Session lock (acquire / release) ────────────────────────────────────────
# Create-if-absent with a timestamp. Refuses if a FRESH lock exists (human session).
# On success we OWN the lock (ceo_release_lock removes it on exit).
ceo_acquire_lock() {
    local now owner
    now=$(date +%s)
    owner="$1"   # e.g. "ceo-deep-20261012T034500Z"
    if [ -f "$LOCK_FILE" ]; then
        local age
        age=$(( now - $(stat -c %Y "$LOCK_FILE" 2>/dev/null || echo 0) ))
        if [ "$age" -lt "$LOCK_TTL" ]; then
            echo "[LOCK] human/other session active (${age}s old < ${LOCK_TTL}s) — refusing. Recommendation only; do not force."
            return 1
        fi
        echo "[LOCK] stale lock (${age}s) — removing and acquiring"
        rm -f "$LOCK_FILE"
    fi
    printf '%s\n' "$owner" > "$LOCK_FILE"
    CEO_LOCK_OWNER="$owner"
    # Only set an EXIT trap if the caller has none, so a caller that needs extra
    # cleanup keeps its own trap (bash traps are not stacked — a second `trap`
    # on EXIT silently replaces the first).
    [ -z "$(trap -p EXIT)" ] && trap 'ceo_release_lock' EXIT INT TERM
    echo "[LOCK] acquired by $owner"
    return 0
}

ceo_release_lock() {
    # Only remove the lock if WE own it (first line == the tag we recorded). This
    # stops a late-exiting process from deleting a lock another session has since
    # taken.
    if [ -f "$LOCK_FILE" ] && [ "$(head -n1 "$LOCK_FILE" 2>/dev/null)" = "${CEO_LOCK_OWNER:-}" ]; then
        rm -f "$LOCK_FILE"
        echo "[LOCK] released"
    fi
}

# ── Detached + streamed opencode run ────────────────────────────────────────
# ceo_run_detached <label> <template-file> [task-file]
#  - builds prompt = template + "\n\n---\n\n" + task  (on disk, avoids ARG_MAX)
#  - passes the prompt via --file (no process substitution, no shell quoting traps)
#  - relies on opencode's default RANDOM port (no collision between runs)
#  - streams --format json to logs/ceo/<label>-<ts>.jsonl  (partial signal survives a kill)
#  - writes the exit code to logs/ceo/<label>-<ts>.exit
#  - returns immediately (detached). Caller polls the .exit file.
#
# Compaction: NOT disabled here. opencode has no per-run --config flag; the knob
# is compaction.auto in ~/.opencode/opencode.json (shared). The status run is
# short + read-only, so auto-compact is harmless there. The DEEP and MOE runs
# enforce context discipline by DISPATCHING FRESH SINGLE-GOAL SUBAGENT SESSIONS
# (never resuming a compacted mega-session) — the compaction-safety mechanism
# the CEO approved. See ceo_prompt_deep.md / ceo_prompt_moe.md.
ceo_run_detached() {
    local label="$1" template="$2" task="$3"
    local ts jsonl exitf prompt_file
    ts=$(date -u +%Y%m%dT%H%M%SZ)
    jsonl="$CEO_LOG_DIR/${label}-${ts}.jsonl"
    exitf="$CEO_LOG_DIR/${label}-${ts}.exit"
    prompt_file="$CEO_LOG_DIR/${label}-${ts}.prompt"

    # Assemble prompt on disk.
    cat "$template" > "$prompt_file"
    if [ -n "$task" ] && [ -f "$task" ]; then
        printf '\n\n---\n\n' >> "$prompt_file"
        cat "$task" >> "$prompt_file"
    fi

    echo "[CEO] label=$label jsonl=$jsonl exit=$exitf"
    # Prompt is fed on STDIN as the positional message (--file only ATTACHES files;
    # it does not supply the message — verified by smoke test 2026-10-12).
    # The watcher runs in the SAME subshell as the call, so `wait` is valid and the
    # real exit code is captured.
    nohup bash -c '
        "$0" run --format json < "$1" >> "$2" 2>&1
        echo $? > "$3"
    ' "$OPENCODE" "$prompt_file" "$jsonl" "$exitf" >/dev/null 2>&1 &
    local pid=$!
    echo "$pid" > "$CEO_LOG_DIR/${label}-${ts}.pid"

    echo "[CEO] detached pid=$pid — poll $exitf for completion"
}

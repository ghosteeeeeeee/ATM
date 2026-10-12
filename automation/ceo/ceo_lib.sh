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
#  - Context safety: auto-compact remains ON (no global override in
#    ~/.opencode/opencode.json). Bounds come from each runner's timeout, NOT from
#    compaction. Context safety is achieved by scoping + fresh-subagent dispatch +
#    checkpoint-before-edit (see ceo_prompt_deep.md) — never by assuming compact
#    is off.
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

# NOTE: there is deliberately no generic "launch a detached run" helper here. Each
# runner (run_ceo_deep.sh, run_ceo_moe.sh) inlines its own nohup+timeout+stdin
# launch so the exact invocation is visible and tested in one place. If you need a
# shared launcher, add it AND update all callers + re-run the smoke test — do not
# let two launch paths drift apart (a `--file` vs stdin divergence here shipped a
# real bug on 2026-10-12 where the prompt was attached as a file and the run failed
# with "You must provide a message or a command").

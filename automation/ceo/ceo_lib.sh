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

# ── Success detection ───────────────────────────────────────────────────────
# opencode exits 0 even when the AGENT stopped without finishing (e.g. a tool
# call is auto-rejected for permission, or the model ends its turn early). A bare
# exit-0 therefore does NOT mean the run produced a decision. Classify the run by
# scanning the streamed jsonl for terminal evidence and write the CLASS (not the
# raw exit code) to the .exit file, so a poller that only reads .exit cannot
# mistake a dead run for a clean success:
#   ok         — a real completion marker, OR evidence of actual work (tool calls /
#                assistant text) with no failure signal. A genuinely finished run
#                always emits one of these.
#   incomplete — the run streamed events but never reached a completion marker and
#                shows no failure (e.g. the model ended its turn early, or the
#                stream was cut). MUST NOT read as ok — this is the size-only
#                fallback trap: a 250-byte markerless jsonl is not a finished run.
#   failed     — a permission rejection / tool error is present
#   silent     — jsonl has no usable content (crash before any output)
ceo_classify_run() {
    local jsonl="$1"
    [ -s "$jsonl" ] || { echo "silent"; return; }
    # Match opencode's real phrasing — it emits "The user rejected permission to
    # use this specific tool call", NOT "permission rejected". Do not drop the
    # 'rejected permission' variant or this stops matching the live failure mode.
    if grep -qiE 'auto-rejecting|rejected permission|permission rejected|"status": *"error"' "$jsonl"; then
        echo "failed"; return
    fi
    if grep -qE '"finish": *"(stop|end_turn|success)"|"type": *"(result|final|message_complete)"' "$jsonl"; then
        echo "ok"; return
    fi
    # No completion marker. Only claim 'ok' if the run demonstrably did WORK
    # (issued tool calls or produced assistant text) — mere byte size is not
    # evidence of completion, and treating it as such recreates the false-success
    # bug this classifier exists to kill.
    if grep -qE '"type": *"tool(_use)?"|"role": *"assistant"|"type": *"text"' "$jsonl"; then
        echo "incomplete"; return
    fi
    echo "silent"
}

# NOTE: there is deliberately no generic "launch a detached run" helper here. Each
# runner (run_ceo_deep.sh, run_ceo_moe.sh) inlines its own nohup+timeout+stdin
# launch so the exact invocation is visible and tested in one place. If you need a
# shared launcher, add it AND update all callers + re-run the smoke test — do not
# let two launch paths drift apart (a `--file` vs stdin divergence here shipped a
# real bug on 2026-10-12 where the prompt was attached as a file and the run failed
# with "You must provide a message or a command").

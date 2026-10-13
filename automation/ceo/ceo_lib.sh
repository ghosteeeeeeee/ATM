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

# ── Prompt-integrity guard ───────────────────────────────────────────────────
# A run whose persona/rules file failed to load is the worst possible outcome:
# opencode will happily execute a task with NO persona, NO protected-flags
# context, and NO rules — silently. Live test 2026-10-12: an agent piped a task
# via the pre-rework `cat ceo_prompt.md - <<TASK |` pattern after that file had
# been renamed; `cat` failed to stderr but the heredoc still reached opencode,
# so the CEO ran as a nameless "acting session" and only the stderr line gave it
# away. Fail LOUD and abort instead.
#
# Usage: ceo_assert_prompt <prompt-file> <required-marker> <label>
ceo_assert_prompt() {
    local prompt="$1" marker="$2" label="$3"
    if [ ! -s "$prompt" ]; then
        echo "[CEO][FATAL] $label prompt is missing or empty: $prompt" >&2
        echo "[CEO][FATAL] refusing to launch a run with no persona/rules — aborting." >&2
        return 1
    fi
    if ! grep -qF -- "$marker" "$prompt"; then
        echo "[CEO][FATAL] $label prompt has no persona marker ($marker): $prompt" >&2
        echo "[CEO][FATAL] the shared base prompt failed to load — a run launched now" >&2
        echo "[CEO][FATAL] would have NO protected-flags context. Aborting instead." >&2
        return 1
    fi
    return 0
}

# The marker check above only proves the BASE prompt loaded. The per-run template
# (deep/moe/status) is assembled with a plain `cat` under `set -uo pipefail` —
# no `-e` — so a missing template silently yields base+task only, and the marker
# still matches: the run launches WITHOUT its run-specific discipline (checkpoint-
# before-edit, single-writer, fresh-subagent dispatch). Same silent-degradation
# family, weaker form. Verify each source file before assembly.
#
# Usage: ceo_assert_template <file> <label>
ceo_assert_template() {
    if [ ! -s "$1" ]; then
        echo "[CEO][FATAL] $2 prompt template is missing or empty: $1" >&2
        echo "[CEO][FATAL] a run launched now would have no run-specific rules. Aborting." >&2
        return 1
    fi
    return 0
}

# Marker present in ceo_prompt_base.md. If the base prompt is ever renamed or
# replaced, update this too — a wrong marker fails closed (abort), never open.
CEO_PERSONA_MARKER='CEO_PROTECTED_FLAGS'

# ── Port ────────────────────────────────────────────────────────────────────
# opencode run already defaults to a RANDOM free port when --port is omitted,
# so concurrent detached runs never collide. We pass --port only for runs that
# must be reachable at a stable address (none currently).
ceo_ephemeral_port() { :; }

# ── Session lock (acquire / release) ────────────────────────────────────────
# Staleness test. Returns 0 (true) if the lock should be treated as stale.
# Owner-aware: a CEO-owned lock whose embedded PID is dead is stale REGARDLESS
# of mtime — this is the friction case that bit the live tester (a dead deep-run
# left a <1h-old lock; mtime-only check refused and the human had to rm it).
# Human/unknown owners keep the age-based check only (we cannot safely
# auto-classify them).
ceo_lock_is_stale() {
    local lock="${1:-$LOCK_FILE}"
    [ -f "$lock" ] || return 0   # absent → nothing to hold
    local age owner pid
    age=$(( $(date +%s) - $(stat -c %Y "$lock" 2>/dev/null || echo 0) ))
    owner=$(head -n1 "$lock" 2>/dev/null)
    case "$owner" in
        ceo-*)
            # Owner tag format: ceo-<label>-<ts>-<pid>  (see ceo_acquire_lock)
            pid="${owner##*-}"
            if [ -n "$pid" ] && [ "$pid" -gt 0 ] 2>/dev/null; then
                if ! kill -0 "$pid" 2>/dev/null; then
                    echo "[LOCK] CEO-owned lock with dead pid=$pid — treating as stale"
                    return 0
                fi
                return 1   # live CEO owner
            fi
            # ceo-* but no parseable PID → fall through to age check
            ;;
    esac
    [ "$age" -ge "$LOCK_TTL" ]
}

# Create-if-absent with a timestamp. Refuses if a FRESH lock exists (human session).
# On success we OWN the lock (ceo_release_lock removes it on exit).
ceo_acquire_lock() {
    local owner
    owner="$1"   # e.g. "ceo-deep-20261012T034500Z-12345" (pid at end)
    if [ -f "$LOCK_FILE" ]; then
        if ! ceo_lock_is_stale "$LOCK_FILE"; then
            local age
            age=$(( $(date +%s) - $(stat -c %Y "$LOCK_FILE" 2>/dev/null || echo 0) ))
            echo "[LOCK] human/other session active (${age}s old < ${LOCK_TTL}s) — refusing. Recommendation only; do not force."
            return 1
        fi
        echo "[LOCK] stale lock — removing and acquiring"
        rm -f "$LOCK_FILE"
    fi
    # Create the parent dir BEFORE the first write attempt. Redirecting a write into
    # a nonexistent dir makes bash emit its own "No such file or directory" that the
    # redirect's own 2>/dev/null cannot suppress, so pre-creating is cleaner than
    # catching the failure. Then verify the write landed: `>` on a missing dir (or a
    # permissions failure) does not abort this function — the old code printed
    # "[LOCK] acquired" and returned 0 while holding NOTHING, and the run would then
    # edit files believing it had the lock. Harmless while the lock lives in /tmp,
    # which always exists; becomes live the moment the lock moves elsewhere.
    mkdir -p "$(dirname "$LOCK_FILE")" 2>/dev/null
    if ! printf '%s\n' "$owner" > "$LOCK_FILE" 2>/dev/null; then
        echo "[LOCK] FATAL: cannot write lock at $LOCK_FILE — refusing to run unlocked." >&2
        return 1
    fi
    # Confirm what landed matches what we intended to own; a partial write or a
    # concurrent writer would show a different owner tag.
    if [ "$(head -n1 "$LOCK_FILE" 2>/dev/null)" != "$owner" ]; then
        echo "[LOCK] FATAL: lock at $LOCK_FILE does not hold our owner tag — refusing to run unlocked." >&2
        return 1
    fi
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
#   ok         — the LAST streamed event is opencode's terminal step_finish with
#                reason=stop, i.e. the agent ran to a clean completion. Anything
#                less (work done but no terminal event) is 'incomplete', never 'ok'.
#   incomplete — the run streamed events (tool calls / text) but the final event is
#                not a completion — the model ended its turn early, hit its budget,
#                or the stream was cut. MUST NOT read as ok: mere evidence of work
#                is not evidence of completion, and treating it as such recreates
#                the false-success bug this classifier exists to kill.
#   ok_after_reject — a permission denial DID happen, but the run recovered and
#                     still reached a clean terminal event. Surfaced separately
#                     from plain 'ok' because the recovery is real and worth a
#                     glance, but it is NOT a failure.
#   failed     — a permission denial happened AND the run did not end clean
#   silent     — jsonl has no usable content (crash before any output)
ceo_classify_run() {
    local jsonl="$1"
    [ -s "$jsonl" ] || { echo "silent"; return; }

    # Completion is detected on the LAST NON-EMPTY LINE ONLY. opencode's terminal
    # event is {"type":"step_finish","part":{"type":"step-finish","reason":"stop"}}.
    # There is no "finish" key and no result/final/message_complete type — an
    # earlier pattern looked for those and matched NOTHING across every real jsonl,
    # so 'ok' was unreachable. Whole-file matching is also wrong: a run killed
    # mid-stream contains step_finish events from earlier turns (deep-20261012T172817Z
    # has 2), so only the final event is trustworthy.
    local terminal_ok=0
    if tail -n1 "$jsonl" | grep -qE '"type": *"step_finish".*"reason": *"stop"'; then
        terminal_ok=1
    fi

    # Hard-fail evidence: a PERMISSION DENIAL, matched on STRUCTURED FIELDS ONLY.
    # BUG-FIX (2026-10-13): the old whole-file grep matched plain output TEXT, so
    # any run that read ceo_lib.sh (whose own grep pattern contains these phrases)
    # or grepped logs about past rejections was guaranteed to self-report 'failed'
    # even when it finished clean — deep-20261013T155406Z and deep-20261012T230504Z
    # were both mislabeled this way. In JSON output the phrase is escaped, so
    # anchoring on the unescaped field boundary cannot match echoed text. The raw
    # stderr banner is anchored off line-start + non-'{' prefix because it is NOT
    # JSON — it lands in the stream interleaved between events.
    #
    # NOTE: a generic tool error ("state":{"status":"error") is deliberately NOT
    # hard-fail. A run that hits one and recovers proves it by ending in a clean
    # stop (deep-20261012T230504Z hit a benign "File not found" read error and then
    # completed); treating any error as fatal hid that as 'failed'.
    local hard_fail=0
    if grep -qE '"error":"The user rejected permission' "$jsonl" \
       || grep -qE '^[^{]*permission requested: .*; *auto-rejecting' "$jsonl"; then
        hard_fail=1
    fi

    if [ "$hard_fail" -eq 1 ] && [ "$terminal_ok" -eq 0 ]; then
        echo "failed"; return
    fi
    if [ "$hard_fail" -eq 1 ]; then
        echo "ok_after_reject"; return
    fi
    if [ "$terminal_ok" -eq 1 ]; then
        echo "ok"; return
    fi
    # Not a clean stop. Work was demonstrably done if we see tool activity, an
    # assistant turn, or a step_finish with any non-stop reason (e.g. the
    # budget-exhausted 'tool-calls' reason the runners emit on a timeout). Mere
    # byte size is NOT evidence of completion — treating it as such recreates the
    # false-success bug this classifier exists to kill — but evidence of WORK is
    # enough to distinguish "started and got cut off" from "produced nothing".
    if grep -qE '"type": *"tool(_use)?"|"role": *"assistant"|"type": *"text"|"type": *"step_finish"' "$jsonl"; then
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

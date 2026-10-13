#!/bin/bash
# run_ceo_consult.sh — CEO CONSULT (read-only opinion on a brief). In-process.
#
# Interactive "quick question" path: takes a brief, runs a bounded read-only
# session that answers with an OPINION only — no edits, no subagents, no session
# lock, no ceo_report.md write. Output goes to stdout. Budget 300s (same as
# status). Added 2026-10-13 after live-tester feedback: status was useless for
# "review this plan" and deep was overkill (13min + subagent dispatch) for an
# opinion.
#
# Usage:
#   run_ceo_consult.sh /path/to/brief.md
#   run_ceo_consult.sh          # no brief → refuses (consult needs a question)
#
# Design basis: CEO decision 20261013T000026Z (automation/ceo/ceo_report.md).

set -uo pipefail

# Resolve the brief to an ABSOLUTE path BEFORE cd'ing (same rules as deep:
# relative paths would re-interpret against /root/.hermes). Canonicalize so the
# /tmp ban is not bypassable via `/root/../tmp/...` and not falsely-triggerable
# via `/tmp/../root/...`.
INJECTED_BRIEF="${1:-}"
if [ -z "$INJECTED_BRIEF" ]; then
    echo "[CEO-CONSULT] usage: run_ceo_consult.sh /path/to/brief.md" >&2
    echo "[CEO-CONSULT] consult needs a question — put it in a brief file (e.g. under automation/ceo/)." >&2
    exit 4
fi
case "$INJECTED_BRIEF" in
    /*) : ;;
    *) INJECTED_BRIEF="$(pwd)/$INJECTED_BRIEF" ;;
esac
if _canon=$(realpath -m -- "$INJECTED_BRIEF" 2>/dev/null) && [ -n "$_canon" ]; then
    INJECTED_BRIEF="$_canon"
elif _canon=$(readlink -f -- "$INJECTED_BRIEF" 2>/dev/null) && [ -n "$_canon" ]; then
    INJECTED_BRIEF="$_canon"
fi
unset _canon

cd /root/.hermes || exit 1
source /root/.hermes/automation/ceo/ceo_lib.sh

TS=$(date -u +%Y%m%dT%H%M%SZ)
BASE="$CEO_DIR/ceo_prompt_base.md"
TASK="$CEO_DIR/ceo_task_consult_${TS}.md"

# ── Brief guards (same failure modes as deep) ───────────────────────────────
if [ ! -f "$INJECTED_BRIEF" ]; then
    echo "[CEO-CONSULT] brief not found: $INJECTED_BRIEF — stopping (caller error)." >&2
    exit 4
fi
case "$INJECTED_BRIEF" in
    /tmp/*|/var/tmp/*)
        _bdir=$(dirname "$INJECTED_BRIEF")
        echo "[CEO-CONSULT] brief is in $_bdir — opencode auto-rejects that path and the session will die mid-run. Move the brief into the repo (e.g. automation/)." >&2
        exit 4 ;;
esac
INJECT_BLOCK=$(cat "$INJECTED_BRIEF")
echo "[CEO-CONSULT] brief attached: $INJECTED_BRIEF"

# ── Build the bounded consult task (inline — no template file to drift) ─────
cat > "$TASK" <<TASK
# CONSULT RUN ${TS} (UTC)

You are running a BOUNDED, READ-ONLY consult. Base persona/rules follow after this block.

## HARD LIMITS (this run)
- **BUDGET: ~3 minutes. Do not exceed a few file/DB reads.**
- **READ-ONLY. Do NOT edit ANY file. Do NOT change params, flags, or blacklists.**
- Do NOT develop signals. Do NOT tune signals. Do NOT dispatch subagents.
- Do NOT write to ceo_report.md or ceo_kanban.md — answer HERE, in this session.
- No session lock is held. If you believe an edit is needed, say so as a recommendation and stop.

## THE QUESTION
Answer the directed brief below. Verify any numbers you cite with a quick query (base prompt SQL rules apply — never trust old reports). Give a clear VERDICT (approve/reject/modify + rationale). If the brief asks for a review, lead with the verdict, then the reasons.

--- BRIEF ---
$INJECT_BLOCK
--- END BRIEF ---

## OUTPUT
Print your answer to this session (stdout). Do NOT append to any report file. Max ~400 words unless the brief demands more detail.
TASK

PROMPT_FILE="$CEO_LOG_DIR/consult-${TS}.prompt"
# Verify sources before assembly — fail closed (same rule as deep/moe/status).
ceo_assert_template "$BASE" "base" || { rm -f "$TASK"; exit 5; }
{
    cat "$BASE"
    printf '\n\n--- TASK ---\n\n'
    cat "$TASK"
} > "$PROMPT_FILE"

if ! ceo_assert_prompt "$PROMPT_FILE" "$CEO_PERSONA_MARKER" "consult"; then
    echo "[CEO-CONSULT] prompt integrity check FAILED — not launching." >&2
    rm -f "$PROMPT_FILE" "$TASK"
    exit 5
fi

echo "[CEO-CONSULT] run ${TS} starting (in-process, read-only, budget 300s)"
# Foreground, stdout passes through to the caller (this is the point of consult).
# Stderr also passes through so errors are visible. Both are also logged.
timeout 300 "$OPENCODE" run --format json < "$PROMPT_FILE" \
    2> "$CEO_LOG_DIR/consult-${TS}.err" | tee "$CEO_LOG_DIR/consult-${TS}.jsonl"
rc=${PIPESTATUS[0]}
echo "$(ceo_classify_run "$CEO_LOG_DIR/consult-${TS}.jsonl") rc=$rc" > "$CEO_LOG_DIR/consult-${TS}.exit"

if [ "$rc" -eq 124 ]; then
    echo "[CEO-CONSULT] ⚠️ TIMED OUT (300s)." >&2
elif [ "$rc" -ne 0 ]; then
    echo "[CEO-CONSULT] ⚠️ exited rc=$rc — inspect $CEO_LOG_DIR/consult-${TS}.err" >&2
fi

rm -f "$TASK" "$PROMPT_FILE"
exit "$rc"

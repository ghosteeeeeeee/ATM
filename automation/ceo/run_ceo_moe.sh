#!/bin/bash
# run_ceo_moe.sh — CEO WEEKLY MoE PANEL (Mondays, UTC). DETACHED.
#
# The 6-expert Mixture-of-Experts profitability-gap panel, split out of the main
# prompt so it NEVER runs inline in a status or deep run. Dispatches 6 parallel
# fresh subagent sessions + a synthesis pass, all checkpointed.
#
# Triggered manually (or via a timer that does not exist yet — wire a
# hermes-ceo-moe.timer before relying on automatic firing). Monday-gated by
# default; pass --force to run on any day (e.g. to re-run a missed Monday).
#
# Design basis: CEO decision 2026-10-12 (automation/ceo/ceo_report.md).

set -uo pipefail
cd /root/.hermes || exit 1
source /root/.hermes/automation/ceo/ceo_lib.sh

FORCE="${1:-}"
DOW=$(date -u +%u)   # 1=Mon .. 7=Sun
if [ "$DOW" -ne 1 ] && [ "$FORCE" != "--force" ]; then
    echo "[CEO-MOE] not Monday (UTC) — skipping. Pass --force to run anyway."
    exit 0
fi

TS=$(date -u +%Y%m%dT%H%M%SZ)
BASE="$CEO_DIR/ceo_prompt_base.md"
MOE="$CEO_DIR/ceo_prompt_moe.md"
TASK="$CEO_DIR/ceo_task_moe_${TS}.md"

cat > "$TASK" <<TASK
# WEEKLY MOE PANEL — ${TS} (UTC)

You are running the MIXTURE-OF-EXPERTS profitability-gap panel. Base persona/rules follow after this block.

## MANDATORY FIRST ACTION
Write automation/ceo/checkpoints/${TS}-moe-decision.md (date, the question the panel must answer, data sources per expert). This is the surviving artifact if you are killed.

## SESSION DISCIPLINE
- Dispatch the 6 experts as PARALLEL FRESH subagent sessions (single-goal each). NEVER one giant session — compaction would degrade it.
- Each expert writes ONLY automation/ceo/checkpoints/${TS}-moe-result-<n>.md. Synthesis (you) is the single writer of the final report, under flock.

## THE 6 EXPERTS (dispatch in parallel)
1. Signal Analyst — signal quality, direction accuracy, hot-set fitness, confluence effectiveness
2. Statistician — 30d trade data, win rates, R:R structure, edge detection, confidence intervals
3. Risk Manager — position sizing, stop-loss effectiveness, exit quality, fee drag, drawdown
4. Regime Analyst — regime detection quality, multi-timeframe alignment, regime-signal correlation
5. Code Architect — filter stacking, dead code, scoring architecture, bug patterns
6. Systems Engineer — pipeline health, execution rate, data freshness, latency

Each expert: query PostgreSQL brain.trades last 30d (use _secrets.BRAIN_DB_DICT), read relevant code, check pipeline logs, return a VERDICT with confidence (0.0-1.0) + root cause of any gap.

## SYNTHESIS (after all 6 return)
Consensus, Confidence (0.0-1.0), Dissent notes, Top 3 actionable fixes (ranked by expected impact), Metric checkpoint (measure in 7d).

## OUTPUT
- reports/${TS}-profitability-gap-moe-panel.md with full verdicts (single writer, under flock).
- Store synthesis to OpenMemory, tags ["moe-panel","weekly","profitability","${TS}"].
- Add delegation tasks to automation/ceo/ceo_kanban.md.
TASK

PROMPT_FILE="$CEO_LOG_DIR/moe-${TS}.prompt"
cat "$MOE" > "$PROMPT_FILE"
printf '\n\n--- BASE PERSONA ---\n\n' >> "$PROMPT_FILE"
cat "$BASE" >> "$PROMPT_FILE"
printf '\n\n--- TASK ---\n\n' >> "$PROMPT_FILE"
cat "$TASK" >> "$PROMPT_FILE"

# Abort if the persona failed to load — a panel run with no protected-flags
# context and no rules is worse than no run at all. (Same guard as deep; see
# ceo_lib.sh ceo_assert_prompt. Live test 2026-10-12.)
if ! ceo_assert_prompt "$PROMPT_FILE" "$CEO_PERSONA_MARKER" "moe"; then
    echo "[CEO-MOE] prompt integrity check FAILED — not launching." >&2
    rm -f "$PROMPT_FILE" "$TASK"
    exit 5
fi

jsonl="$CEO_LOG_DIR/moe-${TS}.jsonl"
exitf="$CEO_LOG_DIR/moe-${TS}.exit"

echo "[CEO-MOE] panel ${TS} starting (detached, budget 3600s)"
# Detached, foreground-in-child so it outlives this parent. The MoE panel does
# not edit live-trading files (analysis + report only), so it does NOT take the
# session lock — it only writes reports/ + checkpoints/ + OpenMemory.
nohup bash -c '
    # Source the lib IN THE CHILD: ceo_classify_run lives there, and the child
    # outlives this parent, so it must define the function itself. Without this
    # the classifier call silently expands to empty and .exit is a blank line.
    source /root/.hermes/automation/ceo/ceo_lib.sh
    timeout 3600 "$0" run --format json < "$1" >> "$2" 2> "$4"
    rc=$?
    # opencode exits 0 even when the agent died mid-run (e.g. a permission
    # auto-reject), so classify by jsonl evidence, not the bare exit code.
    # Keep rc alongside the class so a timeout (124) stays visible — a
    # budget-exhausted run must not read as a clean "ok".
    echo "$(ceo_classify_run "$2") rc=$rc" > "$3"
' "$OPENCODE" "$PROMPT_FILE" "$jsonl" "$exitf" "$CEO_LOG_DIR/moe-${TS}.err" 2>> "$CEO_LOG_DIR/moe-${TS}.err" &
pid=$!
echo "[CEO-MOE] detached pid=$pid — poll $exitf for completion"
rm -f "$TASK"
exit 0

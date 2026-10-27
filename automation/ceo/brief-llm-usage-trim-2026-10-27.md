# CONSULT BRIEF — LLM Usage Trim Review (2026-10-27)

## THE QUESTION

T wants to reduce LLM usage by the automation team. I ran a full analysis of all LLM-calling components. Please review the findings and give a VERDICT on the recommended trim: approve / reject / modify, with rationale.

**Full report:** `/root/.hermes/reports/2026-10-27-llm-usage-analysis.md`

## HEADLINE NUMBERS (verified, from opencode.db + systemd + logs)

- **30-day total: ~$54.67 / 4,475 sessions / 209M in + 28.5M out + 3.68B cache-read tokens**
- **trade-watchdog + brain-auditor = 67% of spend**
- 94.6% of input is cache-read (same 22KB AGENTS.md dragged every session)
- 532 agent git commits in 7 days (brain_auditor 124, watchdog 56, auto_1hr 21)

| Component | Sessions | Cost | Share |
|---|---|---|---|
| trade-watchdog | 1,367 | $20.30 | 37% |
| brain-auditor | 619 | $16.61 | 30% |
| health-monitor | 691 | $4.10 | 7.5% |
| other | 507 | $4.54 | 8% |
| auto-1hr | 665 | $2.39 | 4% |
| ctx-gate-llm | 119 | $0.40 | 1% |
| (all others) | ~350 | ~$4.2 | 8% |

## THE SEVEN FINDINGS

1. **Watchdog LLM runs unconditionally** — 45% of cycles (27/60 snapshots) had ZERO open trades, yet each burned a full session. `run_watchdog.sh` runs deterministic `trade_watchdog.py` (1,936 lines) FIRST, then always spawns a 480s opencode agent to re-read that same JSON. The prompt itself says "The Python watchdog has ALREADY run — DO NOT re-run it." → Fix: gate Step 2 on `open_count > 0` (already written at line 1676). Saves ~$9/30d.

2. **Brain-auditor hourly, largest footprint** — 104k tokens + 2.19M cache-read per session. Most prolific committer (124/7d) but changes_log shows mostly re-refutations ("wrong-side refuted 105th", "autopsy 104th refuted"). → Fix: hourly → every 4h. Saves ~$12/30d.

3. **Health-monitor duplicates `pipeline_watchdog.py`** (runs every 2 min, does lock-freshness + stall detection + auto-restart). Its own logs: "system healthy, no WARN/CRITICAL", "No files changed", 2 commits/7d. → Fix: deterministic script + alert-on-anomaly. Saves ~$3.50/30d.

4. **Context gate spawns a full opencode agent for a one-word verdict, SYNCHRONOUSLY in the trade hot-path** (35s timeout). Verdicts all-time: NAY=75, WARN=5, GO=0, FLIP=0 (disabled 2026-08-01). **18 timeouts = 18 × 35s pipeline stalls.** Every prompt criterion (speed %, z-score, RSI) already computed by `rule_based_context_gate()`. → Fix: encode rules deterministically, delete LLM call. Removes hot-path latency.

5. **Summarizer** writes 141 files to `automation/summaries/`, referenced by exactly one consumer. → Fix: delete. Saves $0.67.

6. **CEO MoE panel is dead** — `systemctl list-timers hermes-moe-panel.timer` → 0 timers listed. `automation/moe-panel/reports/` is empty (prompt writes to `reports/` relative to cwd → lands in `/root/.hermes/reports/`). Last run Oct 14. → Fix: fix path or delete unit.

7. **Fleet redundancy** — health-monitor + auto-1hr + brain-auditor all check pipeline health/trades; signal-reporter + auto-1hr both do signal performance; upgrade-implementer + orchestrator both scan `plans/`. → Fix: merge auto_1hr→signal-reporter, upgrade-implementer→orchestrator. Saves ~$1.50, removes two overlapping "who may edit constants" writers.

## RECOMMENDED TRIM

| Action | Saves/30d | Risk |
|---|---|---|
| Watchdog: skip LLM when open_count==0 | ~$9.00 | Low |
| Brain-auditor: hourly → 4h | ~$12.00 | Low |
| Health-monitor → deterministic | ~$3.50 | Low |
| Delete summarizer | $0.67 | None |
| Merge upgrade-implementer + orchestrator | ~$1.10 | Medium |
| Merge auto-1hr + signal-reporter | ~$0.70 | Medium |
| Fix/delete MoE | $0.33 | None (already broken) |
| **Total** | **~$27 (50%)** | |

Plus context-gate rules conversion (removes 18×35s stalls + all hot-path LLM latency).

## WHAT I WANT FROM YOU

1. VERDICT on each of the 7 items (approve/reject/modify).
2. Which merges are you comfortable authorizing — the two "Medium" risk ones each collapse two writers into one, which touches who can edit `hermes_constants.py`.
3. Any component I've misjudged — e.g. is brain-auditor's hourly cadence load-bearing for something I can't see from the logs?
4. Ordering: what should ship first?

## CAVEATS

- Dollar figures assume linear scaling of measured session costs; real savings slightly lower.
- Watchdog zero-open rate inferred from git history (60 snapshots/7d), not a complete log.
- No changes made. Analysis only.

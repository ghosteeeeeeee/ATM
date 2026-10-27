# LLM Usage Analysis — Automation Team Trim Review

**Date:** 2026-10-27
**Method:** Direct queries against `opencode.db` (session/token/cost), systemd unit inspection, pipeline + agent logs, git history.
**Window:** 30 days unless noted.

---

## TLDR

LLM usage is **~$54.67 / 4,475 sessions / 30 days**. Two components — **trade-watchdog** and **brain-auditor** — are **67% of total spend**. The three biggest trim targets:

1. **Watchdog runs its LLM unconditionally** — 45% of cycles had **zero open trades**. Deterministic step already produced the data.
2. **Brain-auditor runs hourly** with the largest per-run footprint; most findings are re-refutations of the same KPIs.
3. **Health-monitor duplicates** what `pipeline_watchdog.py` already does every 2 minutes.

Realistic cut: **~50% of spend**, plus removal of 18×35s pipeline stalls from the context gate.

---

## Where the spend goes (30 days)

| Component | Sessions | Tokens (in+out) | Cost | Share |
|---|---|---|---|---|
| **trade-watchdog** | 1,367 | 94.7M | **$20.30** | 37% |
| **brain-auditor** | 619 | 64.5M | **$16.61** | 30% |
| health-monitor | 691 | 18.4M | $4.10 | 7.5% |
| other | 507 | 19.4M | $4.54 | 8% |
| auto-1hr | 665 | 10.5M | $2.39 | 4% |
| upgrade-implementer | 59 | 5.5M | $1.31 | 2% |
| signal-reporter | 114 | 5.2M | $1.28 | 2% |
| orchestrator | 57 | 4.8M | $1.12 | 2% |
| subagents | 94 | 4.9M | $1.09 | 2% |
| summarizer | 56 | 3.3M | $0.67 | 1% |
| ceo-status | 85 | 2.5M | $0.43 | 1% |
| **ctx-gate-llm** | 119 | 1.9M | $0.40 | 1% |
| ceo-moe | 27 | 1.7M | $0.33 | — |
| ceo-deep | 11 | 0.2M | $0.04 | — |

**Totals:** 209M input + 28.5M output + 3.68B cache-read tokens.

**94.6% of input tokens are cache-reads** — every session drags the same 22KB `AGENTS.md` + repo context. Cache pricing is cheap, but it means the lever is **fewer sessions, not smaller prompts.**

Total agent-driven git commits in 7 days: **532** (brain_auditor 124, watchdog 56, auto_1hr 21).

---

## The churn, ranked by waste

### 1. Watchdog fires its LLM unconditionally — 45% of cycles have no open trades — $20.30

`run_watchdog.sh` runs deterministic `trade_watchdog.py` (1,936 lines) first, then **always** spawns a 480s opencode agent to re-read that same JSON and write prose. The prompt itself says *"The Python watchdog has ALREADY run… DO NOT re-run it. Just read the outputs."*

`open_count` reconstructed across 60 historical snapshots of `watchdog_recommendations.json` (7d):

```
27 cycles → 0 open trades   (45%)
18 cycles → 1
10 cycles → 2
 5 cycles → 3
```

Each cycle burned a full session (avg 69k tokens + 880k cache-read) regardless. Also the #2 committer (56 commits/7d), frequently force-adding gitignored `data/watchdog_recommendations.json`.

**Fix:** gate Step 2 on `open_count > 0` — `trade_watchdog.py` already writes it (line 1676). Saves ~$9/30d, drops 48 sessions/day of overhead.

### 2. Brain-auditor hourly with largest footprint — $16.61

619 sessions at ~104k tokens + **2.19M cache-read each** — biggest per-run cost of any component. Most prolific committer (124 commits/7d), but `changes_log.json` shows work is largely re-refuting the same findings: *"wrong-side refuted 105th"*, *"watchdog best-cells refuted"*, *"autopsy 104th refuted"*.

**Fix:** drop to every 3–4h. Saves ~$12/30d with minimal loss.

### 3. Health-monitor duplicates a 2-minute deterministic script — $4.10

`pipeline_watchdog.py` runs every 2 min and already does lock-freshness, stall detection, and auto-restart. The hourly LLM session runs `systemctl is-active`, `df -h`, journalctl greps — its own logs confirm the outcome: *"system healthy, no WARN/CRITICAL issues"*, *"No files changed"*, 2 commits in 7 days.

**Fix:** deterministic script + alert-on-anomaly; invoke LLM only when something breaks. Saves ~$3.50/30d.

### 4. Context gate spawns a full agent for a one-word verdict — small $, big operational cost

`llm_context_gate()` shells out to `opencode run` **synchronously in the trade execution hot-path** (35s timeout). Verdict distribution across all logs:

```
LLM NAY:  75      LLM WARN:  5      LLM GO:  0      LLM FLIP: 0 (disabled 2026-08-01)
```

It never returns GO. FLIP was disabled for inverting 31% of trades. **18 recorded timeouts = 18 × 35s pipeline stalls.** Every criterion in its prompt (speed %, z-score, live RSI) is already computed by `rule_based_context_gate()`.

**Fix:** encode the 5 NAY rules + WARN penalty deterministically, delete the LLM call. Removes all hot-path LLM latency — operational win far exceeding the $0.40.

### 5. Summarizer writes reports nothing reads — $0.67

141 files in `automation/summaries/`. Referenced by exactly one consumer. An LLM reading other LLMs' journald output. **Fix:** delete.

### 6. CEO MoE panel is dead and misrouted — $0.33

`systemctl list-timers hermes-moe-panel.timer` → **0 timers listed** (not firing). `automation/moe-panel/reports/` is **empty** — prompt writes to `reports/` relative to cwd, so output lands in `/root/.hermes/reports/`. Last real run Oct 14. **Fix:** fix path or delete unit.

### 7. Fleet redundancy

- `health-monitor` + `auto-1hr` + `brain-auditor` all check pipeline health + trade performance
- `signal-reporter` + `auto-1hr` both compute signal performance
- `upgrade-implementer` + `orchestrator` both scan `plans/` and implement

**Fix:** merge auto-1hr into signal-reporter; merge upgrade-implementer into orchestrator. Saves ~$1.50, removes two overlapping "who may edit constants" writers.

---

## Recommended trim

| Action | Saves/30d | Risk |
|---|---|---|
| Watchdog: skip LLM when `open_count == 0` | ~$9.00 | Low — deterministic steers still emitted |
| Brain-auditor: hourly → every 4h | ~$12.00 | Low — findings mostly re-confirmations |
| Health-monitor → deterministic + alert-on-fail | ~$3.50 | Low — `pipeline_watchdog.py` covers it |
| Delete summarizer | $0.67 | None |
| Merge upgrade-implementer + orchestrator | ~$1.10 | Medium — two writers become one |
| Merge auto-1hr + signal-reporter | ~$0.70 | Medium |
| Fix/delete MoE | $0.33 | None (already broken) |
| **Total** | **~$27 (50%)** | |

Plus context-gate rules conversion: **removes 18×35s pipeline stall and all hot-path LLM latency.**

---

## Caveats

- Dollar figures are arithmetic on measured session costs assuming linear scaling; real savings slightly lower from fixed per-session overhead.
- Watchdog zero-open-trades rate inferred from git history of `watchdog_recommendations.json` (60 snapshots over 7d), not a complete log.
- No changes have been made. This is analysis only.

---

# CEO VERDICT (consult run 2026-10-27, 1800s budget, `ok rc=0`)

> Consult brief: `automation/ceo/brief-llm-usage-trim-2026-10-27.md`
> Full transcript: `logs/ceo/consult-20261027T*.jsonl`

## Overall: APPROVE with 3 modifications

CEO independently re-verified the numbers: opencode.db 30d = **4,477 sessions / $54.67 / 209M in / 28.5M out / 3.68B cache-read** (exact match). trade-watchdog $20.30 + brain-auditor $16.64 = **67.6%**. Git commits 7d = **531**. CTX-GATE verdicts **75 NAY / 5 WARN / 0 GO** ✓. Watchdog zero-open re-measured on a larger sample: **78/178 = 44%** (report used n=60) — claim holds.

### Per-item verdicts

| # | Item | Verdict |
|---|---|---|
| 1 | Watchdog gate on `open_count==0` | **APPROVE** |
| 2 | Brain-auditor hourly→4h | **MODIFY** |
| 3 | Health-monitor → deterministic | **APPROVE** |
| 4 | Context-gate rules conversion | **APPROVE, shadow-first** |
| 5 | Delete summarizer | **APPROVE** |
| 6 | Fix/delete MoE | **APPROVE (delete)** |
| 7 | Two merges | **1 authorize / 1 modify direction** |

**1. Watchdog — approve.** `run_watchdog.sh:56` runs Step 2 unconditionally after Step 1; `trade_watchdog.py:1676` writes `open_count`. Gate is ~3 lines reading the JSON Step 1 just wrote. Caveat: a trade can open seconds after Step 1 — next cycle is 30min away, deterministic steers still run each cycle, so exposure is acceptable. Skip also loses agent prose (`deep_analysis`/`pattern_alerts`, dropped >60min anyway per `trade_watchdog.py:1683-1693`) — consumers are dashboard + auditor, cosmetic.

**2. Brain-auditor — MODIFY, not plain 4h.** The "mostly re-refutations" reading understates load-bearing functions found in `ceo_kanban.md`: #102 found the waiver-expiry gate had **no code path at all**; #103 caught a **4.4x unit-inflation** in a queued CEO GO; #185 retracted a false-positive "math bug". Also cadence-dependent semantics break silently at 4h: (a) tripwires pre-registered as "2 consecutive runs" become 8h windows; (b) time-boxed checkpoints (17:12Z formal) need hourly-or-finer; (c) `LAST-RUN VERIFY` is the system's regression detector. **Required companions:** re-register tripwires with explicit time windows; add a ~10-line deterministic hourly verify (constants git diff, CEO_PROTECTED count, kill flags, traceback count); one-shot `OnCalendar` timer for time-boxed checkpoints. With those: approve 4h, ~$12.

**3. Health-monitor — approve.** `pipeline_watchdog.py` (every 2min, `hermes-watchdog.timer`) already does lock/stall/auto-restart with vacation-pause awareness. Health-monitor's unique residue (disk, journal scan, price-collector/1m-candle liveness) is scriptable. Note: the LLM auto-fixer **violated the vacation pause on 2026-10-15** — deterministic is *safer*, not just cheaper. Port checks before deleting.

**4. Context gate — approve, shadow-first mandatory.** Verified: synchronous `subprocess.run` with `timeout=35` at `decider_run.py:1628`, called hot-path at `:2125`; fail-open on timeout (`hermes_constants.py:884`); 300s verdict cache (`:882`) already dampens latency (report missed this). The LLM's job is to **NAY trades the rule gate passed** — 75 logged NAYs. A literal port of the prompt's 5 NAY rules will not reproduce "default NAY when uncertain". Ship rules in shadow beside the LLM for 1-2 weeks, measure NAY-rate agreement, then flip.

**5. Summarizer — approve delete.** Zero consumers of `automation/summaries/`. $0.67.

**6. MoE — approve delete.** `hermes-moe-panel.timer` **not-found** in systemd (unit file only in `config/`), `automation/moe-panel/reports/` empty, last run Oct 14. Delete units; keep the `mixture-of-experts` skill (separate, manual).

### Merges

- **upgrade-implementer + orchestrator: AUTHORIZE, conditioned.** Both run 12h, both scan `plans/`. Merge into **orchestrator** — its prompt already has the stricter authority rules ("Do NOT disable/enable signals, only implement CEO's decision"), so the merged unit is *safer*. Condition: single explicit "who may edit constants" section; all constants-*value* changes CEO-gated; check plan-implementation throughput for 1 week.
- **auto-1hr + signal-reporter: MODIFY — reverse the direction.** Folding auto-1hr → signal-reporter is backwards: auto-1hr is the **hourly** actor feeding `recent_changes.log` (read by CEO runs); signal-reporter is a deeper **6h** actor. Collapsing to 6h loses kill-detection latency (a bad signal burns trades for 6h); folding the deep prompt into an hourly agent likely **costs more than it saves** (~$7.9 vs the pair's current $3.76). Also: a **deterministic** `hermes-signal-report.timer` (python, 6h) already exists alongside the LLM one — the LLM reporter is the redundant half. **Authorized form:** disable the signal-reporter LLM timer, port its unique rules (boost criteria, NO-INVERSIONS check, regime-block verification) into `auto_1hr_prompt.md`, keep auto-1hr hourly. Saves ~$1.28, one constants writer, no cadence loss.

### Misjudgments flagged

- Brain-auditor hourly is partially load-bearing — 4h fine only with three companions.
- Merge direction on auto-1hr/signal-reporter is wrong as written.
- Ctx-gate stall count overstated (13 in pipeline.log, Oct 11–14 cluster); the 300s cache was missed.
- Everything else — watchdog 44% zero-open, spend table, health-monitor duplication, summarizer dead, MoE dead — **verified accurate**.

### Ordering

1. **Day 1 (~$10, near-zero risk):** watchdog `open_count` gate → delete summarizer → delete MoE units.
2. **Day 1–2 (~$3.50):** health-monitor → deterministic (port disk/timer-liveness/pause checks first).
3. **Day 2–3 (~$12):** brain-auditor 4h **with** tripwire re-registration + deterministic hourly verify + checkpoint one-shot timer.
4. **Week 1 (careful):** context-gate rules conversion **in shadow** — no live flip until verdict agreement measured.
5. **Last (medium risk):** orchestrator absorbs upgrade-implementer; signal-reporter folds into auto-1hr.

Realistic total **~$26–28/30d**. Fixed per-session overhead means expect ~10% less.

# Automation & Self-Learning System Audit — 2026-08-22 01:50 UTC

## Executive Summary

Hermes has a **massive** automation and self-learning infrastructure: **45+ systemd timers**, **3 learning engines** (self_learner, hebbian, A/B), **5 quality gates** (entry, volatility, Monte Carlo, decay detector, signal rotator), and **6 LLM-powered automation agents** (CEO, orchestrator, auto-1hr, bug hunter, summarizer, upgrade implementer). The system is functional but has significant redundancy, blind spots, and missed opportunities.

**Current performance (from goal_progress.json):**
- Win rate 30d: **48.1%** (target: 40% ✅)
- Sharpe 30d: **-0.06** (target: 1.0 ❌)
- PnL 30d: **-$3.62** (target: positive ❌)
- Total trades 30d: **1,173**
- Consecutive losses: **4**

---

## 1. SELF-LEARNING ENGINES

### 1a. self_learner.py — Parameter Optimization (Daily at 06:00 UTC)
**Status: ✅ ACTIVE — but limited scope**

**What it does:**
- Analyzes 4 signal types (bb_bounce, pattern_wolf, accel_300, tl_break)
- Adjusts ONE parameter at a time (TREND_FILTER_NEUTRAL_PCT) in 5% steps
- Kills underperforming signals (50T PnL < -$2 OR 10+ consecutive losses)
- Tunes combo weights (boost/suppress based on 7d WR)
- Writes goal_progress.json for CEO/other agents to read

**Issues found:**
1. **Only 4 signal types analyzed** — 40+ signals exist but only 4 get param tuning
2. **Only 1 parameter tuned** (TREND_FILTER_NEUTRAL_PCT) — all other PARAM_CONFIG entries never hit
3. **Pattern_wolf has only 6 trades** — permanently below MIN_TRADES_BETWEEN (15), never tuned
4. **No outcome tracking of adjustments** — doesn't measure if previous adjustments helped
5. **Combo weight analysis skips disabled signals** — but disabled signals could be re-enabled if combo partner improves

**Key finding from self_learning_log.json:** The TREND_FILTER_NEUTRAL_PCT has been oscillating between 0.24-0.30 for weeks, bouncing between tighten and loosen. The learner is stuck in a local optimum — no other parameter is ever tested.

### 1b. hebbian_learner.py + hebbian_session_learner.py — Associative Memory
**Status: ✅ ACTIVE — but session learner is starved**

**What it does:**
- Seeds concept network from brain/*.md files and key scripts
- Learns co-occurrences from session dumps and event logs
- 1,915 nodes, 25,266 synapses in associative_memory.db
- Daily decay at 0.999x (elephant memory)

**Issues found:**
1. **Session learner learned 0 pairs on Aug 21** — "Processed 0 session turns, Learned 0 event pairs"
2. **Session dumps may not exist** — the learner reads `sessions/request_dump_*.json` but finds nothing
3. **Event log may be empty** — reads `data/event-log.jsonl` but gets nothing
4. **No feedback loop** — hebbian network is never queried by trading logic (entry_gates, signal_compactor, etc.)
5. **Decay log is 43KB of repetitive entries** — the decay detector runs but mostly says "SKIP" or "already False"

### 1c. ab_learner.py — A/B Testing & Trade Pattern Learning
**Status: ⚠️ DEFUNCT — uses psycopg2/PostgreSQL but no timer**

**What it does:**
- Analyzes SL distances per token
- Computes token regime performance
- Writes trade_patterns.json + trade_patterns table in brain DB

**Issues found:**
1. **No systemd timer** — not in the timer list, never runs automatically
2. **Uses psycopg2 (PostgreSQL)** — different DB from the SQLite-based self_learner (data silo)
3. **Writes to `/var/www/hermes/data/trade_patterns.json`** — output file exists but is stale
4. **A/B testing may be disabled** — checks `config/ab_tests.json` which may have `enabled: false`

---

## 2. SIGNAL QUALITY GATES

### 2a. entry_gates.py — Pre-Signal Filters
**Status: ✅ ACTIVE — called by every signal**

Four gates: R:R pre-check, volume filter, candle close validation, session timing. All fail-open (missing data = pass).

### 2b. volatility_gate.py — Regime-Signal Matching
**Status: ✅ ACTIVE — maps ATR% to signal categories**

FLAT/NORMAL/HIGH/EXTREME regimes with curated signal sets per regime. Data-driven from 30d backtest (861 trades).

### 2c. monte_carlo_gate.py — Statistical Decay Detection
**Status: ✅ ACTIVE — blocks unprofitable signal/direction pairs**

1000 Monte Carlo resamples, P(profit) must exceed 35% to allow trades. 5-minute cache.

### 2d. signal_decay_detector.py — Auto-Disable Decaying Signals (6h)
**Status: ✅ ACTIVE — but conservative**

- Hard block: WR < 20% with 3+ trades
- Soft block: WR < 30% with 5+ trades
- **Problem: flag_map is hardcoded** — new signals with new names can't be disabled
- **Problem: decay_log.md is 608 lines of mostly "SKIP" entries** — overhead for little action

### 2e. signal_rotator.py — Regime-Aware Signal Selection (4h)
**Status: ✅ ACTIVE — reads audit + regime data**

- Max 2 changes per cycle
- Never disables signals with WR > 50%
- Never enables signals with WR < 35%
- Writes signal_rotation.md + signal_rotation.json

**Issues found:**
1. **REGIME_SIGNAL_AFFINITY is static** — hardcoded boost/penalize lists, not learned from outcomes
2. **Overlap with self_learner kill logic** — both systems disable signals but use different thresholds
3. **Overlap with decay_detector** — three systems all trying to kill bad signals

---

## 3. LLM-POWERED AUTOMATION AGENTS

### 3a. CEO (hermes-ceo.timer — currently DISABLED/stale)
**Status: ⚠️ LAST RUN 6 DAYS AGO (Aug 15)**

The CEO timer exists but last triggered was 6 days ago. This is the strategic decision-maker.

### 3b. Daily Orchestrator (hermes-daily-orchestrator.timer — every 12h)
**Status: ✅ ACTIVE — runs implementation pipeline**

Reads CEO recommendations, implements changes, validates, reports.

### 3c. Auto-1hr (hermes-auto-1hr.timer — hourly)
**Status: ✅ ACTIVE — hourly trade analysis + auto-fix**

Queries PostgreSQL, diagnoses issues, makes fixes. Max 1 change per hour.

### 3d. Health Monitor (hermes-health-monitor.timer — every 20min)
**Status: ✅ ACTIVE — pipeline health + auto-fix**

### 3e. Bug Hunter (hermes-bug-hunter.timer — every 8h)
**Status: ✅ ACTIVE — system verification + code bug scanner**

### 3f. Summarizer (hermes-summarizer.timer — every 12h)
**Status: ✅ ACTIVE — summarizes automation results**

---

## 4. CONTEXT & MEMORY INFRASTRUCTURE

### 4a. context-compactor.py (every 30min)
**Status: ✅ ACTIVE — patches CONTEXT.md with live status**

### 4b. hermes-brain-sync.py (daily at 05:00 UTC)
**Status: ⚠️ STUB — most functions are TODO**

- `audit_find_stale()` → `# TODO: implement`
- `check_kanban_sync()` → `# TODO: implement`
- Only appends to ideas.md

### 4c. graphify-update (daily at 06:00 UTC)
**Status: ✅ ACTIVE — AST knowledge graph update**

### 4d. error_analyzer.py (every 1h)
**Status: ✅ ACTIVE — scans pipeline logs for recurring errors**

---

## 5. CRITICAL GAPS & ISSUES

### 🔴 GAP 1: No Closed-Loop Feedback
The self_learner adjusts parameters but **never measures if previous adjustments helped**. The log shows TREND_FILTER_NEUTRAL_PCT bouncing up/down for weeks. There's no A/B comparison of "before vs after" wr/pnl.

### 🔴 GAP 2: Session Learner Starvation
The hebbian_session_learner learned **0 pairs** on its last run. The session dumps and event log it reads appear empty. The hebbian network is frozen at 1,915 nodes since seeding.

### 🔴 GAP 3: A/B Learner is Dead
ab_learner.py has no timer, uses a different DB (PostgreSQL), and checks a config that may disable it. Its trade pattern analysis never runs.

### 🔴 GAP 4: Three Overlapping Kill Systems
- self_learner kills signals with 50T PnL < -$2 or 10+ consecutive losses
- signal_decay_detector kills signals with WR < 20% (3 trades) or < 30% (5 trades)
- signal_rotator disables signals based on audit scores

These can fight each other (one enables, another disables) and use different thresholds for the same signals.

### 🔴 GAP 5: CEO Timer is Dead
Last ran 6 days ago (Aug 15). The strategic brain of the system hasn't been active.

### 🟡 GAP 6: Hebbian Network Never Consumed
1,915 nodes and 25,266 synapses exist in associative_memory.db, but **no trading script queries it**. The network is built but never used for decisions.

### 🟡 GAP 7: 43KB Decay Log (Noise)
decay_log.md has 608 lines of repetitive "SKIP: already False" entries. The detector runs but mostly does nothing useful. Log rotation missing.

### 🟡 GAP 8: brain_sync is a Stub
hermes-brain-sync.py has TODO comments for its main functions. It runs daily but only appends to ideas.md.

### 🟡 GAP 9: Combo Weight Blind Spots
Combo weights are tuned but some high-performing combos are marked DISABLED (return_exhaustion_long at WR=67% with edge 0.409). The self_learner skips disabled signals even when their combo weight analysis is relevant.

### 🟡 GAP 10: No Market Regime Learning
The volatility_gate has static regime-signal mappings from Aug 11. These should be re-backtested periodically as market conditions change.

---

## 6. RECOMMENDATIONS

### Priority 1: Close the Feedback Loop (self_learner)
**Add outcome tracking to parameter adjustments.** Before adjusting a parameter, record the current WR/PnL. After N trades, measure if it improved. If not, revert. This stops the oscillation.

```python
# In self_learner.py, add:
# 1. Record baseline before adjustment
# 2. After 15+ trades post-adjustment, measure delta
# 3. If delta negative, revert to previous value
```

### Priority 2: Unify Kill Systems
**Merge self_learner kill, decay_detector kill, and signal_rotator disable into ONE system.** Pick the best thresholds from each and use a single script. Currently they can conflict.

### Priority 3: Fix Session Learner
Check why session dumps are empty. Either:
- Ensure session dumps are being written (check if sessions/ directory gets request_dump_*.json files)
- Switch to reading from a different source (event-log.jsonl, trade outcomes)
- Or feed hebbian from trade_outcomes directly (token + signal co-occurrences from winning trades)

### Priority 4: Revive CEO Timer
Check why hermes-ceo.timer stopped. If it was manually disabled, re-enable. If the service is failing, fix it. The CEO is the strategic layer that other automations depend on.

### Priority 5: Connect Hebbian to Trading
The associative memory should influence decisions:
- Query hebbian network in entry_gates.py: "does this token+signal combo have strong associations?"
- Use hebbian for context: when signal_compactor evaluates a trade, look up related concepts
- Feed hebbian with trade outcomes: winning trades strengthen token↔signal edges

### Priority 6: Restart A/B Learner
Either:
- Add a systemd timer for ab_learner.py
- Or migrate its logic into self_learner.py (since self_learner already handles combo weights)
- The SL distance analysis and token regime analysis are valuable — they just never run

### Priority 7: Periodic Regime Re-Backtest
Every 7 days, re-run the volatility_gate backtest against the last 30 days of data. Update REGIME_SIGNALS dynamically instead of hardcoded sets.

### Priority 8: Clean Up Decay Log
- Add log rotation to decay_log.md (keep last 7 days)
- Reduce noise: only log actual actions, not "SKIP: already False" repeated entries
- Consider making decay_detector conditional: only run if last run was >4h ago

### Priority 9: Implement brain_sync Functions
The TODO stubs in hermes-brain-sync.py should be implemented:
- `audit_find_stale()` — find tasks blocked > 7 days
- `check_kanban_sync()` — verify TASKS.md and kanban.json are in sync

### Priority 10: Expand Parameter Tuning
self_learner.py only tunes 4 signals and 1 real parameter. Expand:
- Add more signals to the tuning list (r2-trend-long variants, wave_catcher, etc.)
- Add more parameters (SL multiplier, TP targets, confidence thresholds)
- Consider Bayesian optimization instead of fixed 5% steps

---

## 7. TIMER HEALTH SUMMARY

| Timer | Frequency | Status | Last Run | Notes |
|-------|-----------|--------|----------|-------|
| hermes-self-learner | Daily 06:00 | ✅ | Aug 21 | Running, but limited scope |
| hermes-session-learner | Daily 06:00 | ⚠️ | Aug 21 | Learned 0 pairs (starved) |
| hermes-hebbian-decay | Daily 04:00 | ✅ | Aug 21 | Fading old synapses |
| hermes-brain-sync | Daily 05:00 | ⚠️ | Aug 21 | Mostly TODO stubs |
| hermes-auto-1hr | Hourly | ✅ | Aug 22 | Active |
| hermes-health-monitor | Every 20min | ✅ | Aug 22 | Active |
| hermes-error-analyzer | Hourly | ✅ | Aug 22 | Active |
| hermes-bug-hunter | Every 8h | ✅ | Aug 21 | Active |
| hermes-signal-rotator | Every 4h | ✅ | Aug 22 | Active |
| hermes-signal-decay-detector | Every 6h | ✅ | Aug 22 | Active but noisy |
| hermes-context-compactor | Every 30min | ✅ | Aug 22 | Active |
| hermes-better-coder | Every 30min | ✅ | Aug 22 | Active |
| hermes-ceo | Daily | 🔴 | Aug 15 | DEAD — 6 days stale |
| hermes-graphify-update | Daily 06:00 | ✅ | Aug 22 | Active |
| hermes-daily-orchestrator | Every 12h | ✅ | Aug 22 | Active |
| hermes-blacklist-tester | Daily | ✅ | Aug 22 | Active |
| hermes-summarizer | Every 12h | ✅ | Aug 22 | Active |
| hermes-upgrade-implementer | Every 12h | ✅ | Aug 22 | Active |
| hermes-signal-reporter | Every 6h | ✅ | Aug 22 | Active |
| hermes-daily-commit | Daily 07:15 | ✅ | Aug 21 | Active |

---

## 8. DATABASE SILO PROBLEM

| System | Database | Type |
|--------|----------|------|
| self_learner | signals_hermes_runtime.db | SQLite |
| hebbian_engine | brain/associative_memory.db | SQLite |
| ab_learner | PostgreSQL (brain) | PostgreSQL |
| entry_gates | atr_cache.json | JSON |
| monte_carlo_gate | signals_hermes_runtime.db | SQLite |
| volatility_gate | candles.db | SQLite |

**Three different DB technologies** for learning systems that should share data. The A/B learner in PostgreSQL can't talk to the self_learner in SQLite. Consider unifying on PostgreSQL or adding a sync layer.

---

*Audit completed: 2026-08-22 01:50 UTC*
*Auditor: DSH autonomous audit*

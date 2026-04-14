# Hermes Trading System — ML/Pipeline Audit Report
**Date:** 2026-04-13 14:03 UTC  
**Auditor:** Hermes Agent (Full Pipeline Analysis)  
**Classification:** Internal — Critical System Review

---

## Executive Summary

**Overall Pipeline Health: 58/100 (MODERATE-LOW)**

The Hermes trading system is operational with live trading enabled, but has several critical failures and systemic issues that require immediate attention. Price data is fresh, signal generation is producing signals, but the execution feedback loop is broken, the ML components are significantly underperforming, and the PostgreSQL brain DB has been unreachable for 15+ hours.

### Key Findings

| Component | Status | Score | Critical Issues |
|-----------|--------|-------|----------------|
| Data Pipeline | ⚠️ FRESH | 75/100 | Price data 10s old (good); PostgreSQL unreachable (CRITICAL) |
| Signal Generation | ⚠️ WORKING | 68/100 | 5620 signals; SHORT bias 62/38; thresholds recently adjusted |
| Hot-Set / AI Decider | 🔴 BROKEN | 40/100 | 37min gap; only 5 LONG entries; decisions table empty |
| Execution (Guardian) | 🔴 BROKEN | 35/100 | PostgreSQL unreachable; decisions table 0 rows |
| ML: Candle Predictor | 🔴 FAILED | 15/100 | 38% accuracy (136K predictions) — BELOW RANDOM |
| ML: MTF-MACD Tuner | ⚠️ UNCERTAIN | 55/100 | 124 token configs; 11 backtest runs; unclear if applied |
| Regime Detection | 🔴 BIASED | 30/100 | 106 SHORT_BIAS vs 6 LONG_BIAS — structurally broken |
| Position Management | ⚠️ PARTIAL | 60/100 | ATR SL/TP working; CASCADE_FLIP disabled; stale tracking unknown |

### Priority Action Items
1. **[CRITICAL]** PostgreSQL brain DB unreachable — entire position tracking is blind
2. **[CRITICAL]** Decisions table has 0 rows — execution loop is untracked
3. **[CRITICAL]** Candle predictor 38% accuracy — model is broken, recommend disable
4. **[HIGH]** ai_decider 37min gap — hotset.json stale
5. **[HIGH]** Regime detector 106:6 SHORT_BIAS ratio — structurally biased

---

## 1. Data Pipeline Analysis

### 1.1 Price Data Health ✅ WORKING

| Metric | Value | Assessment |
|--------|-------|------------|
| Price history rows | 378,420 | Adequate |
| Distinct tokens | 190 | Good coverage |
| Latest price age | 10 seconds | EXCELLENT |
| Price history range | 2024-01-09 to 2026-04-13 | 2+ years |
| Rows per token (avg) | ~2,000 | Reasonable |

**Status: HEALTHY** — Price data is fresh (10 second lag), backfill is working, 190 tokens covered.

### 1.2 Database State

**signals_hermes_runtime.db (Runtime):**
| Table | Rows | Issue |
|-------|------|-------|
| signals | 5,620 | OK |
| signal_history | 0 | 🔴 NEVER WRITTEN |
| token_speeds | 0 | 🔴 NEVER WRITTEN |
| decisions | 0 | 🔴 CRITICAL — nothing written |
| signal_outcomes | 6 | ⚠️ Very few |
| momentum_cache | 171 | OK |
| token_intel | 0 | 🔴 Never populated |
| cooldown_tracker | 0 | 🔴 Never populated |

**signals_hermes.db (Static):**
| Table | Rows | Assessment |
|-------|------|------------|
| price_history | 378,420 | Healthy |
| latest_prices | 190 | Fresh |
| regime_log | 113 | ⚠️ SHORT_BIAS dominated |
| ohlcv_1m | 17,760 | OK |

### 1.3 PostgreSQL Brain DB — CRITICAL FAILURE

```
psycopg2.error: could not connect to server at "10.60.185.99", port 5432
Connection timed out (15+ hours estimated)
```

**Impact:**
- `decider_run.py` cannot read open positions → no position limit enforcement
- `cleanup_stale_signals()` cannot block signals for open positions
- Position tracking is completely blind
- `decisions` table has 0 rows — nothing is being written
- Win rate tracking for `signal_outcomes` only has 6 entries (should be hundreds)

### 1.4 Z-Score Calculations — Statistically Valid

```python
ZSCORE_HISTORY = 200  # ~3.3 days at 1m candles
# Uses rolling 20-bar windows for z-score percentile computation
```

**Assessment:** Z-score computation uses standard stdev/mean approach. Window of 200 is reasonable for 1m data. Phase detection thresholds (60/75/88/95) are well-calibrated.

**Issues:**
- `compute_zscore_percentile()` uses a subsampling approach (step = len//100) which may introduce approximation errors
- Z-score velocity uses `ago = min(60, len(prices)//4)` which varies with token history length

---

## 2. Signal Generation Analysis

### 2.1 Signal Volume & Distribution

**Total Signals:** 5,620

| Decision | Count | % | Assessment |
|----------|-------|---|------------|
| EXPIRED | 2,270 | 40% | Normal — signals not acted upon |
| SKIPPED | 1,491 | 27% | High — many filtered by AI decider |
| WAIT | 815 | 14% | ⚠️ Backlog — signals piling up |
| REJECTED | 708 | 13% | AI decided not to trade |
| EXECUTED | 217 | 4% | Traded — low execution rate |
| PENDING | 89 | 2% | Awaiting review |
| APPROVED | 21 | <1% | Ready to trade |
| COMPACTED | 9 | <1% | Processed by AI |

**Direction:** SHORT: 3,488 (62%) | LONG: 2,132 (38%)

**Confidence Distribution:**
| Bucket | Count |
|--------|-------|
| 80+ | 3,513 (63%) |
| 70-79 | 839 (15%) |
| 60-69 | 508 (9%) |
| 50-59 | 760 (14%) |

### 2.2 Signal Thresholds (Current)

```python
ENTRY_THRESHOLD = 60        # LONG
SHORT_ENTRY_THRESHOLD = 60  # SHORT (was 70, unified at 60 on 2026-04-12)
AI_DECIDER_THRESHOLD = 65
AUTO_APPROVE = 95
CONFLUENCE_AUTO_APPROVE = 85
```

**Recent Changes (2026-04-12):**
- ENTRY_THRESHOLD: 50 → 60 (raised to reduce noise)
- SHORT_ENTRY_THRESHOLD: 72 → 60 (unified)
- ZSCORE_HISTORY: 500 → 200 (reduced)
- BROAD_UPTEND_Z: +0.0 → +0.5 (added uptrend filter for LONGs)

**Assessment:** Recent threshold changes appear designed to fix pipeline breakage from insufficient price history (ZSCORE_HISTORY=500 was too large for the available data). Current thresholds are more conservative.

### 2.3 Signal Hit Rate Analysis

| Signal Type | Executed | Total | Hit Rate |
|-------------|----------|-------|----------|
| percentile_rank | 150 | ~2,400 | 6.3% |
| mtf_zscore | 25 | ~1,200 | 2.1% |
| rsi_individual | 16 | ~500 | 3.2% |
| velocity | 15 | ~1,100 | 1.4% |
| momentum | 0 | ~20 | 0% |

**Observation:** Execution rate is extremely low (217/5,620 = 3.9%). Most signals are filtered out by AI decider or expire before execution. This could be:
1. **Good:** Strict filtering catching weak signals
2. **Bad:** Thresholds too high, missing valid opportunities

### 2.4 Signal Type Quality Issues

**Problem:** `percentile_rank` signals dominate (1049 EXPIRED + 692 SKIPPED + 403 WAIT = 2,144). This signal type is flooding the pipeline.

The `pct_rank_score_fn` scoring formula has a complex structure that may not align well with actual price behavior. The distinction between "bull regime" and "neutral/bear" multipliers may be causing systematic bias toward SHORT signals.

---

## 3. Hot-Set & AI Decider Analysis

### 3.1 Hotset State

```
hotset.json last modified: 2026-04-13 13:38:16
Age: 25+ minutes (should be <10)
Entries: 5 (should be 20)
Direction: ALL LONG (AVAX, SKY, STRK, AAVE, IMX)
```

**CRITICAL:** The hotset has only 5 entries and all are LONG. Per TASKS.md, the hotset was SHORT-only at 04:28. This dramatic directional shift is suspicious and may indicate:
1. Regime detector bias pushing all SHORTs into WAIT/REJECTED
2. AI decider LLM prompt bias toward LONG
3. Threshold asymmetry after the recent threshold changes

### 3.2 AI Decider State

| Metric | Value |
|--------|-------|
| Last ai_decider run | 13:26:44 UTC |
| Last signal_gen run | 13:52:07 UTC |
| Gap | 37 minutes |
| Pipeline heartbeat | OK for both |

**Issue:** ai_decider is running (heartbeat OK) but the hotset.json is stale. The ai_decider may be completing without errors but not writing to hotset.json, OR the write is failing silently.

### 3.3 Decisions Table — CRITICAL FAILURE

```
decisions table: 0 rows (schema exists but never written)
```

`decider_run.py` writes to `decisions` table but it has NEVER received a single row. This means:
- The execution path has NEVER successfully written a decision
- This is either a code path that was never triggered, or a bug in the execution flow
- This makes it impossible to track what was actually traded

### 3.4 WAIT Signal Backlog — 815 Signals

815 signals are stuck in WAIT state. This is abnormally high. The WAIT state means signals have been reviewed by AI but deferred. With 815 in backlog, either:
1. AI decider is producing far more WAITs than APPROVEDs
2. The WAIT→APPROVED transition path is broken
3. New signals are arriving faster than AI decider can process them

---

## 4. ML Components Analysis

### 4.1 Candle Predictor — CRITICAL FAILURE 🔴

```
Total predictions: 136,643
Overall accuracy: 38.06%  ← BELOW RANDOM (50%)
DOWN predictions: 17.75% accuracy (CATASTROPHIC)
UP predictions: 40.41% accuracy
```

**was_inverted Analysis:**
| was_inverted | Count | Accuracy |
|-------------|-------|----------|
| 0 | 73,892 | 35.06% |
| 1 | 62,751 | 41.60% |

**Findings:**
1. The model is performing WORSE than random chance
2. DOWN direction predictions are catastrophically bad (17.75%)
3. The `was_inverted=1` mode actually performs better (41.6% vs 35.06%) — suggesting the model direction may need to be inverted for production use
4. With 136K predictions, this is a statistically robust result — the model is fundamentally broken
5. The model appears to be adding NEGATIVE value to the trading system

**Recommendation:** DISABLE candle_predictor from production immediately. The model's predictions are worse than coin flip and may be actively harming trading decisions.

### 4.2 MTF-MACD Tuner — UNCLEAR EFFECTIVENESS

```
backtest_runs: 11 (completed)
backtest_results: 203,308 rows
token_best_config: 124 tokens configured
monitored_tokens: 207 tokens
```

**Assessment:** The tuner has run 11 backtest sessions and generated configs for 124 tokens. However:
1. It's unclear if these tuned configs are actually being used in signal_gen.py
2. `get_macd_params()` from `macd_rules.py` is called in signal_gen, but it's not clear if the tuned values from mtf_macd_tuner.db are actually being loaded
3. 124/207 tokens have configs — 83 tokens have no tuned config (use defaults)

### 4.3 LLM Compaction — RUNNING but EFFECTIVENESS UNCLEAR

The `_do_compaction_llm()` function in ai_decider.py is the core LLM-based hot-set selection. It:
1. Queries PENDING/WAIT signals from last 90 minutes
2. Filters to signals ≥60% confidence (CONFIDENCE_FLOOR)
3. Feeds to MiniMax-M2 LLM with max_tokens=4000
4. Parses output to select top 20

**Issues:**
1. The prompt complexity suggests significant token cost per run
2. The LLM is making all-or-nothing decisions on signal quality
3. With only 5 entries in hotset.json and a 37min gap, compaction may be failing silently
4. The hotset is ALL LONG despite SHORT_BIAS regime — suggests the LLM prompt may have unintended bias

---

## 5. Execution Quality Analysis

### 5.1 Guardian Path

```
hype_live_trading.json: live_trading=true (LIVE TRADING ON)
hl-sync-guardian.service: RUNNING
Pipeline heartbeat: OK
```

**Execution Flow:**
```
signal_gen → ai_decider → hotset.json → decider_run → hyperliquid_exchange → hl-sync-guardian → HL API
```

**Issues:**
1. **decisions table empty** — nothing is being written to track execution
2. **PostgreSQL unreachable** — position_manager can't read actual HL positions
3. **signal_outcomes has only 6 entries** — win/loss tracking is essentially non-functional

### 5.2 ATR-Based SL/TP — WORKING ✅

From trading.log, ATR-based SL/TP is firing correctly:
```
[ATR-TP] INJ LONG: entry=2.9002, cur=2.9477, ATR=0.006814 (0.23%), k_tp=2.5, dist=0.017036, effective=1.50%, TP=2.991915
[ATR] BTC LONG: entry=70768.0, cur=71653.5, ATR=113.928571 (0.16%), k=1.0, dist=113.928571, effective=1.00%, SL=70936.965000
```

**Status:** ATR self-close mechanism is operational.

### 5.3 Position Sizing & Risk

From the architecture:
- ATR-based dynamic SL/TP (volatility-adaptive)
- ATR_HL_ORDERS_ENABLED = False (self-close only, no HL trigger orders)
- CASCADE_FLIP_ENABLED = False (disabled for safety)
- Stale winner timeout: 15 min
- Stale loser timeout: 30 min

**Concern:** Stale loser timeout (30 min) is DOUBLE the stale winner timeout (15 min). This is backwards — losers should be cut faster, not slower.

### 5.4 Fees & Slippage Impact

Cannot analyze without actual trade data (decisions table empty, signal_outcomes only 6 entries). This is a CRITICAL gap in observability.

---

## 6. Regime Detection Analysis

### 6.1 Regime Log Distribution — SEVERELY BIASED 🔴

```
SHORT_BIAS: 106 entries (94%)
LONG_BIAS:  6 entries (5%)
NEUTRAL:    1 entry (1%)
Total: 113 entries
```

**This is a structural failure.** The regime detector is producing SHORT_BIAS ~95% of the time. This explains why:
- The hotset.json has only LONG entries (the regime is SHORT, so LONGs are contrarian and survive)
- All SHORT signals may be getting blocked by trend filters
- The system has a strong SHORT bias baked into the regime detection logic

### 6.2 Regime Detection Logic Analysis

```python
# From signal_gen.py compute_regime():
if avg_s < -1.5 and avg_m < -1.0: return 'bullish'    # Consensus oversold
if avg_s > 1.5 and avg_m > 1.0: return 'bearish'       # Consensus overbought → SHORT bias
if avg_s < avg_m - 0.3: return 'bullish'               # Mean-reverting UP
if avg_s > avg_m + 0.3: return 'bearish'               # Mean-reverting DOWN → SHORT bias
```

**Issue:** The regime detection uses a "consensus overbought/oversold" approach across ALL tokens. If the market is in a broad SHORT trend (which crypto often is), this creates a feedback loop that produces SHORT_BIAS almost exclusively.

The regime_log shows the regime barely ever changes — it's almost always SHORT_BIAS. This means the regime detection is not useful as a trading signal because it's always saying "short".

---

## 7. Architecture Analysis

### 7.1 Pipeline Flow Diagram

```
Binance Prices ──→ price_collector.py ──→ signals_hermes.db::price_history
                                        └──→ signals_hermes.db::latest_prices
                                        
HL Prices ──────→ 4h_regime_scanner.py ──→ regime_log (SHORT_BIAS 95%)
                                        └──→ hl_cache.json

Signal Gen ─────→ signal_gen.py ──────────→ signals_hermes_runtime.db::signals
                  (Z-score, RSI, MACD)         (PENDING/WAIT/APPROVED/EXECUTED)

AI Decider ─────→ ai_decider.py ───────────→ hotset.json (TOP 20)
                  (LLM compaction)              ⬆ STALE (only 5 entries, 25min old)

Decider Run ────→ decider_run.py ───────────→ hyperliquid_exchange.py
                  (Approval + execution)        └──→ hl-sync-guardian.py
                                                   └──→ HL API (LIVE)
                                                   
Position Mgmt ──→ position_manager.py ───────→ ATR SL/TP self-close
                  (Trailing stops, stale exits)     ⬇ BROKEN (PostgreSQL unreachable)

Dashboard ──────→ hermes-trades-api.py ────→ /var/www/hermes/data/signals.json
                  update-trades-json.py ────→ /var/www/hermes/data/trades.json
```

### 7.2 Bottlenecks & Failure Points

| Component | Risk | Issue |
|-----------|------|-------|
| PostgreSQL brain DB | 🔴 CRITICAL | 15+ hour outage — position tracking blind |
| ai_decider LLM | ⚠️ HIGH | 37min gap, hotset stale |
| decisions table | 🔴 CRITICAL | 0 rows ever written |
| signal_outcomes | 🔴 CRITICAL | Only 6 entries |
| Regime detector | 🔴 CRITICAL | 95% SHORT_BIAS |
| Candle predictor | 🔴 CRITICAL | 38% accuracy (disabled recommended) |
| token_speeds table | 🔴 CRITICAL | 0 rows — speed feature broken |
| token_intel table | 🔴 CRITICAL | 0 rows — intel tracking broken |
| cooldown_tracker table | 🔴 CRITICAL | 0 rows — cooldown broken |

### 7.3 Complexity & Observability Issues

1. **6 separate databases** with complex interdependencies
2. **60+ scripts** in /root/.hermes/scripts/
3. **Multiple timer systems** (systemd timers) running overlapping schedules
4. **No unified observability** — must query 6 DBs + multiple JSON files to understand state
5. **PostgreSQL as single point of failure** for position tracking

---

## 8. Priority Recommendations

### [CRITICAL] #1: PostgreSQL Brain DB Recovery
**Estimated Impact:** Restores position tracking, decisions table, signal_outcomes
**Action:** 
```bash
# Check if PostgreSQL is running
ps aux | grep postgres
# Or restore from backup / check network connectivity
```
**Owner:** DevOps

### [CRITICAL] #2: Disable Candle Predictor
**Estimated Impact:** Prevents actively harmful predictions from influencing trades
**Action:**
```python
# In run_pipeline.py or candle_predictor.py:
# Set candles_enabled = False or bypass the prediction lookup
```
**Root Cause:** Model trained on insufficient/wrong data — 38% accuracy is worse than random

### [CRITICAL] #3: Fix Decisions Table / Execution Tracking
**Estimated Impact:** Restores trade audit trail, enables win rate analysis
**Action:** Debug why decider_run.py never writes to decisions table despite 217 EXECUTED signals
**Likely Cause:** PostgreSQL connection failure is causing write transactions to silently fail

### [HIGH] #4: Fix Regime Detector Bias
**Estimated Impact:** Would restore LONG/SHORT balance in signals
**Action:** Audit regime_log entries. The threshold logic (avg_s > 1.5, avg_m > 1.0) may be too sensitive
**Note:** BROAD_UPTEND_Z=+0.5 may be adding to SHORT bias if BTC/ETH/SOL avg 4h z is frequently >0.5

### [HIGH] #5: Investigate Empty Tables
**Estimated Impact:** Would restore speed feature, signal intel, cooldown tracking
**Action:** 
```python
# Check why these are all 0:
# token_speeds (SpeedTracker must be called in signal_gen)
# token_intel (must be populated by ai_decider)
# cooldown_tracker (must be populated by decider_run)
```
**Root Cause:** Likely same PostgreSQL outage affecting all tracking tables

### [MEDIUM] #6: Hotset Redesign
**Estimated Impact:** Better signal prioritization, fewer WAIT backlogs
**Reference:** TASKS.md notes "Hot-Set Compaction Rewrite" is OPEN — this has been pending since 2026-04-08

### [MEDIUM] #7: Stale Timeout Logic Review
**Issue:** Losers get 30min but winners only 15min — backwards
**Fix:** Swap: STALE_WINNER_TIMEOUT=30, STALE_LOSER_TIMEOUT=15

---

## Appendix: Database Query Results Summary

```
signals_hermes_runtime.db:
  signals: 5,620 total
    EXPIRED: 2,270 (40%)
    SKIPPED: 1,491 (27%)
    WAIT: 815 (14%) ← backlog
    REJECTED: 708 (13%)
    EXECUTED: 217 (4%)
    PENDING: 89 (2%)
    APPROVED: 21 (<1%)
  decisions: 0 ← NEVER WRITTEN
  signal_outcomes: 6 ← FAR TOO FEW
  token_speeds: 0 ← NEVER WRITTEN
  token_intel: 0 ← NEVER WRITTEN
  cooldown_tracker: 0 ← NEVER WRITTEN

signals_hermes.db:
  price_history: 378,420 rows (healthy)
  latest_prices: 190 tokens (fresh, 10s old)
  regime_log: 113 entries
    SHORT_BIAS: 106 (94%) ← SEVERELY BIASED
    LONG_BIAS: 6 (5%)
    NEUTRAL: 1 (1%)

predictions.db:
  predictions: 136,643
    Accuracy: 38.06% ← BELOW RANDOM
    DOWN: 17.75% accuracy ← CATASTROPHIC

mtf_macd_tuner.db:
  token_best_config: 124 tokens configured
  backtest_runs: 11 completed
```

---

*Report generated: 2026-04-13 14:03 UTC*
*Next audit recommended: After PostgreSQL recovery + 24 hours of normal operation*

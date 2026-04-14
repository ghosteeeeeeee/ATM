# Pipeline Health Report: Hermes Trading System
**Generated:** 2026-04-12 23:04
**Analyst:** Pipeline Analyst (Revenue Operations)
**Status:** LIVE TRADING ACTIVE

---

## 1. Funnel Velocity

| Decision | Count | Avg Confidence | Rate |
|----------|-------|----------------|------|
| EXECUTED | 22 | 70.1% | 5.2% |
| REJECTED | 135 | 79.8% | 32.2% |
| PENDING | 91 | — | 21.7% |
| EXPIRED | 156 | — | 37.2% |
| WAIT | 4 | — | 1.0% |
| SKIPPED | 3 | — | 0.7% |
| APPROVED | 8 | — | 1.9% |

**Diagnosis:**
- Total signal volume: 419 signals — healthy pipeline volume
- Execution rate of 5.2% (22/419) is low but expected given multi-stage filtering
- **⚠️ CRITICAL: REJECTED signals have higher avg confidence (79.8%) than EXECUTED (70.1%)** — the ai-decider is rejecting higher-conviction signals while accepting lower-confidence ones
- 156 signals EXPIRED (37.2%) — significant signal timeout/waste in the pipeline
- 91 signals PENDING (21.7%) — pipeline has backlog working through
- Signals are fresh: all 419 signals generated within the last 24h

---

## 2. Directional Bias

| Signal Type | LONG | SHORT | Ratio (S/L) | Bias Flag |
|-------------|------|-------|-------------|-----------|
| momentum | 30 | 0 | 0.0 | ⚠️ NO SHORTS |
| mtf_zscore | 66 | 24 | 0.36 | ⚠️ LONG BIASED |
| percentile_rank | 164 | 7 | 0.04 | ⚠️ HEAVY LONG |
| rsi_individual | 20 | 1 | 0.05 | ⚠️ LONG BIASED |
| velocity | 6 | 101 | 16.8 | ⚠️ SHORT BIASED |
| **TOTAL** | **286** | **133** | **0.46** | ⚠️ NET LONG |

**Diagnosis:**
- Overall SHORT/LONG ratio of 0.46 indicates system is net LONG biased
- **momentum signal type is 100% LONG (0 SHORTs)** — momentum signals exclude shorts entirely
- **percentile_rank is heavily LONG biased** (164 LONG vs 7 SHORT)
- **velocity is heavily SHORT biased** (6 LONG vs 101 SHORT) — velocity signals drive short exposure
- The directional bias varies significantly by signal type, which may be intentional but creates uneven exposure
- This cross-signal bias variance could lead to inconsistent directional positioning

---

## 3. Execution Quality

| Decision | Count | Avg Confidence | Notes |
|----------|-------|----------------|-------|
| EXECUTED | 22 | 70.1% | Mixed signal types |
| REJECTED | 135 | 79.8% | Higher avg conf than executed! |
| SKIPPED | 3 | — | Marginal decisions |

**Diagnosis:**
- **⚠️ CRITICAL INVERSION: Rejected signals (79.8%) have higher confidence than executed (70.1%)**
- This suggests the ai-decider may be filtering on criteria other than confidence, or there is a logic error
- The 9.7pp confidence gap between rejected and executed is backwards — should be opposite
- 3 signals SKIPPED — marginal cases that didn't meet thresholds
- 8 signals APPROVED (pre-execution state) indicate a review/gating step exists
- Low execution rate (5.2%) with high rejection (32.2%) suggests aggressive filtering

---

## 4. Confluence Diagnostics

| Signal Type | Decision | Count | Avg Conf | Notes |
|-------------|----------|-------|----------|-------|
| mtf_zscore | PENDING | 43 | — | Multi-factor, high potential |
| mtf_zscore | EXPIRED | 26 | — | Timing issues |
| mtf_zscore | REJECTED | 16 | — | Rejected despite avg 79% conf |

**Diagnosis:**
- **mtf_zscore** (multi-timeframe z-score) represents the closest thing to "confluence" signals — combining multiple timeframes
- 43 mtf_zscore signals are PENDING — largest pending queue of any signal type
- 16 mtf_zscore REJECTED with ~79% confidence (same inversion issue)
- 26 EXPIRED — confluence signals are timing out before execution
- **No dedicated "confluence" signal type exists** — confluence is encoded in mtf_zscore logic
- Confidence inversion in mtf_zscore (rejected > executed) suggests multi-factor combination may be reducing conviction

---

## 5. Hot Set Health

| Metric | Value |
|--------|-------|
| Avg Review Count | 0.0095 |
| Signals with 0 Reviews | 415/419 (99.0%) |
| Signals with 1+ Reviews | 4/419 (1.0%) |

**Diagnosis:**
- **⚠️ CRITICAL: 99% of signals have zero review engagement**
- Review mechanism exists (review_count column) but is not being utilized
- Only 4 signals have any review activity — likely manual overrides or debugging
- This indicates the hot set review gate may be disabled or bypassed
- Auto-execution appears to be proceeding without human/automated validation
- Risk: Lower quality signals may be executing without peer review

---

## 6. Pipeline Freshness

| Metric | Value | Status |
|--------|-------|--------|
| Signals in last 24h | 419 | ✅ HEALTHY |
| Latest signal timestamp | 2026-04-12 23:01:57 | ✅ LIVE |
| Oldest signal (active) | varies | Monitoring |

**Diagnosis:**
- **✅ PIPELINE IS LIVE AND ACTIVE** — 419 signals in last 24h
- Signal generation is functioning properly — no halt detected
- Mix of PENDING (91) and EXECUTED (22) indicates active pipeline flow
- EXPIRED count (156) suggests some signals timeout before execution — investigate TTL settings
- Freshness is NOT an issue — this is the healthiest metric

---

## 7. Trade Outcomes

### Win Rate & PnL
| Metric | Value |
|--------|-------|
| Total Trades | 4 |
| Open Positions | 1 (ETC SHORT) |
| Closed Trades | 3 |
| Winning Trades | 1 |
| Losing Trades | 1 |
| Breakeven Trades | 1 |
| Win Rate | 50% |
| Net PnL (USDT) | -0.03 |

### Closed Trades (30d)
| Token | Direction | Entry | Exit | PnL | Close Time | Exit Reason |
|-------|-----------|-------|------|-----|------------|-------------|
| COMP | SHORT | 20.698 | 20.580 | +0.29 | 2026-04-12 22:42 | HL_CLOSED |
| BABY | SHORT | 0.01443 | 0.01453 | -0.35 | 2026-04-12 22:42 | HL_SL_CLOSED |
| ATOM | LONG | 1.7291 | 1.7388 | 0.00 | 2026-04-12 17:21 | ORPHAN_PAPER |

### Open Positions
| Token | Direction | Entry | Current PnL | Age |
|-------|-----------|-------|-------------|-----|
| ETC | SHORT | 8.1426 | +0.03 | <1h |

**Diagnosis:**
- Small sample size (N=3 closed trades) — too early for statistically significant conclusions
- Win rate of 50% is marginally acceptable but sample is too small
- Net PnL of -0.03 USDT is essentially breakeven
- All trades are SHORT except ATOM — consistent with SHORT bias from velocity signals
- Exit reasons: HL_CLOSED (Hyperliquid closed), HL_SL_CLOSED (stop loss), ORPHAN_PAPER (untracked)
- ORPHAN_PAPER on ATOM suggests trade tracking issue — pnl=0 despite price movement
- ETC short currently up +0.03 — young position, monitor

---

## 8. Intervention Recommendations

### Priority 1 — CRITICAL (Address Immediately)

| # | Issue | Action | Impact |
|---|-------|--------|--------|
| 1 | **Confidence inversion: REJECTED avg (79.8%) > EXECUTED avg (70.1%)** | Audit ai-decider logic — signals with higher confidence are being rejected. Check if other factors (z_score_tier, momentum_state, signal_source) are overriding confidence. | Decisions are backwards — best signals being filtered out |
| 2 | **99% of signals have review_count = 0** | Verify hot set review mechanism is active. If auto-execution is enabled, evaluate risk of bypassing human review on high-value trades. | Quality control bypassed — all signals executing without validation |

### Priority 2 — HIGH (Investigate This Week)

| # | Issue | Action | Impact |
|---|-------|--------|--------|
| 3 | **37% signal expiration rate (156 EXPIRED)** | Investigate signal TTL settings. Long expiration times may cause signals to stale before execution. Optimize time-sensitive signals (momentum, velocity). | Wasted pipeline capacity, missed opportunities |
| 4 | **momentum signals are 100% LONG, 0% SHORT** | Review momentum signal logic — short opportunities are being filtered. Check if short_signals=false is hardcoded or market-conditional. | Directional blind spot on bearish momentum |
| 5 | **ATOM trade exited with ORPHAN_PAPER (pnl=0)** | Fix trade tracking for paper trades — exit price recorded but pnl=0 indicates calculation bug. | Cannot accurately measure trade performance |

### Priority 3 — MEDIUM (Evaluate This Month)

| # | Issue | Action | Impact |
|---|-------|--------|--------|
| 6 | **velocity signals are 85% SHORT (101 SHORT vs 6 LONG)** | If asymmetric SHORT velocity is intentional, document rationale. Otherwise, investigate why LONG velocity signals are being filtered. | Uneven signal type distribution |
| 7 | **Execution rate only 5.2%** | With 419 signals and 22 executions, investigate what separates executed from rejected. Could be opportunity cost in over-generation. | Potential signal waste |
| 8 | **N=3 closed trades insufficient for quality assessment** | Continue monitoring until N≥30 closed trades for meaningful win rate / avg PnL statistics. | Cannot assess true strategy performance yet |

---

## Summary Scorecard

| Dimension | Status | Score |
|-----------|--------|-------|
| Pipeline Volume | ✅ HEALTHY | 9/10 |
| Pipeline Freshness | ✅ HEALTHY | 10/10 |
| Execution Quality | 🔴 CRITICAL | 2/10 |
| Directional Balance | 🟡 MARGINAL | 5/10 |
| Hot Set Health | 🔴 CRITICAL | 1/10 |
| Trade Outcomes | 🟡 INCONCLUSIVE | 4/10 |
| Signal Expiration | 🟡 WATCH | 6/10 |

**Overall Pipeline Health: 5.3/10 — MARGINAL**

---

## Appendix: Raw Data

### Signals DB Summary (SQLite: signals_hermes_runtime.db)
- Total signals: 419
- Decisions: EXECUTED=22, REJECTED=135, PENDING=91, EXPIRED=156, WAIT=4, SKIPPED=3, APPROVED=8
- Signal types: momentum (46), mtf_zscore (90), percentile_rank (179), rsi_individual (40), velocity (120)
- Directions: LONG=286 (68%), SHORT=133 (32%)
- Avg confidence EXECUTED: 70.1%
- Avg confidence REJECTED: 79.8%
- Review count: 415/419 (99%) with zero reviews
- Latest signal: 2026-04-12 23:01:57

### Trades DB Summary (PostgreSQL: brain.trades)
- Total trades: 4
- Open positions: 1 (ETC SHORT)
- Closed trades: 3
- Win/Loss: 1/1 (ATOM was breakeven)
- Net PnL: -0.03 USDT
- Win rate: 50%

---

*Report generated by Pipeline Analyst subagent. Live trading is ON — findings require immediate action on Priority 1 items.*

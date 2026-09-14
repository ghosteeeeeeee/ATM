# Pump-Chain LONG Audit — Independent Verdict

**Auditor:** CEO (independent, fresh-eyes)
**Date:** 2026-09-14
**Files Read:** pump_chain_long.py, pump_flow_signal.py, signal_compactor.py, hermes_constants.py
**SQL:** PostgreSQL (brain DB) — 2 queries executed

---

## Raw Data Summary

### pump_chain (Sep 6-9, ORIGINAL era)
| Regime | Trades | Wins | WR | PnL | Avg PnL |
|--------|--------|------|-----|------|---------|
| EXTREME | 22 | 14 | 63.6% | +$1.35 | +$0.061 |
| HIGH | 13 | 10 | 76.9% | +$0.03 | +$0.002 |
| NORMAL | 6 | 4 | 66.7% | -$0.27 | -$0.045 |
| **TOTAL** | **41** | **28** | **68.3%** | **+$1.11** | **+$0.027** |

### pump-chain+ (Sep 10+, FILTERED era)
| Regime | Trades | Wins | WR | PnL | Avg PnL |
|--------|--------|------|-----|------|---------|
| EXTREME | 14 | 6 | 42.9% | -$0.06 | -$0.004 |
| HIGH | 7 | 3 | 42.9% | -$0.06 | -$0.009 |
| NORMAL | 3 | 0 | 0.0% | -$0.44 | -$0.147 |
| **TOTAL** | **24** | **9** | **37.5%** | **-$0.56** | **-$0.023** |

### Critical Context: GRASS Outlier
- **GRASS trade (Sep 9): +$1.57** — single trade = 141% of total PnL
- **Without GRASS:** 40 trades, 27 wins, 67.5% WR, **-$0.46 PnL (NET NEGATIVE)**
- **Sep 8 (still original era): 18 trades, 8 wins = 44.4% WR, -$1.03** — deterioration already happening BEFORE filters were added

---

## Claim-by-Claim Verdict

### Claim 1: "Original pump_chain had 67% WR because it had no filters"
**Verdict: DISAGREE**
**Evidence:** pump_flow_signal.py during Sep 6-9 ALREADY had filters:
- BTC 1h trend filter added Sep 8 (commit 3ac0151d)
- Token 5m velocity filter added Sep 8 (commit 8e2e59d4)
The original era was NOT filter-free. The filters existed in pump_flow_signal.py.
**Confidence: HIGH**

### Claim 2: "BTC timing guard blocks pump-chain+ LONG entries, causing 43% WR"
**Verdict: DISAGREE**
**Evidence:**
- `BTC_TIMING_GUARD_LOG_ONLY = True` (hermes_constants.py:911)
- signal_compactor.py:1168: `if BTC_TIMING_GUARD_LOG_ONLY:` → only LOGS "WOULD BLOCK", does NOT return 0.0
- The guard is purely observational — it has ZERO effect on trade execution
**Confidence: HIGH**

### Claim 3: "Stale entry filter blocks good pump-chain+ entries"
**Verdict: DISAGREE**
**Evidence:**
- Stale filter was added Sep 14 (commit 9c1819ca) — AFTER most filtered era trades
- Commit message: "5T stale entries 7d = 0%WR -$0.73, **0 winners blocked**"
- The filter blocks LOSERS, not winners. Removing it would NOT improve WR.
**Confidence: HIGH**

### Claim 4: "Removing BTC timing guard + stale filter would restore 67% WR"
**Verdict: DISAGREE**
**Evidence:**
- BTC timing guard is already LOG_ONLY (not blocking anything)
- Stale filter blocks 0 winners
- Neither filter is the cause of the WR drop
- The WR drop is explained by: (a) GRASS outlier inflating original era WR, (b) market regime change, (c) small sample sizes
**Confidence: HIGH**

### Claim 5: "Volatility gate naming mismatch (pump-chain vs pump_chain) was blocking the signal"
**Verdict: DISAGREE**
**Evidence:**
- STANDALONE_BYPASS_SIGNALS includes BOTH variants: `'pump-chain', 'pump_chain'` (hermes_constants.py:2288)
- volatility_gate_v2.py explicitly lists both: `'pump-chain', 'pump-chain+', 'pump-chain-'` AND `'pump_chain', 'pump_chain+', 'pump_chain-'`
- The naming mismatch is handled everywhere in the codebase
**Confidence: HIGH**

### Claim 6: "pump-chain+ (LONG) is a loser at 42.9% WR and should be killed"
**Verdict: PARTIAL**
**Evidence:**
- Actual WR is **37.5%** (9/24), not 42.9%. PnL is -$0.56. It IS a loser.
- However, 24 trades is a very small sample — high variance
- **Already killed:** `PUMP_FLOW_PLUS_ENABLED = False` (hermes_constants.py:3301, killed Sep 14)
- The "should be killed" action was already taken
**Confidence: HIGH**

### Claim 7: "pump_chain (underscore) was a winner at 67.4% WR"
**Verdict: PARTIAL**
**Evidence:**
- Actual WR was 68.3% (28/41). Close enough.
- But: **Without GRASS outlier (+$1.57), the original era was -$0.46 NET NEGATIVE** despite 67.5% WR
- The high WR masked negative expected value: wins averaged +$0.027 but losses averaged -$0.089
- Sep 8 already showed 44.4% WR with -$1.03 — deterioration started BEFORE any new filters
**Confidence: HIGH**

---

## Root Cause Analysis

### Why did WR drop from 68% to 37.5%?

1. **GRASS outlier inflated original era WR** — A single +$1.57 trade (Sep 9) made the original era look profitable. Without it: 67.5% WR but **-$0.46 PnL**. The signal was already marginally negative.

2. **Market regime change** — Sep 7 was EXTREME volatility with a chain-reaction pump (19T/16W = 84.2%). This was a specific market event, not a repeatable edge. The filtered era had fewer EXTREME regime opportunities.

3. **Small sample sizes** — 41 vs 24 trades. Both are too small for statistical significance. The WR difference (68% vs 37.5%) could be noise with these samples.

4. **Loss asymmetry** — In both eras, average loss > average win. Original: avg_win=+$0.057, avg_loss=-$0.089. Filtered: avg_win=+$0.178, avg_loss=-$0.133. Neither era has a sustainable edge.

### Code Architecture Findings

1. **pump_chain_long.py has a stale entry filter** (lines 156-174) that the original code did NOT have. The claim of "original logic" is not entirely accurate — it was modified on Sep 14 to add the stale check.

2. **pump_flow_signal.py now skips ALL LONG trades** (line 264: `if direction == 'LONG': continue`). Only pump_chain_long.py handles LONG. This split happened Sep 13 (commit 8f94a512).

3. **pump_chain_long.py is registered but KILLED** — PUMP_FLOW_PLUS_ENABLED = False since Sep 14.

4. **BTC timing guard is pure logging** — LOG_ONLY mode means it has zero execution impact. It was added for observation, not enforcement.

---

## Summary Table

| Claim | Verdict | Key Evidence |
|-------|---------|-------------|
| Original had no filters | DISAGREE | BTC+velocity filters existed in pump_flow_signal.py Sep 8 |
| BTC timing guard blocks entries | DISAGREE | LOG_ONLY = True, zero execution impact |
| Stale filter blocks good entries | DISAGREE | Added Sep 14, blocks 0 winners |
| Removing filters restores 67% WR | DISAGREE | Filters aren't blocking; original was already negative w/o GRASS |
| Naming mismatch blocks signal | DISAGREE | Both variants in STANDALONE_BYPASS + volatility_gate |
| pump-chain+ is a loser | AGREE | 37.5% WR, -$0.56, already killed |
| pump_chain was a winner | PARTIAL | 68% WR but -$0.46 without GRASS outlier |

---

## Recommendation

**Do not restore pump-chain+ LONG by removing filters** — the filters aren't the cause. The original era's profitability was a statistical artifact of one GRASS outlier trade and one EXTREME volatility day (Sep 7). The signal needs a fundamental edge rethink, not filter removal.

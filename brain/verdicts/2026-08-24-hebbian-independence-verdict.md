# Independent Audit Verdict — Hebbian V2 Correlation Engine
## 2026-08-24

**Auditor:** Independent subagent, no prior context  
**Files audited:** correlation_engine.py, chain_fire.py, hebbian-v2-correlation-engine-spec.md, pump-loop-usage-spec.md, pump-loop-discovery.md  
**Databases queried:** correlations.db, signals_hermes_runtime.db  
**Method:** Read all files, run own SQL, verify every claim against raw data

---

## Claim-by-Claim Verdicts

### Claim 1: "3,708 trades were processed into 3,499 chains"
**PARTIAL** ⚠️

- Trades processed: **3,708 — CONFIRMED** ✓ (engine_state.total_trades_processed = 3708)
- Chains built: **3,566 — NOT 3,499** ✗
  - `SELECT COUNT(*) FROM token_chains` returns **3,566**
  - The claimed number is off by 67 chains
- Source: associative_memory.db has 3,793 non-test trades total; 85 newer trades weren't ingested yet (last ingest was 2026-08-23 16:45)

**Verdict:** Trade count is accurate. Chain count is wrong — should be 3,566, not 3,499.

---

### Claim 2: "The longest chain is 7 hops: ME→GRIFFAIN→SKR→BSV→ASTER→CAKE→0G→BCH→MORPHO"
**DISAGREE** ✗

- Count the arrows in the claimed chain: **8 arrows → 8 hops, 9 nodes**
- The claim says "7 hops" but the listed chain has 8 transitions
- The chain itself is real: every link verified in token_chains with co_fires ≥ 5
- The actual "loop" (from pump-loop-discovery.md) is a **9-hop cycle**: SKR → BSV → ASTER → CAKE → 0G → BCH → MORPHO → XMR → GRIFFAIN → SKR
- A full DFS was attempted but timed out on 3,566 chains — so I cannot conclusively prove this is the absolute longest chain, but the claimed chain has 8 hops, not 7

**Verdict:** The chain data exists and is valid, but the hop count is wrong (8, not 7). The pump loop discovery doc also says "7 hops" but the listed cycle has 10 arrows (10 hops including the return to SKR, or 9 distinct hops in the core cycle).

---

### Claim 3: "ME→GRIFFAIN has 86% WR with n=14"
**AGREE** ✓

- Actual data: `co_fires=14, win_rate=0.8571 (85.7%), b_wins_after_a=12, b_losses_after_a=2, base_wr=48.5%, lift=1.77x`
- 85.7% rounds to 86% — this is a fair rounding
- n=14 is exactly correct

**Verdict:** Accurate. Minor rounding (85.7% → 86%) is acceptable.

---

### Claim 4: "chain_fire signal has fired 2 times on ADA SHORT"
**AGREE** ✓ (with caveat)

- **2 chain_fire_short signals on ADA found in signals table:**
  - id=1562233, source=chain_fire-,tl_break_short, created 2026-08-24 02:44, decision=EXPIRED
  - id=1563390, source=chain_fire-,confluence-, created 2026-08-24 14:45, decision=EXPIRED
- **0 chain_fire trades in signal_outcomes** — neither signal was actually executed
- Total chain_fire signals ever generated (any token/direction): **2**
- Total chain_fire trades executed: **0**

**Verdict:** 2 signals were generated, both on ADA SHORT. However, both expired without executing. If "fired" means "signal generated" — TRUE. If "fired" means "trade executed" — FALSE (zero trades).

---

### Claim 5: "Cumulative PnL through the full loop is +3.68%"
**PARTIAL** ⚠️

- Sum of avg_pnl_after_a across 9 hops (ME→GRIFFAIN→...→XMR): **+3.677%** — rounds to +3.68% ✓
- **But this number is misleading:** it's a sum of per-hop average PnLs, NOT a compounded return from riding the full loop
- Each hop's avg_pnl is calculated independently: "when A fires, the average PnL of B's trade"
- These are not sequential trades on the same capital — each hop represents a different trade on a different token
- The +3.68% figure is real math but does NOT represent actual portfolio PnL from "riding the loop"
- Also, the loop includes MORPHO→XMR at -0.12% — the spec diagram only shows through MORPHO and omits XMR from the "+3.68%" calculation but includes it in the chain

**Verdict:** The arithmetic is correct (verified: +3.677%), but the interpretation is questionable. It's a sum of independent per-hop averages, not a compound return.

---

### Claim 6: "The correlation engine is wired into brain.py close_trade() for continuous ingestion"
**AGREE** ✓

- `brain.py` line 774: `_close_trade_impl()` is the implementation behind `close_trade()`
- Lines 986-1002: calls `CorrelationEngine().ingest_trade()` with trade data
- Called when `hype_pnl_pct is not None and signal` — i.e., on every trade close that has PnL and signal info
- Fail-open pattern (wrapped in try/except with pass)

**Verdict:** Confirmed. Every trade close triggers correlation engine ingestion.

---

### Claim 7: "The context gate logs chain suggestions"
**AGREE** ✓

- `decider_run.py` lines 1431-1446: inside `context_gate()` function
- Logs `[CORRELATION]` messages when chain lift > 1.3 and confidence > 0.55
- Logs best chain suggestion and all qualifying chains (n >= 3)
- Advisory only — does not block trades

**Verdict:** Confirmed. Chain suggestions are logged in the context gate with `[CORRELATION]` prefix.

---

## Additional Findings

### Spec vs Implementation Gaps

| Spec Feature | Implemented? | Notes |
|---|---|---|
| `signal_chains` table (signal co-occurrence) | **NO** | Table not in DB despite being in spec |
| `half_life_weight` column | **NO** | Not in token_chains schema despite being in spec |
| `next_signals()` method | **NO** | Listed in spec API but not in correlation_engine.py |
| Decay via correlation_engine | **NO** | The systemd timer runs the OLD `hebbian_engine.py decay`, not `correlation_engine.py apply_decay` |

### Pump Loop Structural Issues

1. **Two different loop descriptions exist:**
   - `pump-loop-discovery.md`: AXS → SKR → BSV → ASTER → CAKE → 0G → BCH → MORPHO → XMR → GRIFFAIN → SKR (cycle)
   - `pump-loop-usage-spec.md`: ME → GRIFFAIN → SKR → BSV → ASTER → CAKE → 0G → BCH → MORPHO → XMR
   - These describe the same core cycle with different entry points (AXS vs ME), but the specs disagree on whether XMR→GRIFFAIN is included

2. **Hop count errors in both docs:**
   - Discovery says "7 hops" for a 10-arrow chain
   - Spec says "7 hops" for an 8-arrow chain

3. **Per-hop n=5 chains have low statistical significance:**
   - ASTER→CAKE (n=5), CAKE→0G (n=5), 0G→BCH (n=5) — these are the minimum needed
   - With Bayesian confidence of 0.53-0.60, these are barely above prior (0.50)

### Chain Fire Signal Effectiveness

- **0 out of 2 chain_fire signals resulted in executed trades**
- Both expired — this means the chain_fire signal was generated but never acted on
- The signal type exists and the code is wired in, but no actual PnL has been generated

### Decay System

- The `hermes-hebbian-decay.timer` runs `hebbian_engine.py decay` (old system)
- The new `correlation_engine.py apply_decay()` method exists but is **not called by any timer**
- This means correlation engine chains are NOT being decayed — old data accumulates indefinitely

---

## Summary Table

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 1 | 3,708 trades → 3,499 chains | **PARTIAL** | Trades correct. Chains = 3,566, not 3,499 |
| 2 | Longest chain = 7 hops | **DISAGREE** | Chain has 8 hops, not 7. Hop count is wrong. |
| 3 | ME→GRIFFAIN = 86% WR, n=14 | **AGREE** | n=14 confirmed, wr=85.7% (rounds to 86%) |
| 4 | chain_fire fired 2× on ADA SHORT | **AGREE** | 2 signals generated. But 0 executed (both expired). |
| 5 | Cumulative loop PnL = +3.68% | **PARTIAL** | Math checks out (+3.677%), but it's sum of independent averages, not compounded return |
| 6 | Wired into brain.py close_trade() | **AGREE** | Confirmed in _close_trade_impl(), lines 986-1002 |
| 7 | Context gate logs chain suggestions | **AGREE** | Confirmed in decider_run.py lines 1431-1446 |

**Overall: 4 AGREE, 2 PARTIAL, 1 DISAGREE** — plus several structural issues (missing spec implementations, wrong decay timer, misleading PnL calculation).

---

*Audit performed 2026-08-24 by independent auditor subagent. All SQL queries executed directly against live databases. No trust placed in any prior analysis.*

# Investigation: 862 Signals → 17 Trades Execution Gap

> ## ⚠️ CORRECTED 2026-10-19 20:40 UTC — AUDIT FOUND CRITICAL ERRORS
>
> Independent own-conclusions audit (`brain/verdicts/2026-10-19-execution-gap-own-conclusions.md`, commit `b24d5a3d`) found:
>
> 1. **"Hotset empty 4 days" is FALSE** — a 42MB NUL-blob in `signal-compactor.log` silently truncated plain `grep`. With `grep -a`: 84 non-empty writes today. The hotset is NOT empty.
> 2. **"Most signals conf 72-74" is FALSE** — 89% have conf≥75. SHORT-REGIME-GATE killed only 50 signals vs 936 CONFLUENCE-GATE-BLOCK and 848 SHORT-RSI-HARD-FLOOR.
> 3. **"BTC shifted from EXTREME" is FALSE** — BTC never EXTREME in 21+ days. Shift is token-level ATR expansion.
> 4. **3 real bugs found** — log corruption, compactor/decider vol-gate mismatch (70 wasted executions/day), three divergent RSI sources.
> 5. **Gates tightened Oct 16/18** — SHORT_MIDBAND added, SHORT_RSI_FLOOR reverted 35→45, pump-chain- EXTREME re-blocked. Never evaluated jointly.
>
> **The headline fix (loosen SHORT-REGIME-GATE) would barely help** — it killed 50 signals vs 936/848/695 at the top.
>
> **Corrected root cause:** ~38% of signals structurally unpassable + 20-gate stack tightened 3x Oct 16-18 + cross-layer gate/RSI inconsistencies wasting ~70 executions/day.
>
> **Use the audit verdict, not this report's Executive Summary, for decisions.**

**Date:** 2026-10-19 19:45 UTC (corrected 20:40)
**Investigator:** Hermes (CEO agent), audited by independent subagent
**Trigger:** T reported "no trades taken, no stats generated, winrate stuck at 35%"
**CEO directive:** "Investigate which gate eats the 862 signals before loosening anything"

## Executive Summary (SUPERSEDED — see correction notice above)

~~The 862→17 execution gap is **not a bug** — it's the gate system working as designed in a market regime that doesn't favor our signals. The hotset has been **empty since 2026-10-15 04:06** because:~~

~~1. **Market regime shifted** from EXTREME volatility to NORMAL/HIGH~~
~~2. **SHORT signals blocked** by SHORT-REGIME-GATE (needs conf≥75 in NORMAL/HIGH, most signals have conf 72-74)~~
~~3. **pump-chain- SHORT blocked** in both EXTREME (not in allowed list) and HIGH (PUMP-CHAIN-SHORT-HIGH gate)~~
~~4. **LONG signals blocked** by CONTINUUM-BLOCK (BTC bearish structure) and RR-ENGINE (R:R too low)~~

~~The gates were designed for a different market regime. When the market was EXTREME, SHORT signals passed. Now the market is NORMAL/HIGH, and the same signals are blocked.~~

## Data Sources (Verified)

- **Signals DB:** `data/signals_hermes_runtime.db` (52MB, correct path — `scripts/` version is empty 0-byte file)
- **Trades DB:** PostgreSQL `brain.trades` (source of truth)
- **Compactor log:** `logs/signal-compactor.log` (dedicated log, NOT pipeline.log which only covers through Oct 15)
- **Hotset:** `/var/www/hermes/data/hotset.json`

## Stage-by-Stage Trace

### Stage 1: Signal Detection (24h)

```sql
-- Total signals detected
SELECT COUNT(*) FROM signals WHERE created_at > datetime('now', '-24 hours');
-- Result: 850

-- Decision breakdown
SELECT decision, COUNT(*) FROM signals WHERE created_at > datetime('now', '-24 hours') GROUP BY decision;
-- Result: EXPIRED=840, PENDING=6, FAILED=2, EXECUTED=1, SKIPPED=1
```

**98.8% of signals expire** (840/850). Only 1 EXECUTED.

### Stage 2: Compactor Processing

The compactor runs every minute via `hermes-signal-compactor.timer`. It queries signals with:
- `decision IN ('PENDING', 'APPROVED')`
- `executed = 0`
- `created_at > datetime('now', '-10 minutes')` — **only last 10 minutes**
- `confidence >= 60`
- `combo_key IS NOT NULL`

**Current query result:** 3-5 combo_keys per cycle

**But:** 0 tokens written to hotset every cycle for 4+ days.

### Stage 3: Gate Kills (The Bottleneck)

From dry run (`python3 scripts/signal_compactor.py --dry`):

```
Query: 4 combo_keys in 5-min window (conf>=60, not executed)
  🚫 [VOL-GATE-BYPASS] APT SHORT BLOCKED — bypass denied, vol gate override=0.0 for 'pump-chain-' in EXTREME
  🚫 [PUMP-CHAIN-SHORT-HIGH] FIL SHORT blocked — HIGH vol, no pump-chain- SHORT edge (20%WR)
  🚫 [CONTINUUM-BLOCK] GOAT LONG BLOCKED — BTC bearish structure
  🚫 [RR-ENGINE] GOAT LONG: RR HARD BLOCKED: R:R=0.43 < 0.55 (risk > reward)
  🚫 [SHORT-REGIME-GATE] BTC SHORT blocked — NORMAL vol regime, no quality gate (conf=72, need>=75 or proven family)
Pre-filter: 2 signals passed safety filters
...
Wrote hotset.json with 0 tokens (cycle=13014)
```

**4 signals queried → 2 pass pre-filter → 0 in hotset.**

### Stage 4: Hotset → Decider → Trade

Since hotset is empty, the decider has nothing to execute. No trades.

## Root Cause Analysis

### 1. Market Regime Shift (Primary Cause)

**BTC ATR history (1h candles):**
```
2026-10-13: 0.52% (NORMAL)
2026-10-14: 0.65% (NORMAL)
2026-10-15: 0.52% (NORMAL)
2026-10-16: 0.31% (FLAT)
2026-10-17: 0.23% (FLAT)
2026-10-18: 0.24% (FLAT)
2026-10-19: 0.64% (NORMAL)
```

**Volatility classification (from `volatility_gate_v2.py`):**
- FLAT: ATR < 0.48%
- NORMAL: 0.48% ≤ ATR < 1.0%
- HIGH: 1.0% ≤ ATR < 1.5%
- EXTREME: ATR ≥ 1.5%

**Current token ATRs:**
```
APT: 1.53% → EXTREME
FIL: 1.38% → HIGH
BTC: 0.53% → NORMAL
GOAT: 0.95% → NORMAL
INJ: 1.94% → EXTREME
ACE: 1.39% → HIGH
IMX: 1.09% → HIGH
```

Different tokens have different vol regimes. The gates kill signals based on each token's regime.

### 2. SHORT-REGIME-GATE (Added Oct 4)

**Commit:** `46fac270` — "Fix: SHORT regime gate — SHORT blocked in NORMAL/HIGH unless quality gate (conf>=75 or proven family). 30d data: EXTREME +.47, NORMAL -.49, HIGH -.94. CEO decision D1=A."

**Logic:** SHORT signals in NORMAL/HIGH vol regime require `conf >= 75` OR proven family (only `mover-`).

**Impact:** Most SHORT signals have conf 72-74 → blocked.

**Example:** BTC SHORT conf=72, needs 75 → blocked.

### 3. pump-chain- SHORT Blocked in EXTREME (Added Oct 1)

**Code:** `volatility_gate_v2.py` line 196:
```python
# pump-chain- SHORT removed 2026-10-01 — EXTREME Pump_Flow=0.0 hard block; REGIME_SIGNALS was stale dead path
```

**Impact:** pump-chain- SHORT not in EXTREME allowed list → `_get_signal_type_mult` returns 0.0 → blocked.

**Example:** APT SHORT (pump-chain-) in EXTREME → blocked.

### 4. PUMP-CHAIN-SHORT-HIGH (Added Sep 29)

**Commit:** `7af94a94` — "brain_auditor: PUMP_CHAIN_SHORT_HIGH_BLOCK + audit report (Sep 29 07:30)"

**Logic:** Blocks pump-chain- SHORT in HIGH vol (5T 20%WR -$0.60/14d).

**Impact:** FIL SHORT (pump-chain-) in HIGH → blocked.

### 5. CONTINUUM-BLOCK (BTC Bearish Structure)

**Logic:** Blocks LONG signals when BTC structure is bearish.

**Impact:** GOAT LONG blocked because BTC bearish.

### 6. RR-ENGINE (R:R Too Low)

**Logic:** Blocks signals with Risk:Reward < 0.55 (hard floor).

**Impact:** GOAT LONG R:R=0.43 → blocked.

## Timeline: When Did Hotset Go Empty?

**Last non-empty hotset:** 2026-10-15 04:06 (1 token)

**What happened at that time:**
- Market was still in EXTREME vol for some tokens
- pump-chain- SHORT was already blocked (added Oct 1)
- SHORT-REGIME-GATE was already active (added Oct 4)
- But some tokens still had EXTREME vol, allowing SHORT signals

**After Oct 15:**
- BTC ATR dropped to 0.31% (FLAT) on Oct 16
- More tokens shifted from EXTREME to HIGH/NORMAL
- SHORT-REGIME-GATE started blocking more signals
- Hotset went to 0 and stayed there

## Why Trades Still Happen (17 in 24h)

Trades that DID execute came from:
1. **Manual trades** (ai-trader-manual) — bypass the compactor
2. **Signals that passed all gates** — rare, but happens when conf≥75 and R:R≥0.55
3. **Existing positions** — opened before gates tightened

## CEO's Question: "Which gate eats the most signals?"

From last 100 compaction cycles:
```
35 [CONFLUENCE-GATE-BLOCK] — single-type not in standalone bypass
26 [SHORT-RSI-HARD-FLOOR] — RSI < 35 for SHORT
16 [REP] — repetition/cooldown
9  [PUMP-CHAIN-SHORT-HIGH] — HIGH vol block
3  [CONTINUUM-BLOCK] — BTC bearish structure
1  [PRESERVE-SPIKE-BLOCK] — spike preservation
```

**Top killer: CONFLUENCE-GATE-BLOCK** (35/100) — signals with only 1 source type that aren't in STANDALONE_BYPASS_SIGNALS.

**Second: SHORT-RSI-HARD-FLOOR** (26/100) — SHORT signals with RSI < 35.

**But:** These are from Oct 15 logs. Current logs show different gates:
- VOL-GATE-BYPASS (pump-chain- in EXTREME)
- SHORT-REGIME-GATE (conf < 75 in NORMAL/HIGH)
- PUMP-CHAIN-SHORT-HIGH (HIGH vol)

## Recommendations

### Option A: Loosen SHORT-REGIME-GATE (CEO rejected "loosen filters" but this is data-driven)

**Current:** conf≥75 or proven family (mover- only)
**Proposed:** conf≥70 or add pump-chain- to proven family

**Evidence:** 30d data shows NORMAL -.49, HIGH -.94. But that's aggregate. Check if conf 70-74 in NORMAL/HIGH has edge.

**Risk:** Re-introduces the bleed the gate was designed to stop.

### Option B: Add pump-chain- SHORT back to EXTREME allowed list

**Current:** Removed 2026-10-01
**Proposed:** Re-add with additional filters (RSI floor, dead-gap block)

**Evidence:** Before removal, EXTREME pump-chain- SHORT had 56.3% WR (32T +$0.66).

**Risk:** The removal was data-driven. Need to verify the edge still exists.

### Option C: Wait for market regime to shift back to EXTREME

**Current:** NORMAL/HIGH
**Historical:** EXTREME occurred regularly before Oct 15

**Risk:** Could wait days/weeks. Meanwhile, no trades, no stats, WR stuck.

### Option D: Loosen CONFLUENCE-GATE for standalone bypass signals

**Current:** 35/100 kills are single-type not in STANDALONE_BYPASS_SIGNALS
**Proposed:** Add more signals to STANDALONE_BYPASS_SIGNALS

**Evidence:** Need to check which signals are being killed and their historical WR.

**Risk:** Reduces signal quality (confluence = confirmation).

## Protected Flags

13/13 INTACT. No config changed during this investigation.

## Reproducible Queries

```sql
-- Total signals detected (24h)
SELECT COUNT(*) FROM signals WHERE created_at > datetime('now', '-24 hours');

-- Decision breakdown
SELECT decision, COUNT(*) FROM signals WHERE created_at > datetime('now', '-24 hours') GROUP BY decision;

-- Signal type breakdown
SELECT signal_type, direction, COUNT(*) as n, decision FROM signals WHERE created_at > datetime('now', '-24 hours') GROUP BY signal_type, direction, decision ORDER BY n DESC LIMIT 30;

-- PENDING signals in 10-min window
SELECT COUNT(*) FROM signals WHERE decision IN ('PENDING', 'APPROVED') AND executed = 0 AND created_at > datetime('now', '-10 minutes') AND confidence >= 60 AND token NOT LIKE '@%' AND combo_key IS NOT NULL;
```

```bash
# Dry run to see gates
python3 scripts/signal_compactor.py --dry

# Check current ATR for tokens
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from volatility_gate_v2 import get_atr_pct, classify_volatility
for t in ['APT', 'FIL', 'BTC', 'GOAT', 'INJ']:
    atr = get_atr_pct(t)
    print(f'{t}: ATR={atr:.2f}% → {classify_volatility(atr)}')
"

# Check hotset history
grep 'Wrote hotset' logs/signal-compactor.log | grep -v 'with 0 tokens' | tail -5

# Check gate kills today
grep '2026-10-19' logs/signal-compactor.log | grep -E '🚫.*BLOCKED|🚫.*blocked' | grep -oP '\[([A-Z-]+)\]' | sort | uniq -c | sort -rn
```

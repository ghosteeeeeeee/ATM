# Pump-Chain+ Exit Analysis — 2026-09-21

## Problem Statement

pump-chain+ trades are being stopped out too early, then the price recovers after we're out.

## Missed Opportunities (Last 13 Trades)

| Token | Exit | Peak After | Missed | What Happened |
|-------|------|------------|--------|---------------|
| ALGO | -1.4% | +6.0% | **+7.4%** 🚨 | Stopped out, then pumped |
| HEMI | -1.4% | +3.9% | **+5.3%** 🚨 | Stopped out, then pumped |
| CAKE | -1.6% | +1.0% | **+2.6%** ⚠️ | Stopped out, then recovered |
| NOT | -1.8% | +0.2% | **+2.0%** | Stopped out, barely recovered |
| FIL (volume-breakout) | +4.4% | +4.2% | -0.2% | ✅ Good exit — caught the move |

## pump-chain+ Performance (Last 30 Days)

| Metric | Value |
|--------|-------|
| Total trades | 69 |
| Wins | 32 (46.4%) |
| Avg PnL | +$0.04 |
| Avg PnL % | +1.55% |

### Exit Reasons
| Exit | Trades | WR | Avg PnL |
|------|--------|-----|---------|
| atr_sl_hit | 57 | 45.6% | +$0.03 |
| profit-monster-trail | 5 | 80.0% | +$0.08 |
| rr_engine | 5 | 40.0% | +$0.10 |

## Analysis

### Why Ride-It Wouldn't Fix pump-chain+

1. **46.4% WR** — more than half the entries are bad
2. **Wider SL = bigger losses on bad entries** — currently losing -1.4% to -1.6%, would lose -2.5% to -3.5% with ride_it
3. **The problem is ENTRY QUALITY, not exit management** — bad entries get stopped out because they're bad, not because the SL is too tight

### Why Ride-It Works for volume-breakout

1. **Better signal quality** — volume-breakout fires fewer but higher-conviction trades
2. **Delayed spikes** — the signal predicts moves that happen hours later
3. **Wide SL survives the wait** — ride_it's 2x ATR SL survives the pre-spike dip

### The Tradeoff

| Approach | Good Entries | Bad Entries |
|----------|-------------|-------------|
| Current (tight SL) | Stopped out early, miss recovery | Small loss, cut fast |
| Ride-It (wide SL) | Survive dip, catch recovery | Bigger loss, hold longer |

## Recommendation

1. **Keep pump-chain+ on pump_exit** — don't switch to ride_it
2. **Keep volume-breakout on ride_it** — already done
3. **Improve pump-chain+ entry filters** — the problem is bad entries, not exits

### Entry Filter Ideas for pump-chain+

- **BTC trend alignment** — only LONG when BTC is bullish (already have directional bias)
- **Volume confirmation** — require volume spike at entry
- **RSI filter** — don't enter when RSI > 70 (overbought)
- **Time-of-day filter** — avoid entries during low-liquidity hours
- **Regime filter** — only enter in HIGH/EXTREME (where pump-chain+ has better WR)

## Files

- Ride-It exit spec: `/root/.hermes/plans/ride-it-exit-spec.md`
- Ride-It exit module: `/root/.hermes/scripts/ride_it_exit.py`
- Bug hunter reports: `/root/.hermes/brain/verdicts/ride-it-exit-bug-hunter*.md`

---

# Pump-Chain+ Regime Block Dead Code — 2026-09-21

## Problem Statement

All 7 regime blocks in signal_compactor.py are dead code. They check for volatility regime values (HIGH/EXTREME/FLAT/NORMAL) but the 4h regime scanner only produces momentum values (LONG_BIAS/SHORT_BIAS/NEUTRAL).

## Root Cause

Two independent regime systems were built:
- **Momentum regime** (4h_regime_scanner → `momentum_cache.regime_4h`): `LONG_BIAS`/`SHORT_BIAS`/`NEUTRAL`
- **Volatility regime** (ATR-based → `signal_outcomes.regime`): `FLAT`/`NORMAL`/`HIGH`/`EXTREME`

The compactor reads momentum regime but compares against volatility values. Never matches.

## Dead Code Blocks

| Block | Line | Expected | Actual | Status |
|-------|------|----------|--------|--------|
| pump-chain+ HIGH | 2344 | HIGH | NEVER True | ❌ DEAD |
| v3 SHORT EXTREME | 2320 | EXTREME | NEVER True | ❌ DEAD |
| v3 LONG EXTREME | 2327 | EXTREME | NEVER True | ❌ DEAD |
| v3 SHORT FLAT | 2323 | FLAT | NEVER True | ❌ DEAD |
| v3 LONG FLAT | 2330 | FLAT | NEVER True | ❌ DEAD |
| accel-300 FLAT | 2336 | FLAT | NEVER True | ❌ DEAD |
| coiled-spring NORMAL | 2354 | NORMAL | NEVER True | ❌ DEAD |

## Impact

- pump-chain+ fires in HIGH regime (47% WR) instead of being blocked
- accel-300 fires in EXTREME/FLAT (33-42% WR) instead of being blocked
- Coiled-spring blocks ALL signals (NEUTRAL ≠ NORMAL)

## Fix

Change blocks to use `_get_volatility_regime()` instead of `_regime_4h`.

## Verified By

- Independent audit (own-conclusions skill) — HIGH confidence
- Pipeline logs — 0 firings of any regime block
- PostgreSQL momentum_cache — no HIGH/EXTREME/FLAT/NORMAL values exist

---

# Pump-Chain+ Regime Fix — 2026-09-21

## Problem

All 7 regime blocks in signal_compactor.py are dead code or actively broken:
- Blocks 1-6: Dead code (check for volatility values but momentum scanner never produces them)
- Block #7 (coiled-spring): **Actively broken** — always blocks because 'NEUTRAL' ≠ 'NORMAL'

## Fix

Change blocks to use `_classify_volatility()` with cached ATR instead of `_regime_4h`:
- `_classify_volatility()` is already imported in signal_compactor.py (line 64)
- It takes a pre-computed ATR% and returns FLAT/NORMAL/HIGH/EXTREME
- Cache ATR% at `run_compaction` level to avoid per-signal DB overhead

## Expected Impact

- pump-chain+ blocked in HIGH regime (47% WR → 56% WR in EXTREME)
- accel-300 blocked in EXTREME/FLAT (33-42% WR)
- Coiled-spring unblocked (currently always blocked)

## Verified By

- Independent audit (own-conclusions skill) — HIGH confidence
- Confirmed 7 dead/broken blocks
- Confirmed `_classify_volatility()` returns expected values

---
name: analyze-trades
description: Archive closed trades, reconcile prices, rebuild A/B test data, analyze results, and apply winning adjustments to Hermes trading system.
tags: [hermes, trading, analysis, ab-test, trades]
author: T
created: 2026-04-01
updated: 2026-04-01
---

# Analyze Trades — Hermes Trading Analysis

Archives closed trades, rebuilds A/B test data with corrected experiment parsing, analyzes results, and applies indicator weight adjustments.

## Quick Run

```bash
# 1. Archive closed trades
TS=$(date +%Y%m%d_%H%M)
sudo -u postgres psql -d brain -t -c "
CREATE TABLE IF NOT EXISTS trades_archive_${TS} AS SELECT * FROM trades WHERE status='closed';
DELETE FROM trades WHERE status='closed';
DELETE FROM ab_results;
"

# 2. Run analysis queries (see below)

# 3. Update this skill with findings
```

## Archive + Reconcile

```python
HERMES_DB = '/root/.hermes/data/hermes.db'
RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'
```

## Key Findings (2026-04-01 — 120 archived trades)

### System Bug Summary
| Bug | Count | Net PnL | Impact |
|-----|-------|---------|--------|
| hl_position_missing | 38 | -$9.60 | HL didn't register position — timing race, most expensive bug |
| guardian_missing | 32 | +$2.78 | Guardian not connected — positions forced closed at near-0 |
| guardian_orphan | 7 | -$0.08 | Guardian couldn't find position, marked orphan |
| stale-no-move | 1 | +$2.56 | Manual stale closure, small win |

### System Health
- **Total closed:** 120 trades | 46 wins / 74 losses (38.3% WR)
- **Net PnL:** +$3.96
- **Gross wins:** +$96.59 | Gross losses: -$92.63
- **Avg win:** +133.42% | Avg loss: -114.08%
- Long trades: +$57.58 (21W/15L, 58% WR) | Short trades: -$53.62 (25W/59L, 30% WR)

### A/B Test Results (by SL distance variant)

| SL Variant | n | Net PnL | Avg % | WR | Avg Win% | Avg Loss% | Verdict |
|-----------|---|---------|-------|----|---------|---------|---------|
| SL-3p0 (3%) | 2 | +$20.03 | +200.32 | 100% | +200.32 | — | 🔥 TOO FEW SAMPLES |
| SL-1p5 (1.5%) | 22 | +$4.67 | +50.46 | 55% | +138.62 | -55.32 | ✅ BEST DATA, keep |
| SL-1p2 (1.2%) | 2 | +$1.39 | +13.81 | 50% | +140.32 | -112.70 | ⚠️ TOO FEW SAMPLES |
| SL-1p0 (1.0%) | 24 | -$11.46 | +15.38 | 46% | +142.00 | -91.76 | ⚠️ NARROWING LOSES MORE |
| SL-0p5 (0.5%) | 2 | -$1.25 | -16.54 | 0% | — | -16.54 | ❌ TOO TIGHT, avoid |

**A/B Verdict:** SL-1p5 is holding up as the sweet spot with best data (n=22). SL-1p0 narrows the buffer too much — losses get stopped out faster. Wider 3% looks great but only 2 samples.

### Confluence Level Analysis (biggest signal quality insight)

| Sources | n | Net PnL | Avg % | WR | Verdict |
|---------|---|---------|-------|----|---------|
| conf-24s | 4 | +$8.85 | +135.23 | 100% | 🔥 24-source consensus |
| conf-9s | 4 | +$9.27 | +35.39 | 50% | ✅ strong agreement |
| conf-15s | 5 | -$5.67 | +74.44 | 40% | ⚠️ mixed |
| conf-5s | 8 | +$5.65 | +6.33 | 50% | ✅ mid-tier OK |
| conf-27s | 5 | -$1.07 | +1.58 | 60% | ⚠️ 27 sources = overbought |
| conf-2s | 7 | -$5.00 | -25.28 | 14% | ❌ 2 sources barely enough |
| conf-1s | 14 | -$9.92 | -34.69 | 29% | ❌ single source = noise |

**Confluence Verdict:** Single source (conf-1s) is a coin flip and loses money. 2 sources is barely better than random. **Minimum 3 agreeing sources needed** — conf-24s (24 sources!) is perfect. Consider raising minimum confluence threshold.

### Directional Bias

| Direction | n | Net PnL | WR | Verdict |
|-----------|---|---------|----|---------|
| LONG | 36 | +$57.58 | 58% | ✅ long bias works |
| SHORT | 84 | -$53.62 | 30% | ❌ shorts bleeding |

### SHORT Blacklist Candidates (SHORTs with 0 wins, avg < -50%)
Add to SHORT_BLACKLIST in hermes_constants.py:
- `SOL` (2 trades, -$5.74, avg -609%) — catastrophic on shorts
- `XPL` (3 trades, -$8.79, avg -235%)
- `ZRO` (3 trades, -$4.77, avg -220%)
- `NEO` (2 trades, -$1.30, avg -197%)
- `GMT` (2 trades, -$4.62, avg -177%)
- `FTT` (2 trades, -$0.34, avg -148%)
- `HYPE` (2 trades, -$0.84, avg -129%)
- `XLM` (4 trades, -$0.45, avg -121%)
- `DOGE` (2 trades, -$1.12, avg -98%)
- `MERL` (3 trades, +$2.32, avg -93%) — mixed but high variance

### LONG Blacklist Candidates
- `KAS` (2 trades, -$3.11, avg -85%) — remove from LONG
- `PROVE` (3 trades, -$0.91, avg -84%) — remove from LONG

### Top Performers (profitable tokens)
- `PENGU` LONG (2 trades, +$10.24, avg +189%)
- `TAO` LONG (2 trades, +$3.42, avg +133%)
- `2Z` SHORT (4 trades, +$1.38, avg +143%)
- `AAVE` LONG (3 trades, +$0.78, avg +101%)
- `FIL` LONG (3 trades, +$0.17, avg +100%)

## Actions Required

### 1. Update hermes_constants.py — add new blacklist tokens
```python
SHORT_BLACKLIST = {
    'SUI','FET','SPX','ARK','TON','ONDO','CRV','RUNE','AR',
    'NXPC','DASH','ARB','TRUMP','LDO','NEAR','APT','CELO','SEI',
    'ACE','YZY','ZEREBRO','WLFI','HBAR','MEGA',
    # NEW from trade analysis:
    'SOL','XPL','ZRO','NEO','GMT','FTT','HYPE','XLM','DOGE','MERL'
}
LONG_BLACKLIST = {'SEI', 'ACE', 'KAS', 'PROVE'}  # add KAS, PROVE
```

### 2. Raise minimum confluence threshold
In signal_gen.py or signal flow: **require minimum 3 agreeing sources** before generating a signal. Single and dual-source signals are noise.

### 3. Guardian fix — check hl-sync-guardian.py
32 trades got `guardian_missing` exits. The guardian process exists but may not be connecting to all positions. Check: does guardian monitor all open trades? Are there race conditions on position open?

### 4. HL position race condition
38 trades got `hl_position_missing` — the worst bug by impact. Hyperliquid isn't registering positions before guardian tries to manage them. Add retry/delay logic.

## Hot Set Validation Rules

Tokens in hot set must have ALL of:
- `z_score` not NULL
- `rsi_14` not NULL
- `macd_hist` not NULL
- `confidence` > 60
- Minimum 3 signal sources (confluence check)

Missing any = disqualified, log:
```
HOT_SET_DISQUALIFIED: {token} missing {column}
```

## Re-run Analysis

Run this skill weekly or after major pipeline changes. Archive before each run.

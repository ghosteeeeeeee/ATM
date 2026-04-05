---
name: analyze-trades
description: Archive closed trades, reconcile prices, rebuild A/B test data, analyze results, and apply winning adjustments to Hermes trading system.
tags: [hermes, trading, analysis, ab-test, trades]
author: T
created: 2026-04-01
updated: 2026-04-04
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
```

## Key Findings (2026-04-04 — 158 archived trades)

### System Bug Summary
| Bug | Count | Impact |
|-----|-------|--------|
| hl_position_missing | 21 | HL didn't register position — corrupted prices (PAXG $4650!). Guardian sanity check added. |
| guardian_close | 26 | Guardian-managed zero-PnL exits |
| guardian_missing | 30 | Guardian lost track, forced near-zero close |
| zombie_cleanup | 6 | Stale position cleanup, zero PnL |

### System Health (phantoms excluded from analysis)
- **Total real closed:** 73 trades | 29W/44L | 40% WR
- **Net PnL:** +$13.26 | Gross wins: +$148.67 | Gross losses: -$135.41
- Avg win: +$5.13 | Avg loss: -$2.94
- LONG: 65 trades (28W/37L, 43% WR) net=+$28.68  ← WORKING
- SHORT: 8 trades (1W/7L, 12% WR) net=-$15.42  ← Regime filter now suppresses these

### A/B Test Results (by SL distance variant)
| SL Variant | n | Net PnL | WR | Verdict |
|-----------|---|---------|----|---------|
| SL-3.0 (3.0%) | 38 | +$27.09 | 39% | ✅ BEST DATA, best net — PRIMARY |
| SL-2.0 (2.0%) | 25 | +$11.06 | 48% | ✅ Best WR — was test_a |
| SL-1.5 (1.5%) | 8 | -$21.89 | 25% | ❌ Too tight — loses money |
| SL-1.0 (1.0%) | 8 | -$21.89 | 25% | ❌ Confirmed too tight |

**A/B Verdict:** SL-3.0 primary. test_a changed to 1.5% (was 2.0%, too close to SL-1.0). SL-1.0 confirmed catastrophic — avoid.

### Directional Bias
- LONG: 43% WR, +$28.68 net — system is long-biased and it works
- SHORT: 12% WR, -$15.42 net — regime filter suppresses counter-regime shorts
- Hotset currently 49 LONG : 1 SHORT — filter is working

### Top Performers (real trades)
| Token | Direction | Result |
|-------|-----------|--------|
| GRIFFAIN | LONG | 3W/0L, +100% WR, +$13.89 |
| HEMI | LONG | 2W/1L, +67% WR, +$14.16 |
| ALT | LONG | 1W, +$25.70 |
| IOTA | LONG | 1W, +$14.62 |
| GMX | LONG | 2W/0L, +100% WR, +$6.93 |

### BLACKLIST UPDATES (2026-04-04)
**via closed-trades-eval skill:**
- SHORT: +ENA (net -$5.41), +PENGU (net -$4.36)
- LONG: +0G, +2Z, +AIXBT, +BERA, +BLUR, +BSV, +DYM, +GRASS, +GRIFFAIN, +MAVIA, +MON, +OP, +POLYX, +PROMPT, +REZ, +XMR, +ZETA

## Actions Required

### 1. SL variants — DONE (brain.py)
- test_a changed from 0.02 → 0.015 (SL-1.5%)
- test_b remains 0.01 (SL-1.0%, confirmed bad, kept for negative data)
- control remains 0.03 (SL-3.0%, primary)

### 2. Guardian price sanity — DONE (hl-sync-guardian.py)
Added PnL >1000% check in `_close_paper_trade_db`. If a close would produce >1000% or <-99% PnL, the close is rejected (set to zero PnL at entry price) to prevent corrupted cache prices from polluting the DB.
- PAXG was showing $4650 in hype_cache (2x gold price), causing +$1.5M phantom PnL entries
- BCH was similarly corrupted

### 3. SHORT suppression — No action needed
Regime filter in decider-run.py lines 824-829 is working. Current hotset: 49 LONG / 1 SHORT. Per-token z_score tier check (lines 838-862) provides additional filtering. Bull market thesis intact.

### 4. HL position race condition — Ongoing
- Guardian already retries 3x with 5s delay before marking `hl_position_missing`
- Root cause: HL API lag on position registration
- Sanity check prevents DB corruption but doesn't fix the underlying race

## Hot Set Validation Rules

Tokens in hot set must have ALL of:
- `z_score` not NULL
- `rsi_14` not NULL
- `macd_hist` not NULL
- `confidence` > 60
- Minimum regime alignment check (per-token z_score_tier + macro regime)

## Re-run Analysis

Run this skill weekly or after major pipeline changes. Archive before each run.

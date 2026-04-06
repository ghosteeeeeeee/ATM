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

## Key Findings (2026-04-06 — 209 closed trades after cleanup)

### System Bug Summary
| Bug | Count | Impact |
|-----|-------|--------|
| hl_position_missing | 19 DELETED | Orphan HL positions with corrupted entry prices (~$10). Root cause: `add_orphan_trade` parameter swap (entry_price ↔ amount_usdt). Fix applied 2026-04-05. |
| guardian_missing | ~50 | Guardian lost track, forced near-zero close — top winners |
| trailing_exit | ~30 | Trailing SL triggered — solid wins |

### System Health (cleaned)
- **Total closed:** 209 trades (after 19 corrupted deletions)
- **Net PnL:** +$17.90 | LONG: +$10.84 | SHORT: +$7.06
- LONG: 92 trades (43W/49L, 47% WR)
- SHORT: 117 trades (53W/64L, 45% WR) ← unexpectedly strong
- SHORT outperforming LONG in recent period — regime filter may be too aggressive on LONG bias

### Top Winners (cleaned)
| Token | Direction | pnl$ | Reason |
|-------|-----------|------|--------|
| ME | LONG | +$2.01 | guardian_missing |
| ME | LONG | +$1.63 | guardian_missing |
| PENDLE | LONG | +$1.18 | trailing_exit_+2.52% |
| ME | LONG | +$1.16 | guardian_missing |
| PEOPLE | LONG | +$1.06 | trailing_exit_+2.00% |
| VVV | SHORT | +$1.05 | trailing_exit_+1.82% |
| CFX | LONG | +$0.98 | trailing_exit_+2.03% |

### Systematic Losers
| Token | Direction | n | Net | Action |
|-------|-----------|---|-----|--------|
| ME | LONG | 10 | -$2.77 | **ADDED TO BLACKLIST** 2026-04-06 |

### Guardian Missing Dominance
- Most top winners closed via `guardian_missing` (guardian closed positions near peak before trailing SL could trigger)
- Trailing exits are working but not capturing the biggest moves
- Consider: guardian may be too aggressive — closing at 1-2% when trailing could capture 3-5%

## BLACKLIST UPDATES (2026-04-06)
- **+ME** to LONG_BLACKLIST — 10 trades, net -$2.77 (hermes_constants.py)

## Actions Required

### 1. ME LONG blacklist — DONE
Added to LONG_BLACKLIST in hermes_constants.py. Guardian will now close any open ME LONG positions.

### 2. Corrupted trades purged — DONE
19 `hl_position_missing` trades with entry ~$10 (swap bug) deleted. DB now clean.

### 3. SHORT vs LONG balance — MONITOR
SHORT WR 45% vs LONG WR 47% in recent batch. System may be over-filtering SHORT signals.
Consider: relax SHORT regime filter if SHORT WR continues to outperform.

### 4. Guardian aggressiveness — Consider
Guardian is closing trades before trailing SL triggers. Current trailing_activation=1%, trailing_distance=0.5%.
Top winners close at 1-2% via guardian while trailing SL could capture 3-5%.

## Hot Set Validation Rules

Tokens in hot set must have ALL of:
- `z_score` not NULL
- `rsi_14` not NULL
- `macd_hist` not NULL
- `confidence` > 60
- Minimum regime alignment check (per-token z_score_tier + macro regime)
- NOT in HOTSET_BLOCKLIST

## Re-run Analysis

Run this skill weekly or after major pipeline changes. Archive before each run.

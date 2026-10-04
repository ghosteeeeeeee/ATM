# Signal Performance Report
**Generated:** 2026-10-04 17:13 UTC | **Period:** Last 6h + 24h
**Source:** PostgreSQL brain DB (queried live, not cached)

## Overall Stats
- **6h closed:** 6 trades | WR 33.3% | PnL **-$0.77**
- **24h closed:** 29 trades | WR 48.3% | PnL **-$1.04**
- **Kill switch:** live_trading=true | LIVE_TRADING_ENABLED=True

---

## KILLED (executed)
None. Freeze b960ffe8 (until 2026-10-06 00:38) blocks trading config changes.

## REGIME-BLOCK (PENDING freeze lift — HIGH wins, not a kill)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v3-long+ | LONG | 25.0% | -$0.72 | 8 (24h) | Block NORMAL only (0.0x). HIGH 6T 66.7% +$0.09 kept. Flag stays True. |

**Evidence (all-time regime):**
- NORMAL: 13T, 46.2% WR, -$0.55 ← losing habitat
- HIGH: 6T, 66.7% WR, +$0.09 ← winning (≥55% → no blanket kill)
- 7d overall: 18T, 55.6% WR, -$0.44 (exits bleed more than entries)
- Active since 2026-09-21 (>24h)
- 24h tokens: CFX/ME/COMP/SUSHI/ENS losses; DOT/WCT only winners

**Planned edit (post-freeze, Oct 6):** `scripts/volatility_gate_v2.py` SIGNAL_TYPE_OVERRIDES
```
('NORMAL', 'bb_bounce_v3_long'): 0.0,   # signal_type form
('NORMAL', 'bb-bounce-v3-long'): 0.0,   # source form
('HIGH', 'bb_bounce_v3_long'): 1.0,     # keep winner
('HIGH', 'bb-bounce-v3-long'): 1.0,
```
- `BB_BOUNCE_V3_LONG_ENABLED` remains **True** (verified)
- FAMILY_MAP already has `bb-bounce-v3-long` (hyphen); underscore form maps to `Other` — see ISSUES
- CEO already tracking this signal for post-freeze RSI_MAX 55→40 (kanban 13:50)

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| bb-squeeze+ | LONG | 61.5% | +$0.19 | 13 (24h) | Already at 1.2x (boosted 2026-10-03). No further change. |

**bb-squeeze+ detail:**
- 24h: 13T 61.5% +$0.19 | 7d: 47T 61.7% +$0.50
- Multi-token winners: BLUR +0.49 (2T), SYRUP +0.08, ALT +0.06 (2T), NEAR/LDO +0.05
- Regime: NORMAL 66.7% +$0.27, HIGH 65.4% +$0.38, EXTREME 50% -$0.15 (already blocked)
- Meets boost criteria; weight already raised yesterday — maintain

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v3-long+ | LONG | 25.0% | -$0.72 | 8 | REGIME-BLOCK pending freeze (see above) |
| doji-bottom-long | LONG | 0% | -$0.25 | 1 | n<5 — watch |
| pump-chain- | SHORT | 0% | -$0.24 | 1 | n<5 — watch |
| volume-breakout-long+ | LONG | 0% | -$0.11 | 1 | n<5 — watch |
| continuation+ | LONG | 0% | -$0.02 | 1 | n<5 — watch |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-squeeze+ | LONG | 61.5% | +$0.19 | 13 | Maintained at 1.2x |
| bb-bounce-v2-long+ | LONG | 100% | +$0.03 | 2 | Healthy |
| mtf-regime-trend- | SHORT | 100% | +$0.06 | 1 | Healthy |

## ISSUES
- **Direction inversions (24h):** none found. Clean.
- **Freeze conflict:** regime-block for bb-bounce-v3-long+ is the correct action per SOP (HIGH wins ≥55%) but cannot execute until freeze lifts Oct 6 00:38. Already on CEO post-freeze list.
- **FAMILY_MAP gap (sideways):** `signal_family('bb_bounce_v3_long')` → `'Other'` (underscore form missing from Bollinger list; only hyphen `bb-bounce-v3-long` present). Family-level Bollinger blocks therefore do not apply to the signal_type form. Post-freeze: add `'bb_bounce_v3_long'` to FAMILY_MAP **and** the HIGH:1.0 override together, or the HIGH family Bollinger:0.0 block could kill the winner.
- **psycopg2 gotcha:** `LIKE '%...%'` inside parameterized queries needs `%%` (or pass pattern as a bound param). `%` is a format placeholder. Hit this during this run; training-system flagged the same class earlier today.
- **System bleed:** 24h -$1.04 driven almost entirely by bb-bounce-v3-long+ NORMAL losses (-$0.72 of -$1.04).

---

*signal_reporter | DB-verified 2026-10-04 17:13 UTC | OpenMemory skipped (tenant_mismatch per task instructions)*

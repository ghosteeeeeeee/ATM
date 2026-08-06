# CEO Report — 2026-08-06

## 24h Performance
| Metric | Value |
|--------|-------|
| Total trades | 151 |
| Win rate | 55.6% |
| Net PnL | **+$2.71** |

**Top signals:**
- `tl_break_long`: 14 trades, **100% WR**, +$1.81
- `vel-hermes-`: 46 trades, 43.5% WR, +$0.47
- `zscore-rising+`: 8 trades, 62.5% WR, +$0.23

**Losers:**
- `decider`: 9 trades, 11.1% WR, -$0.18
- `bb_bounce`: 16 trades, 62.5% WR, -$0.15

## System Health
- Pipeline timer: **active** ✓
- HL sync guardian: **active** ✓
- Live trading: **enabled** (re-enabled 02:15 UTC)
- Trailing: tightened (0.30%/0.70%)

## URGENT Issues
1. **bb_bounce STILL FIRING** — 16 trades/24h despite `BB_BOUNCE_ENABLED=False` + `NEVER_REENABLE_FLAGS`. Root cause: line 876 had `BB_BOUNCE_ENABLED=True` (someone re-enabled). Fixed but still firing — possible stale data or registration leak.
2. **decider firing 9 trades** — should be dead after commit 62c549f. Investigate registration bypass.
3. **vel-hermes- firing 46 trades** — in `NEVER_REENABLE_FLAGS` but still generating. Signal registration leak.

## Active Monitoring
- `ma_100_cross`: W LONG first trade opened (03:36). 48h trial.
- `hzscore+` confluence: 100% WR (5/5 today), small PnL per trade but consistent.
- `vortex_break` + `return_exhaustion`: 48h trial window ongoing.

## Open Positions
~200 positions in HL. Largest unrealized PnL: HYPE ($6.7M unrealized on massive positions), BTC ($170K), ETH ($232K).

## Decisions Required
1. **DELEGATE to bug_hunter**: bb_bounce + decider + vel-hermes- signal leak. NEVER_REENABLE_FLAGS not blocking.
2. **CONTINUE monitoring** ma_100_cross and hzscore+ for 48h before parameter changes.
3. **CONSIDER** position size review — 200+ open positions with mixed leverage (3-40x) is high exposure.

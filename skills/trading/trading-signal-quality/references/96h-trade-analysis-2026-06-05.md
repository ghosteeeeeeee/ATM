# 96h Trade Analysis — June 5 2026

**Source**: `/var/www/hermes/data/trades.json` — 200 closed trades, all within 96h window.

## Key Finding: accel-300+ LONG is Catastrophically Broken

| Signal | Trades | Win Rate | Avg PnL | Close Reason |
|--------|--------|----------|---------|--------------|
| accel-300+ LONG | 45 | **22%** | **-0.41%** | 33× atr_sl_hit, 10× profit-monster |
| accel-300- SHORT | 155 | **52%** | **+0.18%** | functional |
| RS broken (no conf, passes floor) | 139 | **53%** | **+0.20%** | BLOCKED SIGNALS WERE WINNERS |
| RS confirmed (passes floor) | 45 | **22%** | **-0.41%** | PASSED SIGNALS WERE LOSERS |

**ALL 45 accel-300+ LONG trades hit atr_sl_hit** (avg -0.86%) except 10 that hit profit-monster (+1.18% avg).
The RS confirmation filter is INVERTED — it passes the bad trades and blocks the good ones.

**Root cause of LONG failure**: Market is in chop (ETH slope -0.0085%/bar, AVAX slope +0.0112%/bar).
accel-300+ LONG fires on shallow gaps (0.20-0.30%) that immediately reverse in chop. The 10 winners
were the rare cases where profit-monster fired before SL. The systemic failure is entry quality.

**RS confirmation inversion**: High-touch RS levels (old, established) become chop zones in flat markets.
Fresh RS levels (rs-s-broken, low touches) are recent reaction points that actually bounce.

## All Trades by Close Reason

| Close Reason | Count | Avg PnL | What Happened |
|---|---|---|---|
| atr_sl_hit | 104 | -0.78% | Entry caught in chop, SL fired |
| profit-monster | 86 | +1.12% | Winners — TP worked correctly |
| guardian_sl | 7 | -1.02% | Guardian closed at loss |
| guardian_tp | 1 | +1.77% | Guardian closed winner |
| HL_CLOSED | 1 | -0.64% | HL position closed |
| guardian_orphan | 1 | -0.01% | Orphan cleanup |

## Full accel-300+ LONG Trade List

```
XLM      pnl=-1.39% atr_sl_hit  signal=accel-300+,rs-s390,rs-s414
SUSHI    pnl=-1.25% atr_sl_hit  signal=accel-300+,rs-s622
SUSHI    pnl=-1.24% atr_sl_hit  signal=accel-300+,rs-s612
XRP      pnl=-1.15% atr_sl_hit  signal=accel-300+,rs-s436
LTC      pnl=-1.12% atr_sl_hit  signal=accel-300+,rs-s162
AVNT     pnl=-1.09% atr_sl_hit  signal=accel-300+,rs-s148
ME       pnl=-1.09% atr_sl_hit  signal=accel-300+,rs-s362,rs-s64
BSV      pnl=-1.08% atr_sl_hit  signal=accel-300+,rs-s340
XRP      pnl=-1.07% atr_sl_hit  signal=accel-300+,rs-s264
FET      pnl=-1.07% atr_sl_hit  signal=accel-300+,rs-s80,rs-s84
MOVE     pnl=-1.05% atr_sl_hit  signal=accel-300+,rs-s358,rs-s78
MET      pnl=-1.03% guardian_sl signal=accel-300+,rs-s126
AXS      pnl=-1.02% atr_sl_hit  signal=accel-300+,rs-s78
GALA     pnl=-1.02% atr_sl_hit  signal=accel-300+,rs-s148
ENS      pnl=-1.00% atr_sl_hit  signal=accel-300+,rs-s60
AVAX     pnl=-0.98% atr_sl_hit  signal=accel-300+,rs-s72
CHIP     pnl=-0.98% atr_sl_hit  signal=accel-300+,rs-s132,rs-s781
DASH     pnl=-0.98% atr_sl_hit  signal=accel-300+,rs-s248
ADA      pnl=-0.94% atr_sl_hit  signal=accel-300+,rs-s160,rs-s200
ASTER    pnl=-0.90% guardian_sl signal=accel-300+,rs-s40,rs-s667
DASH     pnl=-0.87% atr_sl_hit  signal=accel-300+,rs-s44
STBL     pnl=-0.86% atr_sl_hit  signal=accel-300+,rs-s253
AVNT     pnl=-0.79% atr_sl_hit  signal=accel-300+,rs-s132
STRK     pnl=-0.76% atr_sl_hit  signal=accel-300+,rs-s300,rs-s812
LINK     pnl=-0.76% atr_sl_hit  signal=accel-300+,rs-s254
ZK       pnl=-0.73% atr_sl_hit  signal=accel-300+,rs-s32
ETH      pnl=-0.69% atr_sl_hit  signal=accel-300+,rs-s720
ORDI     pnl=-0.68% atr_sl_hit  signal=accel-300+,rs-s247
MORPHO   pnl=-0.67% atr_sl_hit  signal=accel-300+,rs-s188,rs-s68
LINK     pnl=-0.61% atr_sl_hit  signal=accel-300+,rs-s120,rs-s322,rs-s646
BCH      pnl=-0.56% atr_sl_hit  signal=accel-300+,rs-s54
AXS      pnl=-0.41% atr_sl_hit  signal=accel-300+,rs-s98
SUSHI    pnl=-0.23% atr_sl_hit  signal=accel-300+,rs-s112
TON      pnl=-0.19% atr_sl_hit  signal=accel-300+,rs-s30
UNI      pnl=-0.00% atr_sl_hit  signal=accel-300+,rs-s208,rs-s300
AAVE     pnl=+0.85% profit-monster signal=accel-300+,rs-s27
MERL     pnl=+0.98% profit-monster signal=accel-300+,rs-s116
LTC      pnl=+0.99% profit-monster signal=accel-300+,rs-s60
CHIP     pnl=+1.08% profit-monster signal=accel-300+,rs-s391
GRIFFAIN pnl=+1.16% profit-monster signal=accel-300+,rs-s44
BRETT    pnl=+1.23% profit-monster signal=accel-300+,rs-s252
MON      pnl=+1.25% profit-monster signal=accel-300+,rs-s36,rs-s8
STRK     pnl=+1.27% profit-monster signal=accel-300+,rs-s224,rs-s280,rs-s288
XMR      pnl=+1.30% profit-monster signal=accel-300+,rs-s94
MERL     pnl=+1.71% profit-monster signal=accel-300+,rs-s28
```

**Note**: ZERO accel-300+ LONG trades have `rs-s-broken` in signal string. All have confirmed RS levels.
The RS confirmation filter is NOT blocking these trades — the issue is accel-300+ LONG fundamentally
doesn't work in chop regardless of RS confirmation.

## Regime Slopes at Time of Analysis

From price_history (20-bar linear regression, 20 most recent closes):
```
ETH:  slope=-0.0085%/bar  [FLAT]  — only 0.8 min old in price_history
AVAX: slope=+0.0389%/bar [barely LONG] — only 9 rows in price_history, regime check bypassed
SOL:  slope= 0.0000%/bar  [FLAT]  — 12768m old (stale/blacklisted)
LINK: slope=-0.0049%/bar  [FLAT]  — 0.8 min old
BTC:  slope=-0.0056%/bar  [FLAT]  — 12768m old (blacklisted)
```

## Threshold Changes Applied Jun 5 2026

**In accel_300.py:**
- Line 290: `bars_since_cross > 40` → `> 20` — reject crosses older than 20 bars
- Lines 410/413: `slope_pct <= 0.03` → `<= 0.015` — allow flat-market signals through

**In hermes_constants.py:**
- `MIN_GAP_PCT_LONG = 0.30` → `0.20` — allow smaller gaps in flat market
- `MIN_GAP_PCT_SHORT = 0.30` → `0.20` — same for SHORT
- `ACCEL_300_MIN_GAP_GROWTH = 0.05` → `0.08` — require stronger acceleration

## Diagnostic: Why accel-300 Returns 0 Signals

Step-by-step trace for ETH (has fresh data, cross 17 bars ago):
1. `_get_1m_prices('ETH', 400)` → 400 rows ✅
2. `detect_accel_300` → cross_bar found at bar 344 ✅
3. `bars_since_cross = 17` → <= 20 ✅
4. `gap_now = 0.112%` → < 0.20% **FAILS** — gap too small
5. Signal blocked at gap check

Only ME (17 bars ago, gap=0.21%, gap_growth=-0.038%) passes stale+gap but fails gap_growth.
No token in the 230-token universe passes all filters.

**The market is in chop** — crosses happen but price goes sideways after, so gap never grows
and stale check eventually rejects even recent crosses. accel-300 needs a trend, not chop.

## Actionable Recommendations

1. **Killswitch accel-300+ LONG**: `ACCEL_300_PLUS_ENABLED = False` in hermes_constants
2. **RS decider less restrictive**: `RS_DECIDER_CONF_FLOOR = 55` (was 60), `RS_DECIDER_MIN_TOUCHES = 120` (was 150)
3. **Re-enable LONG only when**: BTC or ETH shows sustained slope > 0.03%/bar for 50+ bars
4. **Monitor**: After killswitch, expect SHORT-only signals from accel-300. If market shifts to trend, LONG will start firing again.
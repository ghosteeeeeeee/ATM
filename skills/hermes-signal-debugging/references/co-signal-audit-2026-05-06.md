# Co-Signal Audit Findings — 2026-05-06

## Data Source
742 trades, PostgreSQL `trades` table, deduplicated by token-direction-week.

---

## Winning Combos (verified ≥3 trades)

### LONG — Best Combos
| Combo | Trades | WR | Avg% |
|-------|--------|-----|------|
| `accel-300+,trend_purity+` | 8 | 62.5% | +0.36% |
| `accel-300+,hzscore-` | 30 | 36.7% | +0.66% |
| `gap-300-` | 75 | 40.0% | +0.22% |
| `accel-300+,hzscore-,trend_purity+` | 3 | 66.7% | +1.34% |

### SHORT — Best Combos
| Combo | Trades | WR | Avg% |
|-------|--------|-----|------|
| `hzscore+,pct-hermes-,vel-hermes-` | 39 | **46.2%** | +0.38% |

---

## Poison Combos (must block)

### SHORT Poison
- `hzscore+,vel-hermes-` WITHOUT `pct-hermes-` → **20% WR, −0.064% avg** (39 trades)
  - Adding `pct-hermes-` transforms it to 46.2% WR, +0.382% avg
  - Fix: require `pct-hermes-` as co-signal when both `hzscore+` and `vel-hermes-` present

### LONG Poison
- `accel-300+,ma-cross-5m+` → **16.7% WR, −0.32% avg**
- `accel-300+,pct-hermes+` WITHOUT `trend_purity+` → **35.7% WR, −0.26% avg**

---

## Top Winners (>3% PnL) — Signal Patterns

Signal appears in all top-30 winners:
- `accel-300+,hzscore-` — 5 trades, 100% WR, avg +4.33% (EIGEN +6.65%, MON +4.06%, OP +4.02%, ICP +3.73%, DYDX +3.19%)
- `hzscore+,pct-hermes-,vel-hermes-` — OP +4.29%, UNI +3.73%, AAVE +3.14%
- `gap-300-` — XMR +3.16%, ENS +3.06%, XLM +2.61%, CAKE +2.47%
- `pct-hermes+` standalone — STRK +3.38% (23m)

---

## ATR Trailing Stop — The Real Problem

`accel-300+,hzscore-` at 99% confidence:
- **Winners avg hold: 43 min** | **Losers avg hold: 21 min**
- Losers getting stopped in 4-8 min before momentum develops
- EIGEN held 139 min → +6.65%. MON held 18 min → +4.06%. OP held 39 min → +4.02%
- Losers: XMR -1.03% in 5.9m, BERA -0.20% in 6m, BLUR -0.45% in 8m

**Root cause:** Signal is correct but ATR trailing stop is too tight for this signal's natural rhythm. Winners need time; losers get sniped early.

---

## Flag Changes Made

| Flag | Before | After | Reason |
|------|--------|-------|--------|
| `PCT_HERMES_MINUS_ENABLED` | False | True | Key ingredient in 46.2% WR SHORT combo |
| `MTF_MOMENTUM_PLUS_ENABLED` | True | False | 0% WR in all observed combos |
| `MTF_MOMENTUM_MINUS_ENABLED` | True | False | 0% WR in all observed combos |
| `VEL_HERMES_ENABLED` (vel_hermes.py) | True | False | Match hermes_constants.py consistency |

---

## Co-Signal Gate Logic (signal_compactor.py)

```python
# SHORT: hzscore+ + vel-hermes- REQUIRES pct-hermes-
has_hz_pos  = any('hzscore+'  in s for s in co_signals)
has_vel_neg = any('vel-hermes-' in s for s in co_signals)
has_pct_neg = any('pct-hermes-' in s for s in co_signals)
if has_hz_pos and has_vel_neg and not has_pct_neg:
    return False, "POISON: hzscore+,vel-hermes- missing pct-hermes-"

# LONG: accel-300+ blocks ma-cross-5m+ and pct-hermes+ without trend_purity+
has_accel_pos = any('accel-300+' in s for s in co_signals)
has_ma5m_pos  = any('ma-cross-5m+' in s for s in co_signals)
has_pct_pos   = any('pct-hermes+' in s for s in co_signals)
has_tp_pos    = any('trend_purity+' in s for s in co_signals)
if has_accel_pos and has_ma5m_pos:
    return False, "POISON: accel-300+,ma-cross-5m+"
if has_accel_pos and has_pct_pos and not has_tp_pos:
    return False, "POISON: accel-300+,pct-hermes+ without trend_purity+"
```

---

## Stale Guardian-Closing Markers

Tokens stuck as "guardian closing" with no open HL position must have their markers cleared:
```python
# File: /root/.hermes/data/guardian-closing-markers.json
# Clean stale entries (tokens not in open positions)
```

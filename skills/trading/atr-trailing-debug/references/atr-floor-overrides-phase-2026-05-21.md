# ATR Floor Overrides Phase Multiplier — Low-ATR Token Failure (2026-05-21)

## Pattern: Phase k = 0.08 but SL Still 0.70% Away

**Root cause:** `ATR_SL_MIN_ACCEL = 0.70%` (and `ATR_SL_MIN_INIT = 0.70%`) acts as a hard floor
that overrides any phase multiplier for tokens with very low ATR%.

**FET case study:**
```
Token:       FET
ATR(14):     0.047% of price  (ultra-low volatility)
Phase:       EXTREME (percentile_short=81.5, percentile_long=19.0)
k_phase:     K_PHASE_EXTREME_FAST = 0.08
base_k:      0.50 (NORMAL_VOL tier: 1% < ATR < 3%)
eff_k:       0.08 × 0.50 = 0.04

Computation:
  sl_pct = eff_k × ATR% = 0.04 × 0.047% = 0.0019%
  MIN_SL_PCT = ATR_SL_MIN_ACCEL = 0.70%  ← FLOOR BINDS
  effective_sl_pct = max(0.0019%, 0.70%) = 0.70%

Result: SL always 0.70% above lowest_price, regardless of phase or k.
The 0.08 phase multiplier is completely neutralized.
```

## Why This Is a Problem

For a 5× leverage SHORT on FET:
- SL at 0.70% above current price = price must move 0.70% against us to trigger
- At 5×: 0.70% × 5 = 3.5% loss on position
- T wants "a few minutes" to react when price turns — but 0.70% is ~35+ minutes of adverse move
- The system **survives swings** (wide enough to not get stopped by noise) but **can't close on profit**
  because TP is also too tight relative to SL gap

## Closed Trade Evidence

```
atr_sl_hit trades (losing):
  PURR SHORT  +1.41% move  → -140.7% loss  (sl_dist=1.5, conf=94)
  ORDI SHORT  +0.65% move  → -64.8% loss   (sl_dist=1.5, conf=89)
  MERL SHORT  +0.46% move  → -45.9% loss   (sl_dist=1.5, conf=98)
  NIL SHORT   +0.77% move  → -77.0% loss    (sl_dist=1.5, conf=98)
  LIT SHORT   +0.90% move  → -90.0% loss    (sl_dist=1.5, conf=91)

profit-monster trades (winning):
  GRIFFAIN SHORT -0.68% move → +203.5% pnl
  GALA SHORT     -0.67% move → +200.7% pnl
  TIA SHORT      -0.51% move → +253.7% pnl

Pattern: profit-monster wins on 0.5-0.8% FAVORABLE moves.
         atr_sl_hit loses on 0.5-1.4% ADVERSE moves of similar magnitude.
         Signal direction was correct in both — the SL mechanism is the problem.
```

## The SL/TP Gap Problem

```
For LOW_VOL tokens (ATR < 1%):
  eff_sl_pct = 0.70% (floor, not k×ATR)
  eff_tp_pct = ATR_TP_MIN_ACCEL = 1.1% (floor)
  Gap = 1.1% - 0.70% = 0.40%

At 100× leverage (T's style):
  0.40% gap × 100 = 40% of position
  One small pullback = close at TP before trailing can lock in more
  Winners get stopped out; system survives swings but can't close.
```

## Four Options to Achieve Super-Tight Trailing (< 0.20% from price)

### Option A — Lower the ATR floor (system-wide)
```
Change: ATR_SL_MIN_ACCEL 0.70% → 0.20%
Effect: ALL established trades get tighter SL
Risk:   May cut winners on higher-ATR tokens
```

### Option B — Confidence-gated floor (surgical)
```
Keep: ATR_SL_MIN_ACCEL = 0.70%
Add:  if _signal_confidence >= 90 → use ATR_SL_MIN_INIT_TIGHTCONF = 0.20%
Effect: Only high-conviction signals (conf≥90) get ultra-tight trailing
```

### Option C — Higher-timeframe ATR
```
Change: get_fresh_atr() to use 15m candles instead of 1m
Effect: ATR(14) on 15m = 3-6× larger than 1m ATR
        k × ATR becomes meaningful, floor becomes less restrictive
        BUT: still clamped if floor > k×ATR — needs Option A or B
```

### Option D — Manual trailing_sl per position
```
Action: Manually set trailing_sl on specific position
        e.g., set FET trailing_sl = 0.19350 (0.35% above current)
Effect: Bypasses ATR computation entirely
        Guardian manages with manual SL, not ATR-based
Best for: One-off situations where T wants exact control
```

## What T Tweaked (2026-05-21) — Makes Floor Problem Worse

| Constant | Old | New | Effect |
|---|---|---|---|
| `K_PHASE_ACCEL_FAST` | 0.10 | 0.08 | Tighter SL in acceleration — but floor negates it |
| `ATR_K_NORMAL_VOL` | 2.0 | 0.50 | Much tighter SL — correct, fixed 4-6% SL problem |
| `ATR_K_HIGH_VOL` | 2.5 | 0.25 | Much tighter SL — correct |
| `ATR_SL_MIN` | 0.50% | 1.00% | WIDER floor for trailing — contradicts goal |
| `ATR_TP_MIN_ACCEL` | 1.5% | 1.1% | TIGHTER TP — reduces profit capture |

**The tightening of k (ATR_K_NORMAL_VOL 2.0→0.50) is correct and good.**
**The raising of ATR_SL_MIN (0.50%→1.00%) creates the floor-lock problem for LOW_VOL tokens.**

## Diagnostic Query — Identifying Floor-Locked Trades

```python
# Trades where k×ATR < floor — phase multiplier is useless
import json
with open('/root/.hermes/data/atr_cache.json') as f:
    cache = json.load(f)
atr = cache.get('FET', {}).get('atr', 0)
entry = 0.19406
atr_pct = atr / entry if entry else 0
eff_k = 0.04  # EXTREME phase × NORMAL_VOL base_k
k_x_atr = eff_k * atr_pct
floor = 0.007  # ATR_SL_MIN_ACCEL
print(f'k×ATR = {k_x_atr*100:.4f}%, floor = {floor*100:.2f}%')
print(f'FLOOR LOCKS: {k_x_atr < floor}')
```

## Files Involved

| File | Lines | Role |
|---|---|---|
| `tpsl_utils.py` | 333-372 | `sl_pct = k * atr_pct` then `eff_sl_pct = min(max(sl_pct, MIN_SL_PCT), ATR_SL_MAX)` — floor applied here |
| `tpsl_utils.py` | 354-364 | `MIN_SL_PCT = ATR_SL_MIN_INIT` (new) / `ATR_SL_MIN_ACCEL` (established) — the floor choices |
| `hermes_constants.py` | ATR_SL_MIN_INIT=0.70%, ATR_SL_MIN_ACCEL=0.70% | Both floors currently 0.70% |
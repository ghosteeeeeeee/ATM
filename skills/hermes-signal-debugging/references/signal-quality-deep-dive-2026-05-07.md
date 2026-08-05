# Signal Quality Deep-Dive — 2026-05-07

## What Actually Works (from live outcome data)

### accel-300+ RS-Support Combos — Best Working Signals

These specific combos from the rs.py support/resistance scanner combined with accel-300+:

| Combo | Token | Result | When |
|-------|-------|--------|------|
| `accel-300+,rs-s48` | PURR | +4.74% | May 6 13:40 |
| `accel-300+,rs-s48` | GRIFFAIN | +5.26% | Apr 30 06:48 |
| `accel-300+,rs-s140` | ? | +287% | May 6 |
| `accel-300+,rs-s72` | ? | +298% | May 6 |
| `accel-300+,rs-s44` | ? | +154% | Apr 30 |
| `accel-300+,rs-s150,trend_purity+` | GRIFFAIN | +5.26% | Apr 30 06:48 |
| `accel-300+,momentum,mtf-macd,rsi` | DASH | +4.80% | May 6 06:14 |
| `accel-300+,hzscore-,rs-s1373,rs-s245` | ? | +203% | May 5 20:35 |

**Pattern**: accel-300+ fires when price is at strong support (48+ historical touches = rs-s48, rs-s72, rs-s140, rs-s150, rs-s44). The support level provides a floor. When combined with trend_purity+ or momentum/mtf-macd/rsi confirmation, winners are much larger.

**rs-sNNN meaning**: `rs-s48` = support level with 48 historical touches. Higher touch count = stronger level.

### hwave+,hzscore+ SHORT — Legacy April Winners

| Token | Result | Date |
|-------|--------|------|
| AXS | +153% | Apr 17 |
| INJ | +120% | Apr 17 |
| S | +37% | Apr 17 |

Only 4 trades, all April 17. Small sample but very strong edge. hwave appears to be a heat-wave or regime signal. **hwave is no longer firing** — check if it was disabled or if the source changed (hwave+, hwave- are directional sub-signals).

## What Doesn't Work

### accel-300- (negative acceleration) — NEVER FIRES
phase_accel.py only generates plus signals (PHASE_ACCEL_MINUS_ENABLED=False). There is no accel-300- signal type in the system.

### pct-hermes- SHORT — 5.9% WR, -89% avg PnL
Broken in May bullish regime. Fires at market bottoms, price keeps grinding higher.

### hzscore+ SHORT alone — 21% WR, -39% avg PnL
Too noisy standalone. April had some big wins (GALA +121%, INJ +120%, ZK +86%) but also catastrophic losses (GALA -165%, BCH -132%, EIGEN -130%, XMR -127%).

### gap-300- SHORT combos — All losing badly
`gap-300-,zscore-momentum-` 118 trades, -50% avg. The gap signal fires but the market keeps trending through gap levels.

## Critical: Position Management Issue

### DASH case study
- May 6 08:09 — accel-300+ LONG entered at +4.06%
- May 6 09:16 — Same signal exited at -3.15% (-315% in raw terms)
- May 7 18:57 — accel-300+ LONG entered at -0.22%, exited at -1.12%

**67 minutes from +4% to -3.15%.** The system is closing at +4% (TP trigger) then re-opening on the same accel-300+ signal, getting whipsawed.

Duplicate rows in signal_outcomes: each trade produces 2 rows (entry + exit). For DASH:
- id 3135: `accel-300+` DASH LONG +4.06% (win)
- id 3136: `accel-300+` DASH LONG +3.16% (win)
- id 3145: `accel-300+` DASH LONG -3.15% (loss)
- id 3146: `accel-300+` DASH LONG -4.05% (loss)

The same signal_type appears in entry AND exit rows. This means the guardian/PM is re-opening positions on the same accel-300+ signal that just closed at a profit, then closing at a loss.

### The pattern across all accel-300+ trades (22 unique trades)
- Big wins: DASH +406%, ICP +363%, ZEN +125%, PROMPT +139%
- Big losses: DASH -405%, LINEA -182%, MERL -144%, BERA -135%, BLUR -127%, DYM -119%
- **4 big wins vs 18 big losses** — system is cutting winners and letting losers run

### Root cause hypothesis
The guardian/profit-monster is taking +4-5% profits too quickly (10X-20X leverage makes 4% = 40-80% of equity), then the signal re-fires, enters again, and gets stopped out.

## SQL Reference

```sql
-- Check specific combo outcomes
WITH trade_pnl AS (
  SELECT token, direction, signal_type, MIN(pnl_pct) as exit_pnl, is_win, created_at
  FROM signal_outcomes WHERE signal_type LIKE 'accel-300+,rs-s%'
  GROUP BY token, direction, signal_type, created_at
)
SELECT signal_type, COUNT(*) as trades, SUM(is_win) as wins, ROUND(AVG(exit_pnl)*100,2) as avg_pnl
FROM trade_pnl GROUP BY signal_type ORDER BY avg_pnl DESC;

-- Duplicate row check (entry + exit per trade)
SELECT token, signal_type, COUNT(*) as rows, MIN(pnl_pct) as entry_pnl, MAX(pnl_pct) as exit_pnl
FROM signal_outcomes WHERE signal_type = 'accel-300+'
GROUP BY token, created_at HAVING COUNT(*) > 1;

-- RS signal combo performance
WITH trade_pnl AS (
  SELECT token, direction, signal_type, MIN(pnl_pct) as exit_pnl, is_win, created_at
  FROM signal_outcomes WHERE signal_type LIKE '%rs-s%' OR signal_type LIKE '%rs-r%'
  GROUP BY token, direction, signal_type, created_at
)
SELECT signal_type, COUNT(*) as trades, ROUND(AVG(exit_pnl)*100,2) as avg_pnl
FROM trade_pnl GROUP BY signal_type ORDER BY avg_pnl DESC LIMIT 20;

-- Hwave combo check
SELECT signal_type, token, pnl_pct, created_at FROM signal_outcomes
WHERE signal_type LIKE '%hwave%' ORDER BY pnl_pct DESC LIMIT 10;
```

## Recommendations

1. **Add `accel-300+,rs-s{N}` combos to GOOD_STANDALONE_SIGNALS** — rs-s48, rs-s72, rs-s140, rs-s150, rs-s44 all show strong wins. These fire when accel-300+ coincides with a strong support level bounce.

2. **Investigate guardian/PM close-then-reopen loop** — DASH shows same signal closing at +4% then reopening and closing at -4%. Check if profit-monster or TP logic is too aggressive for leveraged positions.

3. **Remove `pct-hermes-` from GOOD_STANDALONE** — 5.9% WR, -89% avg PnL in current regime. Broken.

4. **hwave+,hzscore+ needs investigation** — 4 trades, +153%/+120%/+37% on April 17. Either the signal stopped firing or its parameters changed. Check if hwave was disabled or renamed.

5. **`accel-300-` does not exist** — if SHORT acceleration signal is desired, phase_accel.py needs PHASE_ACCEL_MINUS_ENABLED=True and logic for negative acceleration.

6. **Don't add signals to GOOD_STANDALONE with < 30 trades** — pct-hermes+ was added based on 3 trades at 100% WR, now 4.7% WR. Always require minimum 30-trade sample.
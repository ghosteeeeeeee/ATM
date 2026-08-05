# SHORT Signal Winners + System Architecture Gaps — May 7, 2026

## All-Time Top SHORT Winners

| Token | Signal | Peak | Date | Avg Exit |
|-------|--------|------|------|----------|
| ORDI | hzscore,pct-hermes SHORT | +873% | Apr 16 | — |
| AXS | hwave+,hzscore+ | +153% | Apr 17 | +27.4% |
| S | hwave+,hzscore+ | +38% | Apr 17 | +27.4% |
| CAKE | ma-cross-5m-short,zscore-short | +372% | Apr 22 | +21.9% |
| DOT | oc-zscore-v9-,zscore-momentum- | +256% | Apr 23 | +26.1% |
| DYM | hzscore+,pct-hermes- SHORT | +218% | Apr 29 | — |
| XAI | hzscore+,pct-hermes- SHORT | +198% | Apr 29 | — |
| MON | gap-300-,zscore-momentum- | +144% | Apr 27 | — |
| ADA | ma-death10,r2s-short12 | +156% | May 6 | — |

## SHORT Signal Ranking by Avg Exit (all trades)

```
hwave+,hzscore+              | 4 trades | 50% WR | avg exit +27.4%  ← BEST (hwave disabled)
hzscore-,pct-hermes-         | 26 trades | 0% WR | avg exit -4.9%  ← second best
hwave-,hzscore+              | 12 trades | 0% WR | avg exit -19.5%
oc-zscore-v9-                | 4 trades | 50% WR | avg exit -73.8%
hzscore+                     | 62 trades | 21% WR | avg exit -39.1%  ← baseline
ma-cross-5m-short,zscore-short | 13 trades | 38% WR | avg exit -68.1%
oc-zscore-v9-,zscore-momentum-| 8 trades | 37.5% WR | avg exit -63.9%
pct-hermes-,vel-hermes-      | 12 trades | 8% WR | avg exit -77.5%
pct-hermes-                  | 17 trades | 6% WR | avg exit -89.2%
```

## Market Regime by Period

| Period | LONG Avg Peak | SHORT Avg Peak | Dominant |
|--------|---------------|----------------|----------|
| Pre-Apr 20 | -28.21% | -26.76% | Both losing |
| Apr 20-24 | -16.16% | -8.91% | SHORT improving |
| Apr 25-May 1 | -13.96% | -6.09% | Transitioning |
| May 1-4 | -22.13% | +8.78% | SHORT working |
| **May 5+** | **+9.92%** | **-8.40%** | **LONG working** |

## Critical Architecture Gaps

### Gap 1: hwave DISABLED April 18
`hwave+,hzscore+` was the best SHORT combo (50% WR, +27.4% avg). hwave was disabled
with comment "hwave removed — compute_score never generates bare hwave." This is the
biggest SHORT gap in the system.

### Gap 2: RS signals never fire (0 occurrences)
rs.py is in SLOW runner (15-min cycles). With RS_COOLDOWN_HOURS=4, fires max 6x/day.
Also: GOOD_STANDALONE_SIGNALS bypass broken (naming mismatch).

### Gap 3: GOOD_STANDALONE_SIGNALS bypass BROKEN
Hyphen keys ('accel-300+') vs underscore DB format ('accel_300_long') — never matches.
ALL single-source signals held to 2+ co-signal gate.

### Gap 4: oc-zscore-v9- not in fast signals list
`oc-zscore-v9-` standalone: 50% WR, +16.2% avg peak. Not in fast runner.

### Gap 5: ma-cross-5m-short blocked by confluence gate
ma-cross-5m-short fires at 55% confidence but needs zscore co-signal (38.5% WR combo)
to pass. Bare ma-cross-5m-short gets blocked.

## Key SQL Patterns

```sql
-- Top winners by peak PnL
WITH trade AS (
  SELECT token, direction, signal_type, created_at,
    MAX(pnl_pct) as peak_pnl,
    MIN(pnl_pct) as exit_pnl,
    MAX(CASE WHEN is_win=1 THEN pnl_pct END) as peak_win
  FROM signal_outcomes
  GROUP BY token, direction, signal_type, created_at
)
SELECT token, direction, signal_type, ROUND(peak_pnl*100,2) as peak_pct,
  CASE WHEN peak_win IS NOT NULL THEN 'WIN' ELSE 'LOSS' END, created_at
FROM trade WHERE peak_pnl > 1.0 ORDER BY peak_pnl DESC LIMIT 40;

-- SHORT signals by avg exit
WITH trade AS (
  SELECT signal_type, direction,
    MAX(pnl_pct) as peak_pnl,
    MIN(pnl_pct) as exit_pnl
  FROM signal_outcomes
  GROUP BY token, direction, signal_type, created_at
)
SELECT signal_type, COUNT(*) as n, ROUND(AVG(peak_pnl)*100,2) as avg_peak,
  ROUND(AVG(exit_pnl)*100,2) as avg_exit
FROM trade WHERE direction='SHORT' GROUP BY signal_type ORDER BY avg_exit DESC;

-- RS combo winners (accel-300+ with RS support)
WITH trade AS (
  SELECT token, direction, signal_type, created_at,
    MAX(pnl_pct) as peak_pnl
  FROM signal_outcomes
  WHERE signal_type LIKE 'accel-300+,rs-%'
  GROUP BY token, direction, signal_type, created_at
)
SELECT token, signal_type, ROUND(peak_pnl*100,2) as peak_pct, created_at
FROM trade ORDER BY peak_pnl DESC;
```

## Action Items

1. Fix GOOD_STANDALONE_SIGNALS naming — change keys to underscore format
2. Investigate re-enabling hwave or equivalent signal
3. Move RS to fast runner with shorter cooldown
4. Add ma-cross-5m-short to GOOD_STANDALONE_SIGNALS
5. Investigate oc-zscore-v9- firing in fast signals list

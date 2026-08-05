# mtp-zscore XLM Case — Choppy Stair-Step Run (2026-05-29)

## What Happened
XLM 1m prices over ~28h: 0.14625 → 0.17860 (+22.12%)
Pattern: 4 distinct leg-up sessions separated by chop/consolidation:

```
05-27 04:00-04:50  0.14752 → 0.14707  (-0.3%)  ← local bottom
05-27 08:30-12:20  0.14790 → 0.15570  (+5.3%)  ← leg 1
05-27 14:00-15:25  0.15290 → 0.16340  (+6.9%)  ← leg 2
05-27 20:00-02:00  0.16400 → 0.17860  (+8.9%)  ← leg 3 (main push)
```

## mtp-zscore Simulation (14/50/150-bar, 3/3 agree, Z in [1.0, 5.0])

| Config | Fires/48h | Problem |
|--------|-----------|---------|
| 3/3 Z[1.0,5.0] current | **372** | Fires every 1-3 min in chop — pure noise |
| 3/3 Z[2.0,5.0] tighter min | **22** | Only fires at strong moments — sparse |
| 2/3 Z[1.0,5.0] agree-2 | **757** | Even noisier — 2/3 too loose |
| 3/3 longer (30/80/200) | **417** | Fewer but still too many fires |

With `Z_SHORT_Z_MIN=1.0`, the 14-bar window clears threshold on random 1-2% moves
during low-vol chop. XLM 1m has low signal-to-noise — fast windows see noise as momentum.

## The "3/3 agree but 14-bar is too big" Paradox

When XLM was in a clean leg start (e.g., 05-27 08:30), the 14-bar z-score would hit
5.2+ while 150-bar z was barely 1.5 (trend just beginning). Z_MAX=5.0 rejects the
14-bar as "too extended" — even though the huge fast z-score is confirming the leg.
The 150-bar z that passes Z_MAX is weak (1.5) but not extended.

Result: 3/3 never fully agree during leg starts. The system fights itself.

## What Would Catch This

| Param | Current | Fix | Reason |
|-------|---------|-----|--------|
| `Z_SHORT_Z_MIN` | 1.0 | 1.5–2.0 | XLM 1m noise needs higher threshold |
| `Z_SHORT_Z_MAX` | 5.0 | 8.0 | Don't reject the big fast moves — they're the best entries |
| `MTP_ZSCORE_MIN_AGREE` | 3 | 2 | 2/3 survives pullbacks within multi-leg runs |
| Short lookback | 14 | 30 | Reduces noise fires; still catches leg starts |

With `Z_SHORT_Z_MAX=8.0`: the 14-bar z=5.2 at leg starts would PASS (current 5.0 rejects it).
The 3/3 would fire more cleanly at real leg starts, not in chop.

With `Z_SHORT_Z_MIN=2.0` + short LB=30: chop noise z-scores (0.5-1.5 range) would be blocked.

## Data Source
`candles.db::candles_1m` — token='XLM', ts in seconds, 1669 rows (05-27 00:38 to 05-28 04:27).
Query: `WHERE token='XLM' AND ts > <now-172800> ORDER BY ts ASC`
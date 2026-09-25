## Error Alerts — 2026-09-25 04:45 UTC
- **WARN** (1x): `Disk at 85% (95G/118G)` — approaching threshold
- **AUTO-FIX**: None applied — monitor, compress logs if >90%
- **WARN** (continuous): `hotset.json empty — no signals survived compaction` — pipeline runs clean but produces no actionable signals
- **AUTO-FIX**: None — market is 118/118 NEUTRAL, compaction is working as intended (filtering noise)

## Error Alerts — 2026-09-25 04:57 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.1s (rc=N)`
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS   TOK decider_run: TOK (most recent call last):`
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: decider_run`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.6s (rc=N)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] W TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.7s (rc=N)`

# TPSL Constant Tweaks Applied 2026-06-25

**T's go-ahead given at ~05:06 UTC.** Backup saved at
`/root/.hermes/scripts/hermes_constants.py.bak-2026-06-25`.
Guardian restarted (PID 2264876) to pick up new constants.

## Changes Applied (hermes_constants.py)

| Constant | Old | New | Reason |
|----------|-----|-----|--------|
| `ATR_SL_MAX` | 0.012 (1.2%) | **0.008 (0.8%)** | Tighter trailing — was the binding constraint at 1.2% above low |
| `ATR_SL_MIN_ACCEL` | 0.015 (1.5%) | **0.005 (0.5%)** | Was DEAD CODE (MIN > MAX) — now alive with MIN < MAX |
| `K_PHASE_ACCEL_STALL` | 0.06 | **0.6** (10x) | Was clobbered by MIN/MAX clamp |
| `K_PHASE_ACCEL_FAST` | 0.05 | **0.5** (10x) | Same |
| `K_PHASE_ACCEL_SLOW` | 0.04 | **0.4** (10x) | Same |
| `K_PHASE_EXH_STALL` | 0.02 | **0.5** (25x) | Same |
| `K_PHASE_EXH_FAST` | 0.03 | **0.4** (13x) | Same |
| `K_PHASE_EXH_SLOW` | 0.02 | **0.3** (15x) | Same |
| `K_PHASE_EXT_STALL` | 0.01 | **0.3** (30x) | Same |
| `K_PHASE_EXT_FAST` | 0.02 | **0.2** (10x) | Same |

## Trace verification (MERL #12177 scenario, pnl=1.07%)

| Stage | Old | New |
|-------|-----|-----|
| base_k (LOW_VOL) | 0.5 | 0.5 |
| K_PHASE_EXH_SLOW | 0.02 | 0.3 |
| final k | 0.01 | 0.15 |
| sl_pct = k × atr_pct | 0.0001 (0.01%) | 0.0015 (0.15%) |
| eff_sl_pct = clamp(0.015, 0.012) | 0.012 (1.2% cap) | 0.005 (0.5% floor) |
| new_sl = 0.019699 × (1 + eff_sl) | 0.019935 | **0.019797** |
| SL distance above current | 1.2% | **0.5%** |

Improvement: SL trails 0.5% above low instead of 1.2% — catches 0.7% more
of every profit move.

## What was NOT changed (per T's direction)

- **Leverage** — T said: "we want to increase it when our signals and
  SL and thus win-rate get better. so don't worry about leverage."
  5x leverage is an amplifier that grows with system quality.
- **PROFIT_MIN_PCT** (0.7%) — not touched this session
- **TP_* constants** — not touched

## Next: monitor and verify

**To watch in next 24h:**
- Any `[TPSL]` log line for an in-profit trade should show
  `eff_sl=0.5%` (not 1.2% anymore)
- Losers should exit at smaller losses (current 0.6-1.4% adverse
  should now be clipped at 0.5%)
- 3x and 5x both should benefit identically
- If a high-vol token (atr_pct > 3%) shows `eff_sl=0.8%` (the new MAX),
  that means ATR computation is producing very small sl_pct and the
  cap is binding — verify it's correct, not the floor

**Companion plan:** `/root/.hermes/brain/plans/tpsl-profit-capture-2026-06-25.md`
updates the 11-fix plan with the applied status.

## Other things in the plan still pending

- Bug #1: lowest_price init (one line, position_manager.py) — separate from constants
- Backfill 12 closed trades' lowest_price=0 → entry_price
- ASTER blacklist (1 line)
- Time-of-day filter (skip 20:00-22:00 UTC)
- ASTER 10s re-open cooldown
- highest_price=1.0 default fix

These are bug fixes (not constant changes) and need separate
T approval per T's "fix obvious bugs directly without asking" rule
for the safest ones (Bug #1).

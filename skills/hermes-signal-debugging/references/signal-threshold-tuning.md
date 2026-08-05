# Signal Threshold Tuning Reference

## Foundational Signal Value Distributions (2026-05-07)

All data from runtime DB + signal_outcomes. These are the REAL thresholds to use.

### `hzscore` (mtf_zscore) — Fires at avg_z ≥ 0.3 by default, no minimum

**Problem**: hzscore fires at ANY avg_z ≥ 0.3, even in chop zones.
- hzscore(LONG) fires at: min=-3.563, p10=-1.324, p50=-0.729, p90=-0.247, max=0.135
- hzscore(SHORT) fires at: min=-0.143, p10=0.163, p50=0.722, p90=2.021, max=2.988

**Winners vs Losers**: 
- Winners: avg_z ~2.0 (price very extended from mean — mean reversion has room)
- Losers: avg_z ~0.72 (price near mean — no room to revert, enters chop)

**Tunable**: `HZSCORE_MIN_VALUE` (new). Current: none. Recommended: 0.6.
Effect: Only fire when z-score is genuinely extreme. Would block ~30-40% of marginal signals.

---

### `pct-hermes` (percentile_rank) — PCT_RANK_THRESH=72 by default

**Problem**: Threshold of 72 means price only needs to be in top/bottom 28% of range.
- pct-hermes(LONG): min=80, p10=85.5, p50=95.5, p90=100, avg=94.1
- pct-hermes(SHORT): min=80, p10=85.5, p50=96.5, p90=100, avg=94.2

**The issue**: Most fires happen at p50=95.5 (median) — meaning price is only top 4.5% of range.
The 72 threshold is far too low. A truly extreme reading is 99+.

**Signal outputs confirm**: Winners in signal_outcomes show rs-s### (support levels) near 99th percentile.
pct-hermes+ at low conf (70-80) = 4.7% WR. pct-hermes+ at high conf (90+) = losing.

**Tunable**: `PCT_RANK_THRESH`. Current: 72. Recommended: 85.
Effect: Only fire at true extremes (top/bottom 15%). Dramatically reduces noise.

---

### `vel-hermes` (velocity) — VEL_HERMES_THRESHOLD=0.03 by default

**Problem**: Threshold 0.03 barely exceeds noise floor.
- vel-hermes(SHORT): min=0.030, p10=0.033, p50=0.036, p90=0.053, max=0.076, avg=0.041

**p90 = 0.053**: The top 10% of signals barely exceed 0.053. Almost all velocity signals
are in the 0.03-0.05 range (barely qualifying). The threshold of 0.03 is noise.

**Tunable**: `VEL_HERMES_THRESHOLD`. Current: 0.03. Recommended: 0.06.
Effect: Only accept genuine velocity. Would reject ~50% of weak signals.

---

### `accel-300` — PERSISTENCE_BARS=3 by default

**Problem**: PERSISTENCE_BARS=3 means price has already run 3 bars by the time we fire.
We're catching the move AFTER it's started, not at the beginning.

**Tunable**: `PERSISTENCE_BARS`. Current: 3. Recommended: 2.
Effect: Fire one bar earlier while still requiring confirmation.

---

## Signal Co-Signal Requirements (from brain DB trade analysis)

### SHORT Signals — What Works
| Combo | Trades | WR | Avg PnL |
|-------|--------|-----|---------|
| `hzscore+,pct-hermes-,vel-hermes-` (3-signal) | 49 | **47%** | +0.466% |
| `hzscore+,pct-hermes-` (2-signal, no vel) | 130 | **33%** | +0.177% |
| `hzscore+,vel-hermes-` (no pct) | ~20 | **20%** | -0.064% |
| `pct-hermes-` alone | ~100 | **35%** | +0.221% |
| `vel-hermes-` alone | ~50 | **42%** | +0.324% |

**Conclusion**: vel-hermes- is only productive as the 3rd signal with hzscore+ AND pct-hermes-.
Without pct-hermes-, hzscore+ alone is 32% WR (poison). vel-hermes- without hzscore+ is weak.

**RULE**: `hzscore+` standalone should be BLOCKED. It should only pass with pct-hermes- AND vel-hermes-.
`vel-hermes-` standalone should be BLOCKED (done 2026-05-05 — removed from GOOD_STANDALONE_SIGNALS).

### LONG Signals — What Works
| Combo | Trades | WR | Avg PnL |
|-------|--------|-----|---------|
| `accel-300+,hzscore-` | 61 | **41%** | +0.529% |
| `accel-300+` alone | 16 | **31%** | +0.405% |
| `hzscore-` alone | ~50 | **38%** | +0.318% |
| `accel-300+,trend_purity+` | 20 | **55%** | (needs more data) |

**Conclusion**: accel-300+ alone is a 31% WR coin flip. It needs hzscore- as co-signal.
The support level (rs-s###) is the difference between winners and losers in accel-300+,hzscore-:
- Winners: EIGEN +6.65% (rs-s350), OP +4.02% (rs-s72), ICP +3.73% (rs-s72)
- Losers: XMR -0.49% (no support), DASH -0.46% (no support)

**RULE**: `accel-300+` standalone should be BLOCKED. It should require hzscore- as co-signal.

---

## Implemented Fixes (2026-05-05/07)

1. **vel-hermes- REMOVED from GOOD_STANDALONE_SIGNALS** (signal_compactor.py) — can only pass as co-signal
2. **PCT_HERMES_MINUS_ENABLED = True** (hermes_constants.py) — was previously blocked
3. **MTF_MOMENTUM_PLUS/MINUS = False** (hermes_constants.py) — blocked (was creating noise)
4. **VEL_HERMES = False** in vel_hermes.py (matched hermes_constants.py)

---

## Implemented Fixes (2026-05-07)

All of the above were implemented on 2026-05-07.

| Fix | File | Value | Status |
|-----|------|-------|--------|
| Add `MIN_Z_VALUE` threshold | `signals/hzscore.py` | 0.4 (was going to 0.6, too tight) | ✅ Done |
| Raise `PCT_RANK_THRESH` | `signals/pct_hermes.py` | **95** (was 80) | ✅ Done |
| Fix confidence formula | `signals/pct_hermes.py` | `70 + (pct_val - 95) * 5` (was capped at 60) | ✅ Done |
| Raise `VEL_ABS_THRESHOLD` | `signals/vel_hermes.py` | 0.04 (was 0.03, tried 0.06 but blocked combos) | ✅ Done |
| Reduce `PERSISTENCE_BARS` | `signals/accel_300.py` | 2 (was 3) | ✅ Done |
| Confluence gate: avg >= 0 not WR >= 40 | `signal_compactor.py` | avg_pnl >= 0 replaces WR >= 40 | ✅ Done |
| Extend compaction window | `signal_compactor.py` | 5 min → **15 min** | ✅ Done |

### Key bugs found during implementation

**Bug: confidence formula capped at 60 — pct=95 and pct=100 both got conf=60.**
Old formula `(pct_val - 72) * 1.25 + 50` with `min(60, ...)` meant everything above pct=82.9 returned 60.
New: `min(95, max(70, 70 + (pct_val - PCT_RANK_THRESH) * 5))` → pct=95 → conf=70, pct=100 → conf=95.

**Bug: signals never combine — 5-min window too tight.**
pct_hermes runs every 1 min, hzscore every 5 min. Their created_at timestamps differ by up to 4 min → outside 5-min window → no combo ever formed.
Fix: 5 min → 15 min window.

**Bug: co-signal gate WR >= 40 too strict.**
pct-hermes- at 35% WR with +0.221% avg was blocked as standalone. But it makes money.
Fix: avg_pnl >= 0 instead of WR >= 40.

### Known issues still open

- **`accel-300` is silent**: 0 signals in 2+ hours. Needs investigation.
- **`vel_hermes` barely fires**: 17 signals in 2 hours. At threshold=0.04 still very sparse.
- **3-signal SHORT combo still rare**: requires all 3 within 15 min for same token.
- **counter_flip/phase_accel LONG signals**: ~7 LONG in 10 min, need WR audit.

## Pending Fixes (not yet implemented)

1. **Investigate accel-300 silence** — why is it producing 0 signals?
2. **LONG signal quality**: accel-300+ is the crown jewel but not firing. Without it, LONG side has no strong signal.
3. **Evaluate counter_flip/phase_accel LONG signals** — producing ~7 LONG signals in 10 min, need WR audit.

# Signal Performance Report

**Period:** Last 6h | 24h  
**Generated:** 2026-10-01 ~22:45 UTC  
**Analyst:** signal_reporter

---

## 6h Performance

No signals with 2+ closed trades in the last 6h window. Clean.

---

## 24h Performance

| Signal | Dir | Trades | WR | PnL | Verdict |
|--------|-----|--------|-----|-----|---------|
| pump-chain- | SHORT | 7 | 28.6% | -$0.46 | LOSER — regime-blocked |
| accel-300- | SHORT | 8 | 37.5% | -$0.34 | KILLED (already, auto_1hr) |
| pump-chain-v5 | LONG | 6 | 33.3% | -$0.17 | KILLED (already, hourly rule) |
| bb-bounce-v3-long+ | LONG | 2 | 0.0% | -$0.12 | Watch — too few trades |

---

## KILLED (executed this run)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | No new kills. accel-300- and pump-chain-v5 LONG already killed earlier today. |

**Prior kills verified:**
- `ACCEL_300_MINUS_ENABLED = False` — auto_1hr kill 2026-10-01 ~10:50 (4T 0%WR -$0.31 last hour, falling-knife SHORTs at RSI 25-38)
- `PUMP_CHAIN_V5_ENABLED = False` — hourly kill rule 2026-10-01 (3T 0%WR -$0.20)

---

## REGIME BLOCKS (executed this run)

Per SOP: signal wins in ANY regime → block losing regimes, do NOT blanket-kill.

### pump-chain- SHORT — NORMAL wins (85.7% WR, +$0.16 all-time)

| Regime | Trades | WR | PnL | Action |
|--------|--------|-----|-----|--------|
| NORMAL | 7 | 85.7% | +$0.16 | ✅ KEPT |
| HIGH | 25 | 48.0% | -$0.36 | 🚫 BLOCKED |
| EXTREME | 84 | 52.4% | -$0.14 | 🚫 BLOCKED |

**Fixes applied:**
1. `decider_run.py` — added EXTREME hard block for pump-chain SHORT (was missing; v2 gate Pump_Flow:0.0 existed but STANDALONE_BYPASS + fail-open let trades through)
2. `hermes_constants.py` — added `PUMP_CHAIN_SHORT_EXTREME_BLOCK_ENABLED = True`
3. `volatility_gate.py` — removed `pump-chain-` from HIGH REGIME_SIGNALS (stale allow: HIGH 48%WR -$0.36 bleed)
4. Existing: `PUMP_CHAIN_SHORT_HIGH_BLOCK_ENABLED = True` (decider_run HIGH block)
5. Existing: v2 `('EXTREME','*'): Pump_Flow=0.0` and `('HIGH','*'): Pump_Flow=0.0`

### accel-300- SHORT — NORMAL wins (75% WR), HIGH loses (0% WR)

| Regime | Trades | WR | PnL | Action |
|--------|--------|-----|-----|--------|
| NORMAL | 4 | 75.0% | -$0.03 | ✅ KEPT |
| HIGH | 4 | 0.0% | -$0.31 | 🚫 BLOCKED |

**Fixes applied (defense-in-depth; signal already killed at source):**
1. `volatility_gate_v2.py` — added `('HIGH', 'accel-300-'): 0.0` to SIGNAL_TYPE_OVERRIDES
2. `market_phase_gate.py` — added `accel-300-` + hyphen variants to Accelerate FAMILY_MAP (was returning 'Other', making family-level blocks dead code)
3. Signal already disabled: `ACCEL_300_MINUS_ENABLED = False`

### pump-chain-v5 LONG — no winning regime (EXTREME 42.9% WR)

Already killed: `PUMP_CHAIN_V5_ENABLED = False`. SHORT variant (`PUMP_CHAIN_V5_SHORT_ENABLED = True`) regime-routed via existing v2 blocks.

---

## BOOSTED (executed this run)

None. No signal met boost criteria (WR > 55% with 5+ trades in 24h). All 24h "winners" had only 1 trade each.

---

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v3-long+ | LONG | 0.0% | -$0.12 | 2 | Watch — below trade threshold |
| continuum-trend- | SHORT | 0.0% | -$0.01 | 1 | Noise — single trade |

---

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| continuum-osc+ | LONG | 100% | +$0.16 | 1 | Insufficient sample |
| bb-bounce-v2-long+ | LONG | 100% | +$0.09 | 1 | Insufficient sample |
| pump-chain- (NORMAL only) | SHORT | 85.7% | +$0.16 | 7 | ✅ Edge preserved via regime block |

---

## ISSUES

1. **CRITICAL (fixed):** pump-chain- SHORT was firing in EXTREME despite v2 `Pump_Flow=0.0` family block. Root cause: decider_run.py only had HIGH block, not EXTREME; STANDALONE_BYPASS signals skip signal_compactor; exception handler fail-opens. Fixed with explicit EXTREME hard block in decider_run.py.

2. **FIXED:** `accel-300-` (hyphen form, actual DB value) was missing from FAMILY_MAP — returned 'Other', making all Accelerate family regime blocks dead code for this variant. Added hyphen variants to Accelerate family.

3. **FIXED:** `pump-chain-v5` was missing from FAMILY_MAP Pump_Flow — returned 'Other'. Added.

4. **FIXED:** `pump-chain-` was still in volatility_gate.py HIGH REGIME_SIGNALS (stale allow entry from before HIGH became a bleed regime). Removed.

5. **No inversions found** in 24h window. Direction labels clean.

6. **Sideways find:** `accel-300-` remains in volatility_gate.py HIGH/EXTREME REGIME_SIGNALS (allow lists). Harmless while `ACCEL_300_MINUS_ENABLED=False`, but stale. Clean up on next constants pass.

---

## Files Changed

| File | Change |
|------|--------|
| `scripts/decider_run.py` | Added pump-chain SHORT EXTREME hard block |
| `scripts/hermes_constants.py` | Added `PUMP_CHAIN_SHORT_EXTREME_BLOCK_ENABLED = True` |
| `scripts/volatility_gate_v2.py` | Added `('HIGH','accel-300-'): 0.0` override |
| `scripts/volatility_gate.py` | Removed `pump-chain-` from HIGH REGIME_SIGNALS |
| `scripts/market_phase_gate.py` | Added accel-300- and pump-chain-v5 to FAMILY_MAP |

---

## Verification

```
signal_family('accel-300-') = 'Accelerate'          ✅
signal_family('pump-chain-v5') = 'Pump_Flow'        ✅
get_combined_multiplier('accel-300-', 'HIGH') = 0.0 ✅
get_combined_multiplier('pump-chain-', 'EXTREME') = 0.0 ✅
get_combined_multiplier('pump-chain-', 'NORMAL') = 1.0  ✅ (edge preserved)
PUMP_CHAIN_SHORT_EXTREME_BLOCK_ENABLED = True       ✅
ACCEL_300_MINUS_ENABLED = False                     ✅
PUMP_CHAIN_V5_ENABLED = False                       ✅
```

**Pipeline restart required** after commit to load new gate code.

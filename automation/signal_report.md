# Signal Performance Report
Generated: 2026-08-02 14:00 UTC

## Summary
- **44 trades in last 24h** — **0% WR, -$33.46 total PnL**
- **Last 6h:** 4 trades, 0% WR, -$8.20
- **Direction inversions:** None detected
- **Critical:** inv-accel-300- disabled but still executing (kill switch bypass)

---

## LOSERS (CRITICAL — disable immediately)

| Signal | Dir | 6h WR | 6h PnL | 24h WR | 24h PnL | 72h WR | 72h PnL | Status |
|--------|-----|-------|--------|--------|---------|--------|---------|--------|
| inv-accel-300- | SHORT | 0% (18) | -13.47% | 0% (30) | -20.12% | 7.5% (40) | -22.24% | **DISABLED BUT FIRING** |
| accel-300-breakout | LONG | 0% (2) | -2.98% | 0% (6) | -6.56% | 0% (6) | -6.56% | DISABLED ✓ |
| accel-300-breakout | SHORT | 0% (2) | -2.83% | 0% (2) | -2.83% | 0% (2) | -2.83% | DISABLED ✓ |
| pattern_scanner | SHORT | 0% (2) | -1.07% | 0% (2) | -1.07% | 0% (2) | -1.07% | WATCH |
| accel-300+ | LONG | 0% (2) | -1.32% | 0% (2) | -1.32% | 16.7% (6) | -3.33% | **DISABLE** |
| inv-accel-300+ | LONG | 0% (2) | -1.56% | 0% (2) | -1.56% | 0% (4) | -2.81% | DISABLED ✓ |

## ENABLED SIGNALS ACTIVELY LOSING

| Signal | Dir | 24h WR | 24h PnL | 72h WR | 72h PnL | Flag Status |
|--------|-----|--------|---------|--------|---------|-------------|
| accel-300+ | LONG | 0% (2) | -1.32% | 16.7% (6) | -3.33% | ACCEL_300_PLUS_ENABLED=True |
| accel-300+ | SHORT | 50% (2) | -0.57% | 50% (4) | -0.38% | ACCEL_300_MINUS_ENABLED=True |

## DISABLED BUT STILL FIRING (Kill Switch Bypass)

| Signal | Dir | 24h Trades | 24h WR | 24h PnL | Expected Status |
|--------|-----|------------|--------|---------|-----------------|
| inv-accel-300- | SHORT | 30 | 0% | -20.12% | INVERSE_ACCEL_300_MINUS_ENABLED=False |

**This is the 19th time this bypass has been flagged.**

---

## RECOMMENDATIONS

### 1. [CRITICAL] Fix inv-accel-300- kill switch bypass
**30 trades in 24h, 0% WR, -$20.12** — signal is disabled in constants but still executing. Root cause: likely a code path that bypasses the enabled flag. Check `scripts/signals/inverse_accel_300.py` and `scripts/signals_runner.py` for flag checks.

### 2. [DISABLE] accel-300+ (LONG)
**0% WR (2 trades in 6h), -$1.32.** ACCEL_300_PLUS_ENABLED=True but this variant is losing. Set to False.

### 3. [WATCH] pattern_scanner (SHORT)
Only 2 trades, 0% WR. Too small sample to disable. Monitor next 24h.

### 4. [KEEP DISABLED] All others
accel-300-breakout, inv-accel-300+, tl_break variants — all correctly disabled.

### 5. [INVESTIGATE] No winning signals in 24h
44 trades, 0 wins. Either market conditions are exceptionally bad or the signal pipeline has a systematic issue. Check if all trades are hitting stop-loss immediately.

---

## DISABLED SIGNALS — NO ACTION NEEDED

| Signal | Status | Notes |
|--------|--------|-------|
| tl_break_long | DISABLED ✓ | 16% WR, -$24.94 (72h) |
| tl_break_short | DISABLED ✓ | 25% WR, -$17.19 (72h) |
| accel-300-vel+ | DISABLED ✓ | 20.6% WR, -$14.56 (72h) |
| accel-300-vel- | DISABLED ✓ | 40% WR, -$5.29 (72h) |
| bb-squeeze | DISABLED ✓ | 0% WR, -$2.41 (72h) |
| bb-squeeze- | DISABLED ✓ | 0% WR, -$2.41 (72h) |

---

## ACTIVE SIGNALS — NO RECENT TRADES

These are enabled in hermes_constants.py but haven't fired in 24h:

| Signal | LONG | SHORT | Notes |
|--------|------|-------|-------|
| pct-hermes- | — | True | Combo signal |
| vel-hermes- | — | True | Combo signal |
| hzscore+ | True | — | Combo signal |
| hzscore- | — | True | 0% WR historical |
| hmacd+ | True | — | Combo signal |
| hmacd- | — | True | Combo signal |
| pattern_flag | True | True | Bull/bear flag |
| pattern_micro_flag | True | True | Micro flag |
| pattern_triangle | True | True | Asc/desc triangle |
| pattern_wolf | True | True | Wolf wave |
| pattern_channel | True | True | Channel flags |
| atr_compression | True | True | ATR compression |
| ma_cross- | — | True | MA cross SHORT |
| counter_flip | True | True | Counter flip |
| hmacd_mtf | True | True | HMACD MTF |
| ema_angle | True | True | EMA angle |
| phase-accel | True | True | Phase accel |
| zscore-pump | True | True | ZScore pump |
| mtp_zscore | True | True | MTP ZScore |
| zscore_rising | True | True | ZScore rising |
| fast-momentum+ | True | — | Fast momentum |

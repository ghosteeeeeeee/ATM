# Signal Performance Report

**Generated:** 2026-08-05 ~21:30 UTC

---

## Summary

| Period | Trades | Wins | WR | Total PnL |
|--------|--------|------|-----|-----------|
| Last 6h | 21 | 14 | 66.7% | -0.83% |
| Last 24h | 158 | 88 | 55.7% | **+27.65%** |

**24h is net profitable. 6h slight drawdown.**

---

## CRITICAL: Direction Inversions Detected

5 signals fired in the **wrong direction** in the last 24h:

| Token | Signal | Expected Dir | Fired Dir | Result |
|-------|--------|-------------|-----------|--------|
| 0G | tl_break_long | LONG | SHORT | +1.96% |
| FET | tl_break_short | SHORT | LONG | +1.15% |
| LINEA | tl_break_long | LONG | SHORT | +0.95% |
| TNSR | tl_break_long | LONG | SHORT | +0.73% |
| PURR | tl_break_long | LONG | SHORT | +2.42% |

**All inversions are profitable** — but this is a logic bug in signal generation. `tl_break_long` is generating SHORT signals, and `tl_break_short` is generating LONG signals. Investigate `scripts/signals/tl_break.py`.

---

## 24h Winners (WR > 55%, PnL > 0)

| Signal | Dir | Trades | WR | PnL | Avg PnL | Status |
|--------|-----|--------|-----|------|---------|--------|
| tl_break_long | LONG | 10 | 100.0% | +11.55% | +1.155% | **KEEP** |
| tl_break_long | SHORT | 4 | 100.0% | +6.06% | +1.515% | **KEEP** (see inversion note) |
| zscore-rising- | SHORT | 31 | 54.8% | +2.69% | +0.087% | **KEEP** |
| zscore-rising+ | LONG | 8 | 62.5% | +2.17% | +0.271% | **KEEP** |
| bb_bounce | LONG | 8 | 75.0% | +1.28% | +0.160% | **KEEP** |

**tl_break_long** is the top performer — both LONG and SHORT directions profitable (SHORT is an inversion bug but still wins).

## 24h Marginal (30-55% WR)

| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|------|--------|
| vel-hermes- | SHORT | 46 | 43.5% | +5.00% | **KEEP** (enabled=False, disabled flag) |
| bb_bounce | SHORT | 8 | 50.0% | -1.12% | **WATCH** |
| pct-hermes- | SHORT | 2 | 50.0% | -0.02% | **WATCH** |

## 24h Losers (WR < 30%, PnL < -1%)

| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|------|--------|
| decider | SHORT | 9 | 11.1% | -1.59% | **DISABLE** — legacy, replaced by signal_compactor |

---

## Disabled Signals — Should Any Be Re-Enabled?

### Candidates for Re-Enable (strong 24h performance)

| Signal | Dir | 24h Trades | 24h WR | 24h PnL | Current Status | Recommendation |
|--------|-----|-----------|--------|---------|----------------|----------------|
| vel-hermes- | SHORT | 46 | 43.5% | +5.00% | **DISABLED** | **RE-ENABLE** — best SHORT edge by PnL |

### Stay Disabled (confirmed losers)

| Signal | All-time WR | All-time PnL | Why Disabled |
|--------|------------|--------------|--------------|
| accel-300+ | 16.7% | -80.21% | No edge |
| accel-300- | 19.0% | -36.28% | No edge |
| inv-accel-300+ | 14.6% | -83.87% | NEVER_REENABLE |
| inv-accel-300- | 17.2% | -101.90% | NEVER_REENABLE |
| gap-300+ | 29.2% | -6.99% | Losing |
| gap-300- | 20.0% | -68.83% | Losing |
| tl_break_long (base) | 20.9% | -79.42% | Old data — re-enabled, protected |
| tl_break_short (base) | 22.6% | -88.40% | Old data — re-enabled, protected |
| pct-hermes+ | 14.1% | -33.83% | Losing |
| hzscore+ | 23.3% | -24.69% | Marginal |
| hzscore- | 15.8% | -53.50% | Losing |
| ma-cross-5m+ | 10.7% | -15.44% | Catastrophic |
| sqx- | 15.8% | -10.38% | Losing |
| sqx+ | 0.0% | -10.74% | 0% WR |
| pattern_scanner | 22.2% | -5.40% | Losing |

---

## Recommendations

1. **FIX** — `tl_break` direction inversion: `tl_break_long` fires SHORT, `tl_break_short` fires LONG. This is a bug in signal generation logic. All 5 inversions happened today.

2. **RE-ENABLE** — `vel-hermes-` (SHORT): 43.5% WR, +5.00% PnL over 24h, 46 trades. Best performing SHORT signal. Currently disabled. Comment in constants says "45% WR, +0.404% avg, re-test enabled" but flag is False.

3. **DISABLE** — `decider` (SHORT): 11.1% WR, -1.59% PnL. Legacy signal replaced by `signal_compactor.py`. 9 trades, all losers.

4. **KEEP** — `tl_break_long` and `tl_break_short`: Both directions profitable after re-enable. Protected from rotator.

5. **KEEP** — `zscore-rising-` and `zscore-rising+`: Consistent winners. Short signal at 54.8% WR, long at 62.5% WR.

6. **WATCH** — `bb_bounce` SHORT: 50% WR, -1.12% PnL. Only 8 trades — needs more data.

7. **NO ACTION** — All other disabled signals remain confirmed losers. Do not re-enable accel-300, inv-accel-300, gap-300, or pattern scanner signals.

---

## Enabled Signal Inventory

| Signal | LONG | SHORT | Status |
|--------|------|-------|--------|
| TL_BREAK | ON | ON | Protected from rotator |
| HZSCORE | ON | ON | Enabled 2026-08-06 |
| HMACD | ON | ON | Active |
| HMACD_MTF | ON | ON | Active |
| RS | ON | ON | Re-enabled 2026-08-06 |
| MACD_1M | ON | ON | Active |
| COUNTER_FLIP | ON | ON | Active |
| HH_HL | ON | ON | Active |
| ATR_COMPRESSION | ON | ON | Active |
| MA_CROSS | OFF | ON | SHORT only |
| EMA9_SMA20 | OFF | ON | SHORT only |
| EXHAUSTION | OFF | ON | SHORT only |
| TREND_PURITY | OFF | ON | SHORT only |
| VOLUME_HL | OFF | ON | SHORT only |
| MA300_CANDLE | OFF | ON | SHORT only |
| MACD_ACCEL | OFF | ON | SHORT only |
| PCT_HERMES | OFF | ON | SHORT only |
| ACCEL_300 | OFF | OFF | Permanently disabled |
| INV_ACCEL_300 | OFF | OFF | NEVER_REENABLE |
| GAP_300 | OFF | OFF | Permanently disabled |
| PATTERN_* | OFF | OFF | Permanently disabled |
| BB_BOUNCE | OFF | OFF | Permanently disabled |
| VEL_HERMES | OFF | OFF | Disabled 2026-08-04 |
| SQUEEZE_CROSS | OFF | OFF | Disabled 2026-07-28 |
| BOLLINGER_SQUEEZE | OFF | OFF | Disabled 2026-08-01 |

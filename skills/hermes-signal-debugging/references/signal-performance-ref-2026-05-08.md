# Signal Performance Reference Data (as of 2026-05-08)

## Top Signal Combos — All-Time (from live signal_outcomes audit)

### Best LONG combos
| Combo | Trades | WR | Avg Peak | Best Trade |
|-------|--------|-----|---------|------------|
| `accel-300+,rs-s16-150` | 9 | 100% | +343% | GRIFFAIN +526% |
| `accel-300+,momentum,mtf-macd,rsi` | 1 | 100% | +480% | DASH |
| `accel-300+` (bare) | 23 | 17.4% | +13.1% | DASH +406% |
| `trend_purity+` (bare) | 8 | 25% | +19.9% | PENGU +233% |
| `hzscore-,momentum+,vel-hermes+` | 22 | 27% | +7.8% | APE +859% |

### Best SHORT combos (REGIME DEPENDENT — only in range/bearish regimes)
| Combo | Trades | WR | Avg Peak | Best Trade |
|-------|--------|-----|---------|------------|
| `hwave+,hzscore+` | 4 | 50% | +27.4% | AXS +153% |
| `oc-zscore-v9-,zscore-momentum-` | 8 | 37.5% | +26.1% | DOT +256% |
| `oc-zscore-v9-` | 4 | 50% | +16.2% | (standalone) |
| `ma-cross-5m-short,zscore-short` | 13 | 38.5% | +21.9% | CAKE +372% |
| `hzscore+,pct-hermes-` | 56 | 3.6% | -4.2% | **AVOID** in strong bullish |

### Net-profitable combos (live data, 2026-05-08)
| Combo | Dir | Trades | WR | avg_pnl | total_pnl |
|-------|-----|--------|-----|---------|-----------|
| `hzscore-,momentum+,vel-hermes+` | LONG | 22+ | 27% | +0.078% | **+1.71** |
| `pct-hermes+,rs-s178` | LONG | 4 | 50% | +0.395% | **+1.58** |
| `hwave+,hzscore+` | SHORT | 4 | 50% | +0.274% | **+1.10** |
| `pct-hermes+,zscore-long` | LONG | 6 | 50% | +0.083% | +0.50 |
| `hzscore,pct-hermes` | LONG | 3 | 100% | +0.037% | +0.11 |

**hwave+,hzscore+** is the best SHORT combo but hwave was disabled April 18. This is the biggest gap in the SHORT arsenal.

## RS Touch Count Quality Bands

| Touch Count | WR | Avg PnL | Notes |
|-------------|-----|---------|-------|
| 1-20 touches | **44%** | **+0.80%** | Fresh reactive bounces |
| 21-50 | 18% | +0.24% | |
| 51-100 | 20% | +0.47% | |
| 100+ | 40% | +0.02% | Ancient macro levels |
| No RS co-signal | 33% | +0.90% | accel-300+ alone |

**Sweet spot for accel-300+ co-signal: 8-36 touches.**
- rs-s8: GRIFFAIN +526%
- rs-s84: MON +3.4%
- rs-s36: FET +3.2%
- rs-s8: APEX +2.2%

## SKIPPED Signal Pattern

**160 SKIPPED signals, all pct-hermes- SHORT**, conf=77.5-88.0. These pass the confluence
gate (SHORT combos like hzscore+,pct-hermes-) but get SKIPPED at decider_run execution
time by wave/trap/regime filters. Not a signal generation problem — an execution filter problem.

## Sub-Second Trade Lifetimes — Pattern (2026-05-11)

The TRB trades revealing timing problem:

| Trade | Dir | Entry Signal | Close Reason | Age |
|-------|-----|-------------|--------------|-----|
| TRB SHORT | SHORT | hzscore+,rs-r1372 | regime_bull_flip | 34s |
| TRB SHORT | SHORT | hzscore+,rs-r8622 | atr_sl_hit | 4s |
| TRB SHORT | SHORT | hzscore+,rs-r2232 | regime_bull_flip | 5s |
| TRB LONG | LONG | accel-300+,rs-s198 | histogram_fading_fas | 51s |
| TRB LONG | LONG | accel-300+,rs-s1764 | histogram_fading_fas | 6s |

**Interpretation:**
- `histogram_fading_fas` on LONG = momentum was already peaking when signal fired. The acceleration spike IS the peak, not the start of a move.
- `regime_bull_flip` on SHORT = macro regime flipped against SHORT direction. Bullish regime running, shorts get stopped out immediately.
- `atr_sl_hit` after 4s = price moved against position immediately after entry.

**Exit reason meanings:**
- `histogram_fading_fas`: MACD histogram contracting fast — momentum broken. From `macd_rules.py` exit signal `histogram_fading_fast` (histogram_rate < -0.10).
- `profit_monster`: profit target hit — position moved favorably and TP was reached.
- `regime_bull_flip`: macro regime shifted from BEAR to BULL, triggering flip exit.
- `atr_sl_hit`: ATR-based stop loss triggered.

## WR Collapse Timeline

| Period | WR | Regime |
|--------|-----|--------|
| Mar 11-30 | ~53% | Range-bound |
| Apr 1-20 | ~25% | Early trend |
| Apr 21-30 | ~14% | Mean-reversion |
| May 5-7 | ~0% | Strong bullish continuation |

In strong bullish regime (May 5+):
- SHORT signals destroyed: pct-hermes- (0% WR), hzscore+ (20.5% WR)
- LONG signals improved: accel-300+ avg peak +9.92% (May 5+), vs +2.6% overall

## System WR (live audit, 2026-05-07)

Overall system: **11.2% WR across 3,280 trades**. Nearly everything loses money.

| Signal | Trades | WR | avg_pnl% |
|--------|--------|-----|----------|
| `accel-300+` LONG | 42 | 19.0% | -27.0% |
| `pct-hermes+` LONG | 64 | **4.7%** | -52.9% |
| `pct-hermes-` SHORT | 32 | **0%** | -52.3% |
| `hzscore+` SHORT | 73 | 20.5% | -33.8% |
| `hl_reconcile` SHORT | 35 | 57.1% | -1453% (!) |

`hl_reconcile` has 57% WR but -1453% avg_pnl — one or two catastrophic trades.

## signal_runner.py — Confirmed Clean (2026-05-08)

**File:** `/root/.hermes/scripts/signals_runner.py` (83 lines, NOT in git)

Verified clean: ThreadPoolExecutor(21 workers) → `_run_signal()` → `getattr(mod, 'run', None)`.
No DB writes, no trade execution, no branching logic. If pipeline shows 0 signals or wrong
counts, the runner is not the culprit — the individual signal module's `run()` is returning
`None`/`0`/`[]`, or `signals/__init__.py` registry is misconfigured.

When doing systematic code review for T: he wants the current script reviewed, not a tour
of related bugs. signal_runner.py → confirm clean, move to next script. Do not branch.
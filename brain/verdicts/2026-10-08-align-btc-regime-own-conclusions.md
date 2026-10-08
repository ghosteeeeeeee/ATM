# Independent Verdict: align-with-btc-regime.md
Date: 2026-10-08
Auditor: own-conclusions (fresh eyes, no priming)

Method: All SQL run live against `dbname=brain user=postgres` on 2026-10-08 ~21:40 UTC.
All code read directly from `/root/.hermes/scripts/{hermes_constants.py,signal_compactor.py,volatility_gate_v2.py}`.
No prior analysis was consulted. Trade window anchored on `close_time` unless noted; `open_time` sensitivity run for Q1 (identical results, ±1 trade in the 70+ bucket).

Caveat: Q1–Q3 use `signal LIKE '%pump-chain%'`, which excludes the underscore-only variant `pump_chain` (6 trades / 30d, ~2%). Immaterial to conclusions.

---

## Actual Data Findings

### Q1: Pump-chain trades, last 14d, by direction × entry RSI bucket
| Direction | RSI bucket | n | PnL sum | PnL avg | WR |
|---|---|---|---|---|---|
| LONG | 30-40 | 2 | -$0.14 | -$0.070 | 0% |
| LONG | 40-50 | 1 | -$0.24 | -$0.240 | 0% |
| LONG | 50-60 | 1 | -$0.17 | -$0.170 | 0% |
| LONG | 60-70 | 8 | **+$0.12** | +$0.015 | **50.0%** |
| LONG | 70+ | 24 | **+$2.22** | +$0.093 | **54.2%** |
| SHORT | <30 | 26 | +$0.07 | +$0.003 | 42.3% |
| SHORT | 30-40 | 17 | **+$0.25** | +$0.015 | **52.9%** |
| SHORT | 40-50 | 5 | -$0.19 | -$0.038 | 40.0% |
| SHORT | 50-60 | 2 | +$0.01 | +$0.005 | 50.0% |

30d sensitivity (pump-chain, RSI buckets):
- LONG 60-70: 24T, +$0.89, 50.0% WR · LONG 70+: 55T, +$2.41, 41.8% WR
- SHORT 30-40: 29T, **-$1.15**, 37.9% WR · SHORT 50-60: 5T, +$0.28, 60.0% WR

### Q2: Pump-chain SHORT by exit_reason, last 7d
| exit_reason | n | PnL sum | PnL avg | WR |
|---|---|---|---|---|
| hard_max_loss | 11 | -$1.57 | -$0.143 | 0% |
| atr_trail_hit | 5 | +$1.11 | +$0.222 | 80% |
| hard_sl | 1 | -$0.10 | — | 0% |
| rr_engine_resistance_break | 1 | +$0.08 | — | 100% |
| trail_sl | 1 | +$0.53 | — | 100% |
| UNIVERSAL_MAX_HOLD | 1 | +$0.06 | — | 100% |

### Q3: Pump-chain trades per day, last 7d
Oct 2: 2 · Oct 3: 15 · Oct 4: 2 · Oct 5: 1 · Oct 6: 3 · Oct 7: 13 · Oct 8: 11 → **47 trades / 7 days = 6.7/day** (range 1–15).
30d: 259 trades over 30 calendar days = **8.6/day** (24 active days).

### Q4: All trades last 14d by `regime` × direction
| regime | direction | n | PnL | WR |
|---|---|---|---|---|
| NEUTRAL | LONG | 225 | +$3.01 | 54.7% |
| NEUTRAL | SHORT | 73 | -$1.47 | 43.8% |
| NULL | LONG | 7 | +$0.08 | 14.3% |

**MAJOR DATA QUALITY FINDING:** The `regime` column contains ONLY `NEUTRAL` (2,277), `NULL` (3,344), or `''` (8) across all 5,629 trades — there is **no BULL_TREND/BEAR_TREND/RANGING anywhere in the `regime` column**. `entry_regime_4h` is **NULL for 100% of rows** (5,629/5,629). All regime analysis — including the plan's "CEO-verified 30d table" — can only come from `_signal_metadata->>'btc_regime'` (81% coverage in 30d: 675/831).

### Q5: Regime analysis via `_signal_metadata->>'btc_regime'`
30d all trades by btc_regime × direction:
| btc_regime | dir | n | PnL | WR |
|---|---|---|---|---|
| BULL_TREND | LONG | 141 | +$0.54 | 56.7% |
| TRANSITIONING | LONG | 103 | +$0.36 | 47.6% |
| BEAR_TREND | SHORT | 97 | -$1.75 | 42.3% |
| RANGING | LONG | 82 | +$0.98 | 57.3% |
| BEAR_TREND | LONG | 64 | -$0.54 | 40.6% |
| RANGING | SHORT | 59 | -$0.82 | 47.5% |
| TRANSITIONING | SHORT | 47 | -$1.41 | 42.6% |
| BULL_TREND | SHORT | 35 | -$0.44 | 48.6% |
| RANGING_BULL | LONG | 26 | +$1.08 | 57.7% |
| RANGING_BEAR | LONG | 14 | +$0.48 | 35.7% |

30d pump-chain by btc_regime × direction (plan's core supporting cells):
- pump-chain LONG BULL_TREND: **26T, +$0.77, 42.3% WR** (9 winners >+$0.10 vs 10 losers <-$0.10, best +$0.69, worst -$0.18 — thin, fragile edge)
- pump-chain LONG BULL/RANGING_BULL with btc_score ≥60: **27T, +$1.65, 44.4% WR**
- pump-chain LONG BEAR_TREND: 20T, -$0.41, 30.0% WR (blocking justified)
- pump-chain LONG RANGING: 17T, **-$1.25**, 29.4% WR (losing — note: plan allows only RANGING_BULL, correctly)
- pump-chain- SHORT BULL_TREND: **20T, +$0.34, 55.0% WR** (exact match to plan)
- pump-chain LONG by btc_score zone 30d: score<40: 32T +$0.55 · 40-60: 25T +$0.84 · **score≥60: 48T +$1.48, 47.9% WR**

**Q5 (CONTINUUM-BLOCK effectiveness): pump-chain LONGs DID open under bear structure.** Last 14d, pump-chain LONG with bear-ish btc_regime: BEAR_TREND 6T (Oct 1×3, Oct 2, **Oct 7, Oct 8**), 0% WR, -$0.67; RANGING_BEAR 3T (+$0.87 net, 2/3 WR). In the last 7d alone: 3 pump-chain LONGs opened under BEAR_TREND/RANGING_BEAR metadata. The exact metadata fields requested (btc_phase/btc_linreg/btc_ema300) do not exist in `_signal_metadata` — only `btc_regime`, `btc_score`, `btc_trend_bias`, `btc_linreg_bias`, `wave_phase` are present (continuum `linreg_direction`/`ema300_position`/`market_phase` appear in 3/2,000 recent rows).

btc_regime NULL bucket, 30d (plan mod #4 check): SHORT **95T, +$3.27, 66.3% WR** — confirmed as by far the best SHORT bucket (every defined regime SHORT bucket is negative). LONG NULL: 61T, -$0.44, 39.3% WR.

### Q6: Exact constant values (read from file)
| Constant | Value | Line |
|---|---|---|
| SHORT_CONTINUUM_SCORE_MAX | **60** (raised 40→60, 2026-10-06) | 1356-1357 |
| LONG_RSI_CEILING | **85** (raised 70→85, 2026-10-07) | 897 |
| PUMP_CHAIN_LONG_RSI_MAX | **85** (raised 70→85, 2026-10-07) | 1344 |
| PUMP_CHAIN_SHORT_RSI_MIN | **45** (raised 40→45, 2026-10-06) | 1349 |
| CONF_FILTER_MAX | **92** (raised from 89); CONF_FILTER_MIN=70 | 1303-1304 |
| BTC_TIMING_GUARD_PUMP_CHAIN_LONG | **1.00** (raised from 0.30) | 1077 |
| BTC_REGIME_ALIGN_ENABLED | **does not exist** anywhere in the codebase (grep clean) | — |

STANDALONE_BYPASS_SIGNALS (line 2732-2794+) contains, among ~90 entries: **'pump-chain', 'pump_chain' (line 2733), 'pump-chain-v5' (2781), and 'pump-chain', 'pump-chain+', 'pump-chain-' (line 2794)**. pump-chain is bypass-listed three separate times. Also present: mover, open-skies, accel-300 family, bb-bounce family, volume-breakout family, trend-ride, tl-bounce, squeeze-reversal, grind-breakout, etc.

---

## Claim Verification

### Claim 1: "LONG RSI 60-70: +$1.26, 64.4% WR"
Verdict: **DISAGREE**
Actual (14d): 8T, **+$0.12**, avg +$0.015, **50.0% WR**. 30d: 24T, +$0.89, 50.0% WR. Neither window reproduces +$1.26 or 64.4%. This number is cited in the constants file itself (line 1344) as justification for raising the ceiling 70→85 — that justification does not reproduce against the DB at 14d or 30d.

### Claim 2: "LONG RSI ≥70: +$0.85"
Verdict: **DISAGREE (number unreproducible; direction debatable)**
Actual (14d): 24T, **+$2.22 sum** (avg $0.09), 54.2% WR — the single best PnL bucket for pump-chain LONG. 30d: 55T, +$2.41, 41.8% WR. The plan's own "falsification" (-$0.46 live) is equally unreproducible. What IS notable: 10 pump-chain LONGs with RSI ≥70 opened Sep 30–Oct 4 when PUMP_CHAIN_LONG_RSI_MAX was still 70, and entries at RSI 97.6/98.2 opened Oct 7-8 despite the ceiling being 85 — see Risks.

### Claim 3: "SHORT RSI 30-40: -$1.35, 33.3% WR"
Verdict: **DISAGREE (sign flipped in current window)**
Actual (14d): 17T, **+$0.25, 52.9% WR** — profitable. 30d: 29T, -$1.15, 37.9% WR (sign matches claim at 30d). The bucket flipped positive in the most recent two weeks. Any filter premised on this bucket bleeding is fitting a stale edge — classic "edges reverse in recent weeks."

### Claim 4: "SHORT RSI 50-60: +$0.29"
Verdict: **PARTIAL**
Actual (14d): 2T, +$0.01. 30d: 5T, **+$0.28**, 60% WR — matches the claim to within a penny, but n=5. Statistically meaningless either way.

### Claim 5: "pump-chain- SHORT atr_trail_hit: 6T, 83% WR, +$1.14"
Verdict: **PARTIAL (snapshot drift)**
Actual (7d): **5T, 80% WR, +$1.11**. Directionally correct; off by one trade (claim was likely taken ~1 day earlier).

### Claim 6: "pump-chain- SHORT trail_sl: 3T, 100% WR, +$0.62"
Verdict: **PARTIAL (n overstated)**
Actual (7d): **1T, 100% WR, +$0.53**. Only one trail_sl exit in the window.

### Claim 7: "pump-chain- SHORT hard_max_loss: 13T, 0% WR, -$1.61"
Verdict: **PARTIAL (snapshot drift)**
Actual (7d): **11T, 0% WR, -$1.57**. Off by 2 trades / $0.04.

### Claim 8: "system fires 2-3 pump-chain trades/day"
Verdict: **DISAGREE**
Actual: **6.7/day (7d)**, **8.6/day (30d)**, highly variable (1–15/day). The plan's own mod #6 says "12T/24h" — the plan is internally inconsistent with this claim, and both overstate vs. each other in opposite directions.

### Claim 9: "8+ filters block signals when BTC is bullish"
Verdict: **PARTIAL (filters exist; the framing is misleading for pump-chain)**
Verified to exist with the stated values: LONG_RSI_CEILING=85 (dynamic: min(85,60) for Grade C/D, line 3751), PUMP_CHAIN_LONG_RSI_MAX=85 (enforced line 2933), PUMP_CHAIN_LONG_RSI_MIN=35, PUMP_CHAIN_LONG_MAX_ENTRY_GAP=1.5, BTC_TIMING_GUARD_PUMP_CHAIN_LONG=1.00 (enforced line 1312), CONF_FILTER_MAX=92 / MIN=70, VOL_FLOOR=0.15, DIRECTIONAL_CAP, blacklists. SHORT-side: SHORT_CONTINUUM_SCORE_MAX=60, SHORT_RSI_CEILING=65, SHORT_RSI_HARD_CEILING=75, SHORT_RSI_HARD_FLOOR=45, PUMP_CHAIN_SHORT_RSI_MIN=45.
BUT: these are **regime-agnostic entry-quality filters, not "BTC-bullish" filters**. The two filters that are actually BTC-state-aware — the BTC chop gate (Layer A, line 1213-1217) and the CONTINUUM-BLOCK (Layer B, line 2609-2615) — **both exempt pump-chain by name**. The only BTC-state filter that binds pump-chain LONG is BTC_TIMING_GUARD (fires only when BTC already moved +1% in 30m). And empirically pump-chain LONG fires freely under bullish BTC: 48 trades in the btc_score≥60 zone in 30d (+$1.48). "8+ filters block signals when BTC is bullish" is true as a list of constants but false as a description of what constrains pump-chain LONG in bullish regimes.

### Claim 10: "RR engine blocks trades with R:R < 1.3"
Verdict: **DISAGREE (wrong threshold, and it blocks nothing)**
- R:R minimums are **regime-adjusted, not fixed**: RR_ENGINE_MIN_RATIO_FLAT=2.5, NORMAL=2.0, **HIGH=1.3**, EXTREME=2.0 (lines 3619-3622). "1.3" is only the HIGH-regime value.
- **RR_ENGINE_SHADOW=True and RR_ENGINE_FORCE=False** (lines 3614-3615) — the engine currently **blocks nothing**; it only logs.
- The only *active* R:R hard block is via the confidence multiplier: RR_ENGINE_CONF_SHADOW=False, **RR_ENGINE_CONF_HARD_BLOCK_RR=0.70** (line 3665) — blocks R:R < 0.70, not 1.3.

---

## Code Integration

**Code check 1 — Does CONTINUUM-BLOCK already block pump-chain LONG during bear structure? NO.**
- `signal_compactor.py:2609`: `_is_pump_chain = 'pump-chain' in bare_source or 'pump_chain' in bare_source`
- `signal_compactor.py:2613`: `_btc_exempt = _is_pump_chain or _is_mover or _is_open_skies or _is_accel_breakout`
- `signal_compactor.py:2615`: `if BTC_CHOP_GATE_ENABLED and not _btc_exempt:` — **the entire continuum block, including the CONTINUUM-BLOCK logic at 2668-2725, is inside this guard.** Pump-chain never enters it; `_btc_mom_ok_for_bypass` stays at its default `True` (line 2608).
- Layer A (chop gate, line 1213-1217): pump-chain is "BTC-exempt … bypassing chop gate" — logged as `[BTC-CHOP-OVERRIDE] BTC-exempt signal type`.
- Empirical confirmation: 6 pump-chain LONGs opened with BEAR_TREND btc_regime in the last 14d (0% WR, -$0.67), 2 of them in the last 48h.
- The plan's implementation premise ("query continuum, bypass the LONG block in bullish regime") is thus building a *second* regime gate for a signal that is currently exempt from the *first* one.

**Code check 2 — Is STANDALONE_BYPASS_SIGNALS already exempting pump-chain from the confluence gate? YES.**
- pump-chain appears three times in the tuple: lines 2733, 2794 (`'pump-chain', 'pump-chain+', 'pump-chain-'`), plus `'pump_chain'` variants and `'pump-chain-v5'` (2781).
- The LONG-NEUTRAL block (line 2774-2804) allows any signal where `(bare_source in STANDALONE_BYPASS_SIGNALS or _src_stripped in …) and _btc_mom_ok_for_bypass`. For pump-chain that second term is **always True** (exempt — see above). Therefore **pump-chain LONG already passes the LONG-NEUTRAL block in ALL regimes, bullish or not.** The plan's stated bypass ("If bullish → bypass LONG-NEUTRAL block", implementation step 2) is, for pump-chain, **a no-op as written**.
- **Stale/contradictory comment:** `signal_compactor.py:2782` says "pump-chain/pump_chain: NOT bypassed — PM Trail + RR Engine both manage" — directly contradicted by lines 2733/2794 in hermes_constants.py. Someone will be misled by this; fix it.

**Code check 3 — Does volatility_gate_v2.py already have per-signal regime routing for pump-chain? YES, extensively.**
- `SIGNAL_TYPE_OVERRIDES` (line 300-410): EXTREME `pump_chain-`/`pump-chain-`/`pump_chain+`/`pump-chain+`/bare all = 1.0; NORMAL `pump-chain+` = 1.0, `pump-chain-` = 1.2, bare `pump-chain` = 0.5; HIGH `pump-chain+`/`-`/bare = 1.0 (with note that PUMP_CHAIN_SHORT_HIGH_BLOCK_ENABLED=True hard-blocks pump-chain- SHORT in HIGH at compactor line 2901).
- `REGIME_SIGNALS` legacy tables list pump-chain in NORMAL and HIGH (lines 72-74, 114-116); EXTREME lists the LONG variants (163-165).
- `VOL_PHASE_MULTS`: `('EXTREME','Pump_Flow'): 0.0` (line 256), HIGH `Pump_Flow: 0.5` (line 284), NORMAL Pump_Flow removed from block (line 268).
- So "regime routing for pump-chain" is already shipped. Any new BTC-regime layer must be checked against this matrix to avoid double-counting (e.g., NORMAL pump-chain- is simultaneously boosted 1.2× here and hard-blocked in HIGH at the compactor).

**Overlap/conflict summary:** The proposed BTC_REGIME_ALIGN gate overlaps with: (a) STANDALONE_BYPASS (already bypasses LONG-NEUTRAL for pump-chain in all regimes), (b) CONTINUUM-BLOCK/BTC chop gate (already exempt pump-chain), (c) volatility_gate_v2 SIGNAL_TYPE_OVERRIDES (already routes pump-chain per vol regime), (d) BTC_TIMING_GUARD (the one filter that actually bites in bullish pumps — and the plan explicitly will not remove it). As written, the new flag either does nothing or does something the plan hasn't specified.

---

## Risks Not Mentioned in Plan

1. **The premise is unverified and probably wrong as stated.** Pump-chain LONG is not blocked in bullish regimes today: 26 BULL_TREND pump-chain LONGs and 48 btc_score≥60 pump-chain LONGs opened in 30d, and pump-chain already bypasses the LONG-NEUTRAL block in all regimes. The plan never names the specific block that currently stops a bullish-regime pump-chain LONG. If the flag bypasses "the LONG-NEUTRAL block," it changes nothing; if it bypasses something else, that something is unspecified — implementation ambiguity is the biggest risk here.
2. **Success metric contradicts the supporting data.** Success = "WR ≥55% on regime-aligned LONG subset." Historical BULL_TREND pump-chain LONG WR is **42.3%** (26T); BULL/RANGING_BULL + score≥60 is **44.4%** (27T). The subset has never run at 55% WR. The metric as written predicts failure even if PnL is fine (+$0.77/30d at $0.03/trade).
3. **The supporting cell is fragile.** BULL_TREND pump-chain LONG: n=26, WR 42.3% (below coin flip), PnL sum +$0.77 driven by 9 winners >$0.10 vs 10 losers <-$0.10. Best single trade +$0.69. This is not a robust edge; a single bad week flips it.
4. **BTC_TIMING_GUARD_PUMP_CHAIN_LONG=1.00 works against the plan's goal.** In exactly the "BTC is pumping, bullish regime" condition the plan wants to allow, a BTC 30m move >+1% blocks pump-chain LONG (compactor line 1312). The plan says it will not remove existing filters — so even with BTC_REGIME_ALIGN on, the timing guard may still block the target trades, and the shadow log will show near-zero would-blocks from the bypassed gate while the real blocker goes untouched.
5. **Baseline instability in the 7d window.** LONG_RSI_CEILING and PUMP_CHAIN_LONG_RSI_MAX went 70→85 on Oct 7; volatility_gate pump-chain NORMAL/HIGH entries were re-enabled Oct 7-8; pump-chain- NORMAL was boosted to 1.2 on Oct 8. The 7d shadow window straddles ≥4 entry-filter changes — counterfactual attribution will be confounded.
6. **RSI ceiling enforcement anomaly (bug candidate).** Pump-chain LONG entries with `entry_rsi_14` = 88.24 (Oct 3, when ceiling was 70), 97.58 (Oct 7) and **98.15 (Oct 8, ceiling=85)** are in the DB. Either `entry_rsi_14` is recorded at a different moment than the filter-time RSI (known detection-vs-execution gap), or the PUMP_CHAIN-RSI-MAX block is bypassed on some path. Needs a bug-hunt before any RSI-based conclusions are trusted.
7. **Regime data plumbing is broken.** `trades.regime` is only ever NEUTRAL/NULL; `entry_regime_4h` is 100% NULL (5,629/5,629) — a dead writer. The plan's success-metrics evaluation must be specified against `_signal_metadata->>'btc_regime'` (81% coverage), and the ~19-24% missing-metadata trades are not random: they are the **best SHORT bucket** (+$3.27/95T/66.3% in 30d). Any "regime-aligned vs not" comparison is biased by coverage.
8. **CONF filter is scale-blind.** Confirmed: `final_confidence` in metadata runs 50.9 → 281.7 (avg 97.1, 10/189 trades >100 in 7d). CONF_FILTER_MAX=92 checks the *pre-multiplier* conf, so it does not see the out-of-scale final values. Plan flags this (sidewise #1) — verified real and worth fixing before any confidence-conditional logic is added.
9. **Metadata vocabulary mismatch.** The plan's implementation step ("query continuum for BTC regime") must reconcile two vocabularies: continuum.db uses `market_phase/linreg_direction/ema300_position` (DECLINING/CALM/RECOVERY/NEUTRAL/STORMY × LEAN_BEAR/BEAR/LEAN_BULL/BULL × ABOVE/AT/BELOW), while trades metadata uses `btc_regime` enum (BULL_TREND/BEAR_TREND/RANGING/RANGING_BULL/RANGING_BEAR/TRANSITIONING). The plan's sidewise finding #4 acknowledges this; it must be resolved in the spec, not in code, or "bullish" will mean different things in the gate vs. the evaluation.

---

## Overall Assessment

**APPROVE WITH CHANGES**

Reasoning:

- **What holds up:** The plan's central 30d table is reproducible nearly to the trade (RANGING_BULL LONG 26T/57.7%/+$1.08 and pump-chain- BULL_TREND SHORT 20T/55%/+$0.34 are exact matches; BULL_TREND/RANGING/pump-chain+ rows are within window drift). The CEO-falsification discipline and mod #4 (regime-NULL is the best SHORT bucket: verified, +$3.27/95T/66.3%) are correct. The governance skeleton — default-OFF flag, shadow logging, 7d window, independent backtest, bug_hunter, pipeline restart — is exactly right and matches AGENTS.md doctrine. Not touching SHORT filters is supported: BEAR_TREND SHORT is -$1.75/30d but pump-chain- BULL_TREND SHORT is a genuine (small) positive.

- **What must change before implementation:**
  1. **Re-scope step 2.** As written, "bypass the LONG-NEUTRAL block when bullish" is a no-op for pump-chain (already bypassed via STANDALONE_BYPASS in all regimes). First ship a *pure shadow-log probe* (log would-block/would-allow for pump-chain LONG under bullish BTC with zero behavior change) for 7d. If it logs zero would-blocks, the premise is dead and the flag should not be built.
  2. **Fix the success metric.** WR ≥55% is inconsistent with the plan's own supporting data (42-44% historical WR in the target subset). Use PnL/trade and max-drawdown guardrails; drop the WR hurdle or set it at ~45%.
  3. **Specify the interaction with BTC_TIMING_GUARD_PUMP_CHAIN_LONG=1.00** — the only BTC-state filter that actually binds pump-chain LONG, and it binds hardest during bullish pumps. If the plan won't touch it, state plainly that the flag likely changes nothing.
  4. **Do not cite the "+$1.26/64.4%" and "+$0.85" numbers again** — they do not reproduce at 14d or 30d (actual: +$0.12/50% and +$2.22/54.2%). The constants-file comment at line 1344 should be corrected too.
  5. **Fix the stale comment** at signal_compactor.py:2782 ("pump-chain NOT bypassed" — false).
  6. **Specify evaluation data source**: `_signal_metadata->>'btc_regime'`, not `trades.regime` (NEUTRAL/NULL only) and not `entry_regime_4h` (100% NULL).
  7. **File a bug-hunt** for the RSI-ceiling anomaly (RSI 98.15 entry with ceiling 85).

- **Bottom line:** The plan is honest about its own falsifications and well-governed, but its constructive premise — that bullish-regime pump-chain LONGs are being blocked — is contradicted by both the code (pump-chain is exempt from every BTC-state gate and already bypasses LONG-NEUTRAL) and the data (48 bullish-zone pump-chain LONGs fired in 30d). Ship the shadow probe first; build the bypass only if the probe shows real blocks. Expected value of the full build, absent probe evidence: ~zero.

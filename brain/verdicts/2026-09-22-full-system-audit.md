# FULL SYSTEM AUDIT — Overcomplication & Profitability
**Date:** 2026-10-01 (file dated per request: 2026-09-22)
**Auditor:** Independent (report-only, no code changes)
**Scope:** Entire signal pipeline — generation → schema ingestion → compactor scoring → hotset → decider execution
**Method:** Read all target files line-by-line, queried live SQLite runtime DB (`signals_hermes_runtime.db`), live PostgreSQL brain DB (trades), pipeline.log, hotset.json, raw_signals.json. Every number below was produced by running code/queries in this session — nothing from memory.

---

## VERDICT IN ONE LINE

**The system is massively over-engineered for its results: 2,057 signals in 24h → 3 executed (0.15% pass-through), hotset currently EMPTY, 75+ gate mechanisms, 28 scoring multipliers — and PostgreSQL (source of truth per AGENTS.md) shows the system is NET NEGATIVE (-$0.40/7d, -$5.96/30d, -$13.30 all-time over 5,437 trades), not "+$1.81/7d". The gate gauntlet is not protecting profit — it is starving the system while the few signals that do trade still lose money.**

---

## 1. TOTAL GATES A SIGNAL MUST PASS: **~75 distinct mechanisms**

The CEO's list of 22 is a significant undercount. Full enumeration, by pipeline stage:

### Stage A — Ingestion (`signal_schema.py add_signal`) — 11 gates
| # | Gate | Status |
|---|------|--------|
| 1 | Dead-signal blocklist | Active |
| 2 | Min confidence floor (<50) | Active |
| 3 | Price validation | Active |
| 4 | Monte Carlo gate | Active (fail-open) |
| 5 | Trend alignment filter (EMA20/50 hard block) | Active |
| 6 | 5m+15m regime confirmation (SHORT) | Active |
| 7 | Confidence ceiling (88) | Active |
| 8 | Directional blacklists (SHORT=127 tokens, LONG=103 tokens) | Active |
| 9 | Signal source blacklist (7 entries + subset matching) | Active |
| 10 | Per-source kill-switch flags | **~200 individual flag checks** in a giant if/elif chain |
| 11 | Ichimoku+RS combo block | Active |

### Stage B — Compactor hard gates (`_score_signal`, return 0.0) — 11 gates
12. Confidence filter (CONF_FILTER_MIN=70 / MAX=92)
13. Directional cap (80% concentration max)
14. BTC chop gate (momentum family blocked when BTC 30m flat; continuum override)
15. BTC timing guard (per-signal chase thresholds)
16. Chop detector (momentum blocked in chop; 4-input regime vote)
17. Time block — **DISABLED (TIME_BLOCK_ENABLED=False)**
18. Pump-chain LONG dead hours — **empty list (no-op)**
19. Pump-chain SHORT dead hours — **empty list (no-op)**
20. Pullback SHORT dead hours — **empty list (no-op)**
21. Pullback SHORT NORMAL-regime block
22. Hall of shame (30d WR < 55% → block)

### Stage C — Compactor hotset build — ~25 gates
23. Blacklists re-check · 24. Solana-only block · 25. Delisted block
26. Slope filter (SHORT vs price trend) · 27. EMA300-slope filter (SHORT)
28. LONG RSI < 20 block · 29. Cosig-gate poison combos (5 hardcoded combos)
30. Weak-combo blocks (3) · 31. **Confluence gate (2+ unique types)** + 116-entry bypass list + NEUTRAL relax
32. SHORT-in-NEUTRAL block · 33. LONG-in-NEUTRAL block
34. accel-300-v3 EXTREME/FLAT blocks (4) · 35. accel-300 SHORT FLAT · 36. accel-300 SHORT RECOVERY-phase
37. pump-chain HIGH blocks (2) · 38. pump-chain RSI_MIN blocks (2) · 39. Coiled-spring regime filter (NORMAL only)
40. Disabled-component check · 41. Continuum block (LONG vs BTC bearish structure)
42. Hotset filters (WR threshold, open-position, recently-flipped, OC-only combo, source blacklist, disabled components)
43. Spike filter (both directions, candle+RSI) · 44. SHORT RSI floor (40) · 45. SHORT RSI ceiling (65)
46. LONG RSI floor (20) · 47. LONG RSI ceiling (dynamic) · 48. SHORT BB dead zones (2)
49. Oversold-SHORT (1m RSI<35) · 50. Vel filter (SHORT) · 51. Pump-chain vel (both dirs)
52. Vol floor (<0.30%) · 53. SL-zone block · 54. TVS override rate-limiter
55. Hotset-final single-source guard · 56. Preserve-merge single-source guard · 57. Preserve spike/pump-chain/age blocks
58. Safety-filter last-resort single-source block

### Stage D — Decider execution (`decider_run.py`) — ~17 gates
59. Dead-hours block (delayed entries) · 60. Max positions cap
61. Context gate (rule-based): speed, momentum, RSI live+detect, z-score, misaligned-direction, counter-trend trap, ranging block, wrong-phase blocks, weak-momentum opposing
62. SHORT RSI hard floor (25, no override) · 63. SHORT RSI floor/ceiling (live+detect double-check) · 64. LONG RSI ceiling/floor (live+detect)
65. LLM context gate (GO/SKIP/NAY) · 66. Similar-setup lookup · 67. Wrong-side penalty/skip
68. Token-sentiment skip · 69. Dynamic inversion · 70. BTC crash filter (crash block + BTC-accel block + BTC momentum filter + BTC level filter)
71. Direction WR gate · 72. Hebbian gate · 73. Macro gate · 74. Signal-quality gate (grade/sharpe/PF) · 75. LLM gate re-check at execution

**Of these ~75: roughly 45 are hard blocks, ~20 are soft score multipliers that compound into near-certain death, and 4 are currently inert (disabled flag / empty lists).**

---

## 2. TOTAL MULTIPLIERS IN SCORING: **28 in the final formula** (CEO listed 25 — three were missed)

Exact formula from `signal_compactor.py` line 2035:

```
final_score = score × survival_bonus × staleness_mult × reg_mult × dir_outcome_mult
  × source_mult × speed_mult × tide_mult × continuum_mult × trend_filter_mult
  × zscore_accel_mult × favorites_mult × leaderboard_mult × combo_mult × penalty_mult
  × amplitude_mult × time_block_mult × phase_mult × confluence_mult × inverse_mult
  × lifecycle_mult × rr_mult × dir_bias_mult × alt_btc_div_mult × vol_regime_mult
  × short_normal_mult × oscillator_mult × regime_conf_mult × thesis_validation_mult
```

**Missing from the CEO's list:** `oscillator_mult`, `regime_conf_mult`, `thesis_validation_mult`. Plus embedded modifiers: source-count bonus (+0.10 inside source_mult), directional-outcome velocity tiers, tide weather-vane adjustment to dir_outcome_mult, integral penalty, direction-lock (0.0), and `tp_bonus_mult` (1.5x) applied post-hoc for ranking.

**Do they conflict? YES — catastrophically.** Five different systems all score "is this direction aligned with the trend/BTC?":
- `reg_mult` (regime ±50%)
- `dir_bias_mult` (BTC momentum: 0.4 / 1.35)
- `continuum_mult` (BTC structure: 0.5 / 1.5)
- `trend_filter_mult` (EMA20/50: 0.7)
- `alt_btc_div_mult` (0.5)

**Worst-case counter-trend LONG:** 0.5 × 0.4 × 0.5 × 0.7 × 0.5 = **0.035x** — score obliterated.
**Best-case pro-trend signal:** 1.5 × 1.35 × 1.5 = **3.0x**.
**Spread between worst and best case on identical confidence: ~85x.** The multipliers don't just overlap — they compound. Meanwhile six separate systems read the same token-performance history (hall of shame, leaderboard_mult, combo_mult, penalty_mult/LOSERS, TVS, directional outcome), and volatility regime is applied three ways simultaneously (vol_regime_mult, regime_conf_mult, short_normal_mult) plus per-signal vol-regime hard blocks.

**In live mode** (`_VOL_GATE_V2_ENABLED=True`): phase_mult and inverse_mult are pinned to 1.0 (folded into lifecycle_mult), so 26 of 28 terms actively vary. Oscillator_mult is shadow-mode (no-op) — 25 active terms.

---

## 3. SIGNAL GENERATORS: 72 registered, **45 enabled**, **~12 actually profitable**

| Metric | Count | Source |
|--------|-------|--------|
| Signal files on disk (`scripts/signals/`) | ~140 | ls |
| Registry entries | 72 | `signals/__init__.py` |
| Enabled + loaded (run fn not None) | 45 | `get_registered_signals()` |
| Registered but disabled (still imported every cycle) | 27 | registry diff |
| Distinct signal types in runtime DB (all-time) | 46 | SQLite |
| Distinct signal types ever marked executed | 22 | SQLite |
| Distinct signal labels traded 30d (PG) | 141 | PostgreSQL |
| Signal families profitable over 30d | **12** | PostgreSQL |
| Signal families losing over 30d | ~128 | PostgreSQL |

**Top profitable signals (30d, PG):**
| Signal | Trades | WR | PnL |
|--------|--------|-----|-----|
| volume-breakout-long+ | 20 | 70.0% | +$2.48 |
| bb_bounce_v2_long | 73 | 74.0% | +$2.08 |
| open_skies* | 19 | 63.2% | +$1.56 |
| pump_chain | 43 | 67.4% | +$0.98 |
| pump-chain+ | 80 | 41.3% | +$0.95 |
| doji-bottom-long | 12 | 66.7% | +$0.67 |
| rr-struct+ | 15 | 73.3% | +$0.59 |
| pullback-entry- | 119 | 52.1% | +$0.35 |

Gross wins across all 30d signals: +$15.22 from 64 profitable labels; gross losses: -$20.99 from 76 losing labels. **The entire negative PnL comes from the long tail of losing signals.** (*open_skies is currently disabled in the registry despite positive 30d PnL — killed 2026-09-17 on a different data window.)

**24h signal-type concentration:** pump-chain 843 (41%), support_resistance 689 (33%), ichimoku_short 129 — top 3 types = 82% of all generated signals. Almost none execute.

---

## 4. PASS-THROUGH RATE (Q1): **0.15% — and currently 0%**

| Window | Signals generated | Trades executed | Pass-through |
|--------|------------------|-----------------|--------------|
| Last 24h (runtime DB) | 2,057 | 3 | **0.15%** |
| Last 7d (PG ÷ runtime) | ~14,400 | 118 | **~0.8%** |
| Current cycle (hotset) | 6–9 combo_keys/5min | 0 | **0% — hotset EMPTY** |

24h fate breakdown (runtime DB):
- **EXPIRED: 1,916 (93.1%)** — died of staleness/confluence starvation
- SKIPPED: 133 (6.5%)
- PENDING: 9
- EXECUTED: 3 (1 with decision=EXECUTED)

Single-source vs multi-source fates (24h): 1,634 single-source EXPIRED vs 269 multi-source EXPIRED. **80% of all signals are single-source — they structurally cannot pass the confluence gate before the 10-minute staleness decay zeroes them.**

Pipeline log: "No signals after pre-filter" appeared **318 times** in the recent log window. Compaction queries return only 6–9 combo_keys per 5-minute cycle; zero survive to hotset.json (cycle 15808: "0 tokens in hotset").

**⚠️ MATERIAL DISCREPANCY — PnL premise:** The CEO states "+$1.81/7d". PostgreSQL (source of truth per AGENTS.md) says:
- 7d: **-$0.40** over 118 trades
- 30d: **-$5.96** over 1,036 trades
- All-time: **-$13.30** over 5,437 trades

The system is not "barely profitable" — on the authoritative record it is net negative. The +$1.81 figure could not be reproduced from PG or trades.json (trades.json rolling window shows 5,422 closed trades, open_count=2, and its per-trade PnL sums differently). **No strategy decision should proceed until this is reconciled.** Additionally, 317 rows have `executed=1` but `decision='EXPIRED'` — an execution-recording inconsistency worth investigating.

---

## 5. KILL RANKING (Q2): Which gate kills the most?

From pipeline.log gate-tag frequency (recent log window, ~20MB tail — indicative, not a full-24h census):

| Rank | Gate | Hits | Type |
|------|------|------|------|
| 1 | **SPIKE-FILTER** | 1,644 | Hard block (both directions) |
| 2 | LONG-NEUTRAL (4h regime) | 1,102 | Hard block |
| 3 | PUMP-CHAIN-SHORT-HIGH (vol regime) | 1,044 | Hard block |
| 4 | CONTINUUM-BLOCK | 892 | Hard block |
| 5 | SHORT-NEUTRAL (4h regime) | 879 | Hard block |
| 6 | PUMP-CHAIN-SHORT-RSI-MIN | 603 | Hard block |
| 7 | LONG-RSI-BLOCK (RSI<20) | 494 | Hard block |
| 8 | HALL-SHAME (30d WR<55%) | 346 | Hard block |
| 9 | PUMP-CHAIN-HIGH | 319 | Hard block |
| 10 | LONG-RSI-CEILING | 226 | Hard block |
| 11 | SLOPE-FILTER | 164 | Hard block |
| 12 | BTC-CHOP-GATE | 145 | Hard block |
| 13 | SHORT-RSI-FLOOR | 102 | Hard block |
| 14 | VOL-FLOOR | 98 | Hard block |
| 15 | OVERSOLD-SHORT | 76 | Hard block |

(Also logged but non-lethal multipliers: REGIME-CONF 1,560, CONTINUUM-AUTH 1,534, ALT-BTC-DIV 121, COMBO 38, TIDE-WV 9.)

**But the #1 killer doesn't appear in these logs at all: staleness/confluence starvation.** 1,916 signals (93%) expired without a specific gate tag — they simply aged out because the confluence gate needs 2+ signal types within a 10-minute window and 80% of signals are single-source. **The confluence gate + staleness decay is the single largest eliminator, killing ~93% of signals by attrition before any named gate fires.**

Notable: pump-chain alone triggers 3 separate hard blocks (HIGH regime ×2 directions, SHORT RSI_MIN, SHORT dead-hours) + spike filter + vel filter + timing guard — yet it is the system's #2 most profitable signal family (+$1.59 combined 30d). **The gates are blocking the winners as aggressively as the losers.**

---

## 6. REDUNDANCIES FOUND

1. **TWO trend filters, same constants, computed twice** — `signal_schema.py` (EMA20/50 hard block + 5m/15m regime confirmation) and `signal_compactor.py` (EMA20/50 penalty mult 0.7). Both import `TREND_FILTER_TIMEFRAME=15m`, `TREND_FILTER_EMA_FAST/SLOW` from the same constants file. Duplicate logic, different enforcement modes.

2. **FOUR overlapping chop/regime systems** — BTC chop gate (momentum_cache velocity), chop detector (4-input vote: market phase + vol regime + directional outcome + BTC momentum), market_phase_gate (signal-composition phase), volatility_gate_v2 (ATR regime + phase + lifecycle + inverse). chop_detector.py's own docstring admits it "combines 4 existing systems." Then the compactor adds its own continuum-based overrides on top.

3. **FIVE trend-alignment multipliers** (see §2) — reg_mult, dir_bias_mult, continuum_mult, trend_filter_mult, alt_btc_div_mult all answer the same question with different data sources and thresholds.

4. **SIX token-performance-history systems** — hall of shame (hard block), leaderboard_mult, combo_mult, penalty_mult/LOSERS, TVS thesis validation, directional outcome weather vane. All read overlapping trade history; three of them can independently zero a signal.

5. **THREE volatility-regime applications** — vol_regime_mult (expansion/compression boost), regime_conf_mult (EXTREME boost), short_normal_mult (SHORT-in-NORMAL penalty) — plus per-signal vol-regime hard blocks. The same ATR classification gates AND multiplies simultaneously.

6. **Continuum consulted in 5+ places with different rule sets** — continuum authority (scoring), continuum block (hotset), SHORT-NEUTRAL continuum override, BTC-chop continuum override, continuum oscillator multiplier (shadow), continuum_context trend boost. Each with its own phase/linreg/EMA condition logic (recently patched 3× on 2026-09-24 alone for false bearish triggers — evidence the rule sets disagree).

7. **Confluence gate vs 116-entry bypass list** — the bypass list covers nearly every active signal family (pump-chain, accel-300 ×6 variants, bb-bounce ×5 variants, r2-trend ×4, squeeze, grind ×2, continuation, hzscore, return-exhaustion, tl-break, ct-hot, more). With 116 bypass entries for 45 active signals, the gate is decorative for most of the roster — yet still kills the long tail (see raw_signals.json: 5 of 8 current-window signals blocked by CONFLUENCE_GATE).

8. **`signal_schema.py` per-source flag chain** — ~1,500 lines of enable-flag checks for signals that no longer exist in the registry (pct_hermes, vel_hermes, hmacd, mtf_momentum, phase_accel, fast_momentum, gap_300, ma_cross, r2_rev, tl_break, bollinger_squeeze, wyckoff, atr_compression, counter_flip, wave_catcher, coin_tracker_hot, pump_catcher, pattern_*, hl_copy_trader, range_finder, range_breakout, vortex_break, mtp_zscore, zscore_rising, exhaustion, ma_100_cross, ema9_sma20…).

---

## 7. DEAD CODE / ORPHANED CONFIG (Q3)

- **27 disabled registry entries** — still imported (try/except) on every pipeline cycle; ema300_dip_long/short, bb_bounce_short/long, macd_divergence, slow_grind ×2, accel_300_v2/v3/v4 ×6, inverse_accel_300_v2, range_reversion ×2, coiled_spring_trigger, btc_wave_detector, pump_chain_long/v4/v5, open_skies, neutral_sniper, breakout_long, trend_purity, rr_structural_v2_long, trend_ignition.
- **~95 orphan signal .py files** on disk not in the active registry.
- **389 `*_ENABLED` flags in hermes_constants, 196 ON** — many ON flags reference signals with no registered generator (WYCKOFF_PLUS/MINUS, ZSCORE_PUMP, HMACD, TL_BREAK, EMA_ANGLE, MACD_1M, MACD_ACCEL, FAST_MOMENTUM, PHASE_ACCEL, ATR_COMPRESSION, COUNTER_FLIP, MTP_ZSCORE…). These flags are still checked by the schema's giant chain and by individual dead signal files.
- **CONF_FILTER_MAX=92 is unreachable** — ingestion caps confidence at 88 (`MAX_CONFIDENCE=88`), so the "overconfident trades buy the top" block can never fire. Dead code.
- **TIME_BLOCK_ENABLED=False** but the check code still runs every signal.
- **Three dead-hour lists are empty** (`PUMP_CHAIN_LONG_DEAD_HOURS=[]`, `PUMP_CHAIN_SHORT_DEAD_HOURS=[]`, `PULLBACK_ENTRY_SHORT_DEAD_HOURS=[]`) yet the code comments claim they were "RE-ENABLED 2026-09-22" — the block logic executes but matches nothing. **Hourly data says it should:** 03h UTC = 52T 38.5% WR **-$3.45** (worst hour); 16–19h UTC = +$1.82, +$2.17, +$2.36, +$0.08 (the profitable window). The concept has signal; the lists are empty.
- **Oscillator_mult shadow-mode** — computes, logs, writes shadow JSON, multiplies by 1.0.
- **317 rows `executed=1` with `decision='EXPIRED'`** — execution-recording path inconsistency.
- **ai_decider.py defunct** (documented) — replaced by signal_compactor.
- **27 disabled flags ON for never-registered signals** — e.g. doji uses DOJI_TOP_ENABLED for both top and bottom (registry line 488: `doji_bottom` gated by `DOJI_TOP_ENABLED` — works but is a config smell).

---

## 8. ANSWERS TO THE SEVEN CEO QUESTIONS

**Q1 — Pass-through %:** 2,057 signals → 3 trades/24h = **0.15%**. Over 7d: ~0.8%. Hotset is currently empty — right now it is **0%**. 93.1% expire from staleness/confluence starvation.

**Q2 — Top kill gate:** By named-gate log frequency: SPIKE-FILTER (1,644), LONG-NEUTRAL (1,102), PUMP-CHAIN-SHORT-HIGH (1,044). **By actual elimination volume: the confluence gate + 10-min staleness decay — it kills ~93% of signals by attrition before any named gate fires.**

**Q3 — Dead code:** Yes, extensive — 27 disabled-but-imported registry entries, ~95 orphan files, ~200 orphan flag checks in schema, unreachable CONF_FILTER_MAX=92, 4 inert gate code paths (disabled time block + 3 empty dead-hour lists), shadow-mode oscillator, 317 execution-flag inconsistencies. Full list in §7.

**Q4 — Does CONF_FILTER_MAX=92 block the best trades?** No — it is **unreachable**. Ingestion caps confidence at 88, so nothing ever reaches 92. The MIN=70 floor blocked only 36 signals in 24h (2% of volume). Of the 1,496 signals in the allowed 80+ band, 1 executed. **The confidence filter is not the bottleneck** — 85% of signals sit in the allowed band and still die downstream.

**Q5 — Does the confluence gate improve win rate?** **No. It reduces trade count ~94% with zero WR gain at the tier it produces.**
| Sources | 30d trades | WR | PnL |
|---------|-----------|-----|-----|
| 1 (single) | 977 | 51.8% | -$5.01 (avg -$0.0051/T) |
| **2 (what the gate produces)** | **42** | **42.9%** | **-$1.00 (avg -$0.0238/T — WORST tier)** |
| 3 | 12 | 66.7% | +$0.11 |
| 4 | 4 | 75.0% | +$0.14 |

The 2-source tier — exactly what the confluence gate is designed to create — is the **worst-performing tier in the entire dataset**. Multi-source trades (58T, 50% WR, avg -$0.0129) underperform single-source trades (977T, 51.8% WR, avg -$0.0051) per trade. The gate is destroying volume to produce inferior trades. (Caveat: single-source trades that execute are pre-selected by the 116-entry bypass list, so they carry selection bias — but that only strengthens the conclusion: the bypass list, not the confluence requirement, is what identifies quality.)

**Q6 — Is the standalone bypass list too restrictive?** **The opposite — it is too permissive to matter.** 116 entries covering nearly every active signal family (accel-300 alone has 6 variants on the list; bb-bounce has 5; r2-trend has 4). With 116 bypass entries for 45 active signals, the confluence gate is decorative for the core roster and only bites the obscure long tail (5 of 8 signals in the current compaction window were blocked as CONFLUENCE_GATE — mostly support_resistance). The list is not the bottleneck; the downstream regime/RSI/spike gates are.

**Q7 — Do time blocks, speed filters, directional caps improve profitability?**
- **Time block:** Currently OFF; dead-hour lists empty. But hourly data (30d) shows a real pattern: **03h UTC is the worst hour (-$3.45/52T, 38.5% WR) and 16–19h UTC is the best (+$6.35 combined)**. The concept works; the implementation is inert. Re-populating the lists is one of the highest-confidence cheap wins available.
- **Speed filter:** SPEED_MIN_THRESHOLD_LONG=50, SIGNAL_FILTER_SPEED_MIN=40 — applied in the context gate. No direct trade-level split available from PG to validate; the filter predates most of the current signal roster. Worth an A/B test rather than assumption.
- **Directional cap (80%):** Rarely binds at MAX_OPEN_POSITIONS=6 (blocks only at 5-1 concentration). Low impact either way.
- **Verdict:** These are not what's killing the system — the confluence gate, regime blocks, and spike filter are. But the inert time block is leaving known money on the table.

---

## 9. OVERCOMPLICATIONS RANKED BY IMPACT

1. **Confluence gate (2+ types) + 10-min staleness** — kills 93% of signals by attrition; the tier it produces (2-source) is the worst-performing in 30d data. **Highest impact, negative marginal value.**
2. **28-multiplier score formula with 5 redundant trend-alignment terms** — compounds to an 85x spread between worst and best case; makes hotset membership nearly impossible; no evidence any individual multiplier beyond the first trend filter adds predictive value.
3. **Four overlapping chop/regime systems** — same question answered four ways with different thresholds; recently required 3 hotfixes in one day (2026-09-24) because the rule sets disagree.
4. **Per-signal regime hard blocks** (pump-chain HIGH ×2, accel FLAT/EXTREME ×5, coiled NORMAL-only, pullback NORMAL) — block the system's most profitable families (pump-chain +$1.59/30d) during regimes where their edge may still exist at smaller size.
5. **Six token-performance-history systems** — overlapping reads of the same data; hall-of-shame's 55% WR bar blocks signals on 15+ trade samples that include old losing eras.
6. **~200 orphan flag checks + 27 disabled imports + ~95 dead files** — pure maintenance drag; every new signal requires touching the schema's if/elif chain.
7. **Execution at $11/trade with 5,437 all-time trades and net -$13.30** — the system has traded thousands of times at micro-size through a 75-gate gauntlet and still lost money. Complexity is not the only problem, but it is hiding the real one: **the edge, where it exists, is confined to ~12 signal families, and the gates prevent the system from concentrating on them.**

---

## 10. WHAT TO CUT / MERGE / SIMPLIFY — PRIORITIZED

### Tier 1 — Do first (highest confidence, lowest risk)
1. **Reconcile the PnL discrepancy.** PG says -$0.40/7d; the CEO believes +$1.81/7d. Query the exact metric the CEO is seeing before changing anything. Fix the 317 `executed=1`/`decision='EXPIRED'` inconsistency.
2. **Remove the confluence gate** (or invert it: require 3+ where data shows 66–75% WR, and accept low volume). Evidence: 2-source tier is the worst in the dataset. Keep the standalone bypass list as the default path — it is already de facto.
3. **Concentrate on the 12 profitable signal families** — bb_bounce_v2_long, volume-breakout-long+, pump_chain/pump-chain+, doji-bottom-long, rr-struct+, pullback-entry-, grind-trend+, continuation+, ema300-dip-short, squeeze/reversal families. Disable or shrink everything else. The data says the entire net loss comes from the long tail.
4. **Re-enable time blocks with real data** — populate `PUMP_CHAIN_LONG_DEAD_HOURS` (block 0–5, 23 UTC per the code's own comment), `PULLBACK_ENTRY_SHORT_DEAD_HOURS` (block 0,1,3,7,10,11), and add a general low-edge-hour block for 02–05 UTC (-$5.96/30d across those hours). This is a config change, not a code change.

### Tier 2 — Structural simplification
5. **Collapse 5 trend-alignment multipliers into 1.** Pick one authority (continuum structure is the most recently patched and most granular) and delete reg_mult, trend_filter_mult, alt_btc_div_mult, dir_bias_mult — or fold them into a single "alignment" multiplier with one set of rules. Target: ≤8 multipliers in the final score.
6. **Merge the 4 chop/regime systems into 1.** One regime classifier (recommend volatility_gate_v2's ATR regime + one structural view), consumed by one gate, one multiplier. Delete the duplicate trend filter in signal_schema (keep the hard block, delete the compactor's 0.7 penalty — or vice versa).
7. **Merge the 6 performance-history systems into 1.** One token-direction performance table, one threshold, one action (block or penalize — not both, not six times).
8. **Strip the per-signal regime hard blocks** in favor of the score multipliers already doing this job (vol_regime_mult, regime_conf_mult). Blocking pump-chain in HIGH vol while it has +$1.59/30d edge is inverting the evidence.

### Tier 3 — Hygiene (do while doing Tier 1–2)
9. Delete CONF_FILTER_MAX (unreachable), the 3 dead-hour code paths if lists stay empty, or populate the lists and keep the code (recommended — see #4).
10. Remove 27 disabled registry entries and their imports; prune ~95 orphan signal files; collapse the schema's ~200-flag if/elif chain to a data-driven dict of active flags only.
11. Fix the doji registry smell (doji_bottom gated by DOJI_TOP_ENABLED).
12. Decide open_skies' fate on current data (positive 30d PnL, currently disabled).

### What NOT to do
- Do not add more gates, more multipliers, or more regime systems. Every addition since the system's inception has reduced trade count without demonstrated PnL improvement.
- Do not tune thresholds on the current architecture — with 75 gates, threshold changes are untestable in isolation (every gate's effect confounds every other's).

---

## 11. CONFIDENCE LEVEL

| Claim | Confidence | Basis |
|-------|-----------|-------|
| Gate count (~75), multiplier count (28) | **High** | Read directly from source; formula at signal_compactor.py:2035 enumerated term-by-term |
| Signal counts (72/45/27/140) | **High** | Executed `get_registered_signals()` and directory listing |
| 24h fates (2,057 → 3 executed) | **High** | Live SQLite query in this session |
| Kill-ranking (log frequencies) | **Medium-High** | ~20MB log tail, not a full-24h census; ranking order robust, absolute counts approximate |
| Confluence analysis (2-source = worst tier) | **High** | Live PG query, n=1,035 trades/30d; per-tier breakdown run directly |
| Hourly PnL pattern | **High** | Live PG query, n=1,036 trades/30d |
| PnL = -$0.40/7d (not +$1.81) | **High for PG** | PG is designated source of truth; +$1.81 could not be reproduced from any queried store — the discrepancy itself is certain, the explanation is not |
| Profitable-signal ranking | **High** | Live PG aggregation |
| "Over-engineered" conclusion | **High** | Triangulated from structure (75 gates/28 multipliers for a 0.15% pass-through), data (worst-performing confluence tier), and results (net-negative all-time) |

**Overall: High confidence in the diagnosis. Medium confidence in exact kill-counts (log-window caveat). The single biggest uncertainty is the PnL discrepancy — resolving it is priority zero.**

---

*Files inspected: signal_compactor.py (5,312 lines), signal_schema.py (4,455 lines), signals/__init__.py (606 lines), hermes_constants.py (4,158 lines), chop_detector.py, market_phase_gate.py, volatility_gate_v2.py, decider_run.py, btc_crash_filter.py, paths.py, brain.py. Databases queried: signals_hermes_runtime.db (SQLite), brain (PostgreSQL). Artifacts read: pipeline.log, hotset.json, raw_signals.json, trades.json.*

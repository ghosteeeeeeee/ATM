# Probability Matrix — Prior-Art Survey (read-only research)

**Goal of this doc:** everything a future "probability matrix" (signal conditions → explicit 0–1 probability) must reuse or must NOT rebuild.
**Method:** direct code reads + one live PG query + one live SQLite query (numbers below were executed, not recalled). All line refs are current as of this survey.

---

## 1. Confidence implementation (signal_compactor `_score_signal` + decider_run hot-set)

### 1.1 Where confidence is born (per-signal, hardcoded)

Confidence is a **0–100 integer invented by each signal file** from hardcoded base + small heuristic bonuses, clamped:

- `scripts/signals/accel_300.py:757-813` — breakout: `confidence = ACCEL_300_BREAKOUT_CONFIDENCE`, `+5` if 5-bar move>1%, `+3` if 1h trend aligns, cap 88. Velocity variant: `confidence = int(min(85, 65 + (velocity_ratio-1.0)*20))` floor 65. Gap variant: `int(min(85, 70 + max(0,(gap-min_gap)*80) + gap_bonus))` floor 70, cap 88.
- `scripts/signals/continuum_score.py:87-125` — `conf = CONTINUUM_SCORE_CONF_BASE(82) + extremity*10`, cap 92; momentum signals flat 75 (constants `hermes_constants.py:5651-5660`).
- `scripts/signals/accel_300_v2_long.py:518-519` — `int(min(88, 62 + gap_bonus + accel_bonus + trend_bonus + fresh_bonus))`, floor 60.
- Audited ceiling: **"Ingestion caps confidence at 88"** — `brain/verdicts/2026-09-22-full-system-audit.md:238`.
- Independent re-derivation: `brain/verdicts/2026-10-24-new-signals-own-conclusions.md:24` — "base 65, +5 ATR, +5 RSI, clamped [55,88]".

→ **HARDCODED tables everywhere; zero data-derivation at birth.**

### 1.2 Hot-set "effective confidence" (decider_run)

- `scripts/decider_run.py:4050-4095` — direction-wave alignment `wave_mult` (hardcoded: 1.15 / 1.10 / 1.00 / 0.88 / **0.70** counter-to-wave), then
  **`effective_conf = float(sig_conf) * wave_mult + speed_pts`** where `speed_pts = ((speed_pctl-50)/100) * SPEED_WEIGHT * sig_conf` (:4090-4091), `SPEED_HOTSET_WEIGHT = 0.25` (`hermes_constants.py:561` — the inline comment at :4087 still says "0.15", stale).
- `decider_run.py:4133-4145` — counter-regime de-escalation: `penalty = min(regime_conf*0.4, 30)`, `escalation = min(survival_rounds*2, 10)`, `confidence -= max(penalty-escalation,0)`.
- Also subtractive: counter-trend trap penalty (:4101-4108, <55 → block), neutral-market penalty (:4146-4159), z-score penalties (:4181-4191), `WRONG_SIDE_PENALTY` (:5315), CTX-GATE −20 (:5929), `LOSERS_CONF_PENALTY` −50 (:5974).

**Phantom field:** `signals.effective_confidence` exists as a SQLite column (`data/signals_hermes_runtime.db`, signals table col #36) and is read in `scripts/signal_schema.py:3616,3617,3649` (`COALESCE(effective_confidence, confidence) >= 25`), but a live query shows **0 of 12,400 rows populated** and **no writer exists anywhere in `scripts/`** (grep: only the three read sites). The comment `signal_schema.py:3674` — "penalty is already baked in by decider_run when writing effective_confidence" — is false. Hot-set quality scoring therefore always falls back to raw `confidence`.

### 1.3 The score formula (`_score_signal`)

Docstring `scripts/signal_compactor.py:1197-1209`:

```
score = confidence × survival_bonus(1+cr*0.15) × staleness_mult(max(0,1-age*0.1) → 0 at 10min)
      × trend_alignment_mult × source_mult × speed_mult(+15% if pctl≥80)
```

Actual mechanics:
- `signal_compactor.py:1513` — `score = float(conf)`.
- Hard blocks return `0.0`: `CONF_FILTER` (`:1212-1215`, `hermes_constants.py:1779-1781` MIN=70 / MAX=95), directional cap (:1220-1228), BTC chop gate (:1236-1363), BTC timing guard (:1381-1416), vol-gate regime bans, staleness floor.
- `signal_compactor.py:2270-2294` — **`final_score = score × max(∏ multipliers, PENALTY_MULT_FLOOR=0.5) × rr_mult`**; the product has **25 factors** (code comments call it "26-factor", counting `rr_mult` which sits outside the floor) = `survival × staleness × trend_align × dir_outcome × source × speed × tide × zscore_accel × favorites × leaderboard × combo × penalty × amplitude × time_block × phase × confluence × inverse × lifecycle × vol_regime × short_normal × oscillator × regime_conf × thesis_validation × chop_score × cell_stats`. Any `0.0` factor = intentional kill (floor never resurrects it, :2283-2292).

`rr_mult` = `risk_reward_engine.rr_confidence_multiplier` (`risk_reward_engine.py:1115`, called `signal_compactor.py:1904,1933`): composite score 0–100 → grade A–F (`:823-833`), grade F or R:R<0.70 → mult 0.0, else 0.70–1.30 by R:R+grade (`:1192-1210`), R:R floor drops 0.70→0.35 when BTC continuum shows confirmed structure (`:1156-1176`).

### 1.4 Execution confidence + the field-semantics trap

- `decider_run.py:4751-4795` — `exec_conf = final_confidence × max(penalty_product, PENALTY_MULT_FLOOR=0.5)` (PENALTY-GATE log :4768); `MIN_EXEC_CONFIDENCE = 40` (`decider_run.py:4602`); below → `PENALTY-BLOCK` (:4810).
- **Drift note `decider_run.py:4796-4807` (brain_auditor #146):** three more reductions run *after* the gate (wrong-side :5315, ctx −20 :5929, losers −50 :5974), so `trades.confidence` ≠ gate-time confidence — 58/58 trades stored <40 were ≥40 at gate (avg divergence +18.2). `_signal_metadata.final_confidence` = the gate-time value. Any probability calibrated on `trades.confidence` must know which of the two it means.

### 1.5 SIGNAL_QUALITY gates — **dead config**

`hermes_constants.py:641-644`: `SIGNAL_QUALITY_ENABLED=True`, `MIN_GRADE='C'`, `MIN_SHARPE=1.0`, `MIN_PROFIT_FACTOR=1.5`.
Repo-wide grep: **zero code references** outside the constants file (only `README.md:263` and prose in `brain/specs/rr_engine_audit.md`). The live grade gate is the RR engine (`RR_ENGINE_MIN_SCORE=50` → grade C, `hermes_constants.py:5179`; `risk_reward_engine.py:891-917`). Sharpe/profit-factor gates exist only as tuner outputs (`mtf_macd_tuner.py`).

### 1.6 Weaknesses (documented, not inferred)

- **Confidence inversion (verified):** `brain/verdicts/2026-10-14-plan-v3-own-conclusions.md:58` — conf 90+ = 442T **−$5.88** vs 70–89 = 178T **+$5.24**, "confidence inversion confirmed".
- `brain/verdicts/2026-10-08-pump-chain-v6-verdict.md:20` — "Confidence not predictive: 90+ bucket ~155 trades ~50% WR" → AGREE (n=155, 49.7% WR, −$0.03).
- `brain/verdicts/2026-09-22-full-system-audit.md:238` — `CONF_FILTER_MAX` unreachable (cap 88); 85% of signals sit in the allowed band and die downstream anyway.
- `brain/transcript-mining/i-gave-jev-control-of-a-trading-bot.md:66` — the calibration study ("bucket signals by confidence and measure actual WR per bucket") is explicitly proposed and **never done**.
- 25 multiplicative factors (the code comment says "26") can compound to ~0.02 → hence the 0.5 floor (`signal_compactor.py:2206-2210`).

**Output type:** 0–100 point score. **No 0–1 calibrated probability anywhere in the confidence path.**

---

## 2. Confluence implementation

### 2.1 The gate ("2+ source types")

- Constants: `CONFLUENCE_REQUIRED = True` (`hermes_constants.py:4094`, "DO NOT DISABLE"), `CONFLUENCE_NEUTRAL_RELAX = True` (:4095).
- Rule comment: `signal_compactor.py:3153-3157` — "2+ unique signal types required; single-source stays PENDING until a co-signal arrives, else EXPIRED".
- Counting: `_signal_type_key()` `signal_compactor.py:3111-3145` strips trailing digits, `-broken`, collapses `rs-s`/`rs-r` → `rs` (anti-fake-diversity, 2026-05-15 fix at :3129-3143); `unique_signal_types = len(set(...))` (:3145).
- Decision ladder `signal_compactor.py:3856-3975`:
  1. `not CONFLUENCE_REQUIRED` → pass (:3856)
  2. ichimoku-LONG bypass (:3863, flag `ICHIMOKU_LONG_BYPASS_ENABLED`)
  3. **`unique_signal_types >= 2` → pass "N unique types"** (:3875)
  4. NEUTRAL relax (4h NEUTRAL) + member of bypass list (:3878-3895)
  5. accel-300 single-source with `conf >= ACCEL_300_STANDALONE_BYPASS_CONFIDENCE` (:3905-3910)
  6. `STANDALONE_BYPASS_SIGNALS` whole-source (:3914) or any part (:3919-3929)
  7. temporal confluence — N fires in window (:3931-3949, shadow by default)
  8. `source.startswith('conf-')` — already-merged confluence signals (:3959)
  9. else **BLOCK: "only N unique types {src} — need 2+"** (:3972)
  - every combo is logged (`[CONFLUENCE-DEBUG]`, :3975).
- `STANDALONE_BYPASS_SIGNALS`: `hermes_constants.py:3513-~3570` — long tuple, each entry annotated with its backtest justification and removals (hzscore, open-skies, bb-bounce-v3-long, hl_copy_trader…). Used at ~10 sites in `signal_compactor.py` plus the decider mirror `decider_run.py:2698-2767`.
- decider side: `decider_run.py:5477-5483` — `is_confluence = len(source_parts) > 1` lets pump-chain exceed its position cap; `decider_run.py:3938` orders `signal_type='confluence'` first when picking the best signal.

### 2.2 How confluence boosts score/confidence

- `signal_compactor.py:1870-1895` — `confluence_mult = get_confluence_mult(families)` (2-min cache), fed into the 25-factor product (:2273).
- `confluence_scorer.py:46-100` — **hardcoded** `STRONG_CONFLUENCES` / `WEAK_CONFLUENCES` combo tables (source: `plans/signal-cluster-analysis-2026-08-26.md`, co-occurrence counts in comments).
- `confluence_scorer.py:111-179` — `score_confluence`: sum matched bonuses/penalties → label `none/weak/moderate/strong/super`.
- `confluence_scorer.py:293-317` — level → multiplier `{super:1.3, strong:1.2, moderate:1.1, weak:1.0, none:0.9}` clamped 0.8–1.3, `+0.1` for phase-specific pairs.
- Merged confluence signal: `signals/signal_confluence.py:194-202` — **confidence = 55 (2 src) / 75 (3 src) / 88 (4+ src)**, all hardcoded (`hermes_constants.py:5108-5114`, `MIN_COMPOUND=3`).

### 2.3 Weaknesses

- **Confluence-by-expiry is the largest single filter in the system:** `scripts/expiry_shadow.py:3-30` — 25,204 signals/6d EXPIRED waiting <5min for a co-signal, averaging **80.5 conf**; plus a statistical warning that event-level stats are pseudo-replicated 2–3× (use `brain/analysis/cluster_t.py`).
- `brain/verdicts/2026-10-30_shadow-redundancy-own-conclusions.md:26,33,93` — conf≥80 **single-source** forward excess ≈ **+0.0016%** (n≈14k, i.e. exactly zero); the negative band means are carried by MULTI-source rows; "protects at every confidence band" is false (90+ flips positive, n=84).
- `brain/creative_improvements.json:3094` — confluence path may only apply a 0.6× dampen when BTC is bearish ("dampen too weak → raise to 0.0").

**Output type:** pass/block + a 0.8–1.3 score multiplier. **Not a probability.**

---

## 3. Coin Tracker

**Files:** `web/coin_tracker.html` (821 lines, served at `/coin_tracker.html`), `scripts/coin_tracker.py` (715 — collector: reads `hl_cache.json`, `candles.db`, `signals_hermes_runtime.db`, writes `coin_tracker.db`), `coin_tracker_score.py` (1620 — scoring engine), `coin_tracker_api.py` (153 — exports registry JSON), `coin_tracker_enricher.py` (100), `coin_tracker_analysis.py` (1123 — Wyckoff/Elliott/S-R/trend-quality/volume-profile), `coin_tracker_schema.py`, plus the signal `scripts/signals/coin_tracker_hot.py`. Timer: `config/hermes-coin-tracker.service/.timer`.

**What it tracks:** per-coin health composite (0–100) from 20 weighted components — momentum, volume, volatility, spread, signals, regime, Wyckoff, Elliott, trend quality, setup, clustering, recency, liquidation, tide, sea state, wind, token regime, contrarian, MACD divergence, R:R.

**Mechanics (one line each):**
- `coin_tracker_score.py:13-38` — `WEIGHTS` = 20 hardcoded floats summing 1.0 (with `ponytail:` notes on the sum).
- `coin_tracker_score.py:1572-1594` — `composite = Σ (component_score × WEIGHTS[component])` → `health_from_score(composite)` (:1477).
- `coin_tracker_score.py:229-246` — `score_signals = 20 + min(60, n*6) + (avg_conf−50)*0.1`, then `×0.7` mixed-direction, `×0.5` recent conflict.
- **Probability-ish math:** `coin_tracker_score.py:444-493` `predict_cascade` — `probability = min(90, 40 + 10*close_clusters + (1−avg_distance)*20)`, `+5` if sea-state winrate<45, `+10` if gusts>2×sustained, capped **95**; converted to a score bonus `(probability−50)/10` at :517. `predict_stop_hunt` :372 similar (confidence→bonus).
- Win rates: `coin_tracker_enricher.py:1-40` injects per-token `signal_winrate` / `signal_pnl` / `signal_trades` + regime class (reef/sandbar/deep) from `weather_station.json`; `coin_tracker_api.py:35` exports registry `win_rate, total_trades`; displayed at `web/coin_tracker.html:533,677,685`.
- **No streaks, no projections** — grep for `streak` across `coin_tracker*` + HTML returns 0 hits.

**Hardcoded:** every weight, every component threshold, the cascade formula constants. **Data-derived:** candle indicators, signal counts/confidence, registry WR, weather-station WR.

**Output type:** 0–100 health score + a heuristic cascade "probability" (0–95, uncalibrated). **Not a calibrated probability.**

---

## 4. Continuum and "v2"

**Naming check:** there is **no `continuum_v2`** anywhere (`grep -rn "continuum.*v2"` → nothing). The three things the task could mean, all covered:
1. the continuum **signal family** — `scripts/signals/continuum_score.py`, `continuum_oscillator.py`, `continuum_trend.py`, `continuum_ma.py` (sources `continuum+`, `continuum-mom+`, `continuum-osc+`, `continuum-trend+`, see `volatility_gate_v2.py:74-77`);
2. the **regime/multiplier layer "v2"** = `volatility_gate_v2.get_combined_multiplier` (`volatility_gate_v2.py:733-800`): per-signal override else vol-phase × lifecycle × inverse-correlation, then ATR-ratio/BTC-trend boost → float 0.3–2.0, all lookup tables;
3. the **SHORT_CONTINUUM filter** (`hermes_constants.py:1838-1845`): block SHORT when BTC continuum `state_score > 60` sustained ≥30min (`SHORT_CONTINUUM_SCORE_MAX=60`, hysteresis 30min).

### 4.1 The engine (`scripts/continuum_engine.py`, 1476 lines)

BTC-only state machine, `continuum.db` (`continuum_states`), tick loop from `hl_cache.json` + `candles.db`.

- **States:** enums `EMA300Position/ZScoreTier/VolumeRegime/Velocity/Acceleration` (:57-90) + hysteresis confirm/deconfirm per state (:344-395, thresholds `continuum_constants.py:12-23`).
- **Directional read ("LEAN_BEAR" in the logs):** `linreg_slope_multi_tf` `continuum_engine.py:216-275` — linreg slope on 1m/5m/15m/1h → count of TFs >+0.01 / <−0.01 → `BULL`/`BEAR` if **all** agree, `LEAN_BULL`/`LEAN_BEAR` if majority, `alignment = agreeing/total` (0–1).
- **market_phase:** `_detect_market_phase` :861-877 — pure threshold rules on (RSI, ATR%, vol ratio): `>60 & ATR>0.5 & vol>1.5 → STORMY`, `RSI<40 & ATR>0.5 → STORMY`, `45<RSI<55 & ATR<0.5 → CALM`, `RSI>55 → RECOVERY`, `RSI<45 → DECLINING`, else `NEUTRAL`. (STORMY was removed from the SHORT-bypass after 30.8% WR, `signal_compactor.py:1288`.)
- **state_score:** `_compute_score` :879-966 — **`50 ± hardcoded points`**: EMA300 ±15, EMA300 duration `min(10, log2(n+1))` ±, z-score ±15, volume ±12, velocity ±10, accel ±8, linreg slope ±14, `±10×alignment` (±5 for LEAN), trend quality ±8, Wyckoff ±8, Elliott ±6, market phase ±5 → clamp 0–100; EMA-smoothed (:764-767).
- **Entry state machine:** phases 0→6 (EMA300 cross → confirmed 60min → z aligning → volume → score≥95 for 20 ticks → ENTRY), :968-1014.

### 4.2 Consumers / how it becomes a "read"

- `continuum_context.get_btc_trend_context` `continuum_context.py:185-270` → `{score, trend_bias, momentum, regime}`; `_score_to_bias` :97-110 maps 45–55 → 0, 100 → +1, 0 → −1; `_classify_regime` :159-183 → `BULL_TREND (score≥65 & linreg BULL/LEAN_BULL)`, `BEAR_TREND (≤35 & BEAR)`, `RANGING_BULL/RANGING_BEAR`, `TRANSITIONING`, `RANGING`.
- The log line **"continuum says DECLINING+LEAN_BEAR"** is `signal_compactor.py:1289-1312` — a plain if/else on `(market_phase, linreg_direction, ema300_position)` used to override the BTC chop gate; mirrored for SHORT at :3358-3385 and in the RR regime exemption `risk_reward_engine.py:1156-1176`.
- Continuum signals emit confidence: `signals/continuum_score.py:87-125` (`82 + extremity*10`, cap 92; momentum 75).
- **`SCORE_WEIGHTS` (`continuum_constants.py:79`) is imported (`continuum_engine.py:40`) but never used** — the score is the hardcoded point table instead. Dead weight.

### 4.3 Weaknesses (documented)

- `brain/verdicts/2026-10-06-wrong-side-own-conclusions.md:134` — "BTC continuum score swings **0↔97 within hours**" (cited as routine noise).
- `brain/creative_improvements.json:3873-3874` — **"Continuum flap detector"** idea: `linreg_direction` flips minute-to-minute (LEAN_BULL↔LEAN_BEAR flicker), never built.
- `brain/verdicts/2026-10-08-signal-habitat-filters-verification.md:125` — SHORT_CONTINUUM logic "looks backwards for pump-chain-" (blocks the profitable band, permits the bleeding one).
- `brain/verdicts/2026-10-30_shadow-redundancy-own-conclusions.md:26` — CONTINUUM-BLOCK n=1,630 and CONTINUUM-BULL gates are **economic-zero** (cluster-robust p>0.1).
- `brain/verdicts/2026-10-07-profitability-plan-audit.md:263` — `z_score` stopped being recorded in September (0% coverage) → metadata gaps for any study.
- `brain/verdicts/2026-09-18-continuum-phases-audit.md` — phase-filter claim audit ("continuum boost too weak to override phase penalties", 95%).

**Output type:** 0–100 score + categorical labels (phase, linreg direction, regime). **Rule/label based; no probability math at all.**

---

## 5. Everything that already looks like probability / calibration / EV

`grep -rin "probabilit\|calibrat\|expected_value\|ev_" scripts/` (the `ev_` branch is dominated by false positives: `prev_`, `leverage`, `ev=` event vars). Real hits, ranked by relevance:

| # | What | Where | Status |
|---|------|-------|--------|
| 1 | **cell_stats** — nightly empirical-Bayes shrinkage WR per `(signal, direction, volatility_regime)`: admission n≥15 cell / blend 10–15 / signal 5–10 / global <5; `blend = (n·cell + K·prior)/(n+K), K=10` | `scripts/cell_stats.py:1-45`, timer `config/hermes-cell-stats.timer`, store `brain/cell_stats.db` | **LIVE consumer:** `signal_compactor.py:2211-2268` — tradeable cell → ×1.2, losing cell (n≥15, wr<0.40) → ×0.5. **Closest existing "condition → win rate" matrix.** |
| 2 | **correlation_engine** — `_bayesian_confidence(n, wr) = (10×0.50 + n·wr)/(10+n)` stored as `confidence` (0–1) per `(token, signal, direction)` | `scripts/correlation_engine.py:48-49,160-164` | **LIVE:** ingested `brain.py:1397-1406`, `position_manager.py:1756-1766`; read `decider_run.py:2604-2613` (advisory), `signals/chain_fire.py`; floor `CHAIN_FIRE_MIN_CONFIDENCE=0.60` (`hermes_constants.py:5093`). A real 0–1 quantity — but for chain-following, not trade win. |
| 3 | **ml_classifier** — RandomForest `predict_proba` win/loss on entry-time features (RSI/MACD/BB position/vol regime/token/signal/direction/hour), AUC + CV eval, saves `models/trade_classifier.joblib` | `scripts/ml_classifier/{__init__,feature_engineering,train_classifier}.py`, spec `brain/plans/ml-trade-classifier-spec.md` | **INERT:** `brain/verdicts/bug-hunter-vacation-mode-2026-10-14.md:24` — "Model is **not** consumed by any live decision path (inert)"; `/root/.hermes/data/models` does not exist on this host (never trained/saved here). |
| 4 | **predict_cascade / predict_stop_hunt** heuristic percentages | `coin_tracker_score.py:444-530` | dashboard-only (§3). |
| 5 | **TVS thesis validation** — % of historical `thesis_validated` for token+direction+signal → boost/penalty mult | `signal_compactor.py:2159-2202` | LIVE, but converted to a multiplier, not a probability. |
| 6 | **pump_chain_v6 calibration gate** — pre-enable agreement check with halt-below-floor | `scripts/analysis/pump_chain_v6_calibration.py` | one-shot enable gate, not a model. |
| 7 | **Hebbian** WR lookups per signal/token (context gate) | `hebbian_engine.py`, `decider_run.py` CTX-GATE | lookup table, fail-open. |
| 8 | **exit_optimizer_shadow** — SL/TP calibrated from MAE/MFE quantiles | `exit_optimizer_shadow.py:6-11` | shadow only. |
| 9 | **ab_optimizer** ε-greedy bandit (`with probability EPSILON: explore`) | `ab_optimizer.py:107-108` | exploration prob, unrelated. |
| 10 | Analysis skills: `winrate-calculator`, `signal-combo-analyzer`, `trade-stats`, `signal-backtest` | `skills/shared/` | offline tooling. |

**No `expected_value` / EV trading code exists** (grep hits are all `prev_`/`leverage`/event-var false positives).

---

## 6. `_signal_metadata` — what a probability matrix could consume (live evidence)

Live PG query over the **last 60 closed trades with non-empty `_signal_metadata`** → **67 distinct keys**:

| Coverage | Keys |
|---|---|
| 60/60 | `rsi_14`, `size_mult` |
| 54–55/60 (core) | `source`, `z_score`, `z_score_tier`, `is_stale`, `rsi_exec`, `rsi_detect`, `rsi_drift`, `btc_score`, `btc_regime`, `btc_trend_bias`, `btc_linreg_bias`, `btc_trend_quality`, `btc_ema300_position`, `btc_ema300_dist_pct`, `btc_ema300_duration`, `btc_ema300_streak`(46), `macd_hist`, `macd_value`, `macd_signal`, `bb_position`, `coin_regime`, `coin_regime_conf`, `wave_phase`, `momentum_score`, `momentum_state`, `volume_spike`, `price_at_signal`, `price_acceleration`, `gap_at_entry`, `staleness_minutes`, `final_confidence`, `speed_percentile` |
| 22/60 | `pm_armed_at` (profit-monster stamp, `profit_monster.py:449-460`) |
| 10/60 | `jup_*` family (wallet, rank, win_rate, leverage, pnl_24h/7d, cluster…), `mirror_source` |
| 8/60 | copy-trader family: `trader_wallet`, `trader_score`, `trader_win_rate`, `cluster_size`, `trust_tier`, `trade_pnl`, `trade_size` |
| 1/60 | `jup_liq_*` |

**Writers:** `brain.py:430` (add_trade signature), `:547-590` (auto-fill `rsi_14`, `btc_ema300_position`), `:768-773` (stamp `size_mult`), `:932` (column 43 of the INSERT); `decider_run.py:6258-6289` injects `staleness_minutes`, `gap_at_entry`, `coin_regime` at execution; `signal_schema.py:2354-2371` fills indicator enrichment + BTC continuum context (`btc_score`, `btc_trend_bias`, `btc_linreg_bias`, `btc_regime`) at detection time.

Sample row (executed): `{"rsi_14":67.31, "source":"bb-squeeze+", "z_score":2.77, "rsi_exec":73.78, "rsi_detect":67.31, "rsi_drift":6.47, "btc_score":99.7, "btc_regime":"BULL_TREND", "wave_phase":"falling", "bb_position":1.19, "coin_regime":"LONG_BIAS", "coin_regime_conf":89, "gap_at_entry":0.968, "volume_spike":0.25, "momentum_state":"rising", "momentum_score":22.8, "speed_percentile":56.2, "staleness_minutes":1.33, "final_confidence":49.5, "btc_ema300_position":"ABOVE", "btc_ema300_duration":1012, "size_mult":1.0}`

**Two confidence fields with different semantics:** `trades.confidence` (post all reductions) vs `_signal_metadata.final_confidence` (gate-time) — `decider_run.py:4796-4807`. Any calibration must pin which one.

---

## 7. Summary table — system → inputs → output type → hardcoded? → calibrated probability? → files

| System | Inputs | Output type | Hardcoded vs data-derived | Calibrated 0–1 probability? | Files (line refs) |
|---|---|---|---|---|---|
| **Confidence** (`_score_signal` + decider hot-set) | per-signal base conf, regime, speed pct, survival rounds, 25 multiplier factors, R:R grade | 0–100 score, hard blocks at 0 | base conf & all multiplier tables **hardcoded**; TVS %, cell_stats WR, speed pct, regime conf data-derived | **No** — 0–100 points; audited as *non-predictive* (90+ = 49.7% WR) | `signal_compactor.py:1197-1209,1513,2270-2294`; `decider_run.py:4050-4095,4133-4145,4751-4807`; `risk_reward_engine.py:823-833,1115-1210`; `hermes_constants.py:641-644,1779-1781,4094` |
| **Confluence** | unique signal-type count after normalization, family combo tables, source count | pass/block + 0.8–1.3 multiplier; merged signal conf 55/75/88 | gate rule + bypass list + combo bonuses **hardcoded**; family set derived from live sources | **No** | `signal_compactor.py:3111-3157,3856-3975,1870-1895`; `confluence_scorer.py:46-100,111-179,293-317`; `signals/signal_confluence.py:194-202`; `hermes_constants.py:3513,4094-4095,5108-5114`; `decider_run.py:5477-5483` |
| **Coin Tracker** | candles (EMA/RSI/MACD/ATR/spread), signal counts+conf, regime, Wyckoff/Elliott, liquidation, weather, registry WR | 0–100 health composite; cascade % (heuristic, cap 95) | all weights/thresholds **hardcoded**; indicators & WR data-derived | **No** (cascade % is arithmetic, never fit to outcomes) | `web/coin_tracker.html`; `coin_tracker.py:1-40`; `coin_tracker_score.py:13-38,229-246,444-493,1572-1594`; `coin_tracker_api.py:35`; `coin_tracker_enricher.py:1-40` |
| **Continuum (+ vol-gate v2 / SHORT_CONTINUUM)** | BTC candles multi-TF: EMA300, z-score, volume, velocity, accel, linreg slope, Wyckoff, Elliott, RSI/ATR phase | 0–100 `state_score` + labels (`market_phase`, `linreg_direction` incl. LEAN_*, `ema300_position`, regime) | indicator thresholds & every point weight **hardcoded** (`continuum_constants.py`); score is arithmetic, not fit | **No** — pure rule/label state machine | `continuum_engine.py:216-275,344-395,861-966`; `continuum_constants.py:12-23,79`; `continuum_context.py:97-183,185-270`; `signals/continuum_score.py:87-125`; `volatility_gate_v2.py:733-800`; `signal_compactor.py:1289-1312,3358-3385` |
| *(bonus)* **cell_stats** | closed PG trades grouped `(signal, direction, volatility_regime)` | shrunken **win rate 0–1** + admission tier | K=10, n-thresholds hardcoded; WRs data-derived | **Closest thing that exists** (empirical-Bayes WR, but not calibrated against predicted probabilities) | `cell_stats.py:1-45`; consumer `signal_compactor.py:2211-2268` |
| *(bonus)* **correlation_engine** | co-fire counts per `(token, signal, direction)` chain | **Bayesian confidence 0–1** | prior 0.50 / weight 10 hardcoded; counts data-derived | Bayesian-shrunk frequency — a real 0–1, but for chain-following, not trade outcome | `correlation_engine.py:48-49,160-164`; `decider_run.py:2604-2613`; `chain_fire.py` |
| *(bonus)* **ml_classifier** | entry-time trade features | `predict_proba` win/loss | model-derived | **Would be** — but inert/untrained | `ml_classifier/*.py`; verdict `brain/verdicts/bug-hunter-vacation-mode-2026-10-14.md:24` |

---

## 8. Reuse vs duplicate — for the probability-matrix design

**Already exists → REUSE (do not rebuild):**
1. **`cell_stats.py` empirical-Bayes cell WR** (`brain/cell_stats.db`) — condition→win-rate with hierarchical shrinkage and admission tiers, already wired into `_score_signal` as a multiplier. A probability matrix's per-condition cell lookup is *this store*, extended (more dimensions, calibration layer on top), not a new one.
2. **`correlation_engine._bayesian_confidence`** — a working 0–1 Bayesian shrinkage helper with a prior; the exact math a probability matrix needs for small-n cells (`(K·prior + n·obs)/(K+n)`).
3. **`_signal_metadata`** — the feature vector is already recorded per trade (67 keys, §6): rsi/z/bb/momentum/btc-structure/speed/staleness/gap. A matrix consumes this; no new telemetry needed. Pin `final_confidence` vs `trades.confidence` semantics first.
4. **`signal_outcomes` / TVS** (`signal_compactor.py:2159-2202`) — per token+direction+signal validated-thesis history already queried nightly.
5. **`ml_classifier`** — feature-engineering + RF pipeline already written (entry-time features, no leakage, AUC reporting). Either wire it up (it's inert) or delete it; do **not** write a third trainer.
6. **`brain/analysis/cluster_t.py`** — required for any significance claim (expiry_shadow's pseudo-replication warning); and `brain/fk_definitions.md` + `brain/analysis/conf_field_semantics_2026-10-25.py` for confidence field semantics.
7. **`winrate-calculator` / `signal-combo-analyzer` / `trade-stats` skills** — offline analysis already exists.

**Would be DUPLICATION if rebuilt:**
- Another 0–100 composite with hand-tuned weights (coin_tracker's 20-weight table is the anti-pattern; a third one adds nothing).
- Another "how many sources fired" score (confluence_scorer + signal_confluence + score_signals already do it three ways).
- A Bayesian WR store (cell_stats and correlation_engine both have one).
- An RF/predict_proba trainer (ml_classifier exists).
- Any re-derivation of "confidence is predictive" — **it is documented as not** (90+ = 49.7% WR, n=155; 90+ −$5.88 vs 70–89 +$5.24). The gap is *calibration*, not another score.

**Genuine gaps a probability matrix would fill (nothing here exists):**
- A **calibrated** map from condition vector → P(win) with out-of-sample / cluster-robust validation (per AGENTS.md THE PATTERN rules: p-values, n, time-window, survivorship checks).
- Any **expected-value** computation (P(win) × payoff) — no EV code exists at all.
- Any consumer that treats a number as a probability rather than a multiplier/label.

**Known landmines:** dead `signals.effective_confidence` column (0/12,400 rows, no writer); dead `SIGNAL_QUALITY_*` constants; `SCORE_WEIGHTS` imported-but-unused in `continuum_engine`; confidence stored under two different semantics; confidence inversion (higher conf → worse returns); `continuum` linreg flapping minute-to-minute.

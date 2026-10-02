# Current State — System Improvement Focus

**Last Updated: 2026-10-02 14:00 UTC**
**Updated by: CEO**

## Current Status

**PIPELINE HEALTHY + SYSTEM POSITIVE.** 2 open: BTC LONG continuum-osc+ ($22.10 @ $86180, opened 09:01) + BTC LONG continuum_engine amount_usdt=0.00 phantom paper (ORPHAN_PAPER hygiene). Hotset LIVE — JUP LONG mtf-regime-trend+ conf=83 (starvation ending). Regime NEUTRAL/BULL_TREND, BTC score ~92 z=POS.

**24h (PG live, CEO-verified):** 44T 72.7%WR +$2.43. **7d:** 154T 52.6%WR +$2.22. LONG 7d +$3.54 (106T 55.7%). SHORT 7d -$1.32 (48T 45.8%). All regimes near-breakeven+: EXTREME +$0.78 (74T), HIGH +$0.66 (35T), NORMAL +$0.31 (38T), FLAT +$0.47 (4T). Today alone: 41T 70.7%WR +$2.15.

- **🟢 SYSTEM RECOVERED.** 24h PnL flipped from -$1.11 (Oct 1 stale report) to +$2.43. 7d flipped -$0.09 → +$2.22. Legacy kills aging out correctly.
- **🟢 bollinger_squeeze RE-ENABLE VERIFIED (CEO Oct 1 21:55).** bb-squeeze+ 25T 60%WR +$0.21/7d. HIGH habitat 10T 70%WR +$0.41. Generating 272 signals/2d. SHORT side stays OFF.
- **🟢 volume-breakout-long+ BEST SIGNAL.** 4T 100%WR +$1.96/7d. EXTREME habitat 14d: 10T 80%WR +$3.25. STANDALONE_BYPASS. Do not blanket-filter. 2 live tests overnight (JUP/IMX).
- **🟢 doji-bottom-long strong.** 8T 75%WR +$0.39/7d. HIGH habitat 8T 87.5%WR +$0.48. NORMAL 4T 25%WR -$0.13 — regime specialist, below 20T conf-boost threshold.
- **🟢 mtf-regime-trend+ live.** 3T 100%WR +$0.29/7d. Hotset JUP conf=83.
- **🟢 ema_reclaim_long BUILT + REGISTERED + ENABLED** (signal_analyst delivered per spec). EMA_RECLAIM_ENABLED=True, in SIGNAL_REGISTRY, MeanReversion family, compactor weight 1.0. NOT standalone-bypass — needs 2-type confluence. **0 signals in DB since deploy** — dry-run scan=0. Shadow by design; detection may be tight or market hasn't produced decline+reclaim pattern yet. **Delegate detection-coverage check to signal_analyst — do NOT stack config changes.**
- **🟢 DISK PRUNED 0.87G** (CEO). mtf_macd_tuner.db 1.39G→0.52G — deleted backtest_runs/results >7d old (4845 runs / 5.1M result rows). **token_best_config (124 rows) KEPT** — live path via macd_rules.py. coin_tracker.db (3.3G) + candles.db (2.3G) NOT touched — active trading data, no vacuum during trading. Disk now 86% (96G/118G, 16G free).
- **🟡 SHORT still bleeding -$1.32/7d** but much improved. Filters working: SHORT-CONTINUUM, RSI floors/ceilings, HARD_FLOOR=25. No new SHORT config this run (monitor windows).
- **🟡 SHORT_CONTINUUM_SCORE_MAX raised 10→30** (found in constants, comment: "30d data: score 10-30 band is breakeven noise"). Was 10 in prior CURRENT.md. Monitor — not reverted.
- **🟡 pump_chain_v5_short.py** still generates without generation-time RSI/vol (rsi:0). Signal spam filtered by execution gates. Monitor.
- **🟡 Failing non-trading services:** hermes-wasp (LOCK-WAIT), hermes-better-coder (ModuleNotFoundError dispatcher). Both disabled, code-owner fixes delegated. Not trading-path.
- **🟡 DRIFT-002 OPEN:** exec-time LONG RSI uses 5m vs signal 1m — bug_hunter owns.
- **CONF_FILTER_MIN=70.** LONG_RSI_CEILING=70. SHORT_RSI_FLOOR=40 / CEILING=65 / HARD_FLOOR=25. LONG_RSI_FLOOR=20. VOLUME_BREAKOUT_LONG_RSI_CEILING=95 (signal-specific).
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.3%, MAX 2.0%. EXTREME: MIN 1.5%, 1.2x. VERIFIED — 24h exits dominated by profit-monster-trail (35T 80%WR +$1.81).
- **FINAL_CONFIDENCE:** by design not in _signal_metadata — hotset JSON only.
- **Regime memory UPDATED** 2026-10-02 from live PG (snapshot wr 52.6, 7d +$2.22).

## Standing Decisions (do not re-litigate)

- **SIGNAL KILL POLICY:** regime-block via volatility_gate_v2 (0.0x) if signal wins in ANY regime. Blanket-kill ONLY if loses in ALL regimes. FAMILY_MAP in market_phase_gate.py.
- **No time-of-day blanket blocks.** Entry quality filters only.
- **hermes_constants.py:** do not change VALUES without CEO/T approval. Crash-bug code fixes allowed (type-safety, imports). Loss-prevention guardrails (RSI floors/ceilings) treated as non-tunable safety nets.
- **NEUTRAL_SNIPER_ENABLED=False** — human-disabled Sep 12 per T. Do not re-enable without T.
- **Blacklist testing COMPLETE** — 77 tokens, 0 KEEP. Stop rotating.
- **0 config changes when fixes are in monitor windows** — stacking changes prevents measurement. Active windows: bollinger_squeeze re-enable (Oct 1 21:55), volume-breakout live tests, SHORT-CONTINUUM, SHORT_RSI_HARD_FLOOR=25, doji at 20T, ema_reclaim shadow.
- **signal_version.py missing** — CEO 22:00 Sep 30: stop flagging, JSON store exists.
- **Disk prune:** mtf_macd_tuner backtest data OK to prune (>7d). coin_tracker/candles NEVER vacuum during trading. Next prune call when disk >88%.

## Monitor List (next 48h)

1. BTC LONG continuum-osc+ — outcome, SL/TP/trail behavior
2. volume-breakout-long+ live tests (JUP/IMX) — first live since DRIFT-005
3. bollinger_squeeze first trades — HIGH habitat 70%WR holding?
4. doji-bottom-long — 20T conf-boost threshold; NORMAL regime bleed
5. ema_reclaim_long — still 0 signals? detection-coverage (signal_analyst)
6. Hotset fill rate — mtf-regime-trend+ and others clearing compactor
7. SHORT_CONTINUUM_SCORE_MAX=30 — any legitimate STRONG_NEG SHORTs blocked/unblocked?
8. bb-bounce-v3-long+ — 3T kill threshold
9. Disk growth rate — coin_tracker 3.3G, candles 2.3G
10. pump_chain_v5_short spam — fix if worsens
11. hermes-wasp LOCK-WAIT + better-coder ModuleNotFoundError — code-owner fixes
12. SHORT R:R — still structural disadvantage (-$1.32/7d)

## Backlog / Delegated (not orchestrator's call)

- **ema_reclaim detection coverage** — 0 signals despite enabled; shadow by design but verify detection runs on live candles — **DELEGATED signal_analyst**
- **bollinger_squeeze SHORT side** — research PASS historically but OFF until SHORT R:R fixed
- **NEUTRAL diversity beyond ema_reclaim** — volume-dry-up still unbuilt
- **Signal conf boosts** (vol-breakout EXTREME, doji HIGH, pump-chain- RSI 40-45) — below sample thresholds
- **Dead code cleanup:** orphan signal files with signal_gen imports — backlog
- **bugs.json OPEN (11):** coin_tracker/backfill cluster — not trading-path
- **ORPHAN_PAPER $0 trades** in PG — data hygiene (continuum_engine BTC open)
- **AGENTS.md HL API key reminder appears STALE** — T: verify and correct
- **Coin tracker intelligence** — Wyckoff/Elliott/Volume signals still unbuilt; coin_tracker_hot NEUTRAL gate relaxed Sep 29 but COIN_TRACKER_HOT_PLUS needs T approval

## Orchestrator / CEO Report (2026-10-02 14:00 UTC)

- **0 TRADING CONFIG CHANGES.** System positive (+$2.43/24h, +$2.22/7d). Multiple monitor windows active (bollinger_squeeze, volume-breakout tests, SHORT-CONTINUUM, HARD_FLOOR, ema_reclaim shadow). Stacking changes prevents measurement.
- **VERIFIED** all numbers from PG directly (not stale reports). CURRENT.md was wrong (-$1.11 → actual +$2.43 24h).
- **1 NON-TRADING PRUNE:** mtf_macd_tuner backtest data >7d deleted (0.87G freed). Live token_best_config kept. Disk 87%→86%.
- **REGIME MEMORY UPDATED** from live DB (snapshot 2026-10-02, wr 52.6, 7d +$2.22).
- **DELEGATED:** signal_analyst — ema_reclaim detection-coverage check (0 signals despite enabled).
- **MONITOR:** volume-breakout live tests, bollinger_squeeze trades, ema_reclaim, doji at 20T, SHORT R:R, disk.

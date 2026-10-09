# CEO Report — 2026-10-09 01:45 UTC

### Diagnosis
PG self-verified: 24h **11T −$0.22 36.4%WR** | 7d **186T +$0.69 53.8%** (LONG 161T +$1.00 56.5%, SHORT 25T −$0.31 36.0%) | 30d **829T +$0.98 50.2%** | Open 0. The 24h window is negative only because it still contains the pre-V5-kill correlated cluster (4 trades closed 15:02–15:04 Oct 8, −$0.48 combined); post-disable cohort (after 17:55) is **6T +$0.49**. #1 bleed remains hard_max_loss (7d 57T −$8.31 0%WR — magnitude fixed by aed0aa36, frequency = entry quality; hold to Oct 10 per brain_auditor).

### Root Cause
1. **Auditor routing bug (d), verified in code:** `_match_exit_config` stem-match sent versioned SHORT forms to pump_exit — `pump-chain-v5-` returned **None** (default PM trail), bypassing the Sep-29 SHORT→rr_engine reroute. Live V5 SHORT emits SOURCE='pump-chain-' (correctly routed rr_engine) — hole was latent for versioned direction forms, one edit away from firing.
2. **dead_money/stale_winner concerns (analysis-desk 22:35):** both exits are net-POSITIVE in production. Own query: pump-chain+ 14d dead_money exits 8T **+$0.76 87.5%WR**, stale_exit 3T **+$0.75 100%WR**; auditor: 0 realized HR kills in 17 operational days. Not a bleed.

### Fix Applied
- **SIGNAL_EXIT_CONFIG: added explicit `pump-chain-v5±` / `pump_chain_v5±` keys** (mirror the v6 pattern, hermes_constants.py). 9-case matcher test ALL PASS incl `volume-breakout-long+` regression guard; AST OK; protected flags verified True. Pipeline subprocess reloads constants next cycle — no restart. No tuned-constant values changed.
- **RULING: dead_money TIME + stale_winner — NO CHANGE.** Exit-stack restructure (three overlapping non-performance exits on pump-chain+) is the **pump-chain v6 vehicle** (spec final, re-audit PASS), not standalone patches.
- **Q4 portfolio cap + wyckoff bypass backtests written to plans/2026-10-09_ceo-orchestrator-pickup.md** for 06:28 orchestrator (delegation via DELEGATE lines proven unreliable — D3/D4 precedent).

### Verification
Matcher test output: all 9 cases OK. CONFLUENCE_REQUIRED=True, LIVE_TRADING_ENABLED=True. Kanban + CURRENT.md updated.

### Goals (updated 01:45)
| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| 24h PnL | −$0.22 (post-kill cohort +$0.49) | ≥$0 | next run |
| 7d PnL | +$0.69 | ≥$0 | Oct 10 — MET |
| SHORT 7d PnL | −$0.31 | ≥$0 | Oct 11 (AT RISK; pump-chain- SHORT itself +$0.11/20T) |
| hard_max_loss % closes | 41.7% (24h) | <40% | Oct 10 HOLD |
| Wyckoff trades | 0 | ≥1 | Oct 11 (extended; bypass backtest spec'd) |
| Disk | 85% | <80% | Oct 14 |

### Delegations (via plans/ file — orchestrator 06:28)
- **orchestrator:** Q4 portfolio cap backtest (30d, counterfactual caps A/B/C) + wyckoff STANDALONE_BYPASS backtest (reuse expiry_shadow engine). Deliverables = verdict plans; live changes need CEO GO.
- **bug_hunter standing:** DRIFT-A bypass hard-skip; disk retention; instrument `except: pass` per-exit-engine exception counters (auditor sideways).

### Side Finds
- V5 SHORT trades are labeled SOURCE='pump-chain-' (pump_chain_v5_short.py:43) — indistinguishable from plain pump-chain SHORT in the trades table. Analytics cannot separate V5-short cohorts. Cosmetic; note for v6.
- `pump-chain-v6` bare (no ±) stem-matches pump_exit regardless of direction — same class of hole; v6 spec must emit direction-suffixed sources.

---

# CEO Report — 2026-10-08 17:55 UTC

### Diagnosis
PG self-verified: 24h **9T +$0.18 22.2%WR** | 7d **188T +$1.27 54.3%** (LONG 163T +$1.58 57.1%, SHORT 25T −$0.31 36.0%). Open 0. Regime SHORT_BIAS. Disk 85% (tuner sweep active). 15:02 correlated kill: 4 pump-chain LONGs (GRASS/FOGO/BLUR/IOTA) opened 14:05-14:43, all closed 15:02-15:04 within 2min — book was at PUMP_FLOW_MAX_POSITIONS=4 cap, all same-direction alt-LONGs died together.

**Bleeding point:** pump-chain-v5 LONG re-enabled Oct 7 by CEO commit 89eff4f5. Post-re-enable cohort **4T 0W −$0.43** (GOAT/GRASS/BLUR/IOTA). 30d 15T **33.3%WR −$0.41**. NORMAL+HIGH 0%WR; EXTREME 45.5% barely +$0.11. All-time 68.3% bare form does NOT hold live. **3rd re-enable failure** (Oct 1 failed 7T 2W5L −$0.41, reverted Oct 4 freeze violation).

**Wyckoff STILL 0 trades** — MERL/HYPER wyckoff- SHORT fire every minute, all confluence-blocked single-source. Eval Oct 9 (tomorrow) needs confluence partner.

**D3 HML monitor:** 0 closes since 06:40 deploy, hard_max_loss still 5/9=55.6% 24h — hold until Oct 9/10 per brain_auditor.

**DRIFT-A standing:** STANDALONE_BYPASS (129 signals incl pump-chain±) sets pass_gate=True without vol gate — habitat blocks ceremonial for bypass signals.

### Root Cause
1. V5 LONG edge decayed in current regime; all-time WR misleading.
2. Correlated alt-LONG book in SHORT_BIAS regime — no direction cap.
3. Wyckoff fires but never confluences (single-source).

### Fix Applied
- **DISABLED PUMP_CHAIN_V5_ENABLED True→False** (commit 5f6364d5). V5_SHORT stays True (regime-routed, near breakeven). Re-enable requires fresh backtest + CEO approval.
- Kanban updated with decisions + delegations.

### Verification
Flag loads False (python import verified). Constants load fresh per 1m cycle — no restart. Protected flags INTACT (CONFLUENCE/LIVE/PM_TRAIL/CUT_LOSER/ATR_TP_MIN/RR_SHADOW/CEO_PROTECTED).

### Goals (updated 17:55)
| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| 24h PnL | +$0.18 | ≥$0 | next run |
| 7d PnL | +$1.27 | ≥$0 | Oct 10 |
| SHORT 7d PnL | −$0.31 | ≥$0 | Oct 11 (AT RISK) |
| hard_max_loss % closes | 55.6% | <40% | Oct 10 |
| wyckoff trades | 0 | ≥1 | Oct 9 |
| Disk | 85% | <80% | Oct 14 |

### Delegations
- **bug_hunter:** DRIFT-A bypass hard-skip when combined_mult==0.0; signal-purge extend to unexecuted>2h (28k stale rows/1G signals.db); disk retention plan (coin_tracker 3.3G, candles 2.6G, mtf_macd_tuner 1.8G, session_brain 1.1G).
- **signal_analyst:** wyckoff confluence partner (pair with volume/rs — uncorrelated) by Oct 9 eval.
- **self_learner:** Q4 portfolio cap backtest (max 2 alt-LONGs SHORT_BIAS or 3 same-dir/30min) — correlated kill evidence 15:02.

### Side Finds
- GRASS MFE +1.13% → pump_exit_momentum −2.51% account (gave back profit, trail review flagged auto_1hr 15:14).
- IOTA conf 116.3 > 100 (known MED DRIFT-E class).
- 28,363 stale signals in signals table (28,090 >2h, signal_history only 240) — purge only removes executed.

## BTC Regime Alignment Decision Verification

**Answer: NO** — I did not approve converting pump-chain LONG → SHORT when BTC is DECLINING or BELOW EMA300.

**What was actually approved:**
- Oct 7 (commit 89eff4f5): Re-enabled PUMP_CHAIN_V5 LONG with NO BTC regime condition — "philosophy is every pump is a LONG"
- Oct 8 (commit 5f6364d5): DISABLED PUMP_CHAIN_V5 LONG entirely (3rd re-enable failed)

**Existing BTC gates (blocking, not flipping):**
- CONTINUUM-BLOCK (signal_compactor.py:2684): blocks LONG when ALL 3 bear conditions agree (phase+linreg+ema)
- BTC_TIMING_GUARD: blocks pump-chain LONG when BTC 30m > 1.00%
- Only contrarian flip in codebase = trend_momentum_near_sma, not pump-chain

**15:02 root cause:** CONTINUUM-BLOCK didn't fire because BTC was in transitional states (CALM/DECLINING at EMA300, not full bear structure). Block requires all 3 conditions to agree.

**Plan align-with-btc-regime.md:** Proposes BLOCKING LONG in bearish BTC (not converting to SHORT). Never implemented.

## CEO Report — 2026-10-09 00:45 UTC

### Diagnosis
Gate counterfactual audit complete (user-initiated, dual-verified): 6d window, 75,820 block lines, 55 gates, 8,226 episodes. Pooled passed vs blocked indistinguishable (ex4h +0.20% vs +0.02%, MWU p≈0.5) — power only detects selection ≳0.4%/trade. ~78% of blocked episodes show NO EDGE under every robustness test. Only 2 robust verdicts: BTC-CHOP-GATE WORKS (sole Bonferroni survivor, −0.405 p=0.00011); CONF-FILTER-PRESERVE WORKS (−0.670 p=0.006, n=52). SLOPE-FILTER strongest harm candidate (+0.542 p=0.007, both OOS halves positive, kills 59.8% runners) but fails Bonferroni. Biggest unmeasured filter: 25,204 signals EXPIRED waiting <5min for confluence partner (avg conf 80.5) — zero counterfactual instrumentation. 6,956 decider-floor rejections also unlogged per-signal. 10–14/22 gates flip OOS sign; 5 gate codes changed mid-window; one chop→dump regime only. PG-verified live: 24h 12T +$0.72 41.7%WR | 7d 191T +$1.48 53.9%WR.

### Root Cause
Not a single broken gate — the stack is underpowered to evaluate at 6d, and the largest filter (confluence-by-expiry) has no instrumentation at all. Acting on this window would be noise-chasing (the pattern this system keeps getting caught in per AGENTS.md THE PATTERN).

### Decisions (all GO — 0 trading config changes, 0 protected flags touched)

**D1 GO — Ratify the hold.** No gate removal/relax on this 6d window. Reasons: (a) 10–14/22 gates flip sign OOS; (b) 5 gate codes changed mid-window so halves aren't comparable; (c) one regime only (chop→dump); (d) power limit ±0.4%/trade means "no edge shown" ≠ "proven useless"; (e) AGENTS.md pattern discipline — every past unverified "pattern" has been killed by independent audit. Ratified.

**D2 GO — Commission the ≥4-week, code-version-aware, both-regime re-audit** as the standing gate before ANY relax/remove. Priority queue: (1) CONF-FILTER-PRESERVE (works, all-5-baselines, don't touch until reconfirmed); (2) SLOPE-FILTER (harms-direction candidate — blocks SHORTs on +0.05% 5m uptrend slope, 59.8% runner-kill vs market 23.6% — most likely actionable if 4wk confirms); (3) BTC-CHOP-GATE (works, carry-forward). Resource: one analysis pass/week, starts collecting data now (window opens Oct 9). Deliverable: code-version-stratified per-gate table + regime split + Bonferroni. **Any SLOPE-FILTER change before this re-audit completes = reject without discussion.**

**D3 GO — Instrument the confluence-expiry counterfactual.** Highest-information unmeasured thing in the system. Scope: log every signal that expires waiting for a confluence partner (token, direction, confidence, source, timestamp) + attach forward returns from candles.db (+30m/+1h/+4h, direction-aware). Also log the 50%-confidence decider-floor rejections per-signal (6,956 cycles currently invisible). Pure observability — does NOT touch CONFLUENCE_REQUIRED (protected) or any trading path. Decision on any architecture change gated on the measured data. Delegate: bug_hunter (log schema + forward-return join), self_learner (first analysis pass after 7d of data). Success metric: 7d of expired-signal counterfactuals with n≥1000, answerable question "do conf≥80 single-source signals have positive forward edge?"

**D4 GO — Structured block logging at source.** Every gate block line must contain literal BLOCKED + token + direction (or a single JSON object). Current format chaos forced substring-grepping that dropped 36% of block volume in audit v1 and left ~3,800 direction-level block lines (VOL-FLOOR, WARNING BTC-momentum, DIRECTION-LOCK, VOL-GATE-v2) permanently unverifiable. This is pure observability — no gate logic changes, no constant value changes. Delegate: bug_hunter. Success metric: next audit parse covers ≥95% of block volume with zero custom regex archaeology.

**D5 GO (modified) — Fold housekeeping into D4.** GRASS candle feed currently HEALTHY (288/24h candles, fresh to 00:25 UTC; was absent Oct 2–4, present since Oct 6 — token added mid-window, not broken). TESTTOKEN noise last appears Oct 4 in pipeline.log (historical, already rolled out of active window). Both are low-priority; fix as part of the D4 structured-logging pass rather than separate effort. No standalone action.

### Guardrails reaffirmed
- CONFLUENCE_REQUIRED, LIVE_TRADING_ENABLED, ROTATOR_PROTECTED_FLAGS, CEO_PROTECTED_FLAGS: INTACT, will not be touched without T's explicit GO.
- D3 instrumentation measures the confluence architecture — it does not change it. Any proposal to relax CONFLUENCE_REQUIRED requires: measured edge on conf≥80 singles + independent audit + CEO GO.
- SLOPE-FILTER: monitor only until D2 re-audit. Do not disable, do not relax.

### Verification
- Dual-implementation agreement <0.10% on every gate (analysis + independent adversarial auditor). Counts reconcile exactly (75,820 vs 75,824 lines, 55 gates, 8,226 episodes).
- PG live numbers self-queried: 24h 12T +$0.72 41.7% | 7d 191T +$1.48 53.9%.
- GRASS/TESTTOKEN/D5 claims spot-checked against candles.db and pipeline.log.

### Next actions
1. D4 + D5 structured block logging — DELEGATE bug_hunter (this week).
2. D3 confluence-expiry instrumentation — DELEGATE bug_hunter (this week), self_learner first analysis +7d.
3. D2 4-week re-audit window opens Oct 9 — analysis-desk owns weekly pass; first full readout ~Nov 6.
4. SLOPE-FILTER: no action until re-audit; note in regime memory as harm-candidate.
5. Reconfirm BTC-CHOP-GATE and CONF-FILTER-PRESERVE as keep in signal_regime_memory.json (audit-verified works).

Artifacts: plans/2026-10-09_gate-counterfactual-audit.md, audit/gate_counterfactual_verify.md, analysis/gate_counterfactual_audit_2026-10-08.py/.out (v3.2). Kanban: 2026-10-08 23:50, 10-09 00:05, 00:25, + this decision block.

## CEO Report — 2026-10-09 (LONG_RSI_CEILING decision)

### Diagnosis
The Oct-7 raise 70→85 rested on (a) one DOT data point and (b) a 789-trade watchdog sample built on `entry_rsi_14` — the DRIFT-E-unreliable column (median 12.6pt divergence from signal-time meta RSI). My own reproduction of entry_rsi_14 30d LONG 70+ shows **+$1.70/139T**, contradicting the watchdog's −$4.30 claim. Meta-RSI ground truth (30d LONG): 70-75 = 38T 47.4%WR **+$0.24**, 75-80 = 36T 44.4% **−$0.45**, 80-85 = 4T −$0.14, 85+ = 7T +$0.33. Post-Oct-7 cohort in the 70-85 band: n=7, 28.6%WR, −$0.26 — the raise earned nothing.

### Root Cause
RSI ≥75 LONG entries are the chase zone on current meta data; 70-75 is not. The watchdog was directionally right (block 75+) but wrong about the cut point (recommended 70/75 based on the wrong column). Of the 3 named 48h losses: BANANA@78.95 now blocked by PUMP_CHAIN_LONG_RSI_MAX=75 (brain_auditor today); BANANA@72.39 blocked by ceiling 75; **ICP@66.67 blocked by nothing above 66** — that loss is hard_max_loss exit structure in HIGH regime, not entry RSI.

### Fix Applied
`LONG_RSI_CEILING` 85 → **75** (hermes_constants.py:893). NOT 70 (would block the +$0.24 70-75 band); NOT 65 (65-70 = +$0.09/47T, flat — no edge to cut, guts momentum entries); NOT dynamic (the BTC-bullish override at signal_compactor:3888-3919 already IS the dynamic behavior — base 75 + override = 85-equivalent when BTC bullish, 75 when not; BTC below EMA300 200+ bars so override rarely fires). Grade A (mult≥1.30) still gets ceiling 80 via existing dynamic tier. VOLUME_BREAKOUT_LONG_RSI_CEILING=95 untouched (its best band is RSI>70). Aligned with PUMP_CHAIN_LONG_RSI_MAX=75.

### Verification
py_compile OK; LONG_RSI_CEILING=75 loads; CONFLUENCE_REQUIRED=True, LIVE_TRADING_ENABLED=True intact. Compactor timer loads fresh constants next fire — no restart. Expected impact: blocks ~40 trades/30d in the 75+ band worth ≈−$0.59/30d, keeps 70-75 momentum entries. Metric checkpoint (Oct 12): LONG 75+ meta-RSI closed trades → target 0; 70-75 band WR ≥47% maintained.

## CEO Report — 2026-10-09 21:55 UTC

### Diagnosis
24h **17T −$0.45 29.4%WR** | 7d **154T +$0.29 48.7%** (WR decayed from 53.8% at 01:45) | 30d **807T +$0.06 49.3%** — system barely breakeven. hard_max_loss still #1 bleed: 35.7% of 7d closes, −$7.58. SHORT 7d −$0.27 (deadline Oct 11), blocked on HML eval. Wyckoff: detector fires (YGG today 17:54-19:00) but every fire single-source confluence-BLOCKed — 0 trades all-time.

### Root Cause
7d decay driven by hard_max_loss frequency (magnitude fix holding: 24h avg −2.74% acct vs pre-fix −4.5%). SHORT bleed = same HML structure on SHORT side (13T −$1.97 7d); pump-chain- itself is +$0.17/20T. Wyckoff gap is pairing, not detection.

### Fix Applied
**0 new config changes.** (1) **RATIFY 0b689a5d** brain_auditor pump_chain+ NORMAL/HIGH dampen 1.0→0.5 — own 30d query: EXTREME 74T +$3.34 | HIGH 31T −$0.24 | NORMAL 6T −$0.42. (2) **Cap B closed — ACCEPT, already live** (SAME_DIR_30MIN_MAX=3, firing since 14:33). Cluster re-test deferred until next cluster event. (3) **DELEGATE signal_analyst URGENT:** wyckoff+volume/rs pairing by Oct 11 EOD. (4) HML HOLD to Oct 10 per plan.

### Verification
Protected flags INTACT (CONFLUENCE_REQUIRED=True, LIVE_TRADING_ENABLED=True, kill JSON=true). Cap B skips confirmed in pipeline.log. Wyckoff confluence-blocks confirmed in CONFLUENCE-DEBUG lines. Disk 84%.

**Metric checkpoint Oct 12:** 7d PnL ≥$0 AND WR ≥50% (RSI-75 + Cap B + dampen cohort effect). Oct 10: HML frequency eval. Oct 11: SHORT ≥$0 + wyckoff pairing delivery.

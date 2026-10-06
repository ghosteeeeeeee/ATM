# Bug Hunter Verdict — ema=AT Bullish Fix (commit 114c1897)

**Date:** 2026-10-05 ~21:15 UTC
**Auditor:** bug_hunter (independent verification)
**Change:** `scripts/signal_compactor.py` +6/−2 — `_cont_bullish` and `_lrc_bullish` now accept `ema300_position in ('ABOVE','AT')` instead of `== 'ABOVE'`

---

## VERDICT: **SAFE TO SHIP**

The fix is correct, well-scoped, syntax-clean, data-validated, and live-proven in production. No blockers. Three MEDIUM/LOW hardening recommendations and two related-path findings below.

---

## 1. Syntax and Scope — **PASS**

- `python3 -c "import ast; ast.parse(...)"` → **OK** (no SyntaxError).
- Both changes present at expected locations:
  - Change 1: lines 2639–2640 (`_cont_bullish`) — exact match to the described diff.
  - Change 2: lines 3708–3709 (`_lrc_bullish`) — exact match.
- `git show 114c1897` confirms +6/−2, only `scripts/signal_compactor.py` touched, commit message accurately describes the incident.
- **Data population verified:**
  - `_cont_row_data`: populated at lines 2592–2604 from `continuum_states WHERE token='BTC' ORDER BY ts DESC LIMIT 1`, with staleness guard at 2593–2596 (`>600s` → row skipped, dict stays `{}`). Check at 2639 is downstream of this. Connection closed in `finally` (2607–2610). No leak.
  - `_lrc_row`: populated at lines 3694–3701, staleness guard `_lrc_age < 600` at 3702–3703 before the check at 3708. Connection closed in `finally` (3698–3699). No leak.
- Pipeline code freshness: `signal_compactor.py` runs via standalone systemd timer as a **fresh subprocess each cycle** (confirmed: `run_pipeline.py` line 22 comment + timer). New code loaded at first compaction after commit (18:46:38 commit → 18:47:00 cycle). No restart required for this step; live behavior below confirms it.

## 2. Data Correctness — **PASS**

- **Valid values** for `ema300_position`: exactly `BELOW`, `AT`, `ABOVE` (`SELECT DISTINCT` on continuum.db; matches `continuum_engine.py:56,280–287` enum).
- **AT definition:** `price` within ±0.15% of EMA300 (`EMA300_ABOVE_BUFFER = EMA300_BELOW_BUFFER = 0.0015`, `continuum_constants.py:23–24`). Genuinely transitional, not a noise band.
- **Hysteresis:** `ema300_position` uses `HysteresisState(5, 3)` (`continuum_constants.py:13`, `continuum_engine.py:465`) — 5 consecutive candles to confirm a new state, 3 to deconfirm. AT is a *confirmed sticky* state, not a transient tick. Treating it as meaningful is justified.
- **Incident-state query (2026-10-05 18:10–18:50 UTC):** BTC was `DECLINING | LEAN_BULL | AT` for the **entire pump**, score rising 45→81, z-tier STRONG_POS from 18:17 onward. Exactly the state the fix targets. (Task description said "score 58→77"; actual DB shows 45→81 across the window, 57→77 in the core 18:18–18:46 span — description accurate.)
- **Current state:** `RECOVERY | LEAN_BULL | ABOVE`, score 83.5 — pump completed, price crossed above EMA300. AT was indeed transitional.
- **Truth-table simulation (executed):**

  | phase | linreg | ema | `_cont_bullish` | `_cont_bearish` | effect |
  |---|---|---|---|---|---|
  | DECLINING | LEAN_BULL | AT | **True** | False | LONG bypass=True (fix fires) |
  | DECLINING | LEAN_BULL | ABOVE | True | False | (worked pre-fix too) |
  | CALM | LEAN_BULL | AT | **True** | False | fix fires |
  | DECLINING | LEAN_BEAR | AT | False | False | velocity fallback — correct |
  | CALM | LEAN_BEAR | BELOW | False | True | bearish path — unchanged |
  | DECLINING | NEUTRAL | AT | False | False | velocity fallback — correct |
  | (stale/empty) | — | — | False | False | velocity fallback — safe |

- With the incident state, `_cont_bullish` now evaluates **True**. ✓

## 3. Logic Correctness — **PASS**

**Change 1 (`_cont_bullish`, line 2680–2681):** `direction=LONG and _cont_bullish` → `_btc_mom_ok_for_bypass = True`. This flag gates the LONG-NEUTRAL block at lines 2740–2762: standalone-bypass-listed signals with 1 confluence type now pass in NEUTRAL 4h regime when BTC structure is bullish. Confirmed effect in live logs (section 8).

**Change 2 (`_lrc_bullish`, lines 3708–3718):** When BTC continuum is bullish, LONGs with RSI above the dynamic ceiling (60–80 by R:R grade) bypass the overbought block — "overbought = momentum." Live proof at 19:07–19:09: `BTC LONG bypass — RSI 71.5 > 70 but BTC bullish` during a `RECOVERY | LEAN_BULL | AT` window. Pre-fix this LONG would have been blocked. Both changes fire as designed.

**Is `_cont_bullish=True` + LONG in NEUTRAL 4h safe?** Yes, with caveats:
- Blast radius is narrow: only applies when (a) 4h regime = NEUTRAL, (b) signal is in `STANDALONE_BYPASS_SIGNALS`, (c) <2 confluence types. All other gates (RSI floors/ceilings, winrate hall-of-shame, blacklists, execution-time RSI, BB dead zones, spike filters) still apply downstream.
- **Bonus safety improvement (not in the commit description):** pre-fix, during `LEAN_BULL+AT` with high BTC velocity, SHORT signals fell through to the velocity check and `_vel_ok=True` would **allow SHORT standalone bypass during a bullish transitional state** — shorting into a pump (BANANA SHORT lesson). Post-fix, line 2682–2683 sets `_btc_mom_ok_for_bypass=False` for SHORT when `_cont_bullish`, closing that vector. The fix is directionally correct on both sides.

**Dead-cat-bounce risk (ema=AT + LEAN_BULL but pump is fake):** Real but bounded. DB evidence: `LEAN_BULL+AT` also occurs at *low* scores — 2026-10-04 18:46–18:49 showed `DECLINING|LEAN_BULL|AT` at score 37–46 (weak bounce in downtrend). With the fix, `_cont_bullish=True` at score 37 → standalone LONGs unblocked in that state. Mitigations: (a) linreg hysteresis requires 5 consecutive bullish candles, (b) AT requires price *at* the EMA (recovered, not falling through), (c) downstream RSI/winrate filters still gate. Residual risk accepted given the trading philosophy ("every pump is a LONG opportunity") and the incident cost (30+ min empty hotset during a live pump). See Recommendation R1 for a tightening option.

## 4. Asymmetry Check — **PASS (with notes)**

- Bearish: `phase in (DECLINING,CALM,RECOVERY) AND linreg bearish AND ema == 'BELOW'` — 3 conditions.
- Bullish (post-fix): `linreg bullish AND ema in (ABOVE,AT)` — 2 conditions, no phase gate.
- **The 2-vs-3 condition asymmetry predates this commit.** The 2026-10-04 fix (already in the file, comment at 2634–2635) deliberately removed the phase gate from bullish: "phase can lag behind momentum — trust momentum indicators over lagging phase." Evidence supports it: during the incident, phase said DECLINING (RSI<45) while structure said bullish pump. Requiring a phase gate on bullish would re-introduce the bug class. **Intentional, correct.**
- **Exact-match vs two-value acceptance:** The new asymmetry (bearish `== 'BELOW'`, bullish `in ('ABOVE','AT')`) is defensible, not a bug:
  - AT is a confirmed hysteresis state (5-candle ON), not noise.
  - Semantics differ by side: AT+bullish-linreg = "recovered to EMA, slope up" = transitional bullish. AT+bearish-linreg would be "fell back to EMA, slope down" = transitional bearish — but the bearish check currently returns **False** for that combo (`ema != 'BELOW'`), falling to velocity fallback rather than firing bearish. That is the *conservative* middle ground: it neither blocks LONGs nor enables SHORTs on transitional bearish data.
  - Symmetrically accepting AT on the bearish side would *block more LONGs and enable more SHORTs* — wrong direction for this system's philosophy. **Two-value acceptance on bullish only is correct.**
- Note: `_cont_bullish` has no score/z-tier floor while the separate score-exception path (2745–2752) requires `60 <= score < 80`. See R1.

## 5. Edge Cases — **PASS**

- **NULL `ema300_position`:** `.get()` → `None`; `None in ('ABOVE','AT')` → `False` → velocity fallback. Safe. (DB default is `'AT'` per `continuum_engine.py:423`, and `continuum_context.py:260` coerces missing→`'AT'`, so NULL is doubly unlikely.)
- **Unexpected value:** any string outside the tuple → `False` → velocity fallback. Safe.
- **`linreg_direction == 'NEUTRAL'`:** both bullish and bearish checks `False` → falls to velocity check (`_vel_ok`, line 2686). Correct — neutral structure deserves no structural override.
- **`ema=AT` + `LEAN_BEAR`:** bullish `False` (linreg gate), bearish `False` (ema gate) → velocity fallback. Correct — bearish linreg overrides any bullish reading of ema; conservative.
- **Stale data (>10 min):** `_cont_row_data = {}` → both checks `False` → velocity fallback. The fix cannot fire on stale data. Safe.
- **Missing BTC row / DB exception:** same fallback path; exception logged at 2688. Safe.

## 6. Impact Assessment — **PASS**

- **Historical blocks:** `grep -c "LONG-NEUTRAL.*BTC flat" logs/pipeline.log` → **2,773** (all-time). Recent examples: IMX (16:46–16:51), YGG (17:21–17:23), NXPC (17:45–17:48), TRX (18:16–18:19, 18:41–18:43) — all during NEUTRAL 4h + BTC structural-bullish-but-AT windows.
- **Post-fix (after 18:47):** `LONG-NEUTRAL.*BTC flat` count = **0**. The block message for non-standalone signals changed to "4h regime NEUTRAL, no LONG edge" (SOL, WLFI, GMX at 19:57–20:14) — this proves `_btc_mom_ok_for_bypass` is now **True** in those windows (the `else` branch only reached when mom_ok=True but the signal lacks standalone-listing/confluence). Direct live proof the fix flipped the flag.
- **TRX bb_bounce_v2_long (conf=77, expired 18:46):** **Would have passed.** Evidence chain:
  1. Source `bb-bounce-v2-long+` (log 18:20–18:21: `CONFLUENCE-GATE-PASS TRX LONG: {bb-bounce-v2-long+} (NEUTRAL-relax: standalone bypass (bb-bounce-v2-long))`).
  2. `bare_source = 'bb-bounce-v2-long'` ∈ `STANDALONE_BYPASS_SIGNALS` (verified by executing the list from `hermes_constants.py`).
  3. During 18:41–18:46 BTC was `DECLINING|LEAN_BULL|AT`, score 74–78 → `_cont_bullish=True` → `_btc_mom_ok_for_bypass=True` → standalone bypass condition at line 2740 satisfied → **TRX passes the LONG-NEUTRAL gate**.
  4. Caveat: the `signals`/`signal_history` tables returned no rows for that window (rotation/archival) — conf=77 could not be DB-verified; log evidence confirms source and block pattern. Honest limitation noted.
- **False-positive risk:** See section 3. Bounded by narrow blast radius + downstream filters + hysteresis. Frequency note: `LEAN_BULL/BULL+AT` is **14.8% of all BTC continuum history, 24.3% of the last 7 days** (5,040 of 20,560 ticks) — the override now fires roughly **2× more often** than the ABOVE-only version. This is a material widening, but the states it unlocks are genuinely transitional-bullish, and it simultaneously *closes* the SHORT-into-pump vector. Net risk reduction.
- **Post-fix trades (real money):** 3 LONGs opened 20:21–20:36 — TURBO (`bb-squeeze+`, entry 0.001062), CRV (`mover+`, entry 0.37997), MERL (`bb-squeeze+`, entry 0.031915); all `status=open`. TURBO/MERL passed via the Change-2 RSI-ceiling override but during `ema=ABOVE` windows (20:20:48–20:34:48), so those particular bypasses would also have fired pre-fix; they validate the override path generally, not the AT-specific widening. The 19:07–19:09 BTC RSI-71.5 bypass during `ema=AT` is the AT-specific live proof.

## 7. Related Code Paths — **WARN (2 findings, no blockers)**

`grep -n "ema300_position"` in signal_compactor.py → 10 sites; in decider_run.py → 4 sites. Audit of every bullish-direction check:

| Location | Check | Status |
|---|---|---|
| signal_compactor.py:2639–2640 | `_cont_bullish` | ✅ Fixed (Change 1) |
| signal_compactor.py:3708–3709 | `_lrc_bullish` | ✅ Fixed (Change 2) |
| signal_compactor.py:1243 | chop gate, CALM branch | ✅ Already accepts AT (2026-09-23 fix) |
| **signal_compactor.py:1244** | chop gate, "structural bull regardless of phase" | ⚠️ **Still `== 'ABOVE'` — Finding F1** |
| **decider_run.py:3337** | BTC-CRASH-OVERRIDE, CALM branch | ⚠️ **Still `== 'ABOVE'` — Finding F2** |
| decider_run.py:935, 1073, 1911 | bearish checks (`ema == 'BELOW'`) | ✅ Bear-side, consistent with compactor |
| signal_compactor.py:2633, 2714, 3463, 3647, 3839 | bearish checks (`ema == 'BELOW'`) | ✅ Bear-side, unchanged by design |

**F1 (MEDIUM) — Chop gate still blocks MOMENTUM LONGs during DECLINING+LEAN_BULL+AT.** Line 1244 requires `_e2 == 'ABOVE'` for the phase-independent structural-bull override. Live evidence: 19:17–19:22, `BTC LONG trendline_bounce_long: BLOCKED — BTC 30m=+0.028% (flat), signal=MOMENTUM` — during the 19:13:47–19:22:17 `DECLINING|LEAN_BULL|AT` window. Same transitional-state bug class, unfixed path. The incident's TRX signal was MEAN_REVERSION family (chop gate only blocks MOMENTUM), so the commit's fix was sufficient for the incident — but MOMENTUM-family LONGs remain exposed to the identical failure mode. Suggested fix: `_e2 in ('ABOVE', 'AT')` on line 1244, mirroring line 1243.

**F2 (LOW) — decider BTC-CRASH-OVERRIDE CALM branch still `== 'ABOVE'`.** Line 3337: `(_p == 'CALM' and _l in ('LEAN_BULL','BULL') and _e == 'ABOVE')`. Narrow path (crash-filter override; RECOVERY/NEUTRAL phases bypass the ema check entirely), but same inconsistency. Suggested fix: accept `('ABOVE','AT')`.

**F3 (LOW) — No audit log when `_cont_bullish` fires for LONG.** Lines 2680–2681 set `_btc_mom_ok_for_bypass = True` **silently**, unlike the bearish paths which log `CONTINUUM-OVERRIDE`/`CONTINUUM-BLOCK` (2644, 2676, 2679). In production you cannot tell from logs which LONGs passed *because of this fix* vs. velocity vs. 1m LONG_BIAS. AGENTS.md requires debug/audit output on everything that makes sense. Suggested fix: add `log(f"  ✅ [CONTINUUM-OVERRIDE] {token} LONG — BTC bullish structure ({_continuum_phase}+{linreg}+{ema}), standalone bypass allowed")`.

## 8. Live Pipeline Test — **PASS**

- Pipeline process: `run_pipeline.py` started 21:04:59; compactor running its own timer cycle every minute (cycle 12236 at 21:10). New code confirmed loaded (section 6 evidence).
- Post-fix LONG activity (20:56–21:08): CC, LDO, JUP, DYDX, ARB, DOT, BTC, NEO, W, SEI all passing `LONG-NEUTRAL-BYPASS` via `1m LONG_BIAS` or standalone-bypass + mom_ok paths. Zero "BTC flat" blocks.
- **Hotset: still empty** (`hotset.json` = `[]`, cycle 12236, 21:10). Root cause is *no longer* the BTC-flat gate — signals now survive compaction gates but die on downstream filters: `No signals above 50% confidence` (194 occurrences 18:47–20:42), RSI blocks (`LONG-RSI-BLOCK RSI 0.0 < 20` oversold-freefall for ARB/YGG/GMX), `HALL-SHAME` 30d WR<55% blocks (FIL/CHIP/ALGO), `PUMP-CHAIN-RSI-MAX/MIN`. **This is a separate problem from the fixed bug** — the fix removed one blocker; signal *generation quality/confidence* is now the binding constraint. Flagging per "see something, say something."
- 3 open LONG trades (TURBO/CRV/MERL) confirm the execution path works end-to-end post-fix.

---

## Bugs Found

| ID | Severity | Location | Description |
|---|---|---|---|
| F1 | **MEDIUM** | signal_compactor.py:1244 | Chop gate structural-bull branch still `== 'ABOVE'` — MOMENTUM-family LONGs blocked during DECLINING+LEAN_BULL+AT (live-proven 19:17–19:22). Same bug class as the fixed issue. |
| F2 | LOW | decider_run.py:3337 | BTC-CRASH-OVERRIDE CALM branch still `== 'ABOVE'`. Same transitional-state gap, narrow path. |
| F3 | LOW | signal_compactor.py:2680–2681 | `_cont_bullish` LONG override fires silently — no audit log, hinders future verification. |

**Sideways findings (unrelated to this commit):**
- **TRX candles.db stale ~5h** at 21:05: `TRX: candles.db stale (18305s old) — falling back to Binance`. price_collector not updating TRX candles. **MEDIUM** — local-data-preferred policy violated; investigate price_collector coverage for TRX.
- Hotset emptiness now driven by confidence/RSI/winrate filters, not BTC-flat. Not a bug in this commit; separate signal-quality workstream.

## Assessment

**Treating ema=AT as bullish is safe and correct.** AT is a hysteresis-confirmed transitional state meaning "price recovered to the EMA300, slope up, not yet confirmed above." Requiring strict ABOVE systematically blind-spotted the exact window when BTC turns bullish — the incident cost was 30+ minutes of empty hotset during a live pump with score 77/STRONG_POS, while SHORTs were correctly blocked. The fix:

1. Correctly targets two code sites; both verified live-proven (Change 1 via zero post-fix "BTC flat" blocks + "no LONG edge" message transition; Change 2 via the 19:07 BTC RSI-71.5 bypass during an AT window).
2. Introduces no syntax, scoping, staleness, or NULL-handling regressions (all edge cases fall safely to the velocity check).
3. Net-widens the bullish override ~2× in time-frequency but only inside a narrow gate (standalone-listed signals, NEUTRAL 4h regime), with all downstream safety filters intact.
4. Simultaneously *closes* a SHORT-into-pump false-positive vector (line 2682–2683), improving symmetry of intent: lenient for LONG, strict for SHORT during bullish structure.
5. Residual false-positive risk (weak bounce at low score with LEAN_BULL+AT) is real but bounded; hysteresis + downstream filters mitigate. Given the trading philosophy and the incident's severity, the risk trade-off is justified.

**No blocker. Ship it.** Apply F1 (one-line) in a follow-up; F2/F3 as cleanup.

## Recommendations

- **R1 (MEDIUM, follow-up):** Consider a score floor on `_cont_bullish` — e.g., `state_score >= 50` or `zscore_tier != 'STRONG_NEG'` — mirroring the discipline of the score-exception path (2745–2752, requires 60≤score<80). DB shows LEAN_BULL+AT occurs at score 23–46 during weak bounces (2026-10-04 18:40–18:50); the override currently fires there too. Backtest before tightening — per AGENTS.md, independent verification required for filter changes.
- **R2 (MEDIUM, immediate):** Apply F1 — change signal_compactor.py:1244 `_e2 == 'ABOVE'` → `_e2 in ('ABOVE', 'AT')`. One line, mirrors line 1243, closes the MOMENTUM-family gap.
- **R3 (LOW):** Apply F2 (decider_run.py:3337) and F3 (add audit log at signal_compactor.py:2680–2681).
- **R4 (MEDIUM, separate workstream):** Investigate hotset emptiness under the new regime — signals pass BTC gates now but fail confidence (conf<50), RSI floors (oversold freefall), and 30d WR hall-of-shame. The compactor fix was necessary but not sufficient for "signals → trades."
- **R5 (MEDIUM, separate workstream):** Fix TRX candles.db staleness (~5h old at 21:05) in price_collector.
- **R6 (process):** After applying R2/R3, per AGENTS.md the pipeline reload step applies only to long-running processes; signal_compactor's timer runs fresh each cycle, so no restart needed — but verify with the next `LONG-NEUTRAL-BYPASS.*AT` log line.

---

*Verification method: all claims from executed commands (ast.parse, git show, SQLite queries on continuum.db + signals_hermes_runtime.db + PostgreSQL brain, truth-table simulation, log greps with counts, live log tail). No numbers from memory. Signals-table gap for the TRX incident window noted honestly in section 6.*

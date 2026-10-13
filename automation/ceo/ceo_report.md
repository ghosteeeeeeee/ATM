## CEO Decision — 2026-10-12 — ceo-comm rework (design-only, no implementation)

### Decisions (lead)
1. **Root cause CONFIRMED** = unbounded scope + all-or-nothing kill. Not a model/provider speed problem. Evidence: `run_ceo.sh:37` is a single `timeout 600 bash -c "cat ceo_prompt.md | opencode run"` — SIGTERM kills the process, zero partial output captured. `ceo_prompt.md` (394 lines) mandates Steps 0–5 as "ACTIVE — every run" (live SQL verification, tune a signal, develop a signal, develop coin_tracker) plus a Monday 6-subagent MoE panel. That cannot fit in 600s. Secondary finding: the script's own comment says "Timeout: 5 minutes (300s)" but the actual timeout is 600 — stale comment, fix on implement.
2. **Compaction-safe design APPROVED with 3 amendments** (full detail below). Your instinct that `-c` resume of a compacted giant session is BAD is correct — auto-compact keeps only ~15k recent tokens and prunes tool outputs; resumed impl sessions would edit files on a summary, not on evidence. Do not use `-c`/`-s` across runs for implementation at all.
3. **Step 0–5 on every run: NO — trim and split.** Concrete split below. The "develop new signal / coin_tracker every run" language is the primary budget blowout and moves to weekly.

### The design I approve
| Piece | Verdict | Amendment |
|-------|---------|-----------|
| (a) Status-report = one read-only bounded session | ✅ | One SQL batch (24h + 7d + per-signal), not Step 2's full interrogation. Budget ~3 min. |
| (b) Decision/impl = fresh single-goal subagent sessions | ✅ | Same pattern that made bug_hunter succeed. One goal per session, parent never edits files itself. |
| (c) Checkpoint-to-disk BEFORE any edits | ✅ | Parent writes `automation/ceo/checkpoints/<ts>-decision.md` (decision + evidence + plan + files-to-touch) BEFORE dispatching. Each subagent appends `<ts>-result-<n>.md`. Even a hard kill leaves the decision and partial results on disk; next run assembles the report from checkpoints. |
| (d) auto-compact OFF on impl sessions | ✅ | Silent mid-edit summarization is strictly worse than a loud overflow failure. Config per-session or via agent config. |
| (e) Detach + JSON stream | ✅ | `nohup`/`systemd-run` + `--format json >> logs/ceo/<ts>.jsonl` + capture exit code to a `.exit` file. Timeout becomes a signal to inspect, not a data-loss event. |

**Amendments / risks you missed:**
1. **Lock is read-only today.** `run_ceo.sh` checks `/tmp/hermes-session-active.lock` but never CREATES it. A detached impl session that edits `hermes_constants.py` while a human session is live would collide. Fix: the detached impl run must acquire the lock before its first edit and release on exit (flock or timestamp file). Status sessions don't need it.
2. **Concurrent-writer hazard.** Multiple detached sessions (status + N subagents) all potentially touching `ceo_kanban.md` / `ceo_report.md`. Rule: subagents write ONLY their own checkpoint files; a single aggregator (parent or next run) is the sole writer of kanban/report. Use `flock` on that writer.
3. **Port collision.** Current script pins `--port 4099`. Two detached sessions = conflict. Use a random/ephemeral port for detached runs, or one port per session type.
4. **MoE panel must leave the normal run entirely.** Separate script (`run_ceo_moe.sh`), own budget (detached, ~30 min), Monday only. Never in the same process as a normal run.
5. **`-c`/`-s` usage policy:** status session may use `-s` within its own short life if it needs a second turn; NEVER resume a prior run's session for implementation. Fresh session every time.

### Concrete run-split (recommendation for Step 0–5)
| Run type | Frequency | Scope | Budget |
|----------|-----------|-------|--------|
| **Status run** | every scheduled tick | CURRENT.md + team updates + ONE SQL batch (24h totals, 7d totals, per-signal 7d) + ONE rotating proactive question + write report. Read-only. | ~3 min, in-process OK |
| **Deep run** | weekly (or when status run flags a problem) | Regime-aware analysis (Step 2b), ONE signal tune, ONE signal-development task — each dispatched as a fresh subagent session with a checkpoint file. | detached, per-task budget |
| **MoE panel** | Monday only, separate script | 6 parallel expert subagents, synthesis to `reports/`. | detached, ~30 min |

Rationale: the current prompt conflates "CEO checks the system" (cheap, frequent) with "CEO improves the system" (expensive, rare). Splitting them keeps the frequent path bounded and makes the expensive path survivable. "Develop new signals / coin_tracker every run" becomes "every weekly deep run" — that alone recovers most of the budget.

### What I am NOT approving
- Resuming one giant `-c` session across runs (your analysis is right; rejected).
- Raising the timeout instead of bounding the work (treats the symptom).
- Removing the checkpoint-before-edit rule for any session that touches files.

### Verification plan (when implemented)
1. Run status session 3× back-to-back — must complete <3 min each, produce a report every time.
2. Kill an impl session mid-flight with SIGTERM — checkpoint file + partial subagent results must exist on disk and be assemblable.
3. Confirm auto-compact-off session fails loudly (non-zero exit, error in .jsonl) on a deliberately oversized prompt instead of summarizing.

---

## CEO Report — 2026-10-12

### Diagnosis
Regime-recalibration backtest claimed a profitable SHORT hump at 2.5–4.0% ATR (t=1.92–2.10, LOO-robust, "+$15.71 suppressed"). I re-derived independently (same basis: 5,140 trades, ATR%(14) from 1h candles pre-open — n matches exactly). **The hump does not reproduce at claimed significance.** System: 24h 26T +$1.00 26.9% WR; 7d 145T −$0.10 37.9% (flipped negative).

### Root Cause
Two-part:
1. **Evidence gap (THE PATTERN).** My repro: SHORT 2.5–4.0 n=209 +$1.68 WR 48.8% **t=0.95** (doc: t=1.92). Sub-bin 2.5–3.0 t=1.72 (doc: 2.09). LOO drops **FET** (not XMR) → t=0.49 (doc: 2.10). Doc's LOO n=244 > my full-band n=209 → band membership differs = unreproducible derivation. "+$15.71" is winners-only sum; true unblock counterfactual is **net ≈ +$2** before fees on 209 extra trades.
2. **What DID reproduce:** LONG FLAT edge t=2.65 ✓; LONG decays with ATR ✓; MAXXED (≥4.0) bad BOTH dirs (LONG 44.4% −$1.48; SHORT 24.0% −$1.16) ✓ direction-consistent.

### Decision
1. **MAXXED tier: APPROVED IN PRINCIPLE, shadow-only first.** ≥4.0% is genuinely toxic both directions. Hard constraint: every existing `regime=='EXTREME'` comparison must treat MAXXED as EXTREME-equivalent (naive relabel would accidentally UNBLOCK EXTREME restrictions — blast-radius audit required before any live wiring).
2. **EXTREME-hi SHORT-allow: REJECTED pending reproduction.** The entire economic case (+$15.71) rests on a hump that fails independent verification. No live change to SHORT treatment in 1.5–4.0%.
3. **LONG-restrict EXTREME-hi: NO** — −$2.46/173T t=−1.21, not significant; blanket blocks need more.
4. **Full ladder re-cut: NO** — correctly rejected; per-signal overrides rest on current buckets.

### Verification (pre-code-change, mandatory)
- **own-conclusions: REQUIRED and ordered** — reproduce the SHORT hump with a checked-in, fully scripted derivation; resolve the n=244-vs-209 band mismatch. Pass bar: |t|≥2.0, LOO-robust, net counterfactual (incl. fee drag) > +$5/30d.
- Any future implementation: 48h shadow logging of would-be decisions before enforcement; protected flags untouched; CONFLUENCE_REQUIRED stays True.

### Next
DELEGATE signal_analyst: MAXXED shadow label (observability only, EXTREME-equivalent mapping) + reproduction script. DELEGATE own-conclusions: fresh-eyes repro of the 2.5–3.0 SHORT cell. 7d PnL now −$0.10 — protecting ≥$0 checkpoint.

---

## CEO Acknowledgment — 2026-10-12 02:22 UTC — MAXXED tier DEPLOYED (T-directed)

### Acknowledged
T-directed MAXXED tier is live. Accept the design and the two-pass verification. Commits 2b6c85ca + 1bf84683 pushed.

### Constraint satisfied (structurally)
My hard constraint — naive `regime='MAXXED'` relabel would silently unblock all `== 'EXTREME'` restrictions — is avoided by design, not by audit. `classify_volatility()` unchanged (still returns EXTREME at ATR%>=4.0); MAXXED is an additive block via `is_maxxed()` on `MAXXED_ATR_PCT_THRESH=4.0`. Zero `== 'MAXXED'` comparisons anywhere. MAXXED can only block more, never less. No relabel risk exists.

### Shipped
- `hermes_constants.py`: MAXXED_ATR_PCT_THRESH=4.0, MAXXED_BLOCK_ENABLED=True, MAXXED_REGIME_LOG=True. New constants only; line-2 protection honored.
- `volatility_gate_v2.py`: `is_maxxed()`.
- `signal_compactor.py`: approval-time block, both directions, logs [MAXXED-BLOCK].
- `decider_run.py`: exec-time backstop in `execute_trade()` — BUG-052-safe (return-before-claim).

### Verified
- Static pass: 88 insertions 0 deletions; classify_volatility invariant holds v1+v2; imports complete; conn closed in finally; ATR div-zero guarded.
- Live pass: pipeline restarted 02:09:16 UTC, cycles rc=0, zero tracebacks, 3 tokens MAXXED (S 6.78%, W 5.51%, STRK 5.43%), dry-run of exec backstop fired correctly, GRASS SHORT (ATR 3.82) correctly not blocked. Kill-switch sanity clean.
- Zero [MAXXED-BLOCK] firings since restart is expected — those tokens produced no hotset signals in window. Block is armed and provably functional.

### Decisions on informational findings
1. Fail-open on <15 closed 1h candles (fresh explosive listings): **accept as-is.** Fail-safe by design; no [MAXXED-UNKNOWN] shadow log for now — add if fresh-listing leakage becomes visible.
2. Inlined ATR-14 copy in compactor (drift risk vs `get_atr_pct()`): **defer.** Matches today; cleanup when next touching compactor. Not worth a standalone diff.

### Extensibility
Higher tier later (e.g. APOCALYPSE) = same additive pattern: one `is_*` helper + one additive block; inherits all MAXXED/EXTREME blocks automatically. Threshold is a named constant. T's requirement met.

### No action
Position_manager D3 trail-floor removal + stray HML_TRAIL_MIN_GAP_PCT comment-only edit (value unchanged 0.20) — housekeeping acknowledged, no further action. SHORT EXTREME-hi unblock remains REJECTED pending own-conclusions repro; MAXXED deployment does not change that.

## CEO Status — 20261012T054722Z
### Health: pipeline=active (timer tick, between-cycle inactive is normal) guardian=active open_pos=1
### Numbers: 24h 19T +$1.58 57.9% | 7d 134T +$0.54 41.8%
### Findings: 7d PnL flipped back POSITIVE (+$0.41→+$0.54); 24h WR strong (57.9%). NEW error: `NameError: PM_TRAIL_ACTIVATE_PCT is not defined` in position_manager (1x) — undefined constant reference, could break a trail path. Repeated: mirror_open "Balance too low" (8x), mark_signal_executed returned=0 (13x). Coin_tracker scores FRESH (agg_scores max ts=2026-10-12 05:49 UTC, 112 coins) — proactive Q12 (rotating: 12 mod 15=12) ANSWERED: updating on schedule.
### Recommendation: Investigate `PM_TRAIL_ACTIVATE_PCT` NameError (likely missing import/constant in position_manager) before weekly deep run.

## CEO Status — 20261012T094722Z
### Health: pipeline=active guardian=active open_pos=1
### Numbers: 24h 22T +$0.75 50.0% | 7d 132T +$1.01 41.7%
### Findings: New alert — `NameError: PM_TRAIL_ACTIVATE_PCT is not defined` in position_manager (1x, not yet repeated); earlier 05:00 batch of 8x `mirror_open Balance too low` + signal rollbacks + hotset failures (trading with thin balance?); continuum OVERRIDE allowing trades despite BTC filter 4x. Proactive (12%15=12): accumulation-phase coins — 90/112 tracked, top predictive_score: ALGO 55.4, SYRUP 54.8, BTC 54.8, MNT 54.6, GMX 54.5 (all setup=NEUTRAL except ZRO LONG 53.8) — phase data fresh (same ts batch); no accumulation→markup transition signal build yet.
### Recommendation: bug_hunter — triage `PM_TRAIL_ACTIVATE_PCT` NameError (undefined constant = trail logic may be dead if raised live); confirm why mirror_open is balance-starved.

## CEO Status — 20261012T134722Z
### Health: pipeline=active guardian=active open_pos=1
### Numbers: 22T +$0.75 50.0% | 7d 129T +$1.33 41.9%
### Findings: clean — 7d PnL holding ≥$0 (+$1.33); 24h WR 50%; open 1 paper position. Error alerts show only repeated expected blocks + resolved crash-loop (hermes-coding-mcp auto-disabled, script missing).
### Proactive Q12 — accumulation coins (coin_tracker agg_scores, fresh ts): 15+ coins in Wyckoff accumulation. Highest-signal: ADA (composite 59, volume_z 98.6), COMP (60.5, vol 59.7), BABY (59.0), BIGTIME (58.2), CHIP (58.0). Momentum universally low (3–23) — textbook pre-spring base.
### Recommendation: trail-arm timeout verdict still awaiting CEO GO (audit first per plan); hermes-coding-mcp unit should be removed or script restored — one-line decision for weekly deep run.

## grind-breakout-v2 Freshness Gate — 2026-10-12

### Decision: APPROVE the fix. Leave MEGA blacklisted. Medium priority — do it now, it's a small verified diff.

### Verified numbers (DB, run today)

| Bucket | Tokens | Status after fix |
|--------|--------|------------------|
| fresh latest_prices + fresh candles | 87 | already scanned today |
| **stale latest_prices + fresh candles** | **42** | **unlocked by fix — true blind spot** |
| stale latest_prices + stale candles | 47 | correctly skipped either way |
| no latest_prices + stale candles | 6 | correctly skipped either way |

Correction to task context: blind spot is **42 tokens, not 95**. The 95 figure counts all tokens the gate skips; 53 of those have stale candles too and should be skipped regardless. Fix expands the scanned universe 87 → 129 tokens (+48%).

MEGA verified: latest_prices frozen 2026-08-11, but candles_5m is **fresh** (last candle 14:50 today). Bug-hunter's diagnosis confirmed — candle collector still tracks it, only the gate blocks it.

### 1. Freshness gate fix — APPROVED
Change `run()` in grind_breakout_v2.py:369 from `price_age_minutes(token) > 10` (reads latest_prices) to candle-age check on `candles_5m` — the table detect() actually consumes. Precedent exists: btc_grind_spike, bb_bounce_v3_long, neutral_sniper, range_reversion, volume_breakout, trend_ride_long already do candle-age checks. Not a novel pattern. Low risk: detect() was already verified correct; this only widens the input set. Blacklists, cooldowns, direction gates all still apply after the check.

### 2. MEGA — LEAVE BLACKLISTED
Blacklisted both directions 2026-08-11 with specific reason (5T, 0% WR, −$0.23, all ATR SL hits, "low-price noise coin"). The freshness fix does NOT bypass blacklists — MEGA still can't trade after the fix. The gate fix and the blacklist are orthogonal. No reason to revisit: nothing has changed about MEGA's trade quality.

### 3. Other signals — systemic, but fix pattern first
~50 signals call price_age_minutes. The bug only bites where the token universe is sourced from candles but gated on latest_prices — 17 signals do `SELECT DISTINCT token FROM candles`. Don't blanket-change price_age_minutes (50+ callers, execution pricing may depend on it). Fix grind_breakout_v2 now, verify for a week, then batch-audit the other 16 as a follow-up if the pattern proves out.

### 4. Priority vs other work
Do it now — it's a ~5-line change to a live, verified-correct signal, and deferring it means continued blind scanning. Not urgent enough to interrupt higher-priority items (PM_TRAIL_ACTIVATE_PCT NameError still open; trail-arm timeout verdict pending). Order: NameError triage > this fix > 16-signal audit.

### Measurable goal
- Universe scanned: 87 → 129 tokens (+48%)
- grind-breakout+ trades/7d: 0-1 → baseline + whatever the 42 new tokens produce
- Zero new losses attributable to the fix in first 7d (blacklists still hold)

BY: ceo-strategic

## CEO Status — 20261012T174723Z
### Health: pipeline=active guardian=active open_pos=0
### Numbers: 24h 21T +$0.10 42.9% | 7d 123T +$1.21 39.8%
### Findings: Clean — both services active, 0 open, 7d PnL improved (+$0.84→+$1.21 vs CURRENT.md). Rotating Q (accumulation coins): coin_tracker fresh (29s), 83/88 coins in accumulation, 4 markup. Highest-predictive accumulation: BTC pred 58.1, ZRO 55.9, HYPER 53.8, FOGO 54.9, LTC 54.3 — 10 coins also flag LONG setup (PONS, GMT, ALT, RESOLV, STX, WLFI, ZORA, SAND, kBONK, kFLOKI). 7d WR 39.8% still well under 50% Oct 15 goal. No new error alerts since 15:00 UTC; disk 83%.
### Recommendation: none — wait on trail-arm GO + Oct 13 deliverables (Reputation 2a, Wyckoff shadow).

## 2026-10-12 — RR Engine Hard Block: Lowered 0.70 → 0.55

**Decision: Option A (softened) — lowered `RR_ENGINE_CONF_HARD_BLOCK_RR` from 0.70 to 0.55.**

### Data Verified (ran myself, not trusted from report)
- 24h: 17T, +$0.17, 47.1% WR
- 7d SHORT: 21T, +$0.21, 28.6% WR (barely profitable)
- 7d LONG: 102T, +$1.00, 42.2% WR
- Log analysis: 1871 total RR hard blocks. SHORT blocks: 386 at R:R 0.00–0.49, **308 at R:R 0.50–0.69** (the marginal zone killing dump SHORTs)

### Why Not Full Removal (Option A pure)
Removing entirely would let R:R 0.35 trades through with 0.70x — the log shows 386 SHORT blocks in that range. Those are genuinely bad (risking 2–3x for 1x reward). 0.55 keeps them blocked.

### Why Not Conditional (Option B)
Requires threading signal-quality context (confluence + trend alignment status) into `rr_confidence_multiplier()` — non-trivial code change across two files. Ponytail says: try the one-constant change first.

### Implementation
- `hermes_constants.py:3902` — `RR_ENGINE_CONF_HARD_BLOCK_RR = 0.55`
- Marginal setups (R:R 0.55–0.69) now get 0.70x penalty (deprioritized in hotset) instead of 0.0x kill
- Other filters unchanged: confluence gate, chop gate, RSI floors, trend alignment

### Risks to Monitor (48h)
- SHORT WR could drop below 28.6% if marginal R:R trades lose money
- If SHORT PnL turns negative, revert to 0.70
- If SHORTs still not firing, lower further to 0.45 or remove entirely

### Expected Impact
- More SHORT signals survive scoring during dumps
- Marginal setups rank lower (0.70x) but aren't eliminated
- Net effect: +5–15 SHORT trades/week in the 0.55–0.69 R:R band

---

## CEO Decisions — Gate Conundrum Package (D1–D6) — 2026-10-12 ~20:40 UTC

Package: T decision request. Plan `plans/2026-10-12_gate-conundrum-deadlock-plan.md`; adversarial verdict `brain/verdicts/2026-10-12_deadlock-gate-verify.md` (commit 49cc558c; auditor's own code + raw tables in /tmp/audit/ — files no longer present, log data frozen 2026-10-12 19:28 UTC). Context: extends Oct-8/9 gate counterfactual audit (55 gates, 78% no-edge, BTC-CHOP-GATE sole Bonferroni survivor) + D3/D4 instrumentation already live. 0 config changes made by the package; 0 trading config changes made by these decisions (D4 approves a future constant change — the constant itself is NOT touched here).

PG context at decision time: 24h 18T +$0.05 | 7d 122T +$1.48 | 1 open.

### Decisions (lead)

| Item | Verdict | Class |
|------|---------|-------|
| D1 — R1 blocked-signal shadow trader | **GO** | instrumentation |
| D2 — R2 gate registry + shadow-first policy | **GO** | process |
| D3 — R3 claim-hygiene standard | **GO** | process |
| D4 — R4 PUMP-CHAIN-VEL deadband | **GO** | bug-fix (1 constant + 3 comparison sites) |
| D5 — R5 evidence-column audit | **GO** | read-only audit |
| D6 — Guardrails | **CONFIRM** | standing rules |

### D1 — R1 shadow trader: GO

Ratify. Instrumentation-only; fits the established D3 (expiry_shadow) / D4 (BLOCKED log format) pattern. Existing infra: `gate_shadow.py` (12,483 events recorded since 10-04, hourly timer live) + `expiry_shadow.py` (30min timer live) — both standalone log/DB parsers, zero code in the trading path.

**First target confirmed: LONG-NEUTRAL-CHOP.** First seen 2026-10-11 04:15 (2 days old). It blocks chop-LONGs — the system's single best cohort (C3: +$3.28/2wk, WR 53.7%). It shipped hours after AIXBT/INJ/USELESS losses, unmeasured. Its gate has bypasses (BTC above EMA300, coin-own-momentum vel>0.3+SMA, strong-confluence+trend), so the shadow must capture the actual blocked set from log lines, not simulate from scratch. If the blocked cohort's counterfactual PnL is positive over 14d → remove the gate on data at the Nov 6 re-audit. If negative → keep. Either way, we get the answer instead of arguing.

**Implementation direction:** extend `gate_shadow.py`'s closer to simulate the real exit stack (SL/TP/trailing from hermes_constants) on blocked signals, producing per-gate counterfactual PnL in $ over 14d. The current closer uses signal_outcomes forward-returns join — adequate for ranking but not for a dollar-denominated gate-removal decision (C6 noted the markout-vs-realized-PnL divergence). Don't fork a new system; extend the existing one.

**⚠️ SIDeways FIND (blocking for R1, pre-existing bug):** gate_shadow recorder has been SILENTLY DEAD since the 2026-10-10 20:48 log rotation. Offset file = 176,599,955; current pipeline.log size = 43,429,899. Seek past EOF records nothing. ~2 days of blocks missed — including the entire lifetime of LONG-NEUTRAL-CHOP (first seen 10-11). The recorder's last event is 2026-10-10 19:59. Fix: reset offset on rotation detection (or size-check before seek). Must be fixed as R1 v1 prerequisite. Severity: HIGH (the shadow data R1/R2 depend on has a 2-day hole).

### D2 — R2 gate registry + shadow-first: GO

Ratify. Registry = single source of truth per gate: first-seen date, evidence grade (trade-level / counterfactual / shadow), n, effect, last-verified. Live gates populated from the verified C1 census (the verdict file has correct first-seen dates for every gate). New hard-veto gates ship shadow-first 14d before enforcement.

The LONG-NEUTRAL-CHOP casualty is the proof case: a 2-day-old gate shipped on intuition, attacking the best cohort, with zero measurement. A first-seen date field + shadow-first rule would have caught both the gate's youth and its counterproductive aim before it went live. Retroactive registry entries for the three young live gates: SHORT-RSI-HARD-FLOOR (first seen 2026-10-12 00:33), LONG-NEUTRAL-CHOP (2026-10-11 04:15), CONTINUUM-BULL (2026-10-05 21:23). All three hit the 2-week minimum by Nov 6.

### D3 — R3 claim-hygiene standard: GO

Ratify. Standard for any future gate proposal: (1) episode-level counts, not raw lines (re-logging inflates ~9×); (2) first-seen dates with explicit window; (3) null-model check for any "always/never" statistic (the 99.7% both-direction-blocked stat was 1 hour BELOW the coin-flip null); (4) direction-signed counterfactual. Lives in brain/SOPs.md.

The deadlock episode is the textbook case: three separate claim-hygiene failures (irreproducible census windowing a <24h gate as a 2-week blocker; vacuous pincer stat; imputed null cohort manufacturing "+$3.53 for RSI≥45") nearly drove a gate-removal program. One of the three was a fabricated number. Standard costs nothing to follow and kills bad proposals at the first step.

### D4 — R4 PUMP-CHAIN-VEL deadband: GO (bug-fix class)

Approve. vel<0 → vel<−0.3% (LONG); vel>0 → vel>+0.3% (SHORT). This is a measurement-floor fix with direct in-system precedent: `SHORT_VEL_FILTER_VEL_THRESHOLD = 0.3` since Aug 16, explicitly justified as "was blocking SHORTs on noise" (hermes_constants.py:1004). The PUMP-CHAIN-VEL founding claim ("ALL 10 losses neg vel, ALL 26 winners pos") is falsified — AIXBT was a +4.59% winner entered at vel −0.21%, blocked by the zero deadband.

**Implementation note (scope correction to plan):** not purely one-constant. The current code hardcodes `0` at three sites: signal_compactor.py:4454 (LONG main), :4480 (SHORT main), :5102/5105 (RESCUE path). Add `PUMP_CHAIN_VEL_DEADBAND_PCT = 0.3` to hermes_constants.py (this GO satisfies line 2); change three comparisons to use it. This also harmonizes with `PUMP_CHAIN_VEL_30M_MIN = -0.3` already used by pump_chain_long.py:203 — the signal module and the compactor currently disagree on the LONG threshold (−0.3 vs 0), which is itself a latent inconsistency. Still bug-fix class, still a small diff, still reversible.

### D5 — R5 evidence-column audit: GO (read-only)

Commission. Independently recompute every evidence column cited in hermes_constants.py comments with cohort statistics. Priority order: (1) columns behind comment-justified threshold constants — entry_rsi_14 is known-bad (r=0.33, mean|Δ|=12.9 pts, 4-day hole whose profitable cohort was imputed into the "+$3.53" claim); (2) exec-time gate inputs; (3) exit-engine features. DO-NOT-MODIFY respected — findings flagged for T/CEO, no edits.

The entry_rsi_14 rot proves the class: constants comments built on an unreliable column manufacture false precision. Find the next one before another threshold gets justified on a broken column. Read-only = zero risk; the audit's output feeds the Nov 6 re-audit alongside R1 shadow data and R2 registry grades.

### D6 — Guardrails: CONFIRM

1. **SHORT-RSI-HARD-FLOOR stays for chop.** Chop<45 shorts: WR 36%, −$4.56/30d, consistent across both RSI derivations (stored + independent candle-recompute). This is the one short-gate with real trade-level backing. Trend-side stays open (no bleed, wide CIs, n=22 — needs more data). No removal. If ever changed, make it chop-conditional (mirror SHORT-RSI-FLOOR's bear-structure override, 1,470 uses in window).
2. **No gate removals on intuition or <2-week windows.** Nov 6 re-audit (standing from D2 of the gate audit) remains the decision gate. Shadow counterfactuals (R1) + registry grades (R2) feed the readout. The deadlock episode is the cautionary tale: a vacuous stat + a <24h-old gate nearly drove a removal program.
3. **DO-NOT-MODIFY / protected flags intact.** 0 trading config changed by this package. D4 approves a future constant addition (PUMP_CHAIN_VEL_DEADBAND_PCT) — the constant itself is NOT added by this decision; implementation is a separate delegated task. hermes_constants.py line 2 honored.

### Delegation (on T's ratification of this package)

1. **bug_hunter: R1 v1** — (a) fix gate_shadow rotation bug (offset reset on rotation/size-check), (b) extend closer to exit-stack simulation, (c) first target LONG-NEUTRAL-CHOP counterfactual. Instrumentation-only; no trading-path edits.
2. **bug_hunter: R4** — add PUMP_CHAIN_VEL_DEADBAND_PCT=0.3 + change 3 comparison sites (compactor main LONG/SHORT + rescue path). py_compile + dry-run. One-constant + three-line diff.
3. **signal_analyst: R2** — build gate registry (brain/gate_registry.db or JSON), populate from C1 census + retroactive entries for 3 young gates, wire into weekly report.
4. **brain_auditor: R5** — evidence-column audit, read-only, prioritized list from hermes_constants.py comment citations. Findings to brain/verdicts/.
5. **R3 standard** — write to brain/SOPs.md (parent or signal_analyst, whichever touches SOPs next).

### Questions for T

1. R1 implementation: extend gate_shadow closer (recommended — same recording infra, richer closer, no fork) vs. build a separate blocked-signal paper trader? Confirm extend.
2. gate_shadow rotation bug is pre-existing infra debt, not from this package. Fixing it is a prerequisite for R1 AND R2 (registry first-seen dates need live shadow data). Priority: ahead of R1 v1 proper. Confirm.

BY: ceo-strategic (acting CEO session, T decision-request package)

## CEO Deep Run — 20261012T205810Z

**Decision:** NO-OP (guard check). Directed brief was a test: "Test brief — guard check. Ignore." No work items dispatched, no live files touched.

**Evidence:** Brief scope block contains only the ignore instruction; no directed task given.

**Work items dispatched:** None.

**Result files:** None (only checkpoint 20261012T205810Z-decision.md).

**Metric checkpoint (7d):** N/A this run — baseline unchanged. Next real deep run picks up from CURRENT.md and prior checkpoints.

## CEO Status — 20261012T214723Z
### Health: pipeline=timers-active (service inactive, by design — compactor/pump-hunter/watchdog timers all firing <2min) guardian=active open_pos=0
### Numbers: 21T −$0.20 38.1% | 7d 128T +$0.86 39.1% (DB self-query)
### Findings: Rotating Q (accumulation): coin_tracker Wyckoff labels 88/95 coins "accumulation" as of 21:48 UTC — 93% uniform label gives no discrimination for an accumulation-phase signal; scores updating on schedule (18min ago). 24h dipped +$0.09→−$0.20 since 18:50; 7d still ≥$0. Kill switch LIVE=true, CONFLUENCE_REQUIRED=true, 0 new errors since 20:48 (all-clear).
### Recommendation: Wyckoff phase detector likely under-calibrated (near-all-accumulation) — signal_analyst should sanity-check phase thresholds before building any accumulation-transition signal; also CEO ratify/revert the 2 trail-arm enables still pending from 18:50 escalation.

## CEO Deep Run — 20261012T230504Z

**Decision:** NO-OP. Directed brief was an empty placeholder ("x") — no question, no work item. Same guard-check class as run 20261012T205810Z.

**Evidence:** SCOPE block reads verbatim "--- DIRECTED BRIEF ---\nx\n--- END BRIEF ---". No directed task to answer; inventing scope would violate the directed-brief rule.

**Work items dispatched:** None.

**Result files:** None (only checkpoint 20261012T230504Z-decision.md).

**Metric checkpoint (7d):** N/A this run — no changes. Baseline unchanged from 21:47 UTC status: 24h 21T −$0.20 (38.1%), 7d 128T +$0.86 (39.1%). Open escalations (trail-arm ratify, Wyckoff shadow rule Oct 13) remain for the next STATUS run or a directed deep run with a real brief.

## CEO Deep Run — 20261012T231259Z

- **Decision:** NO-OP. Directed brief was the empty placeholder "x" — no question or work item. Inventing scope would violate the directed-brief rule (it REPLACES default pick-your-own scope). Fourth identical guard today; prior runs 205810Z, 230504Z, 230650Z all NO-OP'd the same empty brief.
- **Evidence (self-verified ~23:13 UTC):** 24h 22 closed, −$0.23, 36.4% WR. 7d worst: volume-breakout-long+ −$0.51 (25% WR), trend-ride+ −$0.33 (20% WR). 7d best: pump-chain+ +$0.75, pump-chain- +$0.54. CURRENT.md escalations (trail-arm ratify/revert, Wyckoff shadow rule due Oct 13) remain open but out of scope for an empty directed brief.
- **Work items dispatched:** none.
- **Result files:** none (no subagents).
- **Metric checkpoint (7d):** no change made — track 7d WR ≥50% goal and trail-arm ratify/revert escalation on next directed run with real scope.

## CEO Deep Run — 20261012T232327Z

### Decision
**Assessed RR Engine Smart Upgrades plan (`plans/2026-10-13_rr-engine-smart-upgrades.md`) with modifications.** Plan diagnosis is correct (engine measures R:R at worst moment during momentum), but Upgrade 1 as written (velocity-based TP projection) is TOO RISKY. Dispatched a REFRAMED Upgrade 1: momentum S/R filtering — during confirmed velocity, skip nearby S/R levels for TP selection (they are being blown through), fall through to ATR-based TP or next further structural level. Same effect, no forward projection, no overshoot risk. Flag `RR_ENGINE_MOMENTUM_SR_FILTER` defaults OFF (shadow first, zero live impact).

### Evidence (verified via DB self-query + log analysis, ~23:23 UTC)
- 7d: 124 closed, +$0.92, 37.9% WR. 24h: 22 closed, −$0.23, 36.4% WR (first negative day-net since Oct 6).
- RR engine: 1,978 HARD BLOCKED events (mult=0.00, avg R:R=0.46, n=1341), 4,181 PENALTY events, 392 BOOST. Hard blocks are LIVE via `RR_ENGINE_CONF_SHADOW=False`.
- BTC dump verified: 83,136→81,800 (−1.6%). Plan's claimed velocity of −0.3%/candle was inflated — actual 5m velocity was 0.022%/candle, below the plan's own MIN_VELOCITY=0.1 threshold.
- Critical flaw found: Plan's Upgrade 1 contradicts BANANA SHORT lesson in AGENTS.md — shorting at RSI 16.1 (extreme oversold) is exactly the pattern that lesson warns against. The 20 "crushed" SHORTs may have been correctly blocked.
- No counterfactual data exists — we do not know if blocked signals would have won.

### Answers to brief questions
1. **Right approach?** Diagnosis yes, prescription no. Safer fix: momentum S/R filtering (skip nearby levels) instead of TP projection (extrapolate forward).
2. **Implementation order?** Momentum-aware is right priority, wrong form. Ship reframed version in shadow first. Upgrades 2–4 deferred until shadow data validates.
3. **Risks?** Overshoot (plan example projected 81,080, BTC only reached 81,800), contradicts BANANA SHORT lesson, velocity noise on 5m, no counterfactual data, chop trap.
4. **Constants?** MIN_VELOCITY=0.1 too absolute — reframed version uses ATR-relative (0.5×ATR). TP_MAX_EXTENSION=2% aggressive for BTC. TF profile min_rr values unvalidated.
5. **Add/remove?** ADD: momentum S/R filtering. REMOVE/DEFER: Upgrade 3 (double-counts with confluence boost). KEEP: Upgrades 2 and 4 for future runs.

### Work items dispatched
- **Result 1** (`20261012T232327Z-result-1.md`): Momentum S/R filter in `compute_structural_rr()`. Files: `scripts/risk_reward_engine.py` (+67 lines), `scripts/hermes_constants.py` (+9 lines, 4 new constants). Flag OFF by default. Verified: import OK, engine works with flag off/on, no regression on LONG/SHORT. Synthetic test: filter skipped 16 nearby levels, fell through to ATR TP. Committed as `ab1c3083`.
- Code review (subagent): no critical issues. Warnings: ATR timeframe mismatch (1h ATR vs 5m velocity — filter stricter than intended, tune on enable), some call paths do not pass candles_5m (filter inactive there, acceptable for shadow).

### Metric checkpoint (measure in 7d)
- **Hard-block rate**: count of `RR HARD BLOCKED` events per day (currently ~100–190/day). Expect: no change until flag enabled.
- **Shadow log**: when flag is temporarily enabled, count `MOMENTUM SR-FILTER` activations and analyze what would have been allowed vs blocked. Promote to live only if shadow data shows net-positive counterfactual.
- **Win rate**: 7d WR baseline is 37.9%. Target after promotion: 40%+ (measure at 7d post-enable).
- **SHORT PnL**: 7d SHORT PnL baseline. Target: non-negative if filter correctly unblocks momentum SHORTs.
- **BANANA guard**: track whether any promoted trade enters at RSI < 20 (SHORT) or RSI > 80 (LONG) — these should remain blocked regardless of R:R.

### Deferred (future runs)
- Upgrade 2: Timeframe-aware SL/TP (signal files already emit `timeframe` metadata, threading is straightforward but touches many files)
- Upgrade 3: Signal quality context (double-counting risk with existing confluence_mult — redesign before implementing)
- Upgrade 4: Fibonacci retracement levels in S/R map (lowest risk, reuse `hh_hl_signals.py:342-361`)

## CEO Deep Run — 20261013T000026Z (ceo-comm interactive-workflow friction)

**Brief:** 4 friction points from an external agent's conversational live-test of the ceo-comm skill. Decide + implement.

### Decisions
1. **`--wait` on deep — APPROVE (modified).** Foreground for interactive use, budget **600s** (not 1800s). On non-clean finish it prints the class + checkpoint path + jsonl path. Detached 1800s stays the automation default. Rationale: blocking a caller's turn ≤10min beats unbounded polling; an interactive budget that is 3× shorter than automation keeps the foreground path honest about what it can finish.
2. **`.exit` standardization — APPROVE.** Status now writes `class rc=N` via `ceo_classify_run`, same contract as deep/moe. Verified no script or systemd unit parses the status `.exit` as a bare integer (only SKILL.md described the dual format — and flagged it as a trap). The process exit code systemd sees is unchanged.
3. **`--force` / `--ignore-lock` — REJECT the bypass; MODIFY staleness instead.** The lock exists to stop a CEO run editing `hermes_constants.py` while a human session is live; a convenience flag weakens exactly that. Root cause of the friction was diagnosed as mtime-only staleness: a dead CEO owner behind a <1h-old lock reads as "fresh". New `ceo_lock_is_stale()` is owner-aware — a `ceo-*` lock whose embedded PID is dead is stale regardless of age; human/unknown owners keep the age check. No bypass shipped.
4. **"consult" mode — APPROVE as a thin 4th runner**, `run_ceo_consult.sh`, not a `--consult` flag on deep. Deep's lock+detach+classify flow is battle-tested and complex; bolting "skip all that" onto it is more code and risk than a standalone read-only script reusing `ceo_lib` + the base prompt. Consult: in-process, 300s, brief arg required, **no lock, no report write, stdout only**.

### Evidence
- Read all 3 runners + `ceo_lib.sh` + SKILL.md + the last 4 checkpoints before deciding.
- systemd: `hermes-ceo.service` is `Type=oneshot`, `TimeoutStartSec=3600`; the `.exit` FILE format is independent of the process exit code it sees.
- Lock owner tag format is `ceo-<label>-<ts>-<pid>`; stale auto-remove already existed for `age >= 3600s`, which is why a dead owner with a fresh mtime was invisible.

### Verification (run after the implementing session was killed)
The deep session was killed after editing all four scripts but before touching SKILL.md or appending this report. Post-hoc verification by the orchestrator:
- `bash -n` passes on `ceo_lib.sh`, `run_ceo.sh`, `run_ceo_deep.sh`, `run_ceo_consult.sh`.
- consult: refuses with no brief (rc=4), rejects `/tmp` and missing briefs (rc=4), live smoke returned `CONSULT_OK`, left no lock and no report write, did not leave its brief behind.
- `--wait`: parses order-independently with the brief arg, drops budget to 600s, takes the foreground path.
- owner-aware lock: synthetic dead-CEO-PID lock → stale (auto-cleared); alive-PID lock → not stale.
- status `.exit` now writes `class rc=N`.
- SKILL.md updated (consult documented, `--wait` documented, `.exit` contract unified, no-bypass lock policy and owner-aware staleness documented, brief-arg interface promoted to the primary deep command).

### Known open (deliberately NOT fixed here)
**Deep-run budget problem.** A prior deep run spent its full 1800s on investigation and died before dispatching subagents. That is an agent-behavior failure, not a runner-UX one, and its fix surface is `ceo_prompt_deep.md` (investigation-time hint) rather than the shell. Mixing it into this change risked breaking the tested deep flow. Tracked as a separate item.

### Metric checkpoint (measure in 7d)
- Count of interactive deep runs that complete within the 600s `--wait` budget (expect: brief-scoped ones finish; open-ended investigation will not — that is the signal to split investigate from dispatch).
- Count of consult invocations vs deep invocations (expect consult to absorb the "give me your opinion" load that was overloading deep).
- Count of manual lock removals (expect: near zero, now that dead CEO owners self-clear).

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

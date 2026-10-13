# Recalibration Decision — 2026-10-13

**Status:** APPROVED — implement in order below, each with independent revert trigger.
**Context:** System severely throttled (not fully frozen — 16 trades/24h, but 3W/16T −$1.20). WR 36.7% Oct 6-12 vs 53.9% Sep 28-Oct 5. Frequency halved (32→18/day).

## Evidence corrections (verified from brain DB + pipeline logs)

The report had three factual errors — decisions below account for the corrected numbers:

1. **"Profitability didn't improve" is FALSE.** PnL: Sep 28–Oct 5 = **+$0.15** (256T, 53.9% WR) → Oct 6–12 = **+$0.46** (128T, 36.7% WR). Tight filters cut losers harder than they cut winners — profit per trade nearly tripled. The freeze is a *frequency* problem, not a *profitability* problem.
2. **Blocker distribution was wrong.** Actual 24h counts: CONFLUENCE 294 blocks (2215 passes — 12% rate, NOT the main killer), RR HARD BLOCKED 133, SHORT-CONTINUUM 331, MAXXED 240, CONTINUUM-BULL 234, PENALTY-BLOCK 148, EXEC-RSI-HARD-FLOOR only 2. The RR engine is the #1 *hard* killer; CONTINUUM+MAXXED together are the volume killers.
3. **return_exhaustion_short is ALREADY in STANDALONE_BYPASS** (hermes_constants.py:2924). It has **1 closed trade ever (0W −$0.11)**. The fix is disable, not bypass.

Current BTC state at decision time: **BULLISH** (continuum score 98-100, STRONG_POS). CONTINUUM-BULL blocking SHORTs is *correct* behavior right now — not a bug.

---

## Decisions

### 1. RR Engine regime exemption — ✅ APPROVED

**Value:** In confirmed structure (LEAN_BEAR+BELOW-EMA300 for SHORTs / LEAN_BULL+ABOVE-EMA300 for LONGs), `RR_ENGINE_CONF_HARD_BLOCK_RR` effective threshold **0.55 → 0.35**. In chop, stays 0.55.

- 0.35 not 0.30 — Grade D multiplier (0.5x) already punishes these; 0.35 still blocks true garbage.
- Rationale: regime confirms direction; R:R double-gates. 133 hard blocks in 24h, nearly all LONGs in a bull market (BABY R:R 0.44, SUPER R:R 0.53).
- Implementation: `risk_reward_engine.py:1091` — check regime before applying threshold. Move effective threshold to a new constant `RR_ENGINE_CONF_HARD_BLOCK_RR_CONFIRMED = 0.35` in hermes_constants.py.
- **Revert trigger:** ≥10 regime-exempted trades (RR 0.35-0.55) close at aggregate −$1.00 or worse within 7 days → restore 0.55 globally. Log every exempted trade with tag `[RR-REGIME-EXEMPT]`.

### 2. SHORT_RSI_HARD_FLOOR: 45 → 35 — ✅ APPROVED (with scope fix)

**Value:** Both `SHORT_RSI_HARD_FLOOR` and `SHORT_RSI_FLOOR` **45 → 35**. RSI < 35 SHORT still blocked.

- The report only named HARD_FLOOR, but `SHORT_RSI_FLOOR=45` (line 898) is the primary gate — lowering only HARD_FLOOR changes nothing. Both must move.
- 35 not 30 — BANANA lesson (shorting RSI 10 = falling knife) + measured 40-45 bleed band (37T −$2.28). 35 opens the moderate-dump zone while keeping extreme oversold blocked.
- The "no bearish override" design was correct in chop; in confirmed dumps it blocks the philosophy ("every dump is a SHORT").
- **Revert trigger:** 30d rolling: SHORTs with entry RSI 35-45 aggregate PnL < −$1.00 OR WR < 40% with n≥15 → restore 45. Log entry RSI on every SHORT fill.

### 3. MAXXED_ATR_PCT_THRESH: 4.0% → 6.0% — ✅ APPROVED

**Value:** `MAXXED_ATR_PCT_THRESH = 6.0`. `MAXXED_BLOCK_ENABLED` stays True. `MAXXED_REGIME_LOG` stays True (counterfactual data collection).

- 4.0 was calibrated to a lower-vol regime; ATR routinely hits 5-6% now. BLUR blocked at 6.04% for hours.
- Position sizing already scales with ATR/leverage — risk per trade bounded.
- **Revert trigger:** 14d rolling: trades with entry ATR 4-6% (newly unblocked band) aggregate PnL < −$1.50 → restore 4.0. The shadow log already tags these.

### 4. Penalty multiplier floor: 0.3 → 0.5 — ✅ APPROVED (Option A)

**Value:** `signal_compactor.py:2143` `_mult_floor = 0.3 → 0.5`. Also hoist to hermes_constants as `PENALTY_MULT_FLOOR = 0.5` (conventions: no hardcoded constants).

- Option B (remove one multiplier) requires knowing which multiplier to cut — more analysis, more delay. Floor raise is one number, global, and directly addresses the failure mode: floored-to-0.3 signals still below the 40% PENALTY-BLOCK threshold.
- At 0.5, floored signals clear the 40% exec threshold. Multipliers that genuinely stack high still bite (product > 0.5 unaffected).
- **Revert trigger:** 7d: signals that fire *only because* of the 0.5 floor (product was 0.3-0.5) close 0W/n≥5 → revert floor to 0.3. Tag these `[FLOOR-RELIEF]` in logs.

### 5. return_exhaustion_short — ✅ DISABLE (not bypass)

**Value:** `RETURN_EXHAUSTION_SHORT_ENABLED = False` (hermes_constants.py:3401).

- Already in STANDALONE_BYPASS (line 2924) — the report's proposed fix is a no-op.
- 1 closed trade ever: 0W −$0.11. Zero edge, burns signal-slot and confluence-gate cycles.
- **Revert trigger:** none — it has no edge to regress to. Re-enable only with a fresh 30d backtest showing positive PnL.

---

## Recalibrations NOT approved (and why)

- **CONTINUUM-BULL / SHORT-CONTINUUM:** Correct behavior. BTC is bullish — blocking SHORTs is the filter doing its job. These blocked 565 attempts in 24h because the market is one-directional, not because they're broken.
- **CONFLUENCE gate:** 12% block rate (294/2509). Not the freeze driver. SYRUP ichimoku+ single-source block is a per-signal bypass question, not a gate-recalibration question — handle via STANDALONE_BYPASS review separately if ichimoku+ has a proven solo edge.
- **CHASE filter:** No significant recent block volume. Leave alone.
- **PENALTY-BLOCK threshold (40%):** Floor raise (#4) addresses the cause; lowering the threshold would compound with the old floor and mask the problem.

## Implementation order

| # | Change | Risk | Files |
|---|--------|------|-------|
| 1 | `RETURN_EXHAUSTION_SHORT_ENABLED = False` | None (dead signal) | hermes_constants.py |
| 2 | `MAXXED_ATR_PCT_THRESH = 6.0` | Low (sizing scales) | hermes_constants.py |
| 3 | `PENALTY_MULT_FLOOR 0.3→0.5` | Low | signal_compactor.py + hermes_constants.py |
| 4 | `SHORT_RSI_FLOOR` + `SHORT_RSI_HARD_FLOOR` 45→35 | Medium | hermes_constants.py |
| 5 | RR regime exemption (0.35 confirmed / 0.55 chop) | Medium (code change) | risk_reward_engine.py + hermes_constants.py |

**After each change: restart pipeline** (stale-code lesson). Order is lowest-risk-first so a bad step is caught before the next lands.

## Cross-cutting revert

Any change causing **−$2.00 aggregate over 24h from newly-unblocked trade classes** → revert that specific change immediately, keep the rest. Tag every newly-allowed trade with which recalibration unblocked it.

## Note on the WR drop

WR fell 53.9%→36.7% *after* the Oct 6-7 tightening, but PnL rose. This is consistent with the filters cutting mid-tier winners and losers alike, leaving fewer but (per unit) better trades — until volume dropped to near-zero. The recalibrations above restore frequency without returning to the pre-Oct-6 regime: every loosening has a measured revert trigger and a log tag for counterfactual audit.

---

# RSI Consistency Normalization (Cutler→Wilder) — 2026-10-13

**Decision: LEAVE AS-IS (Option 2). No shadow rollout. Reject limit=20.**

## Rationale

1. **The limit=15 "normalization" is a mathematical no-op — the shadow rollout would have nothing to measure.** Wilder with exactly 14 deltas (15 closes) skips the smoothing loop entirely (`range(period, len(gains))` = `range(14,14)` = empty, rsi_utils.py:105) and reduces to `sum(gains)/14` — the identical formula to the Cutler block at signal_schema.py:510-512. The audit's 2000/2000 match is code equivalence, not an empirical coincidence. Collecting 7 days of counterfactual for a no-op is pure overhead.

2. **The only real delta a swap would introduce is the `is_closed=1` filter, not Wilder.** `_get_closes_from_candles_1m` (signal_schema.py:428) includes the in-progress candle; rsi_utils excludes it. That is a candle-set change on a fallback analytics field — near-zero value, and not what anyone asked to normalize.

3. **limit=20 is a tuning change, not a consistency fix.** It shifts 619/622 live values (151 by >10 pts) and touches decider_run exec-time RSI ceilings/floors + drift checks. Zero evidence the extra smoothing benefits anyone. If proposed again, it must arrive as a tuning proposal with a backtest showing enrichment-RSI consumers improve — via the automatic-implementation shadow pattern. Not as a consistency ticket.

4. **Blast radius of the status quo is already contained.** Money-gating RSI comes from rsi_utils (`_ctx_gate_get_rsi` → decider_run.py:950-951; exec-time at 2023-2029); SHORT path fails closed on None. The enrichment RSI (signal_schema.py:512) is a shared fallback + `_signal_metadata` analytics only. Divergence is loudly documented in-code at signal_schema.py:478-504.

5. **Opportunity cost.** 7 days of collection + flip risk + review cycles for cosmetics on a fallback field, while engineering attention is needed on the recalibration plan above.

## Accepted residual (known, documented, no money impact)

- Enrichment `rsi_14` (feeds `entry_rsi_14` / `_signal_metadata`) remains equal-weight Cutler over a live-candle-inclusive 15-close window. Exec-time RSI remains Wilder over closed candles. Consumers reading metadata RSI get a slightly different number than the exec gate saw — by design, until a real tuning case exists.
- Round RSI values (0/20/…/75/100) remain in metadata. They are genuine 3:1 gain:loss ratios from tick quantization — not clamps, not thin data.

## Shipped with this ruling

- **rsi_utils.py:62 cache key omitted `limit`** — latent footgun: any future caller passing a non-default limit would silently share/poison cache entries with default-limit callers (wrong-window RSI). Added `limit` to the cache key. Zero behavior change today (all live callers use the default 20). Also fixed stale docstring (said "defaults to 1m, 15 candles" — default is 20).
- **signal_schema.py divergence comment updated** to record this ruling so the "must go through SHADOW ROLLOUT" mandate from the 2026-10-13 audit is not re-activated by a future agent.

## CEO Status — 20261013T054724Z
### Health: pipeline=inactive(timer-ok) guardian=active open_pos=3
### Numbers: 24h 18T -1.09 22.2% | 7d 126T 0.87 38.9%
### Findings: 24h flipped negative since 18:50 (+$0.09→−$1.09, WR 42→22%); error log shows 4x mark_signal_executed failures + disk hit 85% warn threshold. Proactive Q: new errors — no CRITICAL, all warn-class.
### Recommendation: Investigate the 4x mark_signal_executed failure returns (possible unclaimed/lost signals) and run DB prune (disk 85%, goal <80% Oct 14).

## CEO Status — 20261013T094726Z
### Health: pipeline=active guardian=active open_pos=4
### Numbers: 24h 26T -$0.47 26.9% | 7d 136T +$1.67 39.0%
### Findings: 24h WR 26.9% (brain_auditor flagged CRITICAL; 7d PnL still +$1.67). Disk 85% (DBs 6.3G, no gzip left). 2 unratified trail-arm enables still awaiting CEO decision. Rotating Q (coin_tracker scores): agg_scores fresh (09:48 UTC) but ~20 coin tables empty and 6 stale >14d (AZTEC/BCH Sep 27, ENA Sep 14, HEMI/NOT/CASHCAT/ICP partial) — registry drift, not a timer failure.
### Recommendation: CEO ratify or revert the 2 trail-arm enables before Oct 15 soak review; investigate coin_tracker empty-table registry for dropped tokens.

## CEO Status — 20261013T134726Z
### Health: pipeline=inactive(timer ran 30s ago, normal exit) guardian=active open_pos=0
### Numbers: 24h 47T -$1.11 27.7% | 7d 157T +$1.03 37.6%
### Findings: 24h WR collapsed to 27.7% (brain_auditor flagged 15% at 07:38, now 27.7%); disk 85% (coin_tracker.db 3.3G, candles.db 2.8G); 2 unratified trail-arm enables (bb-squeeze + pump-chain 45m) still awaiting CEO decision — soak deadline Oct 15; coin_tracker timer healthy (last 13:30, next 14:00, scores updating).
### Recommendation: CEO must RATIFY or REVERT the 2 trail-arm enables before Oct 15 soak deadline (one-line each in hermes_constants.py); also set DB retention policy for coin_tracker.db/candles.db before disk hits 90%.


---

## CEO Deep Run — 20261013T155406Z

**Mode:** directed brief (8-item UX feedback from external live-tester) — **decide + checkpoint only, no implementation** (per brief: author implements after confirming with user).

**Checkpoint:** `automation/ceo/checkpoints/20261013T155406Z-decision.md` (FINAL — rulings, evidence, plan, files, rollback).
**Work items dispatched:** NONE (decide-only brief — zero subagent edits by design).
**Result files:** NONE.

### Decision — rulings on all 8

| # | Item | Ruling | Core rationale |
|---|------|--------|----------------|
| 1 | ceo-comm missing from skill catalog | **REJECT-as-diagnosed / MODIFY** | Forensics on the tester session (`/root/.dsh/sessions/.../session-e0ca88f3…`): DSH `skill()` failed **12/12** calls — ceo-comm, trade-analysis, post-change, signal-lab, bug-hunter, own-conclusions, add-signal, volatility-breakdown, trading-decisions all returned "unknown or no longer available". This is a **DSH harness-wide skill-loader failure**, not a ceo-comm registration gap. opencode resolves ceo-comm live (present in this session's catalog). Renaming the skill or adding a skills.json index would fix nothing. **Ship:** docs fallback in SKILL.md ("if skill() returns unknown, `cat` the SKILL.md at `skills/shared/ceo-comm/`") + the 4-runner decision table the tester requested. **Log separately:** DSH skill-loader investigation (which dir it scans; whether pointing it at the user skills dir fixes all 12). |
| 2 | Dead-pattern stub | **CLOSED** | Stub exists (`ceo_prompt.md` fail-loud banner, verified), tester endorses it unreservedly. No change. |
| 3 | Exit-0 trap | **MODIFY (small)** | `.exit` class mechanism is real and working (`ceo_classify_run`, history: ok/failed/incomplete samples). `--wait` already prints the class. Gap is doc + consult stdout — closed by items 7+1 (class line printed with final text; SKILL.md documents `.exit` as THE success signal). |
| 4 | `/tmp` ban at wrong layer (REGRESSION) | **APPROVE — option (b) + text fix; REJECT (a) and (c)** | See full ruling below. Move lock to `/root/.hermes/.run/session-active.lock`; keep the opencode `/tmp`+`/var/tmp` allow; fix stale kill-claims in 3 places. |
| 5 | Budget tight for decision briefs | **APPROVE raise — 1800→2400s; REJECT decide/dispatch split (for now)** | Exactly ONE real budget exhaustion on record (deep-20261012T192508Z, 1617s investigating, `incomplete rc=124`); all other "deaths" were permission-reject kills, now fixed by the config allow. n=1 does not justify a second runner + state handoff. 2400s caps the known worst case (investigation ~1600s + dispatch ~600s) with margin. Revisit split only if exhaustion recurs post-raise. |
| 6 | `--wait` cuts budget | **APPROVE simplify — delete the 600s special case; one 2400s knob everywhere** | Both sides heard: 600s was shipped to bound the caller's blocked turn; but the flag itself signals "I choose to block and watch", and a 600s cap that kills a run which needed ~1700s is strictly worse than waiting. Detached+tail remains available for those who do not want to block. One budget number = one knob to reason about. `run_ceo_deep.sh:71-72` becomes `BUDGET=2400` unconditionally. |
| 7 | Raw `--format json` floods stdout | **APPROVE — but consult-ONLY; brief was wrong about status** | `run_ceo.sh:95` already redirects jsonl to the log file (`>> jsonl 2>&1`) — no stdout flood there, nothing to fix. Only `run_ceo_consult.sh:103` tees raw json to the caller. Fix: jsonl → log only; new `ceo_final_text()` in ceo_lib.sh extracts the last assistant text parts; consult prints final text + `[CEO-CONSULT] class: <result>` line. Fail-soft: empty extract → print pointer to jsonl. |
| 8 | Consult opinions not persisted | **APPROVE — optional `--save`, default OFF** | Verified consult writes nothing durable today (only logs/ceo jsonl/err/exit + temp task file, removed). `--save` appends `automation/ceo/consults/<ts>.md` (brief + ruling); default off preserves the read-only invariant; keep-all retention (KB-sized files; rotate only if it ever hurts). |

### Item 4 full ruling (the regression)

**Chosen end-state: (b) + text fix.** Exact changes:
1. `ceo_lib.sh:23` → `LOCK_FILE="/root/.hermes/.run/session-active.lock"`; mkdir `.run/`, gitignore it.
2. `automation/brain-auditor/run_brain_auditor.sh:5` → same path (only other live reader).
3. `run_ceo_deep.sh:155` CONCURRENCY block: drop the false "opencode auto-rejects /tmp/* … killed instantly" claim (made false by the config allow); keep the do-not-touch instruction as session discipline, referencing the new workspace path.
4. `ceo_prompt_base.md:155`: survival warning stays TRUE for non-temp external paths (brief author's 55s `/root/.opencode` death stands); temp dirs are an explicit carve-out — "allowed but discouraged: style rule, not survival".
5. `brain_auditor_prompt.md:474`: path reference update.
6. **Do NOT touch `hermes_constants.py`** — SESSION_LOCK_FILE (line 2776) is dead code (zero script consumers); the file carries a hard no-write rule; updating a dead constant has zero functional gain.
7. **Keep the opencode config allow as-is.** Rejected (a) revert: restores the kill-on-mention grenade that murdered 172817Z (15s) and 000026Z (557s) — availability loss >> the integrity gain once the lock is out of temp. Rejected (c) narrow+deny: `external_directory` deny for a single FILE inside an allowed dir is unverified to work, and `ask` is useless headless; adds config complexity for no asset (the lock has left the zone).
8. **Do NOT broaden the config** to other paths (`/var/www`, `/etc`, …) — persona workarounds (psql, paths.py imports, systemctl without absolute paths) already cover functional needs.

**Anomaly logged (not acted on):** this session ran `grep`/`ls` against `/root/.opencode/*` paths WITHOUT dying — inconsistent with both the 2026-10-12 kill evidence and the author's recent 55s death. Do not use this anomaly to justify any permission change until independently reproduced.

### Metric checkpoint (measure in 7d)
- Deep-run budget exhaustions (`incomplete rc=124`): baseline 1/12 runs → target 0 after 2400s raise. Recurrence ⇒ triggers the decide/dispatch split reconsideration.
- Consult usage after `--save` ships: ≥1 saved consult/week means the flag earns its keep; 0 after 2 weeks ⇒ delete it.
- `.exit` class misreads (false-success reports): target 0 — class now printed on stdout for consult and `--wait`, documented in SKILL.md.
- DSH skill-loader: follow-up task filed; target = all 12 failing skills resolve or root-caused within 7d.

### Tester keep-list — all honored
Decision table ships in SKILL.md (item 1). ⛔ banner stays (item 2). Checkpoint-first + `.exit` class stay (items 3-4). Consult re-derivation of caller numbers is mandated in the consult task template already — no change.

**Shipped order (severity, not the tester's):** 4 → 5+6 → 7 → 8 → 1-docs → (2,3 closed).

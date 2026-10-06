# Independent Audit — Ride-It Exit (post-fix)

**Auditor:** independent verification agent (fresh read, no reliance on prior reports)
**Date:** 2026-10-06 02:40–03:00 UTC
**Scope:** `scripts/ride_it_exit.py`, `scripts/position_manager.py` (ride_it invocation, `_match_exit_config`, `_is_ride_it`, UNIVERSAL_MAX_HOLD, HARD_MAX_LOSS), `scripts/hermes_constants.py` (RIDE_IT_*, SIGNAL_EXIT_CONFIG, PROFIT_MONSTER_BYPASS_SIGNALS), PostgreSQL brain DB, SQLite candles DB, pipeline logs. Prior bug-hunter report read but independently re-verified; two of its claims found factually wrong (see §D).

---

=== INDEPENDENT VERDICT ===

**THE TWO BUG FIXES ARE REAL, CORRECT, AND LOAD-BEARING.** The ATR off-by-one fix produces bit-exact agreement with an independent manual recomputation on 4 live tokens; the old code inflated ATR 13–44%. The phase-1 SL widen fix is live-proven in production logs and DB state — ride_it re-widens the SL over the VOL-GATE persist every cycle. ride_it **is active in production right now**: `manage_ride_it_exit()` executes every pipeline cycle on ride_it-mapped open positions, writes phase-1 SLs computed from the fixed ATR, and both guardian overlays bypass the fixed signal families.

**BUT ride_it is NOT a self-contained, production-grade exit system.** Three structural facts, all verified against live data, mean its design premise ("survive the wait for the delayed spike") is largely nullified in production:

1. **HARD_MAX_LOSS fires before ride_it's survival SL on every ordinary loser.** Global net closes at −1.0% unleveraged; ride_it's phase-1 SL sits 1.3–2.5% below entry. Live proof — **during this audit**, trade 15964 (SUPER, `trend-ride+`), which ride_it was actively managing with SL at −1.94%, closed at 02:49:25 via `hard_max_loss` at −1.05%. Same pattern: USELESS (SL −2.50%, closed −1.17%), HBAR (SL −1.30%, closed −1.01%), IO (closed −1.08%). **4 of 7 `trend-ride+` trades died to hard_max_loss; 0 of 7 exited via ride_it.** ride_it's survival SL is only reachable on gap-throughs (price jumping past both thresholds in one cycle), and even those exits get labeled `atr_sl_hit`/`atr_trail_hit`, not `ride_it_exit`.
2. **Overlay bypass gaps are still unfixed** for `mover-`, `mover`, and underscore `volume_breakout*` variants. Historical DB evidence: `mover-` 9/12 closed by `profit-monster-trail` — the exact premature-profit-taking ride_it was built to avoid.
3. **The real SHORT source string `volume-breakout-short-` does NOT route to ride_it.** Direct execution of `_match_exit_config('volume-breakout-short-')` returns `None`. The previous bug-hunter report claimed it routes "via volume-breakout+- branch" — **that claim is false** (verified by running the code). Consequence: volume-breakout SHORT trades get no ride_it management, are bypassed from PM trail (substring `volume-breakout` matches), AND are exempted from the 8h universal max hold (`_is_ride_it` substring matches) — leaving only hard_max_loss/stale/soft-trigger as backstops. `VOLUME_BREAKOUT_MINUS_ENABLED = True`, so this gap is live.

**Ride_it has 0 exits in all-time history** (`exit_reason LIKE 'ride_it%'` → 0). Its only two live post-fix trades (SUPER, USELESS) both closed via hard_max_loss before any ride_it logic could fire. The system is running, but it has not yet demonstrated its intended behavior end-to-end.

**Readiness: CONDITIONAL.** Safe to leave running for LONG `trend-ride+` / `volume-breakout-long+` (bypassed, actively managed, loss side capped by the global net — no new risk introduced). Not ready to be *relied upon* as an exit engine until: (a) bypass gaps fixed, (b) `volume-breakout-short-` routing fixed, (c) phase-1 spike-lock clobber fixed (§B-6), (d) CEO decides whether hard_max_loss should exempt ride_it — otherwise ride_it is a profit-side-only system and should be documented as such.

---

## A. ATR Computation — FIX VERIFIED CORRECT (independent recomputation)

Method: fetched the same `candles_1h` rows ride_it uses (19 rows, `is_closed=1`, DESC), then computed ATR four ways: (a) ride_it's fixed method (reverse→ASC, SMA of last 14 TRs), (b) independent manual computation pairing each candle with its true previous close without any reverse call, (c) the old buggy method (no reverse), (d) Wilder RMA as textbook reference. Then called the actual `ride_it_exit._get_atr()`.

| Token | `_get_atr()` actual | (a) fixed | (b) independent | (c) old buggy | inflation of (c) | (d) Wilder | atr_pct (fixed) |
|---|---|---|---|---|---|---|---|
| SUPER | 0.002336 | 0.002336 ✓ exact | 0.002336 ✓ exact | 0.003329 | **+42.5%** | 0.002651 | 0.978% |
| POL | 0.001198 | 0.001198 ✓ exact | 0.001198 ✓ exact | 0.001723 | **+43.8%** | 0.001233 | 1.099% |
| BTC | 355.335 | 355.335 ✓ exact | 355.335 ✓ exact | 466.000 | **+31.1%** | 342.534 | 0.415% |
| ETH | 13.487143 | 13.487143 ✓ exact | 13.487143 ✓ exact | 15.257857 | **+13.1%** | 12.555 | 0.498% |

- **The fix is exact.** Both the module's own output and an independently written computation agree to full float precision on all 4 tokens. The DESC-order bug inflated ATR 13–44% pre-fix, which would have pushed phase-1 SLs to the 2.5% cap on every trade.
- **Design note (not a bug):** ride_it's ATR is a **simple average (SMA) of the last 14 TRs**, not Wilder RMA. It differs from Wilder by −12% to +7% on live tokens. The RIDE_IT constants (2.0× mult, 1.3% floor, 2.5% cap) were tuned against this SMA — do not "fix" to Wilder without re-tuning.
- **Note on prior report A4:** bug_hunter reported BTC ATR = 347.2143 at ~02:00–02:15 UTC; my run at 02:44 gives 355.335. Both are correct for their timestamps — the 02:00 1h candle closed between runs. Consistency, not discrepancy.
- Position_manager's two other ATR sites (sl_zones ~2682, pump_exit ~2793) also carry the reverse fix — code-read verified, same pattern.

## B. Phase-1 SL Widen Logic — WORKS, BUT CLOBBERS SPIKE-TRAIL PROFIT LOCKS (new bug)

Read `ride_it_exit.py:347-369` and traced: `sl_distance = atr×2.0`, floored at 1.3% of entry, capped at 2.5%; LONG `phase1_sl = entry − sl_distance`; `should_update = phase1_sl > current_sl×1.0005 OR phase1_sl < current_sl×0.9995` (0.05% deadzone, both directions). Executed the real module with `_persist_sl` patched to capture writes:

| Scenario | Result | Verdict |
|---|---|---|
| Tight SL −0.5%, price −0.2%, phase 1 | TRAIL_SL → phase-1 target (widen) | ✓ fix works |
| SL exactly at phase-1 target | HOLD, zero DB writes | ✓ deadzone works |
| SHORT, SL=0, phase 1 | TRAIL_SL → entry+dist | ✓ |
| ATR=0 (no candles) | HOLD, no write | ✓ |
| RIDE_IT_ENABLED=False | HOLD | ✓ |
| 25h hold, +1% | EXIT `ride_it_max_hold: 25.0h, +1.0%` | ✓ |
| Phase 2, 2 bad candles, +2% | EXIT `ride_it_momentum` | ✓ |
| Phase 2, 2 bad candles, +0.5% | HOLD (below 1% profit floor) | ✓ per code |
| **Spike trail at +3.2% (SL=peak−0.5%=0.24626, ABOVE entry), vol drops to 3×, still phase 1** | **TRAIL_SL → 0.235658 (entry−1.9%) — profit lock DESTROYED** | **✗ NEW BUG** |

**New bug B-6 (MEDIUM):** phase-1 `should_update` allows *lowering* a LONG SL unconditionally. If the volume-spike override has locked a profitable SL above entry, and volume then recedes below 5× while the trade is still inside phase 1 (<2h), phase-1 logic resets the SL to entry−1.9%. The trade keeps +3% unrealized but its stop sits at −1.9% — full round-trip risk. This directly defeats the spike override's stated purpose ("catches explosive moves regardless of phase"). **Fix:** in phase 1, skip the update when `current_sl >= entry_price` for LONG (or `<= entry` for SHORT) — never loosen a profit lock. Prior report tested only that widening works; it did not test the spike→phase-1 interaction.

**Live confirmation of widen fix:** pipeline.log shows `[RIDE-IT-P1] SUPER LONG: SL → $0.235930 (1.8%)` every ~45–90s from 02:02 through 02:49, then the value moved to `$0.235659 (1.9%)` after the 02:00 1h candle closed (fresh ATR 0.002336×2). DB `stop_loss` for 15964 = 0.23565857 = ride_it's computation from live ATR. The widen fix is load-bearing and visible in production.

**Observation (pre-existing, fragile):** every ride_it position costs 2 DB writes/cycle — tpsl/VOL-GATE persist (`[PERSIST] SL_write=…`) runs at ~line 2616, ride_it at ~2916, so ride_it wins the write race only because it executes later. Log lines are also double-emitted per cycle (two log sinks). Correct today; any reordering or second writer after ride_it silently reverts the wide SL.

## C. Production Activity — RIDE IT IS ACTIVE

- `logs/pipeline.log`: continuous `[RIDE-IT-P1]` / `[RIDE-IT-SPIKE]` / `[RIDE-IT-P2]` lines every cycle for ride_it-mapped positions, 02:02–02:49 UTC (and the trade closed mid-audit at 02:49:25 — see §E).
- PostgreSQL: 0 exits with `exit_reason LIKE 'ride_it%'` all-time (confirms historical inertness). 2 open positions at audit start: SUPER `trend-ride+` (id 15964, ride_it-managed, SL 0.23566) and POL `bb-squeeze+` (id 15962, not ride_it). SUPER closed via `hard_max_loss` at 02:49:25 during this audit. **No ride_it-managed trade is open right now.**
- `hermes-price-collector.timer` active (every 30s, up 1d4h). Candle freshness at 02:45 UTC: 1h max age 0.77h (current hour not yet closed — normal), 5m max age 0.18–0.27h. SUPER/POL/BTC/ETH all have 4,654+ closed 1h and 8,640+ closed 5m candles. ATR/volume/momentum inputs are computable for all active tokens. (`scripts/candles.db` is a stale decoy; real DB is `/root/.hermes/data/candles.db` per `paths.py`.)
- Guardians: `profit_monster.log` and `cut_loser.log` show "Found 1 open positions" while 2 were open — SUPER excluded by bypass. **Bypass is observably working in production for `trend-ride+`.**

## D. Overlay Bypass — WORKS FOR FIXED FAMILIES, GAPS REMAIN (prior report partially wrong)

Executed per-part matching (production splits `signal` on commas — `position_manager.py:2715`) plus the exact `_match_exit_config` body and `_is_ride_it` needles against **all 397 distinct production signal strings** and full trade history:

- **Bypassed correctly:** `trend-ride+`, `trend_ride_long`, hyphenated `volume-breakout*` (substring `volume-breakout` / `trend-ride` in `PROFIT_MONSTER_BYPASS_SIGNALS`). Matching semantics confirmed in code: `cut_loser.py:65-68` and `profit_monster.py:86-89` both use `AND NOT (signal LIKE %s …)` with `%needle%` params — substring semantics, so `trend-ride` covers `trend-ride+`.
- **Gaps still present (NOT fixed — prior Issue #1 remains open):** ride_it-mapped signals absent from the bypass list: `mover-` (12 trades, **9 closed by profit-monster-trail**), `mover` (9 trades, 4 PM trail), `volume_breakout` bare/underscore variants (15+ trades across combo signals). PM trail activates at +0.4% and cuts early — the opposite of ride_it's design. **These families will keep getting PM-interfered until `'mover-'`, bare `'mover'`, and `'volume_breakout'` are added.** (Note `'mover'` as substring also covers `mover+`, which was deliberately removed from ride_it — CEO decision needed on that interaction.)
- **Wrong claim in prior report (C2/C3):** bug_hunter stated `volume-breakout-short-` → ride_it "via volume-breakout+- branch". **False** — direct execution returns `None`. The rev-2 matcher's version-only raw-prefix branch requires the remainder to be exactly `-vN`; `short-` is not. The actual SHORT source emitted by `scripts/signals/volume_breakout.py:53` (`SOURCE_SHORT = 'volume-breakout-short-'`) therefore does **not** get ride_it. Underscore variant `volume_breakout_short_` *does* route to ride_it (via `volume_breakout`+`_` prefix). **Fix:** add `'volume-breakout-short-'` (and/or `'volume-breakout-short'` stem) to SIGNAL_EXIT_CONFIG → ride_it, and to PROFIT_MONSTER_BYPASS_SIGNALS.
- **Over-exemption from UNIVERSAL_MAX_HOLD:** `_is_ride_it` substring needles match 2 signal families that `use_ride_it` does NOT manage: `mover+` (22 trades — `mover+` was removed from ride_it config but the bare `mover` needle still exempts it; prior report documented/accepted this) and `rs-r69,volume-breakout-short-` (the routing gap above). These trades get no ride_it 24h backstop AND no 8h universal backstop — only hard_max_loss/stale/soft-trigger. `mover+` avg PnL is −$0.045 over 22 trades; removing its only time-based backstop is a live risk, not a theoretical one.

## E. UNIVERSAL_MAX_HOLD Exemption & Hard-Max-Loss Interaction — EXEMPTION CORRECT, DESIGN IMPLICATION SEVERE

- `_is_ride_it` at `position_manager.py:3288-3292`: needles `ride_it`, `trend-ride`, `trend_ride`, `volume-breakout`, `volume_breakout`, `mover`. Executed against all 397 production signals: **zero ride_it-mapped signals fail the exemption** (no false negatives); 2 families over-exempted (§D). Exemption logic itself is correct.
- Constant sanity (read directly): `RIDE_IT_ENABLED=True`; phase-1 mult 2.0 / floor 1.3% / cap 2.5% (floor<cap ✓); trail activate 2% > distance 1.2% ✓; phase1→phase2 = 7200s < max hold 24h ✓; `RIDE_IT_MAX_HOLD_HOURS=24` (1440min) > `UNIVERSAL_MAX_HOLD_MINUTES=480` — exactly why the exemption exists, and it works.
- **HARD_MAX_LOSS (design implication, now live-proven):** `HARD_MAX_LOSS_PCT = CUT_LOSER_PNL = −1.00` (`hermes_constants.py:700`), applied unleveraged (`compute_live_pnl` confirmed unleveraged raw market return) to **every** position with no ride_it exemption (`position_manager.py:3374-3383`). ride_it's phase-1 floor is −1.3%. Therefore: **any losing ride_it trade reaching −1.0% is closed by hard_max_loss before price ever reaches ride_it's wider SL.** Verified live during this audit — SUPER (ride_it-managed, SL −1.94%) closed `hard_max_loss` at −1.05%, 61 minutes into the trade, phase 1. Historical `trend-ride+`: 4/7 hard_max_loss, 3/7 profit-monster-trail (pre-bypass), **0/7 ride_it**. ride_it's "survival" SL effectively never executes for ordinary losers; its production value is concentrated on the profit side (trail at +2%, momentum exit, VOL-GATE TP ~+2.2%, 24h max hold) plus rare gap events. **If the intent is for ride_it trades to survive >1% dips, hard_max_loss (and stale_loser at −1.0%) need a ride_it exemption or a ride_it-specific threshold — CEO decision required; do not change silently (hermes_constants.py rule).**
- **Correction to prior report Issue #6:** bug_hunter flagged PM-internal `should_cut_loser` Priority-2 as preempting ride_it SL at lev=1. **Moot in practice:** Priority-2 threshold = `−sl_distance×100×max(lev,1)` = −1.3% at lev=1, −3.9% at lev=3 — but hard_max_loss (−1.0%) always binds first for any sl_distance ≥ 0.010. Priority-1 (actual SL price) likewise only fires at the SL price, which hard_max_loss beats on slow grinds. Only gap-throughs reach SL-price checks, and those run *before* hard_max_loss in the loop (ATR check at ~3000 vs hard_max_loss at ~3375) so gap exits are labeled `atr_sl_hit`, not ride_it.
- **Analytics caveat:** because trail-SL hits are reclassified to `atr_trail_hit` (`check_atr_tp_sl_hits`, ~line 482-489) and momentum/max-hold exits are the only `ride_it_exit` labels, ride_it's actual contribution will be **undercounted** in exit-reason GROUP BYs even when it works correctly.

## F. Additional Issues Found (beyond prior report)

1. **(MEDIUM) Phase-1 clobbers spike-override profit lock** — §B-6, new, simulation-proven.
2. **(MEDIUM) `volume-breakout-short-` routing gap** — §D, prior report's claim was wrong; live signal family affected; compound gap (no ride_it + bypassed + max-hold-exempt).
3. **(MEDIUM) Bypass gaps unfixed** — §D; `mover-` 9/12 historical PM-trail interference is concrete evidence.
4. **(LOW, latent) `_parse_hold_time` naive-string failure:** with a naive ISO string (e.g. `'2026-10-05T01:55:10.213523'`), `datetime.fromisoformat` succeeds producing a naive datetime, then `now(aware) − entry_dt(naive)` raises TypeError → outer except → **returns 0**. Consequence chain: phase-1 SL reapplied forever, ride_it 24h max_hold never fires, universal 8h max_hold exempt (ride_it signal) → **no time-based backstop at all**. *Current production path is safe* — psycopg2 returns datetime objects and the `isinstance(datetime)` branch handles naive correctly (verified: naive datetime obj → 25.000h). The string branch is only reachable if open_time is ever serialized (JSON caches, hype_cache merges). Latent, not live. Fix: after `fromisoformat`, apply the same `tzinfo is None → utc` coercion the datetime branch has.
5. **(LOW) Dead config:** `RIDE_IT_TP_PHASE1_MULT = 3.0` imported in `ride_it_exit.py:34` but **never used** — `manage_ride_it_exit` contains no TP logic; ride_it TP actually comes from the generic VOL-GATE (~2.2% on SUPER: target 0.2456262). Docstring line 9 also references a TP that doesn't exist. Wire it or remove it.
6. **(LOW) Magic number:** `ride_it_exit.py:383` `if profit_pct > 0.01:` — momentum-exit profit floor is hardcoded; violates the no-hardcoded-constants rule. Name it `RIDE_IT_MOMENTUM_MIN_PROFIT` in hermes_constants.py.
7. **(LOW) Dual-engine combo conflicts:** signals like `rs_s,volume_breakout_long` (4 trades), `rs_s,rs_s,volume_breakout_long` (2), `mover_,rs_r` (1) match **both** ride_it and rr_engine on different parts. Code order: ride_it (0b) runs, then rr_engine (0) — both can TRAIL_SL and persist, causing write conflicts; historical exits on these combos are PM-trail/cut-loser, i.e., not ride_it-managed at all despite the mapping.
8. **(INFO) `direction=None` falls through to the SHORT branch** in `manage_ride_it_exit` (no else-guard) — cosmetic; production always passes LONG/SHORT, but a malformed pos would compute SHORT-style SLs.
9. **(INFO) SOFT TRIGGER (2h, 0.3% trail) and stale-winner (+0.6%/60min) apply to ride_it positions** — no `_is_ride_it` guard. A flat/negative ride_it trade at 2h+ gets a 0.3% leash that defeats phase-2's "wait for the spike" design; a +0.6%-flat winner gets closed before ride_it's trail even activates at +2%. Prior report Issue #2 — confirmed still unguarded, remains a live interference path.

## F-Data. Trade Data Summary (PostgreSQL, verified by query)

**All-time ride_it-mapped signals** (`trend-ride*`, `volume*breakout*`, `mover*`) — exit reasons:
`atr_sl_hit` 46 (−$1.04) · `profit-monster-trail` 34 (+$1.89) · `hard_max_loss` 6 (−$0.59) · `hard_sl` 4 (−$0.87) · `cut-loser-CL-T1` 3 (−$0.30) · `hard_tp` 2 · `UNIVERSAL_MAX_HOLD` 1 · `atr_tp_hit` 1 · `atr_trail_hit` 1 · `ride_it_exit` **0**.

**30d LONG per-signal:** `volume-breakout-long+` 24T, 16W (67%), avg +$0.127, avg hold 3.14h, 18/24 atr_sl_hit, 1 hard_max_loss, quick-loss(<30min) 4%. `mover+` 22T, 12W, avg −$0.045, 7 PM-trail, 1 UNIVERSAL_MAX_HOLD. `trend-ride+` 7T, 3W, avg −$0.026, 4 hard_max_loss, 3 PM-trail, quick-loss 14%. Signal quality is mixed; the exit system's interference (PM trail pre-bypass, hard_max_loss always) — not entry quality alone — explains much of the ride_it-mapped underperformance.

---

## Bottom Line

| Question | Answer |
|---|---|
| Is the ATR fix correct? | **Yes — bit-exact vs independent recomputation; old code inflated 13–44%.** |
| Does phase-1 widen work? | **Yes — live-proven; but it clobbers spike-override profit locks (new bug).** |
| Is ride_it active in production? | **Yes — called every cycle, SL writes visible in DB/logs. 0 exits so far; both live trades died to hard_max_loss first.** |
| Does the overlay bypass work? | **For trend-ride/hyphenated volume-breakout: yes, live-verified. Gaps remain for mover-/mover/underscore variants (unfixed) and volume-breakout-short- (routing broken — prior report wrong).** |
| Is the UNIVERSAL_MAX_HOLD exemption correct? | **Yes for ride_it-mapped signals; over-exempts mover+ and volume-breakout-short- combos.** |
| HARD_MAX_LOSS before ride_it SL? | **Yes — structurally, on every ordinary loser. ride_it's survival SL is a gap-event-only backstop. CEO decision needed.** |
| Remaining bugs prior report missed? | **Yes: phase-1 spike-lock clobber (MEDIUM), volume-breakout-short- routing (MEDIUM, prior claim false), naive-string hold-time latent bug (LOW), dual-engine combo conflicts (LOW), dead TP constant, magic number.** |
| Ready for production? | **Running, and safe for the bypassed LONG families (no new risk). Not yet a trustworthy exit engine: bypass gaps, SHORT routing hole, spike-lock clobber, and the hard_max_loss ceiling must be resolved before ride_it can claim its design goal.** |

*All tests executed against live code and live databases 2026-10-06 02:40–03:00 UTC. Simulations patched `_persist_sl` to capture-only — no DB writes performed by this audit. A live production exit (trade 15964, hard_max_loss) was observed at 02:49:25 UTC during the audit window.*

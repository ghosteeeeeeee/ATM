# Bug Hunter — Ride-It Exit: Full Independent Verification

**Date:** 2026-10-06 02:15 UTC
**Scope:** Commits `1b6f8f54` (ATR off-by-one, phase-1 SL widen, PROFIT_MONSTER_BYPASS additions, UNIVERSAL_MAX_HOLD exemption, SIGNAL_EXIT_CONFIG) + `e1d60cac` (_is_ride_it alignment), plus the prior follow-up (underscore variants in _is_ride_it). Everything re-verified from scratch — no reliance on prior bug_hunter findings.

---

## VERDICT: **SAFE TO SHIP** (with 4 WARN-level overlay-interference findings — none block the ride_it exit itself)

**Live readiness: YES — ride_it exits are ACTIVE in production right now.** The pipeline is executing `manage_ride_it_exit()` on the currently open SUPER trade (`trend-ride+`, id=15964) every cycle, writing phase-1 SLs computed from the fixed ATR, and both guardian overlays (profit_monster, cut_loser) are bypassing it live. The next ride_it trade will use the ride_it exit.

---

## Checklist Results

### A. ATR Computation — **PASS (all 3 locations + live data)**

| # | Item | Result | Evidence |
|---|------|--------|----------|
| A1 | `ride_it_exit.py:_get_atr()` reverse fix | **PASS** | `rows.reverse()` present at `scripts/ride_it_exit.py:63`, correctly placed after `fetchall()` (line 59) and before the TR loop (lines 68-72). Comment documents the DESC/ASC bug. |
| A2 | position_manager sl_zones ATR (~line 2682) | **PASS** | `_atr_rows_slz.reverse()` at `scripts/position_manager.py:2683` — inside `if len(_atr_rows_slz) >= 15:` guard, before TR computation. |
| A3 | position_manager pump_exit ATR (~line 2793) | **PASS** | `_atr_rows.reverse()` at `scripts/position_manager.py:2788` — same pattern, guarded by `>= 15` rows. |
| A4 | Live test vs manual calculation | **PASS** | `_get_atr('BTC', 14)` = **347.2143**. Independent manual ASC computation from the same `candles_1h` rows = **347.2143** — exact match. Buggy (no-reverse) computation on identical rows = 516.5714 (**+48.8% inflation**), confirming the fix is real and load-bearing. |
| A5 | ATR reasonableness | **PASS** | BTC ATR = 0.405% of price (85,794.5). SUPER ATR = 0.92% of entry (0.24033). Both inside the expected 0.2–1.5% band for majors. |

### B. Phase-1 SL Logic — **PASS (all edge cases tested with real code)**

| # | Item | Result | Evidence |
|---|------|--------|----------|
| B1 | Phase-1 section read | **PASS** | `ride_it_exit.py:347-369`. `sl_distance = atr*2.0`, floored at 1.3% of entry, capped at 2.5% of entry. |
| B2 | SL widen allowed (not just tighten) | **PASS** | `ride_it_exit.py:359`: `should_update = phase1_sl > current_sl*1.0005 or phase1_sl < current_sl*0.9995`. Live-proven: pipeline log 02:10:11 shows VOL-GATE writing SL=0.237206, then `[RIDE-IT-P1] SUPER LONG: SL → $0.235930` (widen back to ride_it target). Old code (`phase1_sl > current_sl` only) would have left VOL-GATE's tighter SL in place. Simulation: cur_sl=-1.0% → TRAIL_SL to phase-1 target ✓; cur_sl=-5.0% → TRAIL_SL to phase-1 target ✓ (converges both directions). |
| B3 | Edge cases | **PASS** | `current_sl=0` → TRAIL_SL set ✓. `entry_price=1.23e-6` (micro) → TRAIL_SL=1.19925e-06, 2.5% cap applied ✓. `SHORT` + `current_sl=0` → SL set at entry+dist (0.24473) ✓. `ATR=0` (unknown token) → HOLD, no write ✓. |
| B4 | 0.05% deadzone math | **PASS** | Deadzone is multiplicative ±0.05% around current_sl (lines 359/362). Simulated: SL exactly at phase-1 target → HOLD, no DB write ✓; SL at target×1.0004 (inside deadzone) → HOLD ✓; SL at target×1.002 (outside) → TRAIL_SL ✓. |

### C. Exit Config Mapping — **PASS**

| # | Item | Result | Evidence |
|---|------|--------|----------|
| C1 | SIGNAL_EXIT_CONFIG read | **PASS** | `hermes_constants.py:1639-1703`. |
| C2 | All 10 required ride_it mappings | **PASS** | Live-executed `_match_exit_config` replica against the real config: `trend-ride+`→ride_it, `trend_ride_long`→ride_it, `volume-breakout+`→ride_it, `volume-breakout-`→ride_it, `volume-breakout-long+`→ride_it, `volume_breakout+`→ride_it, `volume_breakout-`→ride_it, `volume_breakout`→ride_it, `mover-`→ride_it, `mover`→ride_it. **Zero missing.** |
| C3 | `mover+` NOT in ride_it | **PASS** | `'mover+'` not a config key; live match returns `None` → default PM-trail path ✓. |
| C4 | `_match_exit_config` rev-2 (`volume-breakout-long+`) | **PASS** | Exact-match branch returns ride_it for `volume-breakout-long+` (never reaches prefix logic). Rev-2 version-suffix rules tested live: `pump-chain-v5`→pump_exit ✓, `volume-breakout-v2`→ride_it ✓, `mover-v2`→ride_it ✓, `trend-ride-v3`→ride_it ✓, `pump-chain-1`→None (correctly rejected — `-1` is not `-vN`) ✓, `bb-squeeze+`→None ✓. Also verified real DB signal parts route correctly: `rs_s`→rr_engine, `rs-s36`→rr_engine, `volume_breakout_long`→ride_it (via `volume_breakout`+`_` prefix branch), `volume-breakout-short-`→ride_it (via `volume-breakout`+`-` branch — the actual SHORT source string from `scripts/signals/volume_breakout.py:53`). |

### D. Overlay Bypass — **PASS for the fixed signals (live-proven); WARN for two uncovered variants (see Issues #1)**

| # | Item | Result | Evidence |
|---|------|--------|----------|
| D1 | `trend-ride` + `trend_ride_long` in PROFIT_MONSTER_BYPASS_SIGNALS | **PASS** | Both present at `hermes_constants.py:1592` (added in `1b6f8f54`). `volume-breakout` also present (line 1591). |
| D2 | cut_loser uses the list with substring/LIKE matching | **PASS** | `cut_loser.py:65-68`: `AND NOT (signal LIKE %s OR …)`, params `%{s}%`. |
| D3 | profit_monster uses the same list | **PASS** | `profit_monster.py:86-89`: identical `LIKE %s` OR-block. |
| D4 | `trend-ride` substring matches `trend-ride+` | **PASS** | Tested both Python `in` and SQL `LIKE '%trend-ride%'` semantics against the real source strings: `trend-ride+` ✓ bypassed, `trend_ride_long` ✓ bypassed, `volume-breakout-long+` ✓ bypassed. |
| D5 | **Live proof in production** | **PASS** | 2 open positions (POL `bb-squeeze+`, SUPER `trend-ride+`). profit_monster.log and cut_loser.log every cycle: **"Found 1 open positions"** — SUPER is excluded by the bypass filter while POL remains. Guardian bypass verified working end-to-end, not just statically. |

### E. UNIVERSAL_MAX_HOLD Exemption — **PASS**

| # | Item | Result | Evidence |
|---|------|--------|----------|
| E1 | `_is_ride_it` at ~line 3285 | **PASS** | `position_manager.py:3288-3292`. Needles: `ride_it`, `trend-ride`, `trend_ride`, `volume-breakout`, `volume_breakout`, `mover`. |
| E2 | Coverage of required variants | **PASS** | All six needles present; covers hyphen + underscore + bare forms consistent with `_match_exit_config` coverage (verified `e1d60cac` alignment claim independently). |
| E3 | Signal-string tests | **PASS** | Executed the exact logic: `trend-ride+`→True (exempt) ✓; `volume_breakout_long`→True ✓; `rs_s,mover`→True (comma-joined, substring hits `mover`) ✓; `pump-chain+`→**False** (not exempted) ✓; `bb-squeeze+`→**False** ✓. Tested against all 393 distinct real signal strings in PostgreSQL — no non-ride_it signal falsely exempted except the documented `mover+` over-match (Issue #4). |
| E4 | Non-ride_it not exempted | **PASS** | `pump-chain+`, `bb-squeeze+`, `confluence`, `accel_300-v2-long`, `rs-s36` all return False. |

### F. End-to-End Flow — **PASS (verified live, not just on paper)**

| # | Item | Result | Evidence |
|---|------|--------|----------|
| F1 | Full flow traced | **PASS** | `check_and_manage_positions` → sl_zones ATR check (line 2663) → `_match_exit_config` per signal part (line 2736) → `use_ride_it` gate (2907-2912) → `manage_ride_it_exit()` (2916) → ATR from `candles_1h` → phase-1 SL widen/tighten (ride_it_exit.py:347) → `TRAIL_SL` returns → `pos['stop_loss']` updated in-memory (2928) + `_persist_sl` writes brain DB (ride_it_exit.py:226-234) → `check_atr_tp_sl_hits` (3000) reads the ride_it SL/TP. |
| F2 | `manage_ride_it_exit()` actually called | **PASS — LIVE** | `position_manager.py:2916`. Production log evidence, every ~45s cycle: `[RIDE-IT-P1] SUPER LONG: SL → $0.235930 (1.8%)` (02:02→02:14 UTC, continuous). DB `stop_loss` for trade 15964 = 0.23593 = ride_it's phase-1 computation from live ATR (0.0022×2, floored/capped) — ride_it's write wins each cycle (it runs after VOL-GATE's persist; verified in code order + DB state). |
| F3 | Correct action types | **PASS** | Simulated with `_persist_sl` patched to no-op: `HOLD` (deadzone/no-ATR/malformed pos) ✓, `TRAIL_SL` (phase-1 widen/tighten, phase-2 trail, spike) ✓, `EXIT` (max-hold 25h → `{'action':'EXIT','reason':'ride_it_max_hold: 25.0h, +1.0%'}`) ✓. position_manager handles EXIT → `close_paper_position(trade_id, "ride_it_exit", exit_detail=…)` (2922) ✓, TRAIL_SL → memory update (2928) ✓. |
| F4 | Exception handling | **PASS (no gaps that break the loop)** | position_manager block: `try/except ImportError + Exception` (2914-2932) — a ride_it failure logs WARN and the position loop continues. ride_it helpers: all DB readers catch broadly and return safe defaults (ATR→0→HOLD, vol_ratio→1.0, candle counts→0); `_persist_sl` catches and logs; `_parse_hold_time` handles datetime/ISO/naive/garbage → 0. Simulated malformed inputs (None entry, None open_time, empty pos, string prices, garbage open_time string, price=0, direction=None): **zero exceptions** — all returned HOLD or correct SL values. direction=None falls through to SHORT branch (treated as SHORT) — cosmetic only; production always passes LONG/SHORT. |

### G. Constants Sanity — **PASS (no conflicts)**

| # | Item | Result | Value (hermes_constants.py) |
|---|------|--------|------|
| G1 | `RIDE_IT_ENABLED` | **PASS** | `True` (line 3806) |
| G2 | `RIDE_IT_SL_PHASE1_MULT` | **PASS** | `2.0` (3809) |
| G3 | `RIDE_IT_SL_PHASE1_FLOOR` | **PASS** | `0.013` (3810) |
| G4 | `RIDE_IT_SL_PHASE1_CAP` | **PASS** | `0.025` (3811) |
| G5 | `RIDE_IT_TRAIL_ACTIVATE` | **PASS** | `0.02` (3815) |
| G6 | `RIDE_IT_TRAIL_DISTANCE` | **PASS** | `0.012` (3816) |
| G7 | `RIDE_IT_MAX_HOLD_HOURS` | **PASS** | `24` (3828) |
| G8 | `UNIVERSAL_MAX_HOLD_MINUTES` | **PASS** | `480` (hermes_constants.py:1030) |
| G9 | Conflicts | **PASS** | floor(1.3%) < cap(2.5%) ✓; trail activate(2%) > distance(1.2%) ✓; phase1→phase2 (2h) < max hold (24h) ✓. `RIDE_IT_MAX_HOLD` (1440 min) **>** `UNIVERSAL_MAX_HOLD` (480 min) — this is exactly why the `_is_ride_it` exemption exists, and the exemption is verified working (E-section). No constant conflict. |

### H. Live Data Check — **PASS**

| # | Item | Result | Evidence |
|---|------|--------|----------|
| H1 | ride_it exits all-time = 0 | **PASS** | PostgreSQL: `SELECT COUNT(*) FROM trades WHERE exit_reason LIKE 'ride_it%'` → **0**. ILIKE '%ride%' → none. Confirms the inertness that motivated the fixes. |
| H2 | Open ride_it-managed trades | **PASS — ACTIVE** | Trade **id=15964, SUPER, LONG, signal=`trend-ride+`**, entry 0.24033, opened 2026-10-06 01:48:50 UTC (age ~25min, phase-1), sl_distance=0.013, lev=3. Actively managed by ride_it right now (F2 logs). Also USELESS `trend-ride+` (id=15963) ran 01:27–01:53 today — closed by the global hard_max_loss net (see Issue #3 context). |
| H3 | Candle data availability | **PASS** | `CANDLES_DB=/root/.hermes/data/candles.db` (note: `scripts/candles.db` is a stale decoy — do not use). SUPER: 4,653 closed 1h + 8,640 closed 5m candles, latest 1h closed candle age ≤1.1h. POL: 4,655 / 8,642. BTC: 3,055 / 8,640. `hermes-price-collector.timer` **active**. ATR/volume/momentum inputs all computable for active tokens. |

---

## Issues Found

### Issue #1 — WARN (MEDIUM) — Bypass list missing `mover-`/`mover` and underscore `volume_breakout*` variants
- **Where:** `hermes_constants.py:1561` (PROFIT_MONSTER_BYPASS_SIGNALS); affects `cut_loser.py:65` and `profit_monster.py:86`
- **Detail:** SIGNAL_EXIT_CONFIG maps `mover-`, `mover`, `volume_breakout+/-`, `volume_breakout` to ride_it, and `_match_exit_config` also routes the real signal parts `volume_breakout_long`/`volume_breakout_short_` to ride_it. None of these underscore/bare variants are in PROFIT_MONSTER_BYPASS_SIGNALS (which only has hyphenated `volume-breakout`), so profit_monster and cut_loser guardians still double-manage them.
- **Proof it bites in production:** historical exit reasons from PostgreSQL — `mover-`: **9/12 closed by `profit-monster-trail`**, 2 hard_sl, 1 cut-loser-CL-T1, **0 ride_it exits**; `rs_s,volume_breakout_long`: 2× `cut-loser-CL-T1` + 2× `profit-monster-trail`; `rs_r91,volume_breakout_short_`: `profit-monster-trail`. PM trail activates at 0.4% and cuts early — the opposite of ride_it's "let it run" design.
- **Impact:** Future `mover-` / underscore-variant trades get PM/cut_loser interference despite ride_it management in position_manager. `trend-ride+` and hyphenated `volume-breakout*` are correctly bypassed (live-verified).
- **Suggested fix:** Add `'mover'` (bare substring covers `mover-` and `mover+`… note `mover+` was deliberately removed 2026-09-25 for PM management — so add `'mover-'` and bare `'mover'` carefully, or restructure), and `'volume_breakout'` (underscore bare covers all underscore variants) to PROFIT_MONSTER_BYPASS_SIGNALS. Requires CEO decision on `mover+` interaction.

### Issue #2 — WARN (MEDIUM) — SOFT PEAK-EXIT TRIGGER and stale_exit apply to ride_it positions
- **Where:** `position_manager.py:3313-3364` (SOFT TRIGGER: SOFT_TRIGGER_HOURS=2.0, SOFT_TRAIL_PCT=0.003) and `check_stale_position` at line 505 (STALE_WINNER_MIN_PROFIT=0.6%, 60min stalled; STALE_LOSER_MAX_LOSS=-1.0%, 8min stalled). SpeedTracker is live in production (updates every pipeline run, 176 tokens).
- **Detail:** Neither check exempts ride_it signals. A ride_it trade that is flat/slightly negative at 2h+ gets its SL raised to price×0.997 by SOFT TRIGGER — a tight leash that defeats phase-2's "wait for the delayed spike" design (a 0.3% dip after the trigger stops the trade out before any spike). Similarly stale_winner closes ride_it trades at ≥+0.6% flat-for-60min — before ride_it's trail even activates at +2%.
- **Live evidence:** SOFT TRIGGER firing in production today (`SOFT TRIGGER HBAR LONG SL set to … 0.3% trail, age=2.4h, pnl=-0.95%`, 00:42-00:44 UTC). Note the current SUPER trade is protected only because its pnl is positive; if it goes negative after 2h, SOFT TRIGGER will tighten its SL.
- **Suggested fix:** Add the same `_is_ride_it` substring guard to the SOFT TRIGGER block and (CEO decision) to stale_winner. Ride_it already has its own trail/momentum/max-hold exit logic.

### Issue #3 — WARN (MEDIUM, design interaction) — Global -1.0% nets fire before ride_it's 1.3–2.5% phase-1 SL
- **Where:** `position_manager.py:3374` — `HARD_MAX_LOSS_PCT = CUT_LOSER_PNL` = **-1.0** (unleveraged, applies to every position, no ride_it exemption). Stale_loser also -1.0%.
- **Detail:** ride_it's phase-1 SL floor is 1.3% below entry, but any losing ride_it trade reaching -1.0% price move is closed by `hard_max_loss` (step 7) before price ever reaches ride_it's wider SL (step 1 ATR-hit check only fires on gap-throughs past the SL). So ride_it's "survival" SL effectively never executes for ordinary losing trades — the global net caps losses at -1.0% first. Evidence: today's USELESS `trend-ride+` trade closed via `hard_max_loss` (-0.12 USDT); historical trend-ride+ exits: 3× hard_max_loss, 3× profit-monster-trail (pre-bypass).
- **Impact:** Not a code bug — a deliberate global safety net — but it means ride_it's value in production is concentrated in **profit-side** behavior (trail at +2%, momentum exit, TP ~2.2%, 24h max hold) plus gap events, not in letting losers breathe to -2.5%. If the CEO wants ride_it to genuinely survive >1% dips, hard_max_loss/stale_loser need a ride_it exemption or a ride_it-specific threshold. Recommend an explicit decision; do not change silently (hermes_constants.py rule).

### Issue #4 — WARN (LOW, documented & accepted) — `_is_ride_it` over-matches `mover+`
- **Where:** `position_manager.py:3288-3292` — substring `'mover'` also matches `'mover+'`.
- **Detail:** `mover+` was removed from ride_it config (SIGNAL_EXIT_CONFIG comment: "ride_it hurts mover+") and uses default PM trail, yet it is exempted from UNIVERSAL_MAX_HOLD via the substring. Commit `e1d60cac` explicitly documents and accepts this ("over-inclusive … benefit outweighs"). Historical `mover+` had 1 UNIVERSAL_MAX_HOLD exit; with the exemption those trades now stay open longer under PM-trail management only.
- **Status:** Known tradeoff, accepted by commit author. No action required; noted for the record.

### Issue #5 — WARN (LOW) — `RIDE_IT_TP_PHASE1_MULT` is dead config
- **Where:** `hermes_constants.py:3812` (3.0, "3x ATR TP target"); imported in `ride_it_exit.py:34` but **never used** — `manage_ride_it_exit` contains no TP logic. ride_it docstring (line 9) also references the TP that doesn't exist.
- **Detail:** TP exits for ride_it trades actually come from the generic tpsl_utils VOL-GATE dynamic ATR system (~+2.2% on SUPER: target 0.2456262). This works (TP exits fire via `check_atr_tp_sl_hits`), but the ride_it-specific TP is inert config and the docstring is misleading.
- **Suggested fix:** Either wire `RIDE_IT_TP_PHASE1_MULT` into ride_it (override VOL-GATE TP for ride_it signals) or remove the constant + docstring reference. Low priority.

### Issue #6 — WARN (LOW) — PM-internal `should_cut_loser` Priority-2 can preempt ride_it SL at leverage 1
- **Where:** `position_manager.py:349-390` (Priority 2: `pnl_pct <= -sl_distance*100*max(lev,1)`; live_pnl is **unleveraged** per `pnl_utils.compute_live_pnl`).
- **Detail:** With `sl_distance=0.013` (A/B control) and **lev=1**, the internal cut fires at -1.3% price move — earlier than ride_it's ATR-scaled phase-1 SL (up to -2.5%). At lev=3 (current SUPER trade) threshold is -3.9% and ride_it's SL wins. The standalone guardian `cut_loser.py` correctly bypasses `trend-ride`; the position_manager-internal check has no bypass.
- **Suggested fix:** Skip `should_cut_loser` Priority-2 (or the whole internal cut) for `_is_ride_it` signals — ride_it already has phase-1 SL + hard_max_loss as its loss stack. Check the A/B test arm distribution first: if ride_it signals can run at lev=1, this is a live gap.

### Issue #7 — WARN (LOW) — Hard-coded constant violation
- **Where:** `ride_it_exit.py:383` — `if profit_pct > 0.01:` (momentum-exit profit floor) is a magic number; hermes_constants.py rule requires `RIDE_IT_MOMENTUM_MIN_PROFIT`-style naming. Also `position_manager.py:3311-3312` `SOFT_TRIGGER_HOURS`/`SOFT_TRAIL_PCT` hardcoded (pre-existing, outside ride_it scope but same rule).
- **Suggested fix:** Move to hermes_constants.py on next constants-touching change.

### Observation #8 (not a defect) — VOL-GATE ↔ ride_it SL write ping-pong
Every cycle the tpsl_utils VOL-GATE persist (`[PERSIST] SL_write=0.237206`) runs before ride_it (`[RIDE-IT-P1] SL → $0.235930`), so each ride_it position costs 2 DB writes per cycle and ride_it's value only sticks because it executes later in the same cycle (code order: persist wiring ~line 2615 → ride_it ~2916; verified in logs and final DB state). Correct today, but fragile: any future reordering (or a second writer after ride_it) would silently revert ride_it's wide SL. Consider gating the VOL-GATE dynamic persist for `_is_ride_it` signals, or asserting ordering in a test.

---

## End-to-End Flow Assessment

```
signal source (e.g. 'trend-ride+' from scripts/signals/trend_ride_long.py:67)
  → trades.signal = source string (PostgreSQL brain DB)
  → position_manager.check_and_manage_positions (fresh process each ~1m pipeline cycle)
      → _match_exit_config('trend-ride+') = 'ride_it'          [verified live]
      → manage_ride_it_exit(token, dir, cur, pos, trade_id)    [called at line 2916]
          → _get_atr() from candles_1h, rows.reverse() ASC     [verified: exact manual match]
          → volume-spike override / 24h max-hold / phase-1 SL widen / phase-2 trail
          → _persist_sl() → brain DB trades.stop_loss          [verified in DB + logs]
      → check_atr_tp_sl_hits uses ride_it SL + VOL-GATE TP     [TP exits still work]
  → guardians (profit_monster, cut_loser) bypass via PROFIT_MONSTER_BYPASS_SIGNALS
      [live-verified: 'Found 1 open positions' of 2 — SUPER excluded]
  → UNIVERSAL_MAX_HOLD (480min) skipped for _is_ride_it        [code + substring tests verified]
  → ride_it's own 24h max hold is the backstop                 [EXIT path simulated ✓]
```

**Judgment:** The ride_it exit is no longer inert. Both fix commits do what they claim: the ATR reverse fix is exact (manual recomputation matches to the digit; the old code inflated ATR 48.8% on BTC), the phase-1 widen fix is live-proven in production logs (ride_it re-widens SL over VOL-GATE every cycle), config mapping covers every real signal variant found in 393 production signals, and the guardian bypass is observably working on the open trade. Action types, exception handling, edge cases (SL=0, micro prices, SHORT, ATR=0, malformed rows) all behave safely.

The residual risks are **overlay-interference** issues (Issues #1–#3, #6): global nets and other exit systems will still close ride_it trades at thresholds ride_it's design would not choose (-1.0% hard max-loss, 0.3% soft trail at 2h+, stale-winner at +0.6%, PM-trail on uncovered signal variants). These do not break ride_it — they bound it. They are product/design decisions for the CEO, not correctness blockers.

## Live Readiness: Will the next ride_it trade use the ride_it exit?

**YES — with confidence, backed by live evidence:**
1. Current pipeline code is loaded post-fix (pipeline cycles at 02:10–02:14 UTC > commits 01:46/01:55; `[RIDE-IT-P1]` lines show the *widened* SL behavior that only the fixed code produces).
2. An actual ride_it trade (SUPER `trend-ride+`) is being managed by ride_it **right now**, with ride_it's phase-1 SL winning the DB write race each cycle.
3. Both guardians bypass it in production (1 of 2 open positions visible to them).
4. UNIVERSAL_MAX_HOLD will not kill ride_it trades at 8h (exemption verified; ride_it's own 24h max hold is the backstop).
5. Candle data for ATR/volume/momentum is fresh and sufficient on active tokens; price_collector timer active.

**Caveats to watch on the first live rides:** Issue #1 (PM/cut_loser interference on `mover-`/underscore-variant signals), Issue #2 (SOFT TRIGGER tightening at 2h+ if trade is negative), Issue #3 (hard_max_loss at -1.0% caps the "survival" SL). First exits will likely be `atr_tp_hit` (~2.2% VOL-GATE TP), `ride_it_exit` (trail/momentum/max-hold), or `hard_max_loss` — all expected paths.

---

*Verified by: bug_hunter (fresh pass). All tests executed against live code and live databases on 2026-10-06 02:00–02:15 UTC. Simulations patched `_persist_sl` to no-op — no live DB writes performed by this verification.*

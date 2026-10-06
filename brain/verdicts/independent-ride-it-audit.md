# Independent Audit — Ride-It Exit System vs Current Exit Stack

**Auditor:** independent subagent (fresh read, no priming; all numbers from code I ran and queries I executed)
**Date:** 2026-10-05 (DB "now" = 2026-10-05 23:23 UTC)
**Scope:** LONG trades closed in last 30 days, PostgreSQL `brain` DB; forward 5m candle replay from `/root/.hermes/data/candles.db`
**Artifacts:** `brain/verdicts/audit_scripts/sim_exit_strategies.py`, `brain/verdicts/audit_scripts/sim_results.json`

---

## === INDEPENDENT VERDICT ===

### Bottom line

**Do NOT switch any signal to ride_it in its current form.** The simulation shows the ride-it *concept* (wide ATR stop + late trailing) would improve expected PnL on several trend/continuation signals, but the *implementation* is a proven no-op in the live stack: in 16 days since deployment (2026-09-19) it has produced **0 exits out of 0 opportunities** — `SELECT exit_reason, COUNT(*) FROM trades WHERE exit_reason LIKE 'ride_it%'` → **0 rows, all-time**. Three structural defects make it inert (details in §5), and the one signal it is actually configured on (`mover+`) is one where the simulation says ride-it *hurts*.

If the goal is "let winners run" on specific signals, the data supports a **fixed** ride-it (or simply wider SL + later trail) on a short list: **volume-breakout-long+, doji-bottom-long, bb_bounce_v2_long, grind-trend+, pump-chain+**. It actively hurts: **mover+, slow_grind, sma20_dip, bb-bounce-v2-long+, rr-struct+**.

---

### 1. Which signals currently use which exit configs

Verified by replicating `position_manager._match_exit_config` (lines 2715–2753, incl. the 2026-09-30 rev-2 version-suffix fix) against `SIGNAL_EXIT_CONFIG` (hermes_constants.py:1638–1693), and cross-checked against actual exit_reason distributions in the DB (which engine actually closed each trade).

| Signal (30d, LONG) | n | Config match | Exit engines actually observed in DB (exit_reason → n, WR) |
|---|---|---|---|
| pump-chain+ | 90 | `pump_exit` | atr_sl_hit → 66 @40.9%; pump_exit_dead_money → 9 @55.6%; PM trail → 5; rr_engine_support_br → 5; atr_trail_hit → 2; hard_max_loss → 2; pump_exit_momentum → 1 |
| bb-squeeze+ | 67 | **None → default** | profit-monster-trail → 49 @83.7%; **hard_max_loss → 15 @0%**; atr_sl → 1; atr_trail → 1; hard_sl → 1 |
| pump_chain | 41 | `pump_exit` (but PM bypass does NOT match — see §6) | **profit-monster-trail → 25 @96%**; atr_sl → 9; cut-loser-CL-T1 → 6; HL_CLOSED → 1 |
| bb-bounce-v2-long+ | 33 | None → default | PM trail → 24 @70.8%; CL-T1 → 5; atr_sl → 2; HL → 1; hard_sl → 1 |
| bb_bounce_v2_long | 28 | None → default | PM trail → 17 @94.1%; CL-T1 → 7; atr_sl → 4 |
| volume-breakout-long+ | 24 | **None** (rev-2 fix excluded it) + **PM-trail bypassed** via `'volume-breakout'` substring → **ATR SL/TP only** | atr_sl_hit → 17 @64.7%; hard_tp → 2; hard_sl → 2; atr_trail → 1; HARD_SL_FAILED → 1; hard_max_loss → 1. **No PM exits, no ride_it exits.** |
| mover+ | 22 | `ride_it` | atr_sl_hit → 13 @30.8%; profit-monster-trail → 7 @100%; hard_max_loss → 1; UNIVERSAL_MAX_HOLD → 1. **Zero ride_it exits.** |
| bb-bounce-v3-long+ | 20 | None → default | PM trail → 13 @76.9%; hard_max_loss → 6; UNIVERSAL_MAX_HOLD → 1 |
| sma20_dip | 19 | None → default | PM trail → 10 @80%; CL-T1 → 9 |
| grind-trend+ | 18 | None → default | PM trail → 14 @64.3%; CL-T1 → 3; atr_sl → 1 |
| coiled_spring | 18 | None → default | PM trail → 9 @88.9%; CL-T1 → 8; atr_sl → 1 |
| doji-bottom-long | 16 | None → default | PM trail → 11 @81.8%; atr_sl → 4; hard_max_loss → 1 |
| slow_grind | 15 | None → default (PM_TRAIL_BYPASS has `'slow-grind'` hyphens — does NOT match `slow_grind`) | CL-T1 → 6 @0%; profit-monster-T1 → 6 @100%; atr_sl → 3 @0% |
| rr-struct+ | 15 | `rr_engine` | atr_sl_hit → 7 @71.4%; PM trail → 5 @100%; rr_engine_support_br → 2; CL-T1 → 1 |
| trend-ride+ | 3 (all-time) | `ride_it` | n=3 closed, 100% WR — **sample far too small to evaluate**; 2 still open |

Config constants (all verified in `hermes_constants.py`):
- `TRAILING_ACTIVATION_PCT = 0.0040`, `TRAILING_DISTANCE_PCT = 0.0120` (lines 708–709) — govern **brain/HL guardian** trailing, stored per-trade (live data: avg trail_act 0.004–0.006, trail_dist 0.010–0.012 after AB-test variants).
- `PM_TRAIL_ACTIVATE_PCT = 0.004`, `PM_TRAIL_DISTANCE_PCT = 0.002` + `PM_TRAIL_TIERS` (0.2/0.5/0.8/1.2% by peak profit) — the **profit_monster** paper-side trail, which is what "default PM trail" actually means for unlisted signals. Both trail systems run simultaneously on live trades.
- Ride-it constants (lines 3796–3819): SL phase1 = `min(max(2.0×ATR1h, 1.3%), 2.5%)`; trail activates at **2%** profit, distance **1.2%**; momentum exit after 2h at >1% profit + 2 consecutive 5m closes < −0.5%; volume-spike override ≥5× avg-20 vol AND |profit|≥3% → 0.5% trail; max hold 24h; phase1→2 at 2h.
- Live initial SL: `ATR_SL_MIN_INIT=0.013`, `ATR_SL_MAX_INIT=0.020`; stored sl_distance avg 1.20–1.63% per signal. `UNIVERSAL_MAX_HOLD_MINUTES = 480` (8h) force-closes everything.
- `CUT_LOSER`: CL_TIER1 window now [−2.5%..−1.0%] (inverted-bug fixed 2026-10-02; before that T1 fired zero for 3 days); `CL_HARD_STOP_PCT=-3.0`. **cut_loser does NOT exempt ride_it signals** (cut_loser.py reuses `PROFIT_MONSTER_BYPASS_SIGNALS`, which does not contain any ride_it key).

### 2. Actual performance & exit-path pathologies (30d, LONG, n≥15)

Leverage-normalized: all 429 trades are live Hyperliquid (paper=false), avg leverage ~4.1x; `pnl_pct` in DB is leveraged (`pnl_pct/leverage == price_move_pct` exactly — verified row-by-row). Win rate from `pnl_usdt > 0` is leverage-safe.

| Signal | n | WR | avg hold | win hold | loss hold | quick-loss % of losers | avg price-move | total USDT |
|---|---|---|---|---|---|---|---|---|
| pump-chain+ | 90 | 44.4% | 2.01h | 2.60h | 1.53h | **32.0%** | +0.21% | +$2.04 |
| bb-squeeze+ | 67 | 62.7% | 0.84h | 0.71h | 1.05h | **40.0%** | +0.02% | +$0.20 |
| pump_chain | 41 | 68.3% | 1.12h | 0.99h | 1.39h | 7.7% | +0.18% | +$1.11 |
| bb-bounce-v2-long+ | 33 | 54.5% | 1.27h | 1.50h | 1.00h | **40.0%** | +0.01% | −$0.32 |
| bb_bounce_v2_long | 28 | 64.3% | 1.94h | 2.03h | 1.77h | 20.0% | +0.08% | +$0.18 |
| volume-breakout-long+ | 24 | 66.7% | **3.14h** | **3.67h** | 2.09h | 12.5% | **+0.68%** | **+$3.04** |
| mover+ | 22 | 54.5% | 1.73h | 1.49h | 2.03h | 10.0% | −0.15% | −$0.99 |
| bb-bounce-v3-long+ | 20 | 50.0% | 2.13h | 1.36h | 2.91h | 20.0% | −0.10% | −$0.35 |
| sma20_dip | 19 | 42.1% | 0.85h | 0.50h | 1.10h | 18.2% | −0.35% | −$0.73 |
| grind-trend+ | 18 | 50.0% | 1.09h | 1.39h | 0.79h | 22.2% | +0.16% | +$0.24 |
| coiled_spring | 18 | 44.4% | 1.96h | 1.81h | 2.08h | 10.0% | −0.23% | −$0.58 |
| doji-bottom-long | 16 | 68.8% | 2.89h | 2.64h | 3.43h | 20.0% | +0.29% | +$0.66 |
| slow_grind | 15 | 40.0% | 1.79h | **3.44h** | 0.70h | **33.3%** | −0.47% | −$0.80 |
| rr-struct+ | 15 | 73.3% | 3.37h | 2.81h | **4.92h** | 0.0% | +0.41% | +$0.59 |

**Quick-loss ≠ premature exit.** High quick-loss rates (bb-squeeze+ 40%, bb-bounce-v2-long+ 40%, slow_grind 33%, pump-chain+ 32%) co-occur with `hard_max_loss`/`cut-loser` exits at 0% WR — these are trades that dumped immediately after entry (bad entries), not trends cut short. Simulation confirms: widening the stop on bb-squeeze+ or slow_grind makes them *worse* (§4). The genuine "trend cut short" candidates are the ones with **long win holds**: volume-breakout-long+ (3.67h), rr-struct+ (2.81h), doji-bottom-long (2.64h), pump-chain+ (2.60h).

**volume-breakout-long+ is the system's best signal and it runs on no profit engine at all** — PM bypassed via `'volume-breakout'` substring, ride_it not matched (rev-2 fix), only ATR SL/TP + hard_tp. +$3.04 on 24 trades.

### 3. Simulation methodology

`brain/verdicts/audit_scripts/sim_exit_strategies.py`: 429 trades (14 signals + trend-ride+), real entry_price from DB, forward 5m candles replayed from `candles.db` (Sep 6–Oct 5 coverage; 0 trades skipped). Conservative candle rules: SL checked against candle low before the candle high updates the trail (no intra-candle look-ahead); open-below-SL exits at open; max hold exits at candle close; data-end exits at last close. ATR(14) computed on 1h candles at entry time, chronologically (correct Wilder pairing).

Strategies:
- **CUR-A** (task spec "current"): SL −1.5%, trail activates 0.4% profit, distance 1.2%, ratchet, no cap.
- **CUR-B**: PM trail tiers (0.4% act; 0.2/0.5/0.8/1.2% tiers), SL −1.5%.
- **CUR-C** (realistic current default): CUR-B + cut_loser cut at −1.0% + 8h universal max hold.
- **RIDE-A** (task spec ride_it): SL = entry×(1−min(max(2×ATR1h,1.3%),2.5%)), no trail <2% profit, trail 1.2% at ≥2% peak, 24h max hold.
- **RIDE-B**: RIDE-A + momentum exit + volume-spike override (full implementation).
- **RIDE-C**: RIDE-A under the *live overlay* — cut_loser at −1.0% + 8h universal hold (what ride_it actually experiences in production today).

Validation: CUR-C reproduces actual WR closely on several signals (bb_bounce_v2_long sim 64.3% = actual 64.3%; pump_chain sim 70.7% vs actual 68.3%; volume-breakout sim 70.8% vs actual 66.7%). Spot-checks of individual trades confirm entry prices align with first forward candle within ±0.07% and SL/trail logic fires on the candles it should.

### 4. Simulation results (price-move %, unlevered, n=429)

| | WR | avg PnL | avg hold | exit mix |
|---|---|---|---|---|
| ACTUAL (DB, leverage-normalized avg of pnl_pct/lev ≈) | 56.0% | +0.19% | — | — |
| CUR-A (task "current") | 43.4% | +0.15% | 5.37h | sl 425, data_end 4 |
| CUR-B (PM tiers) | 77.2% | +0.16% | 3.63h | sl 428 |
| CUR-C (realistic current) | 70.4% | +0.11% | 3.27h | sl 313, cut_loser 112, 8h hold 4 |
| **RIDE-A (pure ride_it)** | **53.4%** | **+0.38%** | 9.76h | sl 401, 24h max hold 22, data_end 6 |
| RIDE-B (full impl) | 53.4% | +0.38% | 9.76h | **identical to RIDE-A** |
| RIDE-C (ride_it + live overlay) | 38.2% | +0.20% | 5.68h | sl 122, **cut_loser 241**, 8h hold 63 |

**RIDE-A vs CUR-A** (pure concept vs task's current spec): ride-it wins on WR in 13/15 signals and on PnL in 10/15. Per-signal RIDE-A / CUR-A / CUR-C (WR% / avg PnL%):

| Signal | RIDE-A | CUR-A | CUR-C | verdict |
|---|---|---|---|---|
| pump-chain+ | 56.7 / +0.79 | 48.9 / +0.39 | 74.4 / +0.24 | ride-it improves PnL & WR vs CUR-A |
| bb-squeeze+ | 47.8 / +0.17 | 32.8 / −0.05 | 71.6 / +0.16 | PnL ~tie vs realistic current; WR much worse |
| pump_chain | 53.7 / +0.36 | 51.2 / +0.30 | 70.7 / +0.15 | ride-it PnL better, WR worse than actual 68.3% |
| bb-bounce-v2-long+ | 45.5 / −0.32 | 33.3 / +0.06 | 78.8 / +0.12 | **ride-it hurts PnL** |
| bb_bounce_v2_long | 67.9 / +1.02 | 57.1 / +0.22 | 64.3 / 0.00 | ride-it clearly improves (pure) |
| volume-breakout-long+ | 70.8 / **+1.56** | 58.3 / +0.62 | 70.8 / +0.12 | **strongest ride-it case** |
| mover+ | 40.9 / −0.39 | 36.4 / −0.11 | 68.2 / +0.17 | **ride-it hurts** (WR & PnL) |
| bb-bounce-v3-long+ | 45.0 / +0.05 | 35.0 / +0.02 | 70.0 / +0.03 | ~neutral |
| sma20_dip | 36.8 / −0.67 | 42.1 / −0.06 | 52.6 / −0.28 | **ride-it hurts** |
| coiled_spring | 55.6 / +0.49 | 16.7 / −0.29 | 66.7 / +0.02 | pure ride-it helps; overlay washes out |
| grind-trend+ | 72.2 / +0.68 | 50.0 / +0.12 | 72.2 / +0.17 | ride-it improves PnL, WR ties |
| doji-bottom-long | 75.0 / +1.40 | 62.5 / +0.23 | 68.8 / +0.10 | **ride-it clearly improves (pure)** |
| slow_grind | 20.0 / −1.32 | 6.7 / −0.82 | 46.7 / −0.40 | **ride-it hurts** (signal failing anyway) |
| rr-struct+ | 53.3 / +0.32 | 66.7 / +0.83 | 80.0 / +0.32 | **ride-it hurts** (rr_engine works) |
| trend-ride+ | 66.7 / +0.41 | 66.7 / +0.41 | 100 / +0.35 | n=3, no conclusion |

**RIDE-C is the reality check:** under today's live overlay, ride-it's WR collapses to 38.2% because cut_loser chopped 241/429 trades at −1.0% before the wide stop or late trail could matter. Even so avg PnL (+0.20%) edges CUR-C (+0.11%) — the late trail captures bigger winners — but at a WR cost (38% vs 70%) that would look like a disaster in live monitoring and would likely trip loss-cooldown/losers-list machinery.

**RIDE-B ≡ RIDE-A exactly:** the momentum exit and volume-spike override fired **zero times** across 429 simulated trades. Momentum exit requires >1% profit AND 2 consecutive 5m closes each < −0.5% after 2h — structurally near-dead. Spike override needs ≥5× volume AND ≥3% move — also near-dead. Two of ride-it's three "phase 2" features are dead code in practice.

### 5. Ride-it implementation bugs & edge cases (all verified in code)

1. **`_get_atr` off-by-one — ATR systematically inflated.** `ride_it_exit.py:54–68` fetches 1h candles `ORDER BY ts DESC` (newest first) then computes TR as `max(h−l, |h−pc|, |l−pc|)` with `pc = rows[i-1][3]` — that's the **newer** candle's close, not the previous one. Measured on real data: CRV +14%, BABY +62%, **AVAX 2.03× inflation** (correct 1.43% vs buggy 2.89%). The same reversed-pairing bug exists in `position_manager.py:2682–2685` (sl_zones) and `position_manager.py:2789–2794` (pump_exit) — **three copies of one bug**. Impact on ride-it: phase-1 SL pushed toward/into the 2.5% cap → wider stops than intended → bigger SL losses.
2. **Phase-1 "survival wide SL" can never widen.** `manage_ride_it_exit` phase 1 (lines 343–362) only updates when `phase1_sl > current_sl` for LONG — i.e., only ever **tightens**. With live initial SL at 1.27–1.63% and simulated ride-it SL averaging 2.28% (floor binds only 3% of the time; `2×ATR1h` avg = 3.08%, so the 2.5% cap binds for most trades), the update almost never fires, and when it does it tightens. **The design intent ("wide SL to survive the wait") is not implementable through this code path.** This is the root reason ride-it is a no-op: the live trade keeps its normal ATR SL.
3. **`RIDE_IT_MAX_HOLD_HOURS = 24` is dead.** `UNIVERSAL_MAX_HOLD_MINUTES = 480` (8h) force-closes every position first (position_manager.py:3279–3293). No ride-it trade can ever reach its 24h exit. Sim: 22 RIDE-A trades hit 24h max-hold; under the real overlay (RIDE-C) 63 trades die at 8h instead.
4. **No exemption from cut_loser / PM trail.** `SIGNAL_EXIT_CONFIG` maps a signal to `ride_it` but nothing disables the other engines. cut_loser.py reuses `PROFIT_MONSTER_BYPASS_SIGNALS` (no ride_it keys) → cut_loser cuts ride-it trades at −1.0%; profit_monster PM trail (0.4%/0.2%) exits winners at ~0.6% from peak — long before ride-it's 2% activation. Live proof: mover+ (ride-it configured) exits are 13× `atr_sl_hit` + 7× `profit-monster-trail` + 0× ride_it.
5. **Momentum exit can only protect winners.** Line 376: `if profit_pct > 0.01` (also: hardcoded constant — violates the repo's no-magic-numbers rule). Losers in freefall get no momentum exit; they ride to the wide SL (or to cut_loser in the live stack).
6. **ATR=0 → full no-op.** `_get_atr` returns 0 with <15 closed 1h candles (new/illiquid tokens) → `manage_ride_it_exit` returns HOLD immediately. Combined with bug #2, ride-it contributes nothing on new tokens.
7. **`_parse_hold_time` failure → phase-1 forever.** Unparseable `open_time` → hold_hours=0 → never reaches phase 2 → no trail ever.
8. **Dead import:** `RIDE_IT_TP_PHASE1_MULT` imported (line 34) and never used — phase-1 TP was designed and abandoned silently.
9. **Volume-spike override ordering:** checked before max-hold/momentum; when `should_update` is False it returns HOLD early, skipping the other checks for that cycle (self-heals next cycle; minor).
10. **trend-ride signal itself:** enabled (`TREND_RIDE_LONG_PLUS_ENABLED=True`), source `trend-ride+` → ride_it config; RSI band tightened to 50–65. Only 3 closed trades all-time — not enough to judge; leave config unchanged.

### 6. Config-matcher & naming bugs found along the way (severity: high — they decide which engine runs)

1. **`volume-breakout-long+` (best signal: 24T, 66.7% WR, +$3.04) matches NOTHING.** Exact match fails; rev-2 `_match_exit_config` deliberately excludes direction-word remainders (`-long+` is not a `-vN` version tag), so `'volume-breakout+'` never matches it. It also bypasses PM trail via the `'volume-breakout'` substring in `PROFIT_MONSTER_BYPASS_SIGNALS`. Net: the top LONG signal runs on raw ATR SL/TP with no profit-taking engine whatsoever.
2. **Hyphen/underscore forks create two different exit systems for the same signal family.** `'pump-chain+'` is PM-bypassed (substring `'pump-chain'`) → pump_exit/ATR stack → **44.4% WR**. `'pump_chain'` (underscore) is NOT bypassed → PM trail fires → **68.3% WR, 25 trail exits at 96% WR**. Same fork: `PM_TRAIL_BYPASS_SIGNALS = ('slow-grind',...)` never matches live signal `slow_grind`. The better-performing variant is the accident.
3. **`rr-struct+` gets both rr_engine and PM trail** (bypass entry commented out 2026-09-25) — works (73.3% WR) but the config intent is muddy.

### 7. Recommendations

**Do not switch anything to ride_it today** — it changes nothing measurable (zero exits in 16 days; preempted by every other engine), and its one live beneficiary candidate would be harmed by bugs #1–#4 anyway.

**If ride-it is to be kept, fix in this order (each verified against the sim):**
1. Fix `_get_atr` off-by-one in all three copies (ride_it_exit.py, position_manager sl_zones, pump_exit) — TR must pair each candle with the **older** candle's close.
2. Make phase-1 SL able to **widen** (update when `phase1_sl != current_sl`, clamp below initial SL; or set ride-it SL at trade open via decider_run instead of retrofitting in position_manager).
3. Exempt ride-it signals from cut_loser and PM trail (add them to the bypass lists, or gate profit_monster/cut_loser on exit-config == 'ride_it'), and reconcile `RIDE_IT_MAX_HOLD_HOURS` (24h) with `UNIVERSAL_MAX_HOLD_MINUTES` (8h) — today the 8h hold silently wins.
4. Either wire the momentum exit to fire for losers too, or delete it + the spike override (both are dead: 0 fires in 429 sims) — and replace the hardcoded `0.01` with a constant.

**Then switch (fixed ride-it, pure semantics — RIDE-A results):**
- **volume-breakout-long+** — strongest case: longest win hold (3.67h), delayed spikes, sim +1.56% vs +0.12–0.62% current, WR 70.8% ≈ actual. Also fix its matcher gap (§6.1) regardless.
- **doji-bottom-long** — sim +1.40% vs +0.10–0.23%, WR 75%.
- **bb_bounce_v2_long** — sim +1.02% vs 0.00–0.22%, WR 67.9%.
- **grind-trend+** — sim +0.68% vs +0.12–0.17%, WR 72.2%.
- **pump-chain+** — sim +0.79% vs +0.24–0.39%; wide stop saves the 32% quick-loss shakeouts; but keep pump_exit's momentum/time exits as an overlay (its dead_money exits work: 9 @55.6% WR).

**Keep on current exits (ride-it hurts or adds nothing):**
- **mover+** — remove ride-it config today (it's inert anyway; simulation says ride-it worsens it: RIDE-A −0.39% vs CUR-C +0.17%). Its real problem is entries (13/22 SL hits at 30.8% WR), not exits.
- **rr-struct+** — rr_engine + PM trail delivers 73.3% WR; ride-it drops sim WR to 53.3%.
- **bb-squeeze+, bb-bounce-v2-long+, slow_grind, sma20_dip** — high quick-loss rates are entry-quality problems (hard_max_loss/cut-loser exits at 0% WR within 30min); a wider stop only makes each loss bigger. Fix entries or leave.
- **pump_chain, bb_bounce_v2_long** (underscore variants) — current PM-trail behavior already strong (96%/94% WR on trail exits); don't disturb.
- **trend-ride+** — n=3; leave until sample ≥15.

**Housekeeping (separate from ride-it):**
- Fix the hyphen/underscore exit-config forks (§6.2) — normalize signal names or make bypass/matcher both underscore+hyphen aware. This alone moved pump-chain family WR by 24 points.
- Decide what engine volume-breakout-long+ should run (§6.1) — it is currently unmanaged and still the top earner; do not break it while "fixing" the matcher.

---

### Evidence index
- Constants: `scripts/hermes_constants.py` — TRAILING_* (708–709), PM_TRAIL (1523–1609), SIGNAL_EXIT_CONFIG (1638–1693), RIDE_IT_* (3796–3819), TREND_RIDE_* (2242–2262), UNIVERSAL_MAX_HOLD (1030), CUT_LOSER (1729–1749).
- Exit logic: `scripts/position_manager.py` — `_match_exit_config` (2715–2753), ride_it branch (2901–2929), pump_exit (2755–2899), universal hold (3279–3293); `scripts/ride_it_exit.py` (full); `scripts/profit_monster.py:86–89,405–410`; `scripts/cut_loser.py:62–74`; `scripts/decider_run.py:564–621`; `scripts/signals/trend_ride_long.py` (full).
- Queries: per-signal stats, exit_reason distributions, stored SL/trail params, ride_it all-time exits (0 rows), leverage verification — all run against `brain` PostgreSQL on 2026-10-05.
- Simulation: `brain/verdicts/audit_scripts/sim_exit_strategies.py` + `sim_results.json` (429 trades, 6 strategy variants, candle replay with no intra-candle look-ahead; spot-checks validated entry alignment ±0.07%).
- ATR bug measurement: correct chronological Wilder ATR vs ride_it `_get_atr` logic on CRV/AVAX/BABY at real entry times (ratios 1.14× / 2.03× / 1.62×).

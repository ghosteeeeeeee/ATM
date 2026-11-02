# MFE-Exit Performance Report + Loss-Side Options — 2026-11-01

**Prepared for:** T (CEO of Hermes) · **Status:** analysis only, no live changes in this report
**Report-only directive honored:** nothing in §4 was implemented.

---

## TLDR

1. **mfe-exit is working as armed.** 16 live closes: pre-arm era churned (0.6–7.7 min holds, fee-negative); armed era (peak ≥ 0.40%) is **8/8 wins, +1.60…+2.35% lev each, holds 17 min–5.4 h**, ≈ +$0.30 net of fees.
2. **Grid on all 83 closed mirror trades:** giveback **40% loses to 30% at every arm**; **arm 0.40% is the best-balanced** setting (0.20% makes ~26% more profit but cuts holds to 0.7 h; 0.65% doubles holds but after-fee profit collapses to ≈0; 1.0% blows up into floor hits). Shipped stack (pm-trail + mfe, arm 0.40, giveback 30%) = **+16.65 after fees, 77% WR** vs reality −45.01 after fees.
3. **Your pro-entry claim is confirmed:** 61% of mirror entries are ≥ +0.20% favorable within 15 min (median +0.28%); median time-to-peak 226 min at median peak +0.91% — winners develop over hours, which is why high arms fail.
4. **Loss side:** 22 of 28 losing trades (−95.8 of −111.3 lev%) closed via ratcheted ATR stop + HML (both ≈ −0.8…−0.9% price @5x). The **JUP HML shadow eval is due** (45 distinct trades ≥ pre-registered N=40). Options ladder in §4 — report only.

---

## 1. What was built (context, shipped earlier)

**mfe-exit:** close when price gives back **30% of the peak favorable move** (threshold = 0.7 × peak favorable %, both directions; engages only after peak ≥ `MFE_EXIT_ARM_PCT`).

| Constant (scripts/hermes_constants.py) | Value | Note |
|---|---|---|
| `MFE_EXIT_ENABLED` | True | revert lever = False |
| `MFE_EXIT_GIVEBACK_PCT` | 0.30 | T's spec |
| `MFE_EXIT_ARM_PCT` | 0.004 (0.40% price) | raised from 0.0 after no-arm churn |
| `MFE_EXIT_SIGNALS` | ('jup_yolo',) | mirror book only, substring scope |

- Implementation: `scripts/position_manager.py` section 7c (after UGB-PT, before time exits); fail-open on missing peak; CEO trades exempt; logged errors, never swallowed.
- Engine: `scripts/jup_exit_sim.py` (`replay_layers` walker) — **independently verified 288/288 replay match + 3/3 hand-checks** (verdict: `brain/verdicts/2026-10-31_mfe-exit-sim-independent-verify.md`, which REFUTED the original "+98 vs bg" headline as a strawman: honest figure +42 vs actual closes, p=0.135, n=45).
- Audit: bug_hunter **SHIP**; also patched pre-existing `cut_loser` missing-`continue` fall-through (`4b6631bf`, restored in `e56e7942` after a stale-staging commit reverted it).
- Commits: `e56e7942` (ship), `e40c3cf8` (arm), `82edb2bb` (grid analysis) — all pushed.

## 2. Live performance (16 `mfe_exit` closes)

| era | n | holds | outcome |
|---|---|---|---|
| pre-arm (peaks ≤ +0.21%) | 8 | **0.6–7.7 min** (one 366 min straggler) | ±$0.01 gross, **fee-negative** (fees.net_pnl −0.006/−0.018), 3 micro-losses, repeated HYPE LONG loss-cooldown blocks |
| **armed (peak ≥ +0.46%)** | **8** | **17 min – 5.4 h (avg ≈ 2.5 h)** | **8/8 wins**: +1.60, +1.60, +1.64, +1.68, +1.85, +1.89, +1.93, +1.95, +2.35% lev → gross +$0.38, ≈ **+$0.30 after fees** |

Examples: SOL SHORT +1.95% (5.4 h), HYPE LONG +2.35% (2.5 h), ETH LONG +1.68% (3.5 h). All exit details show peak ≥ 0.46% → genuinely armed. Total across 16: gross +$0.46.

No-arm churn root cause (fixed by `e40c3cf8`): threshold 0.7×peak on a +0.05% peak = +0.035% → closed any blip within minutes; fills on fast traverses below entry; fee (0.09% price round-trip) exceeded the entire win.

## 3. Grid backtest — 83 closed mirror trades (`analysis/mfe_exit_grid.py`)

Method: audited `replay_layers` engine, complete-bars filter, 12 h horizon, background stack = tightest floor (HML `CUT_LOSER`/lev vs ATR SL) + ATR TP + timeout. Fees = −0.45% lev/trade (0.09% × 5x).

```
row              WR%   gross  afterFee  avgHold  medHold  floor
g30_arm0.00      69   +36.50    -0.85    0.2h     0.1h      4
g30_arm0.20      85   +54.11   +16.76    0.7h     0.3h     11
g30_arm0.40  ←   77   +50.71   +13.36    1.2h     0.6h     19   (shipped arm)
g30_arm0.65      65   +38.58    +1.23    2.5h     1.1h     28
g30_arm1.00      45   -26.32   -63.67    4.0h     1.9h     42
g40_arm0.00      69   +34.79    -2.56    0.3h     0.1h      4
g40_arm0.20      85   +48.16   +10.81    0.8h     0.3h     11
g40_arm0.40      77   +40.87    +3.52    1.3h     0.7h     19
g40_arm0.65      65   +33.93    -3.42    2.6h     1.1h     28
g40_arm1.00      45   -29.41   -66.76    4.1h     2.1h     42
pm+g30_arm0.20   85   +56.29   +18.94    0.7h     0.3h     11   (combo)
pm+g30_arm0.40   77   +54.00   +16.65    1.2h     0.6h     19   (≈ shipped stack)
pm_actual (real) 64    -7.66   -45.01    1.5h     0.9h      —
bg (floor only)   30   -98.89  -136.24    5.7h     4.3h     52   (strawman baseline)
```

**Answers:**
- **Giveback 40% vs 30%: 30% wins at every arm** (arm 0.40: +40.87 vs +50.71 gross; +3.52 vs +13.36 after fees). A wider giveback only hands back more before closing.
- **Arm 0.40 vs alternatives:** 0.20 makes more profit (+54.11/+16.76) but holds collapse to 0.7 h; 0.65 survives 2.5 h but after-fee profit ≈ +1.23 (noise); 1.0 never engages on 42/83 → floor blowup (−26.32). **No setting delivers both longer holds AND more profit than 0.40** — the trade-off curve doesn't allow it on this book.
- Shipped combo `pm+g30_arm0.40` = **+16.65 after fees / 77% WR / 1.2 h avg hold** — best combined profile.

**Entry-quality note (T: "pros enter right after the peak/trough"):** first-15m favorable ≥ +0.20% on **61%** of entries (median +0.28%); median time-to-peak **226 min**, median peak **+0.91%** — confirms the claim and explains why arm 1.0% fails.

## 4. Loss-side options (REPORT ONLY — nothing implemented)

What actually closed losers (83 closed mirror trades, leveraged %):

| close_reason | n | sum | avg |
|---|---|---|---|
| atr_sl_hit (ratcheted ATR/SL stop) | 12 | −53.8 | −4.49 |
| hard_max_loss (HML) | 10 | −42.0 | −4.20 |
| mfe_exit | 3 | −0.8 | −0.27 |
| stale_exit | 2 | −11.1 | −5.55 |
| cut-loser-CL-T1 | 1 | −6.2 | −6.18 |
| UNIVERSAL_MAX_HOLD | 1 | −0.2 | −0.16 |

Stops + HML = **22 of 28 losses, −95.8 of −111.3** — both land ≈ −0.8…−0.9% price @5x. mfe-exit cannot manage losses (threshold strictly positive by design; its 3 losses avg −0.27).

**Options ladder (cheapest/strongest first):**

1. **Run the pre-registered JUP HML shadow eval — DUE NOW.** `[JUP-SHADOW-HML]` has **45 distinct trades ≥ N=40** for thresholds −0.65/−0.50 price vs the current −0.80 baseline (`CUT_LOSER_PNL=-4.00` @5x). Zero new code; enforce only if net-positive per the pre-registration (CEO previously rejected shipping −0.50 without exactly this data).
2. **jup-scoped never-armed TAT** (cut trades never reaching +0.40% peak within 45–60 min): the proven signal-scoped pattern — the universal version (MFE-CUT) failed candle-OOS at 40.2% false-kills, so this must ship shadow → OOS first. Candidate pool: bg row's 52 floor hits (avg −4 lev).
3. **Tighten `CUT_LOSER_PNL` −4.00 → −3.00** (−0.60% price @5x): protected constant — needs T/CEO sign-off. Note brain_auditor moved it *looser* (−6→−4) on 10-31; only reverse if shadow eval supports it.
4. **ATR-SL unit mismatch** (`compute_atr_sl_pct` tier thresholds fraction-vs-percent → SL de-facto fixed 2.50% system-wide, MED sideways finding): system-wide fix moves every signal's stop (CEO-level); scoped alternative = jup-only SL floor constant.
5. Minor: tighten `STALE_LOSER_*` (2 fires, avg −5.55 — slow bleed); ARM-BE/UGB-BE enforcement (shadows collecting, prior verdict PASS non-EXTREME); extend per-token loss caps (cooldowns currently 0.3→0.7 h). **Size cannot shrink — already at the $11.1 notional floor.**

## 5. Caveats

- Grid is **in-sample** (the book it would run on); fees are the uniform −0.45%/trade estimate (slippage not modeled); trades with unfinished 12 h horizons still drift — re-run `python3 analysis/mfe_exit_grid.py` after all horizons elapse.
- The "+42 vs actual closes" figure carries **p=0.135 (n=45)** — direction robust (+17…+36 band across intra-bar conventions), magnitude not decision-grade. Re-measure protocol: `brain/verdicts/2026-10-31_mfe-exit-sim-independent-verify.md`.
- Live armed-era sample = 8 trades over ~16 h — encouraging, not significant.

## 6. Artifacts

- Grid script: `/root/.hermes/analysis/mfe_exit_grid.py` (commit `82edb2bb`) · output: `/root/.hermes/data/mfe_exit_grid.json`
- Exit sim: `/root/.hermes/scripts/jup_exit_sim.py` · verdict: `/root/.hermes/brain/verdicts/2026-10-31_mfe-exit-sim-independent-verify.md`
- Constants/implementation: `scripts/hermes_constants.py` (`MFE_EXIT_*`), `scripts/position_manager.py` (7c)
- Commits: `e56e7942` (ship), `e40c3cf8` (arm), `82edb2bb` (grid) — pushed

---

## 7. CEO verdict (consult 2026-11-02, `ok rc=0`, brief `brief-mfe-exit-params-loss-options.md`)

**Q1 — RATIFY shipped arm 0.40 / giveback 0.30.**
- Giveback 40%: **reject** — strictly worse at every arm; nothing in the mechanics rewards it.
- Arm 0.20: **reject as default** — its +$2.29 after-fee edge is noise-grade (±2 dip events flip signs), moves holds 1.2h → 0.7h (opposite T's "survive longer" goal), and generates more fast-traverse closes that fill below threshold — slippage unmodeled, hits this class hardest.
- Adaptive giveback / time-component: **park as research only.** "A working exit > a cleverer exit." Live 8/8 is n=8 — never decision input.

**Q2 — loss-side ladder:**
- **(a) Run the JUP HML shadow eval NOW (due: 45 ≥ N=40)** with four mandated guardrails: (1) replay fills through the audited `replay_layers` engine, distinct-id basis — flags ≠ exit prices; (2) count winner preemption alongside loser savings (the 10-31 verdict's exact failure mode: −0.50 saved +$0.69, preempted 5 winners ≈ −$0.79 → net −$0.10); (3) sign-stability — net must survive ±2–3 dip-event perturbation, marginal net (< ~$0.50 at n=45) → extend sample, don't enforce; (4) fees in, enforce only per pre-registration via automatic-implementation.
- **(b) No action needed** — jup TAT shadow already shipped by brain_auditor #214 (2026-11-01): `JUP_TRAIL_ARM_TIMEOUT_SHADOW=True`, 90m. Do NOT shorten to 45–60m (45m fires on eventual winners; MFE-CUT OOS class = 40.2% fk). Enforce only after candle-OOS passes the standing gate (fk<20% AND net>0 AND n≥20).
- **(c) CUT_LOSER −4.00→−3.00: DEFER behind (a)** — tightening again on intuition before the pre-registered eval returns is churn; if (a) is net-positive → jup-scoped tighten first; global −3.00 only as a separate pre-registered shadow trial.
- **(d) ATR-SL unit mismatch: real bug, verified by execution** — `get_atr_pct` returns percent but `_atr_tier` compares against fraction thresholds (`ATR_PCT_LOW/HIGH_THRESH=0.01/0.015`) → every realistic ATR → 0.025 (2.50%) floor/ceil (CEO re-ran: 0.5/1.0/1.24/3.0 → all 0.025). Fix = one-line input normalization in `compute_atr_sl_pct`; **ship jup-scoped shadow first**, OOS, then widen — not defer, not system-wide now.

**Q3 — what's missing:**
1. **The exit isn't the drag — the entry is.** jup_yolo_mirrored is still **−$0.65 over 7d at 59.5% WR** (CEO-verified); worst family volume-buildup− (−$1.05, 34T). `STOP_TIGHTEN_SOURCES` (+$2.74/30d jup) already exists — check its coverage before building new exits. Exit micro-params vs entry quality: spend the hours on entries.
2. **Slippage unmodeled and asymmetric** — biases any faster/more-frequent-exit recommendation (arm 0.20) optimistic.
3. **Grid horizon incomplete** — re-run `analysis/mfe_exit_grid.py` before any parameter *change* (not needed for ratify).
4. **Loss-side 0% WR is not a finding** — HML/atr_sl are loss-only by construction; the levers are size-per-loss (already at $11.1 floor) and *when* we cut = (a)/(c)/(d).

**Bottom line: ratify Q1 as shipped; execute (a) with the four guardrails; (b) no action; defer (c) behind (a); fix (d) jup-scoped shadow-first.**

---

## 8. Execution record (2026-11-02, T: "proceed on CEO-approved fixes")

**(a) JUP HML shadow eval — EXECUTED, verdict REJECT×4 → NO enforcement (pre-registration honored).**
`analysis/jup_hml_shadow_eval.py` (four guardrails implemented: replay fills via audited `replay_layers` distinct-id / winner-preemption vs loser-savings legs in USD / sign-stability bootstrap + flip count / fees noted delta-neutral):

| stack | -0.65 floor Δ | -0.50 floor Δ | verdict |
|---|---|---|---|
| pm + mfe (shipped), n=84 | **−$0.30** (save +$0.48 / preempt −$0.78) | **−$0.42** (+$0.97 / −$1.39) | REJECT / REJECT |
| pm-only, n=84 | **−$0.27** (+$0.48 / −$0.75) | **−$0.38** (+$0.97 / −$1.35) | REJECT / REJECT |

Winner preemption (5 and 10 winners → non-wins) beats loser savings on both thresholds, both stacks — same failure mode as the 2026-10-31 trades-level check, now confirmed by candle replay. `HARD_MAX_LOSS_PCT`/`CUT_LOSER_PNL` untouched (bug_hunter verified: zero lines in the HML region). Shadow keeps collecting as drift monitor; re-run only if the exit stack changes materially.

**(d) ATR-SL corrected-value shadow — SHIPPED (jup-scoped, zero behavior).**
- `tpsl_utils.compute_atr_{sl,tp}_pct_norm()` added (originals byte-identical, additive-only verified): input normalized percent→fraction before `_atr_tier`. Proof of bug: ATR 0.5/1.0/1.24/3.0 → shipped path **all 2.50%**; corrected path 1.50/1.50/1.50/2.50% (TP: 1.50–2.00%).
- `position_manager` `[JUP-SHADOW-ATRSL]` block (after trail-shadow, before HML check): logs once per open jup trade per pipeline minute (fresh subprocess — dedup comment corrected by bug_hunter), direction-aware db levels, logged excepts. **152 lines live, 0 errors** (e.g. #16700 BTC LONG: act_sl 2.50% vs fix_sl 1.50%, db_sl 0.77 = ratcheted stop).
- Eval on DISTINCT `[JUP-SHADOW-ATRSL]` ids → then OOS → widen (CEO order; system-wide `compute_atr_sl_pct` change NOT made).

**Audit:** bug_hunter **SHIP** (`bad2f4a3` — 3 comment/label patches; REJECT×4 re-reproduced independently). Tree note: the change-set rode into `c556a3c2` when a concurrent task committed `git add -A` mid-audit (content verified == audited).

**Open items for CEO (bug_hunter MEDs, need sign-off, not patched):**
1. Eval's `min_flips_to_erase` sign-fragility gate is degenerate for net>0 — if a future run comes back net-positive, ENFORCE would fire with only the $0.50 marginal gate active (CI/flip gates inert). Metric direction fix = pre-registration change → CEO.
2. Eval baseline omits `min()` with ATR-SL floor (inert today: all 84 jup trades are 5x; diverges only if non-5x mirror trades appear).
- Sideways: `position_manager:3866` ATR-floor HML shadow still bare `except: pass` (the exact swallow class we eliminated elsewhere); `tpsl_utils_debug.py` is an unreferenced divergent copy — cleanup candidates.

**(b) TAT: no action** (already shipped by brain_auditor #214, 90m). **(c) CUT_LOSER −3.00: deferred** behind (a) per CEO — (a) now REJECTs, so tightening stays deferred until the exit stack changes materially.

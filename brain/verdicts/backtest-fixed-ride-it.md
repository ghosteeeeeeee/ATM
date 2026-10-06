# Backtest: FIXED ride_it exit vs current exit stack

**Date:** 2026-10-06 · **Analyst:** Quant desk (subagent) · **Status:** Complete
**Verdict:** 🟡 **Ride_it does NOT beat the current exit stack — aggregate is WORSE by 6.1 pct-points over 377 trades. Do not expand ride_it mapping on this evidence.**

## Artifacts

| File | Contents |
|------|----------|
| `brain/verdicts/audit_scripts/sim_fixed_ride_it.py` | Full simulation (replay over actual 5m candles) |
| `brain/verdicts/audit_scripts/sim_fixed_results.json` | All numbers below (machine-readable) |

## Data & method (what was actually run)

- **Trades:** PostgreSQL brain DB (`BRAIN_DB_DICT`), `status='closed' AND direction='LONG' AND close_time >= NOW()-30d`, matched by signal part to 8 families → **380 classified, 377 simulated** (2 tokens had no candles, 1 had insufficient coverage).
  Families: ride_it candidates `volume-breakout-long+` (27), `doji-bottom-long` (16), `bb_bounce_v2_long` (67, incl. `bb-bounce-v2-long+` variant), `grind-trend+` (18), `pump-chain+` (144, incl. `pump_chain`/`pump-chain-v5` variants); controls `bb-squeeze+` (70), `mover+` (20), `rr-struct+` (15). Combo signals (e.g. `rs-s36,volume-breakout-long+`) matched by part.
- **Candles:** `data/candles.db` via `scripts/paths.py` — 5m replay per trade from open_time; 1h candles for ATR. Candle coverage: 2026-09-06 → 2026-10-06.
- **ATR:** computed per the bug-fixed path — 1h query DESC, **reversed to ASC**, TR with true previous close, ATR(14). Phase-1 SL refreshed from live ATR during replay (exercises the widen fix).
- **Replay:** candle-by-candle on 5m closes; adverse exits evaluated against candle low (fill at trigger level); trail/stale/soft/max-hold evaluated on close. All parameters imported from `hermes_constants.py` (no hardcoding).
- **Stacks simulated per task spec:** `current` (1.5% SL, HARD_MAX -1.0%, PM trail 0.4%/1.2%, SOFT PEAK-EXIT, stale_exit, 8h hold), `ride_it` (phase-1 SL 2.0x ATR ∈ [1.3%, 2.5%], HARD_MAX -1.0%, phase-2 trail 2%/1.2% + momentum + vol-spike override, SOFT, stale, 24h hold). Sensitivities: `current_tiered` (production PM_TRAIL_TIERS), `current_pump` (production pump_exit for pump-chain+), `ride_it_nohardmax` (WARN #3 probe).

## Step 4 — Results per signal

### Ride_it candidates (task-spec stacks, both applied to same trades)

| Signal | n | Win% cur → ride | Avg PnL% cur → ride | Total PnL cur → ride | Δ total | Verdict |
|---|---|---|---|---|---|---|
| volume-breakout-long+ | 27 | 44.4 → 40.7 | +0.15 → +0.10 | +3.94 → +2.82 | **-1.12** | ❌ worse |
| doji-bottom-long | 16 | 56.2 → 56.2 | +0.17 → +0.18 | +2.66 → +2.87 | **+0.21** | 🟡 noise-level better |
| bb_bounce_v2_long | 67 | 50.7 → 50.7 | +0.04 → +0.04 | +2.79 → +2.73 | **-0.06** | ➖ flat |
| grind-trend+ | 18 | 44.4 → 44.4 | +0.19 → +0.19 | +3.34 → +3.34 | **0.00** | ➖ identical* |
| pump-chain+ | 144 | 46.5 → 45.1 | +0.18 → +0.16 | +26.32 → +22.59 | **-3.73** | ❌ worse |

\* grind-trend+: **zero** ride_it-specific exits fired (no trade reached +2% before stale_winner/soft/unmodeled close) — the two stacks produced byte-identical exit mixes.

### Controls (signals that should NOT use ride_it)

| Signal | n | Win% cur → ride | Total PnL cur → ride | Δ total | Verdict |
|---|---|---|---|---|---|
| bb-squeeze+ | 70 | 57.1 → 58.6 | -0.38 → -0.12 | +0.26 | 🟡 noise |
| mover+ | 20 | 45.0 → 45.0 | +0.49 → -0.87 | **-1.36** | ❌ worse (confirms 2026-10-05 audit) |
| rr-struct+ | 15 | 60.0 → 60.0 | +1.96 → +1.64 | -0.32 | ❌ slightly worse |

### Aggregate (377 trades)

| Metric | Current | Ride_it (fixed) | Δ |
|---|---|---|---|
| Win rate | 49.9% | 49.3% | -0.6 pp |
| Avg PnL% | +0.109 | +0.093 | -0.016 |
| **Total PnL (pnl_pct-sum)** | **+41.12** | **+35.01** | **-6.11 (-14.9% relative)** |
| Avg hold | 1.17h | 1.21h | +0.04h |

### Exit reason distribution (aggregate, task-spec stacks)

| Exit reason | Current | Ride_it |
|---|---|---|
| unmodeled_close (no spec'd trigger by close_time) | 162 | 185 |
| hard_max_loss (-1.0%) | 100 | **114** |
| pm_trail | 57 | — |
| stale_winner (+0.6%/60min) | 35 | 36 |
| soft_peak_exit | 23 | 29 |
| ride_it_trail (2% activation, 1.2% dist) | — | **13** |
| ride_it_momentum / phase1_sl / spike_trail | — | **0 / 0 / 0** |

**Why ride_it loses:** its designed profit engine barely activates. Trail activation at +2% fired **13 times in 377 trades**; momentum exit and vol-spike override fired **zero** times; phase-1 SL fired **zero** times. Profit-taking degrades to stale_winner at +0.6% or unmodeled close, while losses still hit the same -1.0% hard stop — and hit it **more often** (114 vs 100) because trades survive longer without PM trail's early exits. The current stack's PM trail books +0.4%–1% winners 57 times; ride_it gives that up hoping for +2% that (almost) never comes.

## Step 5 — Overall assessment

### Which signals improve / worsen
- **Improve:** doji-bottom-long (+0.21) and bb-squeeze+ control (+0.26) — both far inside noise for n=16/70.
- **Worsen:** pump-chain+ (-3.73, the largest sample and largest loss), volume-breakout-long+ (-1.12), mover+ (-1.36 control), rr-struct+ (-0.32 control), bb_bounce_v2_long (-0.06 flat).
- **Flat:** grind-trend+ (0.00 — ride_it path never engaged).

### Is the aggregate improvement meaningful?
**There is no aggregate improvement.** Ride_it is **-6.11 pct-points** worse over 377 trades, win rate -0.6pp, with the worst outcome on the highest-volume signal (pump-chain+, n=144). Not one signal shows a meaningful positive delta. **Honest verdict: the fixed ride_it implementation, as configured and layered under the current overlay stack, does not help.**

### Impact of HARD_MAX_LOSS capping ride_it's survival SL (WARN #3)
The WARN is confirmed and quantified:

1. **Ride_it's phase-1 survival SL (1.3%–2.5%) is dead code under the overlay stack.** It fired **0 times** in 377 trades with HARD_MAX_LOSS active. Even in the `ride_it_nohardmax` probe (hard stop removed), it fired only **3 times** — because SOFT PEAK-EXIT (0.3% trail at 2h when pnl≤0) and stale_loser (-1.0%/8min) catch trades before they ever reach -1.3%. The "survive the noise" design never gets to fire: the loss side is capped at ~-1.0% by overlays regardless.
2. **The -1.0% hard stop is currently HELPING ride_it, not hurting it.** Removing it (probe): aggregate ride_it improves +2.82 (WR +2.4pp) — but that's mostly volume-breakout-long+ (+5.07) and doji (+2.37) recovering losers that would otherwise bleed deeper; pump-chain+ gets **much worse (-7.22)** — high-vol momentum losers ride past -1.0% and exit deeper via stale_loser/unmodeled close. Even with the hard stop removed, ride_it aggregate (37.83) still loses to current (41.12).
3. **Net:** HARD_MAX_LOSS does not "cap" a working survival mechanism — it substitutes for one that never activates. Ride_it's edge case (a trade that dips -1.5% then runs +5%) is rare: only 3 trades in 377 even reached the phase-1 SL level, and production evidence (below) shows the loss-cutting machinery realizes losses well beyond -1% anyway.

## Production-reality caveats (read before acting)

These numbers come from actually running the code on actual candles, but three facts limit how far the absolute figures translate to production:

1. **All 380 trades are live (`paper=False`)** — managed by HL guardian/brain stack, not position_manager's paper path. Actual 30d exit reasons for these families show the spec'd overlays barely fire in production: **zero `stale_exit` rows** (stall conditions strict; `STALE_ROTATION_ENABLED=False`), `hard_max_loss` only ~9 exits (realizing avg **-3% to -4.8%** — gapped through -1.0% on wake latency). Dominant production exits: `atr_sl_hit` (99 trades beyond -1%, avg **-5.47%**; but avg **+1.78%** on volume-breakout winners — ATR trailing books the profits), `profit-monster-trail` (bb_bounce_v2_long: 16 exits avg **+3.44%**, 93.8% WR — the **tiered** trail letting winners run), `cut-loser-CL-T1` (avg **-4.76%**).
2. **The task-spec stacks idealize loss-cutting at exactly -1.0%;** production realizes losses at -3% to -5.5%. Absolute sim PnL ≠ production PnL. The relative comparison (both stacks share the idealization) is the valid part.
3. **Sim "current" under-captures vs actual on big winners** (volume-breakout sim +0.15% vs actual +3.04%; rr-struct sim +0.13% vs actual +2.09%) because the task-spec stacks omit the ATR trailing engine that actually runs winners in production — symmetrically for both stacks, but it means **stale_winner (36 exits) carries ride_it's profit side in the sim, and stale exits have fired 0 times in production.** If ride_it went live with stale exits inert, its real profit capture would be **worse than simulated**, not better. This strengthens, not weakens, the negative verdict.
4. Sensitivities (JSON): `current_tiered` beats flat-current on most families (bb_bounce +4.58 vs ride_it +2.73) except pump-chain+ (19.38 vs ride_it 22.59); production-faithful `current_pump` under-performs flat PM trail on pump-chain+ (10.98 — dead_money cuts winners at 2h/pnl<2% that production closed at avg +2.08%). PM trail tiering is a live question for another audit; it does not rescue ride_it.

## Recommendation

1. **Do not expand ride_it mapping.** Keep `volume-breakout-long+` → ride_it only if the mapping fix is needed for other reasons; on exit-quality evidence it costs -1.12 on that signal and -3.73 on pump-chain+. Keep mover+ off ride_it (audit already removed it; sim confirms -1.36).
2. **If ride_it is to survive, its parameters must change before re-test:** trail activation at 2% is unreachable for these trade profiles (13/377 activations). An activation between PM trail's 0.4% and 2%, or a phase-1 SL below the -1.0% overlay (i.e. ≤1.0%), would give the engine something to actually do. Re-run this script after any parameter change.
3. **Separate finding (out of scope, flagging):** production losses realize at -3% to -5.5% (`atr_sl_hit` avg -5.47%, `cut-loser-CL-T1` avg -4.76%) while `HARD_MAX_LOSS_PCT=-1.0%` is documented as the safety net — the guardian T1 window `[-2.5%, -1.0%]` and wake latency make the -1.0% floor largely theoretical for live trades. Worth a dedicated audit of live loss-realization vs documented stops.

*Method: replay simulation, not live trading. Every number above was produced by executing `sim_fixed_ride_it.py` against the brain DB and `candles.db` at 2026-10-06T02:49Z. Stall detection for stale_exit is approximated from candle ranges (no speed-tracker percentile in replay) — documented in script docstring.*

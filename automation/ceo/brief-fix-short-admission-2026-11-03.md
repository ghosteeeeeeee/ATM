# BRIEF: T ESCALATES — "tell the ceo to FIX IT" (2026-11-03, second consult same day)

## T's directive (verbatim intent)
"Tell the CEO to FIX IT: 'we require every dump to happen in EXTREME vol, at RSI 45-65,
with 2 sources, before the machine will take a short' — ESPECIALLY THIS. What does that
even mean? Does it look like it is working by any metric?? Ref: 'and half the shorts it
does birth, we deliberately rebrand as longs.'"

→ T is not asking for another diagnosis. He is asking: (1) prove by METRICS whether the
current short-admission funnel is working at all — his rhetorical question reads "it isn't";
(2) FIX it — the three admission conditions he names (EXTREME-vol dependence, RSI 45-65
band, 2-source confluence) are the target, plus the fade's rebranding of half our shorts.

## State of the world (first consult today, VERIFIED numbers — build on, don't re-derive)
- Funnel 7d: births SHORT 4,884 vs LONG 3,473 (shorts born 1.4:1 MORE) → approval kills
  2,578 (52.8%) vs 1,396 (40.2%) → fills 55 (1.1%) vs 197 (5.7%). Last-200: 155L/45S;
  L 49.0% WR −$1.67 vs S 64.4% WR +$0.26. BTC −2.27%/24h.
- Top short killers/7d: confluence single-type 966 (87% ichimoku-), pc-short-high 535,
  short-rsi-hard-floor 457, oversold-knife 226, rr/rep/vol ~360, SHORT-REGIME-GATE score-kill
  ~190/day hidden (conf 60-74, NORMAL/HIGH vol, no tombstone).
- Fade: CONTRARIAN_LIVE_PREFIXES={'pump-chain-'} flips pc- SHORT→LONG — 27 of last-200 longs;
  pc- short fills 7d = 0; fade itself +EV (+$0.18/7d) — correct to keep, but it mechanically
  mints longs on dump days. Without it ratio = 1.8:1.
- Prior standing evidence: gate-shadow fwd (98.6% join) — SHORT blocks historically COSTLY
  (+$250-eq), LONG blocks protective (−$532-eq); short-relax study 0/25 gates passed relax
  bars (that verdict covered per-gate BLOCK counterfactuals — NOT the upstream admission
  conditions T now names); unclog waiver expired 10-24; knife<35 hard; SHORT_CONTINUUM=60;
  philosophy: every dump is a SHORT opportunity, no blanket kills, no time-of-day blocks.

## IN FLIGHT — do not duplicate (implementation subagent 74e824af, launched 15:0x after
your first verdict): A1 SHORT-REGIME-GATE shadow exemption (SHORT_BIAS + conf 60-74, bar
14d n≥15/+$0.50/2-of-3d) · A2 flip#1 bear-override shadow re-arm (bar 14d n≥20/+$1.00/LOO)
· A3 pause ichimoku-short detection · A4 tombstone the score-kill. Registry entries
short-regime-exempt-shadow / flip1-bear-override-reshadow / ichimoku-short-pause being added
(deadline 11-17). Your fix must EXTEND or SUPERSEDE these — if you supersede A1/A2 with a
stronger change, say so explicitly and say what happens to those entries.

## What T wants you to deliver

### 1. The metric verdict — "is it working?"
Answer with numbers, for the CURRENT short-admission stack as a whole and for each of the
three conditions T names:
- Admission efficiency: fill rate/birth by direction vs what a regime-matched baseline would
  admit (e.g. fills per 100 births when regime=BEAR/SHORT_BIAS vs now).
- Outcome quality: what did the BLOCKED short cohorts actually do next (gate_shadow fwd
  basis is built for this — reuse it, do not re-mine)?
- Counterfactual: over the last 14-30d, what would fills/P&L/WR have been with each of the
  three conditions relaxed (EXTREME-only vol → all vol in SHORT_BIAS; RSI floor 45 → 35;
  2-source → 1-source for shorts in BEAR) — individually and combined? Use the existing
  shadow/counterfactual machinery (gate_shadow fwd, shadow_trades, decision_reason tombstones,
  signals_hermes_runtime) — real joined data, honest n, units-guarded (pnl_usdt = price_move%
  × notional), fees noted (BUG-073).
- If the answer is "it is not working by any metric", SAY THAT plainly — T asked exactly that.

### 2. THE FIX — executable, ranked
For each of the three conditions + the fade rebranding, rule ONE of:
- **RELAX NOW (live)** — only if a metric above clearly supports it AND you can name the
  exact constant/site/value; state the revert. This is T's preferred answer ("fix it") —
  prefer immediate relief where data supports it over another shadow cycle.
- **SHADOW with bar** — if data is insufficient: exact flag (polarity!), site, bar, deadline.
- **KEEP** — with the metric that justifies it (be prepared for T to challenge).
Specifics expected:
a) EXTREME-vol dependence: which gates impose it (pc-short-high, SHORT-REGIME-GATE NORMAL/
   HIGH kill, vol-gate, ACCEL blocks) — do they become no-ops on BEAR days? Proposed unified
   rule, e.g. "in regime_4h SHORT_BIAS/BEAR, vol-regime family blocks on SHORTS are
   downgraded to shadow" — exact sites/values.
b) RSI 45-65 band: hard floor 45 + knife 35 + ceiling — what exact floor/band works under
   BEAR structure with the metrics to back it? (Note flip#1 already encoded this idea and
   expired — either re-arm it with force or replace it; do not leave it expired-and-shadowed
   if you can justify live.)
c) 2-source confluence for shorts: which requirement (CONFLUENCE_REQUIRED, single-type kill)
   and what single-source alternative is acceptable in BEAR? ichimoku- is being paused —
   what remains?
d) Fade rebranding: 27/200 longs from pc- fades. Options: keep as-is (+EV), cap its share,
   or require regime confirmation before fading INTO a long on a dump day. Recommend ONE with
   the metric.
Constraints unchanged: no blanket kills (route via regime/volatility), no time-of-day blocks,
flag polarity rules (BUG-068), units guard, don't re-block what gate-shadow proves protective,
0/25 verdict stands for per-gate relaxations you don't supersede with new evidence.

### 3. Execution package
Ranked table: action | exact file:line + constant/value | live-or-shadow | metric that
justifies it | revert path | bar+deadline if shadow. Everything under standing delegation
(CEO label = go) so it ships immediately after your verdict. Note which entries in the
registry/calendar this supersedes.

## APPENDIX — data your PREVIOUS run (timed out at 1800s, rc=124) already verified. DO NOT re-derive; go straight to the metric verdict + fix table.

1. **Births by btc_regime (7d, signals_hermes_runtime):** SHORT BEAR_TREND 1,828 (biggest single bucket) / TRANSITIONING 928 / BULL 852 / RANGING 831 / RB 153 / RU 265. LONG BEAR 1,050 / BULL 730 / RANGING 618 / TRANS 709 / RB 145 / RU 203. Shorts ARE born in the bear.
2. **Fills 14d by btc_regime (PG):** SHORT BEAR_TREND 55T **−$0.67, 50.9% WR** | SHORT TRANSITIONING 30T +$0.55, 63.3% | SHORT RANGING 7T +$0.10, 85.7% | LONG BULL 111T −$0.46 | LONG BEAR 49T −$0.83, 49.0% | LONG RANGING 35T −$0.63, 42.9%.
3. **Fills 14d by coin_regime (PG):** **LONG in SHORT_BIAS = 90T −$1.14, 48.9% WR = the single worst filled cell in the book** | SHORT in SHORT_BIAS 74T −$0.24, 56.8% | LONG in LONG_BIAS 189T −$0.73, 52.9% | SHORT in LONG_BIAS 28T −$0.27, 57.1%.
4. **gate_shadow.db 7d SHORT block counts:** CONFLUENCE-GATE-BLOCK 2,609 (vs LONG 503) · SHORT-NEUTRAL 1,314 · SHORT-RSI-HARD-FLOOR 1,240 · PUMP-CHAIN-SHORT-HIGH 1,239 · SHORT-CONTINUUM 858 · OVERSOLD-SHORT 779 · VOL-GATE-BYPASS 430 · SHORT-REGIME-GATE 293 · SHORT-RSI-CEILING 180 · EXEC-RSI-HARD-FLOOR 52.
5. **fwd_4h counterfactuals (all-time, + = blocked direction would have WON = gate COSTLY):** CONFLUENCE SHORT **+0.0437%/ev n=9,791 (costly)** vs CONFLUENCE LONG −0.2026 (protective) · VOL-FAMILY 3 (pc-short-high + vol-gate-bypass + short-regime) SHORT **+0.2667%/ev n=6,134 = +$218.6-eq total (costly)** · SHORT-NEUTRAL+SHORT-CONTINUUM SHORT +0.0794 n=8,693 (costly). → Every major SHORT gate's fwd counterfactual is COSTLY; the LONG mirrors are protective.
6. **Constants you had opened:** STANDALONE_BYPASS_SIGNALS (:3382, long-heavy list incl. pump-chain, bb-squeeze, accel-300...), PUMP_CHAIN_SHORT_HIGH_BLOCK_ENABLED=True (:3680, rationale "HIGH 14d 14.3%WR"), SHORT_NEUTRAL_BLOCK_ENABLED=True (:2709), ACCEL_300_V3_SHORT_EXTREME/FLAT_BLOCK=True (:2711-2712), plus the confluence single-type chain at signal_compactor.py:3540-3690 (ichimoku LONG-only bypass, storm waiver shadow, neutral-relax, accel standalone bypass).

The tension the verdict must resolve: **we are blocking shorts at every layer whose own fwd-join says the blocks COST money (5), while our worst filled cell is LONGing the SHORT_BIAS regime (3) — and T's three named conditions (EXTREME-vol dependence, RSI 45-65, 2-source confluence) are exactly gates 4's expensive short blocks + the vol family.** Deliver the fix table per the original brief (RELAX NOW / SHADOW+bar / KEEP per condition + fade), with the metric behind each ruling. Budget this run to DECIDE: at most a few confirmatory queries, then verdict.

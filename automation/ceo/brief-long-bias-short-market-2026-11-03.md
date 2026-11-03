# BRIEF: Why are we still long-biased in a short market? (T, 2026-11-03)

## T's complaint (verbatim intent)
"We're still long biased in a short market WHY?? Look at BTC over the last few hours and
look at the trades, mostly long — the last 200 trades have only 45 shorts, why?? Are we
allergic to profit??"
→ He wants the ROOT CAUSE, named gate-by-gate, and concrete changes. Philosophy is fixed:
every dump is a SHORT opportunity, no blanket kills, no time-of-day blocks — route via
regime/volatility gates, not bans. Ranked, executable answers only.

## Verified numbers (gathered just now, 2026-11-03 ~05:00Z — trust these)
**BTC (local candles_5m, is_closed=1):**
- 24h: **78,449 → 76,788 = −2.09%**, red in 15 of 24 hourly bars; clean slide legs
  11-02 15:00−0.45% / 17:00−0.45% / 20:00−0.41% and 11-03 02:00−0.53%.
- 4h blocks: −0.30% / −0.65% / −0.64% / −0.72% / +0.55% (bounce at 21:00), last 3h −0.21%,
  last 90m +0.06% — i.e. a real downtrend day now chopping sideways at the lows.

**Direction split (PG, source of truth):**
- Last 200 closed: **LONG 155 (77.5%) vs SHORT 45 (22.5%)** — T's 45 confirmed.
  By direction: **LONG 76W/155 = 49.0% WR, net −$1.67 | SHORT 29W/45 = 64.4% WR, net +$0.26.**
  Window spans 10-29 15:45 → 11-03 02:54.
- Last 24h closed: LONG 22 (7W, −$1.47) vs SHORT 12 (8W, $0.00).
- Open book: 3 LONG / 2 SHORT. Opens last 6h: 6 LONG / 2 SHORT.
→ The profitable side (SHORT) is the minority side; the losing side (LONG) is 3.4:1 of flow.
T's "allergic to profit" is, on this window, arithmetically fair.

## Prior rulings and evidence (DO NOT re-derive — build on these)
1. **direction-bias consult (2026-10-30):** bias TRUE but ranked third-order then; fill
   ratio at detection ≈ **2.05:1 LONG:SHORT**. It is now 3.4:1 on closes — worse.
2. **gate-shadow fwd study (10-31, joins at 98.6%):** blocking MORE shorts was priced
   **costly (+$250-eq)** while LONG blocks are protective (−$532-eq). I.e. the system's
   short-side gates historically cost money — but that measured BLOCKED shorts (counterfactual),
   NOT the admission ratio we now see. The two are different questions: per-gate blocking
   value vs upstream signal/admission mix.
3. **short-relax study (closed 10-31):** 0/25 SHORT gates cleared relax bars (n≥50, t≥+2,
   2/3 positive days, LOO) → "accept base rates, no gate relaxed." That verdict covers
   RELAXING gates; it does NOT explain why so few short SIGNALS are born/allowed in the
   first place — the admission side was never decomposed.
4. **Unclog waiver EXPIRED 10-24** — [35,45) SHORT band shorts are blocked at all layers.
   **Knife floor RSI<35 blocks shorts unconditionally.** SHORT_CONTINUUM BTC>60 blocks.
   Short-RSI-ceiling blocks hot shorts. All live.
5. Active signal families skew long: bb-squeeze+, continuum-trend+/osc+, pump-chain+,
   r2v2-long3, jup_yolo — the hotset/winner-cell machinery (AMPLIFY) rewards these.
   Short families: pump-chain-, volume-buildup-, jup-yolo short mirror, warrior-sr?
6. Regime scanners: 4h/15m regime + coin_regime LONG×SHORT_BIAS exist; SHORT_BIAS gates
   LONG admission — but the observed flow is still 77% long, so either SHORT_BIAS rarely
   triggers or it is not the binding constraint.
7. Today's live context: stop-tighten shadow (jup/vb-), fade CONTRARIAN-LIVE (pc- LONG
   fades — note: fade turns SHORT signals into LONGS by design!), storm waiver shadow.

## The question to answer
**Why does the machine still emit 3.4:1 longs into a −2.09%/24h tape, when the short side
is the 64% WR / positive side?** Decompose with evidence, gate-by-gate and layer-by-layer:
1. **Birth:** how many SHORT signals are DETECTED per day vs LONG (scripts/signals/*,
   signals_runner) — is the pipeline short-starved at source (indicator params, family
   enablement, hotset composition)?
2. **Admission:** of those, how many die at each layer (blacklist, regime, RSI floors/ceilings,
   confluence≥2, winrate min, speed, family bans) — per-gate kill table for SHORTs vs LONGs,
   last 7d, with n.
3. **Execution:** approval→fill ratio per direction; Z-FLIP/fade conversion (pc- fades become
   LONGS — quantify how many shorts became longs this way in the last 200).
4. **Sizes/holds:** are LONGs held longer/closer-stopped (exit asymmetry already studied —
   don't redo), only to the extent it affects direction counts.
Deliver: ranked root causes with numbers, then ranked concrete changes (file/flag/gate,
exact values, shadow-first bars) that raise SHORT participation toward the tape WITHOUT
violating: no blanket kills, gate-shadow evidence (don't re-block what protects), the
0/25 short-relax verdict (don't relax protective gates), and BUG-class flag polarity rules.
Include what you would NOT change and why. If the honest answer includes "the fade converts
shorts to longs by design and that's correct," quantify its share and say what (if anything)
should still change.

## Deliverable
Verdict + ranked root-cause table (layer, gate, n, effect) + ranked actions with pre-registered
bars, ready to execute under standing delegation (CEO label = go).

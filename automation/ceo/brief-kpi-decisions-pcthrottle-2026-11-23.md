# BRIEF: T — 3 KPI decisions + "why is pump-chain throttled?!" (2026-11-23)

## T's words (verbatim intent)
"Ask the CEO those questions… **also ask why pump-chain is being so severely throttled — not
seeing any recent trades. BTC is gearing up for a pump or dump and that was our best tracker.**"
→ Two parts: (1) rule the three pending KPI-framework decisions; (2) diagnose the pump-chain
throttle NOW — a big BTC move is building and the historically best tracker is dark.

## Part 1 — the three pending decisions (rule each)
1. **Fold retirement ACK:** registry has it PENDING T ACK. Limb1 MET (cum fee-net since 11-04
   = −$4.37), limb2 broken (references retired 7-metric verifier). Replacement circuit-breaker
   spec'd: NS1 < −0.010 AND NS2 < −$8.00 on 3 consecutive verifier runs → CEO recommends
   shadow-only to T. Current status 1/2, not firing. Rule: retire the old wording?
2. **R2 wiring (money-sizing):** `DRAWDOWN_TIER_1/2_PCT` (5%→0.5×, 10%→0.25×) +
   `KELLY_DRAWDOWN_CIRCUIT_BREAKER` exist in constants with ZERO code references (dead config).
   Current R1 = −73.6% of equity → would be tier-2 (0.25× size) if wired. Wiring = live sizing
   clamp = T's money call — but he asked YOU to put it in front of him. Rule: wire it or not,
   with the number.
3. **Arm-rate control-tower section** (display-only, armed 95.8%+2.50 vs unarmed 18.5%−3.68/7d):
   build it or leave it in auto_1hr?

## Part 2 — pump-chain throttle (the urgent one)
**T's read: BTC gearing up for a pump-or-dump, pump-chain was our best tracker, zero trades
recently. Parent's verified data (2026-11-23 00:47Z):**
- **Closes by day:** 11-10:1 · 11-11:1 · 11-13:1 · 11-17:1 · **11-21:6 · nothing since** · 0 open now.
- 30d by variant: pump-chain+ 38T WR42.1% · pump-chain− 33T WR36.4% · combo7T.
- **Registry actions that throttled it (verify each):**
  - **`amplify-pcv6-extreme-short-cell` CLOSED NO-CELL + KILL EXECUTED 11-21** — pump_chain_v6
    disabled (the cell died: early n=8 +$0.35 didn't reach the bar? adjudicate the kill as
    executed-per-registration or premature).
  - **`watch-pc-flip-demote-55` DEMOTE EXECUTED 11-13** — CONTRARIAN_LIVE=False (pc-→LONG
    inversion off after WR 64.6→52.9 breach).
  - **ceiling-75 owns the 75+ band** (override-vs-ceiling: "ceiling owns 75+, band dead 3T 0%").
  - `pump-chain-plus-weight-kill-review` = INSUFFICIENT (do NOT demote pc+ — protection stands).
  - `winner-cell-drop-pcplus` BAR MET at 11-14 (pump-chain+ EXTREME cell — what shipped?).
  - Plus the standing gates: pc-short-high KEEP, confluence, compaction staleness, brake.
- Diagnosis doc context: pump-chain family = 30/100 top trades all-time (+$14.06), but
  post-8/22 pump-chain+ is **+$0.01 (cent-noise, OOS sign flips)** per agent-7 — and the
  winner-side-protection-review entry says pc− 30d payoff 2.13 (protect, don't cut).

**Questions to rule:**
1. **Full attribution:** which throttle owns the current darkness — v6 kill (11-21, matches
   the "no trades since 11-21" timing exactly), fade demote (11-13), ceiling band, gates, or
   detector silence (is pump-chain even FIRING? run the mover/detector census — signals born
   vs born-and-died, like the Nov-13 method)? Name the owner with numbers.
2. **Is the kill correct per its own bar** (pcv6 NO-CELL: n=8 +$0.35 early — did it deserve
   the bar's time, or was the cell too young)? If premature and BTC is about to move,
   recommend restore with the bar it should have gotten.
3. **For the building move:** what is the fastest legitimate path to pump-chain coverage on
   this pump-or-dump — restore v6 (if the kill was premature), lean on pump-chain+/- (the
   protected carriers), re-arm the fade (bar breach says no — respect it), or accept other
   detectors? Give T ONE recommendation with the revert.
4. **The tension to resolve honestly:** diagnosis says pump-chain+ has NO edge on clean data
   (+$0.01, t ns, OOS flips) while winner-side-protection says pc− payoff 2.13/30d and
   all-time it's the biggest winner source — which is decision-relevant for THIS move?
Constraints: no blanket kills/reversals without bars, protected flags, net-of-fees, token-day
dedup, flag polarity, speed mandate. Read-only consult — rulings + one recommendation.

# BRIEF: T — "losses bigger than wins, same old same old" — the payoff fix (2026-11-08)

## T's words (verbatim intent)
"Still allergic to profit eh? Losses bigger and more frequent than wins, same old same old."
"Continue, and then share your analysis with the CEO — get its feedback. **What do we need to
change NOW, what goes in shadow, what gets built — get better at this, become profitable.**"

→ T wants the payoff inversion FIXED (avg loss 1.75x avg win), not just observed. Ranked,
executable: live-now vs shadow vs build. Speed mandate in force.

## Parent's analysis (fresh PG queries 2026-11-08 17:50Z — trust, spot-check)

**Fold line (11-07) did NOT fire — both limbs narrowly missed:** cum fee-net since 11-04 =
**−$1.10** (63T) vs threshold −$1.50 (limb1 NOT met) · verifier now **2/7** vs required ≤1/7
(limb2 NOT met: jup share 26% ✅ and ratio 1.8:1 ✅ now PASS; HML/24h/72h/fleet-WR still FAIL).

**Win/loss structure (T's claim verified):** 7d WR 55.8% (wins MORE frequent) but
**avgWin +$0.062 vs avgLoss −$0.108 = payoff 0.57 (losses 1.75x bigger)** → −$0.025/trade
× 154T = −$3.80 net7d. 24h: 11T, −$0.23, WR 54.5%.

**The anatomy — exits split cleanly (7d):**
| Exit path | n | Net | Verdict |
|---|---|---|---|
| profit-monster-trail | 48 | **+$2.41** | winner engine works |
| mfe_exit | 28 | **+$1.26** | works |
| **hard_max_loss (HML)** | 32 | **−$4.39** | bleed #1 (avg −0.124) |
| **atr_sl_hit** | 26 | **−$3.22** | bleed #2 (avg −0.112) |
| trail_arm_timeout | 11 | −$0.36 | minor |
→ Winners +$3.67 vs these two paths −$7.61. THE problem = exactly two exit paths.

**KEY NEW FINDING — stop-tighten 0.75 IS working, on its scope:** HML by open-day
(in-scope = jup/vb sources, enforce landed 11-04 03:50):
11-01: 5 in / 2 out · 11-02: **10 in** / 1 out · 11-03: 5 in / 5 out · 11-04: 2 in / 4 out ·
11-06: **0 in** / 1 out · 11-08: **0 in** / 2 out → **post-enforce in-scope HML = 0.**
The remaining HML is ALL out-of-scope (pump-chain+ was 21 hits/30d, bb-squeeze 9, etc.).
atr_sl_hit continues too (11-06 had 6 hits = −$0.76, avg −0.127 = ~0.9% price → out-of-scope
signals with unclamped ATR stops).

**Composition fixed, payoff not:** jup share 64%→**26%** ✅ · ratio 4.3→**1.8** ✅ ·
two green days this week (11-05 +0.18, 11-07 +0.05) but 11-06 −0.67, 11-08 −0.18.
**Amplifier cells are LOSING since the boost (11-04):** bb-squeeze+ 19T 57.9% net −$0.41 ·
warrior-sr-confirm+ 6T 16.7% net −$0.26 — both were boosted to raise their share.

**Per-signal 7d (n≥5):** jup 79T WR64.6% net −1.56 (payoff 0.47!) · bb-squeeze −0.41 ·
warrior −0.26 · hl_copy −0.19 · pc- fade −0.14.

## Questions to answer
1. **Extend the 0.75% stop-tighten clamp to which additional signals, if any?** The proof is
   in-scope HML = 0 post-enforce; out-of-scope HML continues (pump-chain+ 21/30d, bb-squeeze 9/30d).
   Rank by HML frequency × clamp feasibility (their SL placement paths, WR/stop interaction from
   the stop-asymmetry sweep). Or is the −4% cut on those signals intentional protection?
2. **atr_sl_hit −$3.22/7d:** the ATR stop realizes ~0.9% price on out-of-scope signals (clamp
   doesn't cover them). Same question: clamp them, tighten ATR distance, or leave?
3. **Amplifier revert?** bb-squeeze/warrior both negative since their weight boost — was the
   amplifier a mistake (share up, PnL down), or too early (n=19/6)?
4. **The math to profitability:** if avgLoss moves −0.108 → −0.07 (closer to avgWin), 7d flips
   from −$3.80 to roughly +$1.5. What is the fastest legitimate path to that: scope-extension
   of the clamp, atr_sl tightening, HML threshold, or something else? Quantify per lever.
5. **Deliver:** CHANGE-NOW list (live, with revert), SHADOW list (bars+deadlines), BUILD list
   (telemetry/studies needed), each ranked by expected $/day. State what T should see in the
   logs within 48h as proof. Constraints: no blanket kills, protected flags, net-of-fees,
   token-day dedup, flag polarity, speed mandate.

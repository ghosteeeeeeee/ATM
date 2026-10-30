# CONSULT: direction-bias audit — "system seems long biased in a short-biased market"

**Budget ~30 min; print by ~minute 22. Deliverable: verdict on T's claim + per-direction
survival anatomy + labeled rebalance actions (T's standing "proceed" delegation means
your label = the go). Numbers over comfort.**

## T's message (verbatim, 2026-10-30 ~06:40 UTC)

> "I don't think we're taking enough shorts, system seems long biased in what looks like
> a short biased market for a while, looks like way more longs than shorts being taken"

## Verified grounding (re-verify; correct me plainly)

**Market:** BTC **−4.87%/7d** (81,649 → 77,675); continuum RECOVERY/LEAN_BEAR/BELOW.

**The imbalance (PG closed):**
| window | LONG | SHORT |
|---|---|---|
| 7d fills | **117, 57.3% WR, $0.00** | **57, 61.4% WR, +$0.16** |
| 30d fills | 565, 47.1%, −$1.93 | 199, 41.7%, −$2.26 |
| daily since 10-25 | 14/15/15/23/15 | 6/13/2/6/4 |

LONG:SHORT fill ratio **2.05:1 (7d), 2.84:1 (30d)** — every day LONG-dominant since10-25.
Short 7d WR is BETTER (61.4 vs57.3) yet shorts are half the flow.

**Signal production (runtime DB, 7d):** created SHORT 5,560 > LONG 3,175 — MORE short
signals fire — but expired: SHORT 5,510 vs LONG 3,045 → **survival: LONG 4.1% vs SHORT
0.9% (4.6×)**. The gates, not the detectors, create the fill bias.

**Structural suspects to audit (not conclusions):** (a) the SHORT storm-lane (confluence
storm-waiver) is STILL SHADOW — bar 2/3, never one live fill; (b) asymmetric RSI bands:
SHORT admitted [45,65] + knife<35 dead + bear-only [35,45) exemption vs LONG [32,75] +
bull-override path; (c) family bans: pump-chain- dead in EXTREME (vol-gate 0.0) + HIGH
hard block, while pump-chain+ runs NORMAL/HIGH/EXTREME with a bull-override; (d) the
contrarian fade converts pc- SHORTs → LONGs (by-design bias, shadow bar pending);
(e) SHORT-only extras: velocity filter, spike SHORT ceiling, midband SHORT;
(f) knife doctrine bites SHORTs hardest in crash-speed RSI moves.

## Questions

1. **Verdict on the claim** with the per-direction survival anatomy: which gates produce
   the 4.6× survival gap, which are data-backed (shorts genuinely bad there) vs
   structural accident (asymmetric by inheritance, never re-examined)? Cite the new
   tombstone census — the reasons are real names now.
2. **Rebalance rulings (labels):** (i) is the storm-waiver enforce flip (bar 2/3) the
   first fix — should it be judged EARLY given the fill imbalance, or stay on cadence?
   (ii) any SHORT-band relaxations with counterfactual evidence (e.g., is the [45,65]
   admission band +45-floor still right post-trial with RSI<45 bear exemption live)?
   (iii) should LONG flow be dampened in bear-continuum regimes (the mirror of storm),
   or is 2:1 acceptable because LONG gates are simply stricter-and-better (7d LONG
   net $0.00 vs SHORT +$0.16 — both tiny)?
   (iv) the fade's LONG conversion: net direction effect measured — keep as-is?
3. **The one number that matters:** in a −4.87% week, SHORTs net +$0.16 and LONGs $0.00
   — is the honest conclusion "the mix is wrong" or "both sides are flat and the mix is
   the least of it"? Say it straight; if the mix is third-order, say third-order.
4. **What NOT to touch** (protected flags, knife<35, trial pair, family bans with
   negative data, fade RC1 stack).

## Guardrails
READ-ONLY; labels implement under T's standing delegation. No blanket anything.

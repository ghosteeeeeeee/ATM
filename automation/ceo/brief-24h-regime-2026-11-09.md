# BRIEF: T — "last 24h looks bad; volatility and trends USED to work — what happened?" (2026-11-09)

## T's words (verbatim intent)
"Analyze the last 24 hours, looks bad (aside from the manual and pending trades). Whatever we
seem to be doing doesn't seem to be working. **Volatility and trends used to work really well
for us — now what happened?**"
→ Excludes manual/pending. Wants attribution for the bad 24h + a real answer on the
vol/trend edge: dead, regressed, or masked by our recent tightening.

## Parent's fresh data (PG, trust — spot-check)
**Last 24h EXCLUDING manual/pending: 9 fills, 44.4% WR, gross −$0.40, NET −$0.50.**
- Losses: jup_yolo_mirrored SHORT ×3 = −$0.35 · atr_sl_hit ×3 = −$0.39 · HML ×1 = −$0.11
- Winners tiny: r2v2-long3 ×2 +$0.04, atr-trend- ×1 +$0.01, volume-buildup- ×1 +$0.02
- Note: `atr-trend-` SHORT filled (new signal from the 11-06 atr-trend-accel reckoning) — first fill was a WIN.
- 7d context: NORMAL +$0.19 (68.4% WR) vs HIGH −$1.68 / EXTREME −$0.72.

**Regime scoreboard, then vs now (30d window, ex-manual, net-of-fees):**
| vol_regime | prev23d (n / WR / net) | last7d (n / WR / net) |
|---|---|---|
| NORMAL | 221 / 48.4% / −$3.96 | 57 / **68.4% / +$0.19** |
| HIGH | 112 / 52.7% / −$3.46 | 36 / 47.2% / −$1.68 |
| EXTREME | 230 / 38.3% / −$4.96 | 18 / 44.4% / −$0.72 |
| FLAT | 24 / 70.8% / −$0.08 | 9 / 55.6% / −$0.27 |
→ In the last 30d: **HIGH and EXTREME were NEVER net-positive** (EXTREME 38% WR at n=230 was
the book's biggest engine and biggest loser). NORMAL just turned green post-fixes. So either
(a) T's memory of vol working refers to >30d ago (check when it last paid), or (b) we made vol
work by admission changes and the edge moved to NORMAL, or (c) the vol edge never existed at
our sizes and fees ate it. The CEO must settle this with the long view.

## What changed recently (context — don't re-derive)
11-03 ceiling 65→75 · 11-04 stop-tighten 0.75 ENFORCE + Cap C + LONG-bypass + amplifier +
fill-cap 15 · 11-06 storm-latch diagnosis (NO-CONVERT, floor is the bottleneck, linreg-fade
storm shadow) · 11-08 scope-widen 2→8 sources + combo-substring fix + CAP050 shadow ·
11-08 storm (BTC −2.11%, floor killed 100% of storm shorts, waiver NO-CONVERT). Also pending
reads: contrarian 11-11, storm/linreg bars 11-12, CAP050/slippage 11-14.

## Questions to answer
1. **Attribute the bad 24h:** 9 fills, −$0.50 — how much is (a) the known two bleed paths
   (atr_sl ×3, HML ×1 = −$0.50 of it), (b) jup SHORT ×3 −$0.35 (Cap C capped LONGS but
   shorts flow — is jup-short the new concentration?), (c) noise at n=9? Net it out.
2. **The vol/trend question, long view:** pull HIGH/EXTREME (and trend-following signal
   families: continuum, trend-reclaim, atr-trend, momentum) net performance by month going
   back as far as data allows — WHEN did vol/trend stop paying? Before or after our admission
   changes? Distinguish market regime change vs our stack. If the edge died >30d ago, say so
   with the date.
3. **Is the stack over-tightened?** 9 fills/24h with vol in the tape (BTC −2.11% on 11-08)
   — compare admission: how many HIGH/EXTREME candidates were born vs filled last 24h/7d vs
   the same metrics in the month the edge last worked. Name the specific gates responsible for
   the delta (fwd-counterfactual where available).
4. **What to change now:** given NORMAL is the only green regime — do we (a) lean the stack
   toward NORMAL-regime edges and explicitly accept not catching vol, (b) fix the vol admission
   so HIGH/EXTREME can pay again (which gates, with bars), or (c) wait for the CAP050/scope-widen
   reads (11-14/11-21) before touching anything else? Ranked, with the $ expectation of each.
5. **Deliver:** attribution table for24h, the vol-edge timeline (when it paid, when it stopped),
   ranked actions (change-now / shadow / wait) with bars and dates, and what T should see in
   logs within 48h. Constraints: no blanket kills, protected flags, net-of-fees, token-day dedup,
   flag polarity, speed mandate, fold-framework still in force (fold line passed with no fold:
   cum −$1.10 vs −$1.50).

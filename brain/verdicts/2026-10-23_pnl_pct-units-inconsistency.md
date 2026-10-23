# pnl_pct UNITS INCONSISTENCY — same column, two meanings (brain_auditor, 2026-10-23, run #103)

**Status: DATA-INTEGRITY FINDING (MED-HIGH). No code change — money column is safe, the
percent column is not. Every pending live_pnl counterfactual must use the money basis.**

## Ground truth (entry/exit prices, not inference)

| trade | px_move (from entry/exit) | pnl_pct stored | semantics | pnl_usdt vs amount×px_move |
|-------|---------------------------|----------------|-----------|----------------------------|
| WLFI #16360 lev5 | −0.966% | −4.8306 | **leveraged (×lev)** | −0.11 vs −0.107 ✓ |
| ZRO  #16364 lev5 | −0.976% | −4.8819 | **leveraged** | −0.11 vs −0.109 ✓ |
| POLYX #16365 lev3 | −1.258% | −1.2577 | **unleveraged (price %)** | −0.14 vs −0.140 ✓ |
| GRASS #16075 lev3 | +2.873% | +2.8729 | **unleveraged** | +0.57 vs +0.566 ✓ |
| ALT  #16299 lev3 | +1.808% | +1.8080 | **unleveraged** | +0.20 vs +0.201 ✓ |
| WLD  #16259 lev5 | −0.697% | −0.6973 | **unleveraged** | −0.15 vs −0.154 ✓ |

14d census (closed, amount>0, pnl_pct≠0 → n=346 of 348): **304 leveraged-class / 17
unleveraged-class / 25 too-small-to-classify** (pnl_usdt rounded to 2dp). Of the 17,
**4 are trailing_activated** (armed cohort). paper flag does NOT explain the split
(17 are paper=FALSE).

## ROOT CAUSE — it is the EXIT PATH, not the trade type (30d, exits n≥10)

| exit_reason | unleveraged-class | leveraged-class | total |
|-------------|-------------------|-----------------|-------|
| **hard_sl** | **45** | 3 | 55 |
| profit-monster-trail | 0 | 209 | 227 |
| hard_max_loss | 0 | 148 | 154 |
| atr_sl_hit | 0 | 103 | 110 |
| atr_trail_hit | 0 | 36 | 38 |
| stale_exit / UM_HOLD / pump_exit_dead_money | 0 | 44 | 46 |
| trail_arm_timeout | 1 | 16 | 18 |

**The `hard_sl` close path writes price-move % into `pnl_pct`; every other exit path
writes leveraged account %.** (trail_sl/trail_arm_timeout are mixed — 2 outliers.)
So the semantics of the column depend on HOW the trade died, which no consumer can
infer without also reading `exit_reason`. `pnl_usdt` is correct on every path.

## Rule (unit-safe derivation)

- **Money**: `pnl_usdt` is ALWAYS `amount_usdt × price_move` — trust it. This is real PnL.
- **Price move %**: derive as `pnl_usdt / amount_usdt × 100`. Do **not** assume `pnl_pct`
  and do **not** blindly divide `pnl_pct / leverage` — that understates price move ~3–5x
  for the 17-trade class.
- **Account (leveraged) %**: `pnl_pct` only when the trade is in the leveraged class
  (check: `pnl_usdt/(amount_usdt×pnl_pct/100) ≈ 1/leverage`).

## What it already broke

1. **TAT variant-C pack (#93/#98, queued for CEO GO)** — headline bug. Cuts were credited
   as `live_pnl (unleveraged poll) − trades.pnl_pct (leveraged for 87% of trades)` →
   WLFI credited "+4.22pp" where money truth is **+$0.042**. Rebuilt unit-correct:
   `brain/analysis/tat_variant_c_pack_2026-10-23.py` (--selfcheck runs the real
   evaluate/sign path; break-tested: dropped-/100, sign-inverted and one-sided-sign
   variants all FAIL). **Reproducer is exact**: naive ex-POLYX = **+13.00pp / 6 cuts /
   fk 0 / p=0.03125 = #93's published pack to the cent**; with POLYX closed naive =
   +14.08pp (#98's +13.40 used POLYX's open-time +0.40 snapshot). **Correct money basis =
   +$0.410 / 14d, 7 cuts, fk 0/7, sign 7/0 p=0.016, halves +$0.200 / +$0.210** — the
   three pre-registered criteria (≥15 fires / fk<20% / net>0) still MET, but the impact
   is **~4.4x smaller than the published pack claimed**.
2. **`actual_pp = pnl_pct / leverage` in the 2026-10-22 giveback / breakeven scripts**
   — understates price move for any of the 17 in their cohorts (4 armed ones overlap).
   Their `$` figures (from pnl_usdt) are unaffected; pp tables for those trades are wrong.
   Both verdicts' NET$ sign conclusions stand on money terms; re-derive pp before citing.

## Pending evals that MUST use the money basis (Oct 25 batch)

HML-SHADOW (live_pnl in log), MFE-CUT shadow, UGB-BE / UGB-PT, TAT variant-C, exit-ladder /
peak-trail candle OOS. Formula: `cf_usdt = amount_usdt × live_pnl/100`, compare to
`trades.pnl_usdt`. Anything comparing `live_pnl` to `pnl_pct` directly is the same bug class
as the TAT pack — the trail-arm-candle-oos verdict called this the "units landmine"
(2026-10-17) and #93/#98 walked into it anyway.

## Suggested fix (CEO / not shipped)

Make `hard_sl`'s close path write the same semantic as every other exit (leveraged
account %), OR stop deriving money consumers from `pnl_pct` at all and add a generated
`price_move_pct = pnl_usdt / amount_usdt * 100`. Until then, SQL consumers use the money
derivation above. Do NOT flip semantics blindly — watchdog/HTML consumers already read
`pnl_pct` as "account %" for 87% of rows and as "price %" for the hard_sl minority.

# MFE/MAE 8h — last 100 shadow trades (by created_at DESC)

analyzed=57  skipped=43 (ZRO:no entry price, ME:no entry price, GMX:no entry price, HBAR:no entry price, IO:no entry price, KAS:no entry price, LTC:no entry price, POL:no entry price, SAGA:no entry price, YGG:no entry price, CRV:no entry price, PENDLE:no entry price, VIRTUAL:no entry price, STX:no entry price, ME:no entry price, CC:no entry price, CAKE:no entry price, GMT:no entry price, KAS:no entry price, NXPC:no entry price, POL:no entry price, SAGA:no entry price, YGG:no entry price, PENDLE:no entry price, RESOLV:no entry price, YGG:no entry price, CC:no entry price, COMP:no entry price, YGG:no entry price, RESOLV:no entry price, SAND:no entry price, CC:no entry price, DYDX:no entry price, ETH:no entry price, GMX:no entry price, IO:no entry price, SAND:no entry price, RESOLV:no entry price, ETH:no entry price, GMX:no entry price, CC:no entry price, PUMP:no entry price, USELESS:no entry price)
dominant candle method: {'5m': 24, '1m': 33} (union of 1m+5m used for extremes)
window coverage (best series): min=58% median=62% max=67%
coverage <80% (extremes may understate): 57 (ACE 58%, ACE 58%, CASHCAT 58%, FOGO 58%, ALT 58%, COMP 58%, BABY 58%, PAXG 60%, ENA 60%, TRX 59%, YGG 59%, COMP 60%, POL 60%, DYDX 60%, AR 61%, ETC 61%, SOPH 61%, CRV 61%, APE 61%, RENDER 61%, ACE 61%, POL 61%, BLUR 61%, GMT 61%, DYDX 62%, KAS 61%, WLD 61%, APT 62%, SEI 62%, NEO 62%, JUP 62%, ADA 61%, BLUR 62%, STABLE 62%, WLFI 62%, COMP 62%, BABY 62%, ADA 62%, ADA 62%, AVNT 62%, CASHCAT 62%, FOGO 62%, GRASS 62%, FARTCOIN 63%, SYRUP 62%, ENS 62%, GOAT 63%, IOTA 63%, ENA 63%, ONDO 64%, BTC 64%, COMP 64%, BIGTIME 66%, BIGTIME 66%, BTC 66%, BANANA 66%, BABY 67%)

## 1. Exit-reason census (n=57)
  rr_sl_hit                    n= 24  win= 0  avg_net=-0.593%
  trail_sl                     n= 14  win=14  avg_net=+0.244%
  atr_sl_hit                   n=  5  win= 0  avg_net=-0.856%
  hard_max_loss                n=  4  win= 0  avg_net=-1.072%
  rr_trail_hit                 n=  4  win= 3  avg_net=+0.119%
  atr_trail_hit                n=  3  win= 3  avg_net=+0.546%
  pump_exit_dead_money         n=  2  win= 2  avg_net=+0.934%
  cut_loser_t1                 n=  1  win= 0  avg_net=-1.211%

## 2. Exits inside the 8h window (n=57; held-to-8h excluded: 0)
  split: profitable exits=27, stopped-out/negative=30
  T=0.2% price: stopped-early + bigger-move-followed = 17/57 (30%)  [10 winners giving up tail, 7 losers it went without us]
  T=0.3% price: stopped-early + bigger-move-followed = 17/57 (30%)  [10 winners giving up tail, 7 losers it went without us]
  T=0.5% price: stopped-early + bigger-move-followed = 13/57 (23%)  [9 winners giving up tail, 4 losers it went without us]
  (a) LOSERS — post-exit continuation:
    fav_after >= 0.3% : 7/30
    fav_after >= 0.5% : 4/30
    fav_after >= 1.0% : 3/30
    fav_after >= 2.0% : 0/30
  (b) WINNERS — tail given up:
    fav_after >= cap + 0.3pp : 10/27
    fav_after >= cap + 0.5pp : 9/27
    fav_after >= cap + 1.0pp : 8/27
  by exit reason @T=0.3%:
    trail_sl                     7
    rr_sl_hit                    5
    rr_trail_hit                 2
    hard_max_loss                1
    cut_loser_t1                 1
    atr_trail_hit                1
  magnitude of foregone move (early group, n=17): median 1.45pp  p75 2.06pp  p90 2.33pp  max 2.75pp
  direction split of early group: LONG 4 / SHORT 13
  exited before the 8h favorable peak at all: 57/57

## 3. Big-MFE cohort — MAE you must survive to catch the move
   MFE>=   n MAE_to_peak p50     p75     p90     max  >HMLcap   med exit
    0.5%  41            0.21    0.74    1.04    2.08    6/41   rr_sl_hit
    0.8%  31            0.21    0.86    1.04    2.08    5/31   rr_sl_hit
    1.0%  28            0.21    0.86    1.04    2.08    4/28   rr_sl_hit
    1.5%  18            0.05    0.39    1.05    2.08    3/18   rr_sl_hit

  HML survival math (CUT_LOSER 4% account / MAE price%):
    MFE>=0.8% cohort, MAE@p50=0.21% price -> max leverage with HML intact = 19.0x
    MFE>=0.8% cohort, MAE@p75=0.86% price -> max leverage with HML intact = 4.7x
    MFE>=0.8% cohort, MAE@p90=1.04% price -> max leverage with HML intact = 3.9x
    MFE>=1.0% cohort, MAE@p50=0.21% price -> max leverage with HML intact = 18.9x
    MFE>=1.0% cohort, MAE@p75=0.86% price -> max leverage with HML intact = 4.7x
    MFE>=1.0% cohort, MAE@p90=1.04% price -> max leverage with HML intact = 3.9x
    MFE>=1.5% cohort, MAE@p50=0.05% price -> max leverage with HML intact = 85.9x
    MFE>=1.5% cohort, MAE@p75=0.39% price -> max leverage with HML intact = 10.3x
    MFE>=1.5% cohort, MAE@p90=1.05% price -> max leverage with HML intact = 3.8x

## 4. Would current stops have survived the ride? (MFE>=0.8% cohort)
  n=31: HML cap stops you first: 5 | survivable to peak with HML intact: 26
  SL needed to survive to peak: p50 0.21% | p75 0.86% | p90 1.04% price
  minutes from open to 8h-peak: p50 219m | p75 249m | p90 253m | max 271m

  4b. Wider-stop scenario applied to the WHOLE cohort (gross, no fees):
    actual (as traded, net): -4.87%
    SL=0.80% (+HML coupled to 4.0% account @5x): scenario gross +50.31% | stops hit 8/31 | max single-trade scenario loss -0.80%
    SL=1.17% (+HML coupled to 5.8% account @5x): scenario gross +62.79% | stops hit 2/31 | max single-trade scenario loss -1.17%
    SL=1.62% (+HML coupled to 8.1% account @5x): scenario gross +61.89% | stops hit 2/31 | max single-trade scenario loss -1.62%

## 5. Split-half check (reproducibility @T=0.3%)
  older half : 9/28
  newer half : 8/29

## 6. Early-exit detail @T=0.3% — worst 15 (most missed)
  10-26 17:05 BLUR   SHORT cut_loser_t1           cap=+2.23% after=+4.97%  missed=+2.75pp mfe8h=+5.24% mae_pk=-1.83% net=-1.211%
  10-26 17:22 COMP   LONG  rr_sl_hit              cap=-0.67% after=+1.66%  missed=+2.33pp mfe8h=+1.75% mae_pk=1.05% net=-0.925%
  10-26 17:05 SEI    SHORT rr_sl_hit              cap=-0.45% after=+1.76%  missed=+2.21pp mfe8h=+2.52% mae_pk=0.47% net=-0.719%
  10-26 17:12 COMP   LONG  hard_max_loss          cap=-0.40% after=+1.71%  missed=+2.11pp mfe8h=+1.81% mae_pk=0.99% net=-0.940%
  10-26 17:04 COMP   LONG  rr_trail_hit           cap=+0.45% after=+2.52%  missed=+2.06pp mfe8h=+2.61% mae_pk=0.21% net=+0.146%
  10-26 17:00 IOTA   SHORT rr_sl_hit              cap=+0.47% after=+2.10%  missed=+1.63pp mfe8h=+2.33% mae_pk=-0.47% net=-0.603%
  10-26 17:05 WLD    SHORT trail_sl               cap=+2.50% after=+4.04%  missed=+1.54pp mfe8h=+4.63% mae_pk=-1.65% net=+0.090%
  10-26 17:00 GOAT   SHORT rr_sl_hit              cap=+0.56% after=+2.04%  missed=+1.48pp mfe8h=+2.46% mae_pk=-0.42% net=-0.562%
  10-26 16:44 BABY   SHORT atr_trail_hit          cap=+0.71% after=+2.17%  missed=+1.45pp mfe8h=+2.72% mae_pk=0.39% net=+0.691%
  10-26 17:05 KAS    SHORT trail_sl               cap=+0.20% after=+1.63%  missed=+1.43pp mfe8h=+1.91% mae_pk=0.28% net=+0.097%
  10-26 17:05 JUP    SHORT trail_sl               cap=+1.07% after=+2.26%  missed=+1.19pp mfe8h=+2.94% mae_pk=-0.42% net=+0.124%
  10-26 17:05 APT    SHORT trail_sl               cap=-0.01% after=+0.90%  missed=+0.92pp mfe8h=+1.49% mae_pk=0.86% net=+0.219%
  10-26 16:46 BANANA SHORT rr_sl_hit              cap=-0.46% after=+0.42%  missed=+0.89pp mfe8h=+0.54% mae_pk=1.07% net=-0.546%
  10-26 17:05 GMT    SHORT trail_sl               cap=+0.09% after=+0.72%  missed=+0.63pp mfe8h=+1.01% mae_pk=0.43% net=+0.095%
  10-26 17:05 ADA    SHORT trail_sl               cap=-0.20% after=+0.34%  missed=+0.54pp mfe8h=+0.78% mae_pk=0.97% net=+0.291%

## 7. Gate impact on early exits @T=0.3%
  gate-blocked early exits: 12
  gate-passed early exits: 3

DONE

# HARVEST artifact #3 — stop-tighten backstop vs HML coverage (goal-704ed65e round 3, generated 2026-11-04)
Units guard: price-at-cut = |pnl_usdt|/amount_usdt*100 (pnl_pct is LEVERAGED — comparing it to a price level is the BUG-class trap; audit #103 rule).

## All HML 30d (n=150): price realized at cut
- min 0.00% | p25 0.63% | **p50 0.81%** | p75 0.99% | max 1.72%
- cut realized INSIDE 1.0% price (HML fires BEFORE a 1.0% backstop): **115/150 (77%)**
- cut realized PAST 1.0% (backstop would fire first): 35/150 (23%) — saving = only the excess above 1.0%

## In-scope stop-tighten sources (jup_yolo* + volume-buildup-)
  jup_yolo*: n=21 p50=0.85% | backstop@1.0 fires first for 2/21
  volume-buildup-: n=12 p50=0.90% | backstop@1.0 fires first for 4/12

## Coverage at various backstop levels (in-scope HML only)
  backstop 0.75% price would pre-empt 31/33 in-scope HML
  backstop 0.8% price would pre-empt 30/33 in-scope HML
  backstop 0.9% price would pre-empt 15/33 in-scope HML
  backstop 1.0% price would pre-empt 6/33 in-scope HML

## CONCLUSION (corrects artifact #2's open question)
- **stop-tighten @1.0% does NOT fix HML.** The account cut (live PnL) beats the SL to the
  touch on 77% of HML trades (p50 realize 0.81% price < 1.0%). It covers only the 23% tail.
- Tightening to 0.75-0.8% would pre-empt more, but stop-asymmetry showed 0.75 LOSES WR
  (jup -2.3pp) because winners' MAE reaches that band — and for p25/p50 HML (<=0.81%)
  even 0.8% barely wins the race. The backstop is the wrong tool for THIS bleed.
- **HML needs its own fix (candidate set for CEO package):** (a) earlier account cut
  (threshold tuning — quantify: cut at -3% account saves the 0.63-0.99% middle at cost of
  letting fewer recover; recovery_replay data exists), (b) entry timing on the mid-band
  45-60 population (artifact #2), (c) per-signal hold rules for the 2 carriers
  (pump-chain+ 21, jup 20 — pump-chain+ has NO registered fix).
- Note: stop-tighten shadow still valuable for ATR-widened rides (its original target) —
  just not an HML fix. Keep the 11-14 bar as registered.

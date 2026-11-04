# HARVEST artifact #2 — HML decomposition (goal-704ed65e round 2, generated 2026-11-04 03:17Z)

Source: PG `trades`, exit_reason='hard_max_loss', 30d. Fees noted separately (BUG-073).

## Headline
- **HML 30d: 150 trades, −$17.10 = 46% of ALL 30d gross losses (−$37.39).**
  HML is THE loss engine — bigger than fees ($9.47) and bigger than every signal cell's bleed combined.
- 30d book context: gross −$7.60 / net −$17.07 (fees $9.47).

## HML carriers (30d, n>=6)
| signal | dir | HML | of n (fleet table) | cell net |
|---|---|---|---|---|
| pump-chain+ | LONG | 21 | 88 | −0.32 |
| jup_yolo_mirrored | LONG | 14 | 97 | −2.82 |
| pump-chain- (fade shorts incl. combo) | SHORT | 12 | 52+11 | −0.45/+0.14 |
| bb-squeeze+ | LONG | 9 | 54 | −0.68 |
| bb-bounce-v2-long+ | LONG | 9 | 50 | −1.57 |
| volume-breakout-long+ | LONG | 9 | 17 | −1.26 |
| volume-buildup- | SHORT | 8 | 67 | −1.27 |
| ai-trader+ | LONG | 7 | 29 | −1.15 |
| r2v2-long3 | LONG | 6 | 26 | +0.14 |
| jup_yolo_mirrored | SHORT | 6 | 25 | −0.42 |

## Entry-condition split (parsed subset n=41/150 — metadata RSI coverage only 27%, DATA GAP)
- Entry RSI buckets: 35-45: 15 | 45-60: 13 | 60-75: 11 | <35: 1 | >=75: 1
- p50 entry RSI: jup 55 (n=19), volume-buildup- 45 (n=7)
- **Interpretation (preliminary, n=41): HML entries are MID-BAND, not extreme** — this is
  NOT the BANANA (oversold-long) failure class; entries ride INTO −4% account cuts.
  Entry-condition re-validation should focus on 45-60 band + staleness, not RSI extremes.
- Staleness: not parseable in this subset (field absent) — second data gap.

## Implication for the exit fix
- stop-asymmetry 1.0% price backstop (shadow live, 11-14 bar) fixes ATR-widened rides
  (jup realized loss p50 0.94% vs initial SL 0.64) — quantify backstop-vs-HML overlap
  in the next round: for each HML trade, would a 1.0% price SL have fired BEFORE the
  −4% account cut? (depends on leverage/amount per trade — compute, don't assume.)
- pump-chain+ (21 HML, gross-positive but fee-flipped) is the UNOWNED carrier — no
  registered fix targets it yet. Candidate: pc+ entry staleness/chase or cut tuning —
  needs the same counterfactual treatment as jup.

## Data gaps to close (feed the CEO package)
1. rsi_exec/meta_rsi stamped on only 27% of HML rows (41/150) — detect-time metadata
   coverage incomplete despite #190's 14 fields.
2. staleness field absent in this subset.

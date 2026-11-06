# Decision Request: jup_liq_cascade — trend-filter exemption + hotset residency

**Ask:** Two rulings on the new liquidation-cascade signal (`jup_liq_cascade`,
source `jup-liq+`/`jup-liq-`) so we can convert its first trade.

---

## What the signal does (shipped 2026-11-05, add-signal skill followed)

Follow JUP YOLO **liquidation cascades** — `yolo-api.jup.ag/trades` carries
`kind='liquidate'` as a first-class event (market/side/leverage/notional).
When longs get liquidated one by one, faster than baseline, we go SHORT;
shorts liquidated → LONG. Opposite thesis of `jup_yolo_mirrored` (follows
live positions); this follows FORCED flow.

- **Leverage weighting (your spec):** ≥1000x → 1.0 ("little wiggle room,
  instantly wrong"), ≥500x → 0.6, else 0.3. Measured: median `heldFor` of
  liquidated positions = **14s**, 16/26 liquidations were 1000x — your
  thesis is empirically the market's shape.
- **Trigger = spike vs per-cell EWMA baseline** (measured baseline ~87
  liqs/5min feed-wide, per-cell up to 26.7/5min → absolute counts would
  fire on noise). Window score ≥ max(8.0 weighted units, 2.5×cell baseline).
- Guards: feed-failure → cycle skipped (never mass-fire), dust notional
  filter, cooldown 1h/token+direction, kill-switches, blacklists, both
  vol gates (v1+v2), STANDALONE_BYPASS (cascade is self-contained).

## Live status: 4 signals fired, 0 trades executed

| signal | conf | fate |
|---|---|---|
| #1710447 ETH SHORT | 88 | EXPIRED — approved combo fell out of hotset |
| #1710470 ETH SHORT | 75.8 | SKIPPED — exec: NOT in hot-set |
| #1710471 BTC SHORT | 88 | EXPIRED — fell out of hotset |
| #1710476 BTC SHORT | 79 | SKIPPED — exec: NOT in hot-set |

Signal → approval works; **conversion bottleneck = hotset residency** (approves,
then compactor hotset turns over before decider execs). Also caught & fixed in
review: the signal was registered only in the DEAD vol gate (v1) — live gate
(v2) would have killed every non-merged fire; both gates now patched, live
`should_trade_v2` 15/15 TRADE.

---

## Ruling 1 — trend-filter exemption (the flagged question)

`TREND_FILTER_ENABLED=True`. The mirror (`jup_yolo_mirrored`) IS exempt
(`_jup_yolo_exempt`, signal_schema.py:677-683); `jup_liq_cascade_*` is NOT.

Consequence: a shorts-liquidated **LONG** cascade during a bearish 1h trend
is blocked at `add_signal` (`DEBUG ... [trend_filter]`). For this thesis that
may be exactly the move we want — liquidation cascades are precisely the
events that END trends (forced flow exhausts, snap-back) or accelerate them;
either way the cascade signal is a *fact-based* event, not a directional
opinion the trend filter is designed to catch.

- **(a) Exempt `jup_liq_cascade_*` like the mirror** (add to
  `_jup_yolo_exempt`-style list or its own `_jup_liq_exempt`): cascade events
  are structural facts; trend filter blocks the counter-trend half of the
  thesis. Risk: counter-trend LONGs into falling knives (the BANANA-shaped
  worry, though this is not an oversold-RSI entry — it's a forced-flow event).
- **(b) Keep the filter**: only counter-trend-ALIGNING cascades execute
  (bear-trend short liquidations → LONG blocked; bull-trend long
  liquidations → SHORT blocked). Effectively halves the signal's coverage
  but keeps every protection the mirror's exemption gave away.
- **(c) Partial**: exempt SHORT side only / LONG side only.

Note: mirror exemption precedent exists but was granted when the mirror was
"follow proven +2000% uPnL traders" — a different epistemic claim than
"liquidations just happened". Your call whether the precedent extends.

## Ruling 2 — hotset residency (why 4 fires → 0 trades)

All 4 approved, then died before exec: 2 `fell out of hotset`, 2
`exec: NOT in hot-set`. The compactor's hotset has turnover pressure
(confluence churn, 5-min staleness, competing sources), and our signal
waits in line.

Options:
- **(a) Do nothing yet** — n=4, maybe just variance; watch next fires
  (STANDALONE_BYPASS already lets it qualify solo; the compactor gave
  conf 88 = approved, it's the residency window that's short).
- **(b) Residency boost** — source-scoped hotset residency/ttl bump for
  `jup-liq` (mirrors how speed/hot bonuses work), so an approved cascade
  survives until exec. Touches hotset policy — needs your sign-off.
- **(c) Exec-priority** — cascade signals get priority at exec over
  older queued signals (they decay fast; a 30-min-old liquidation cascade
  entry is worthless — freshness IS the thesis).

My lean: (a) for now — 4 samples is noise — but if the next 3 fires die
the same way, (c) over (b): priority-at-exec doesn't lengthen residency
for everyone, it just stops making a decaying event wait in line.

## Context / constraints

- Protected flags untouched; trend-filter exemption would be a
  signal-schema list edit (mirror-pattern), hotset changes touch
  compactor policy.
- Bug-hunter verified the signal twice (commits f6fc0e89, a0b71175);
  both vol gates now registered; fire-time crash paths guarded.
- add-signal SKILL.md updated with the two-vol-gate rule (was missing).
- Measured data if you want more: `limit=500` feed shows ~129 liquidate
  events per page across 10 (market, side) cells; ZEC:long 39, SOL:long 13
  in the current page.
- Open position: none yet (0 trades).

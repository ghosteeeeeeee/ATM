# Decision Request: JUP YOLO Mirror SHORT-side gates

**Ask:** Which system-wide SHORT gates should the `jup_yolo_mirrored` signal be
exempted from (if any)? The mirror is currently near-long-only by accident, and
we need your call before touching protected flags in `hermes_constants.py`.

---

## Context

The JUP YOLO mirror (new, ~24h old) follows Solana leaderboard traders'
positions by direction onto Hyperliquid. Pipeline:
`jup_yolo_leaderboard.py` (10-min scrape, 66 tracked wallets) →
`jup_yolo_monitor.py` (60s poll, freshness gate ≤10 min, cluster bonus) →
`add_signal(source='jup_yolo_mirrored')` → compaction → decider → HL trade.

Performance so far: **23 trades, 14W/7L = 67% WR, -$0.23 net** (early big
losses being paid back: trades since the last batch are **8W/1L = 89%, +$0.20**).
`profit-monster-trail` exits: **14/14 wins**. 2 trades currently open.

## The problem: 22 LONG vs 1 SHORT

The one SHORT that got through (ETH SHORT #16573) **won +1.35%**.

But the feed says the pros ARE shorting hard — tracked-wallet positions in
tradeable markets right now:

```
BTC short ×6, HYPE short ×4, SOL short ×3   = 13 SHORT
SOL long ×3, BTC long ×2, ETH long ×1, HYPE long ×1 = 7 LONG
```

85 SHORT signals have been created by the mirror. **Executed: 0.**

## The four gates killing SHORTs (with evidence)

| # | Gate | Effect | Evidence |
|---|------|--------|----------|
| 1 | **`SHORT_BLACKLIST`** (124 tokens incl. **SOL, ZEC, XRP**) | Biggest short clusters die before a signal exists. SOL is 3 of 13 tracked short positions. | **1,246** `SOL SHORT SHORT_BLACKLIST` block lines in `/root/.hermes/logs/jup_yolo.log` |
| 2 | **`SHORT_RSI_HARD_FLOOR = 45`** | BTC/HYPE SHORT signals tombstoned at approval when RSI < 45 (oversold → bounce; the BANANA lesson) | signal rows #1697515, #1697509: `blocked@approval: short-rsi-hard-floor` |
| 3 | **Compaction 5-min staleness** | SHORT signals expire before surviving to APPROVED | 65 of 85 SHORT signals `EXPIRED` vs 143/257 LONG |
| 4 | **Same-token direction conflict** | Mirror emits both directions for BTC (different wallets disagree) → `OPP-PENALTY ×0.70` + `CONFLICT-RESCUE` picks one | pipeline log 17:00:02 |

Result: SHORT side is ~1.9% of executed trades, and the market skew of our
tracked wallets right now is short-heavy.

## Why this is a policy call (we won't touch flags without you)

1. **`SHORT_BLACKLIST` is a protected flag** (AGENTS.md: do not modify without
   asking T). SOL/ZEC/XRP earned their place there — prior copy-SHORT analysis
   showed SHORT copy at 36% WR bleeding. The blacklist protects ALL signals,
   not just this mirror.
2. **`SHORT_RSI_HARD_FLOOR = 45`** is backtested and CEO-calibrated (2026-10-18
   revert 35→45 after pre-registered trigger; BANANA lesson: shorting oversold
   = catching a falling knife in reverse).
3. Your standing philosophy (AGENTS.md): *"Every pump is a LONG opportunity.
   Every dump is a SHORT opportunity... No time-of-day blocks, no blanket regime
   kills."* These gates look like exactly the blanket blocks the philosophy
   forbids — but they were added because shorts at bad conditions LOST real money.

## Options

**A. Leave all gates in place.**
Mirror stays mostly-long. Shorts only pass when every gate clears (ETH SHORT
proved the path works). Cost: we ignore 13 of 20 tracked positions; if the
tape flips, our mirror under-participates on the winning side.

**B. Exempt `jup_yolo_mirrored` from `SHORT_BLACKLIST` only.**
Mirror could short SOL/ZEC/XRP when the pros do. RSI floor + compaction +
conflict penalty still apply. Targeted: only this signal source widens; all
other signals keep the blacklist. Risk: re-opens the exact SOL/ZEC short path
that historically lost — but now behind the freshness gate (≤10 min entry),
cluster requirement, and quality-filtered leaderboard wallets we didn't have
before.

**C. Exempt from `SHORT_BLACKLIST` AND `SHORT_RSI_HARD_FLOOR`.**
Full "mirror the pros both ways." Maximum participation, maximum exposure to
the two gates that were calibrated to stop real losses. The BANANA/oversold
lesson applies directly to shorts this signal would now take.

**D. Something else** (e.g. exempt only specific tokens, or keep RSI floor at
a lower value for this source, or wait for 50+ trades of evidence first).

## What we need from you

1. Pick A / B / C / D (or direct a different shape).
2. If exempting: exact scope — `jup_yolo_mirrored` source only, or something wider?
3. Any sizing guardrail you want on mirrored SHORTs (e.g. half-size first N
   trades, or none — current sizing is flat $11 × 5x)?

## Fresh numbers to verify against (2026-10-30 ~18:40 UTC)

- Trades: 23 total (21 closed, 2 open); LONG 22 → 13W/9L = 59% WR, -$0.48;
  SHORT 1 → 1W/0L, +$0.03
- Post-last-fix batch: 9 closed, 8W/1L = 89%, +$0.20
- Feed (tracked, tradeable): 13 short vs 7 long
- SHORT signals: 85 created, 0 executed (65 expired, 18 skipped, 2 pending)
- Tracked wallets: 66 (10-min leaderboard scrape, top realized PnL + recent boards)

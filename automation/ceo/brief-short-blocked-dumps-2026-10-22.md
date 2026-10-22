# CONSULT: Are we blocking SHORTs? Missed opportunities in tonight's dump

## T's observation (2026-10-22 ~03:00 UTC)

> "Looks like we're blocking shorts. Look at BTC over the last few hours and the alts as
> well that dumped — all missed opportunities."

**This brief demands a detailed, table-supported answer — ignore the ~400-word soft cap.**

## Grounding — quick orchestrator queries (re-verify yourself, cite your own numbers)

Market (candles.db):
- **BTC 1h**: 84,844 close at 22:00 UTC → 82,971 at 02:00 UTC ≈ **-2.2% in ~5h**, red
  hourly closes since 22:00 (01:00 candle alone -800).
- **Alts, last 6h (15m candles)**: ALT -11.5%, STRK -8.5%, CC -6.2%, SAND -6.1%,
  INJ -6.0%, OP -5.8%, EIGEN -5.7%, DYM -5.6%, FIL -5.6%, ARB -5.2%, ZK -5.1%,
  AVAX -4.9% — 20+ coins down ≥5%.

Short-side behavior (signals_hermes_runtime.db `signals`, direction='SHORT'):
- **Last 6h: 205 EXPIRED (compaction_stale_10min), 9 SKIPPED, 4 FAILED, 1 PENDING — 0 executed.**
- ~~Last 7d: 0 SHORT rows with decision in (EXECUTED, TRADED, APPROVED)~~ — **CORRECTED:
  this was an artifact.** `_purge_executed_signals` (signal_compactor.py:5849) deletes
  EXECUTED rows after 1h, so the signals table can't answer this. PostgreSQL brain says
  7d: **LONG 120T (-$2.19), SHORT 38T (-$1.07)** — shorts do trade, just 3× fewer.
  **Tonight is the real anomaly: exactly ONE trade opened 00:00-04:00 UTC — a LONG at
  01:44 (closed, $0.00). Last 12h: LONG 6 (-$0.36), SHORT 1 (-$0.04).**
- Observed kill reasons in that window:
  - `trade failed at execution: RSI hard floor (detect): 23.5 < 45` (YGG ×2),
    `RSI hard floor: 30.7 < 45` (SUSHI), `RSI hard floor (detect): 20.0 < 45` (WLFI)
  - `[CTX-GATE] CHIP SHORT blocked: pump-chain-,pump-chain-v6-: LIVE RSI 37.9 < 45
    (extreme oversold — hard block, no bearish override)` ×3; same for CRV at RSI 40.0
  - `[CTX-GATE] FIL SHORT blocked: misaligned SHORT: z=0.71 accel=+0.0051 (rising, wrong
    for SHORT)` ×2 — FIL was -5.5% over the window
  - YGG `hotset failure cooldown` ×3; BTC `continuum_trend_short` still PENDING at 02:57

Note: prior notes say SHORT_RSI_FLOOR / SHORT_RSI_HARD_FLOOR = **35**, but every live
message tonight says **45**. Find where 45 actually comes from.

## Head start — prior consult run (timed out at 900s, verified queries, don't re-derive)

**Gate census, " SHORT " lines in logs/pipeline.log, window 00:00–02:59 UTC** (mixed
✅ pass / 🚫 block — count is volume, not blocks; classify the 🚫 ones first):
`SPIKE-FILTER 598 · BTC-CHOP-3H 448 · SHORT-NEUTRAL-BYPASS 426 · VOL-GATE-BYPASS 325 ·
SHORT-RSI-HARD-FLOOR 265 · CONTINUUM-OVERRIDE 230 · PUMP-CHAIN-SHORT-HIGH 201 ·
SHORT-NORMAL 150 · CONFLUENCE-GATE-BLOCK 116 · BTC-CHOP-OVERRIDE 67 · MAXXED-BLOCK 21 ·
VEL-FILTER 13 · SHORT-REGIME-GATE 10 · CTX-GATE 8 · SLOPE-FILTER 6 · PUMP-CHAIN-VEL-SHORT 5 ·
EXEC-RSI-DETECT-FLOOR 4 · OVERSOLD-SHORT 4 · SHORT-RSI-CEILING-OVERRIDE 2`

Lead observations to verify, then move past them:
1. **Two-layer RSI trap.** `[OVERSOLD-SHORT] YGG: SHORT bypass — 1m RSI 23.5 < 35 but
   BTC bearish (oversold = continuation)` PASSED at detect, yet
   `[EXEC-RSI-DETECT-FLOOR] YGG SHORT BLOCKED — detect RSI 23.5 < 45 (live recovered
   to 49.5)` killed it at execution — **live RSI was 49.5, above the floor, and it
   still blocked on detect-time RSI.** Is the exec floor using stale detect RSI when
   live says OK? That would mean the oversold override can never actually fire.
2. **FIL**: vel filter passed (BTC bearish pullback) → PUMP-CHAIN-VEL-SHORT blocked
   (30m vel +0.314% > +0.300% "token rising") 01:10 → CTX-GATE "misaligned, accel
   rising" 01:12 — FIL then fell 1.0566 (01:00) → 1.0122 (02:30) ≈ **-4.2%**.
3. **Code pointers**: `rule_based_context_gate` decider_run.py:1052 · bear overrides
   signal_compactor.py:3252/3271, 4149/4168, 4211/4229 · confluence gate +
   VOL-GATE-BYPASS enforcement signal_compactor.py:3400-3470 · exec RSI floor sites
   decider_run.py ~1911/1925 · accel = (vel_5m − vel_15m)/span speed_tracker.py:~300 ·
   vol-gate overrides volatility_gate_v2.py:338+ (EXTREME pump-chain- = 0.0 @:376,
   NORMAL pump-chain- = 1.2 @:401) · CONFLUENCE_REQUIRED signal_compactor.py:3531.
4. Also classify: MAXXED-BLOCK (21) and CONFLUENCE-GATE-BLOCK (116) — confluence
   requirement may be starving single-source short setups during fast dumps.

## Questions to answer

1. **Attribution.** For the dump window (00:00–03:00 UTC), attribute every missed short
   to the exact gate that killed it: name, constant, value, `file:line`. Include the 205
   compaction expiries — is compaction (`compaction_stale_10min`) starving the short
   side specifically, or does it hit longs equally? (Compare longs in the same window.)
2. **The RSI-45 floor.** Trace it in code. Is it applied at detect AND execution? Is the
   bearish/bear-structure override genuinely unable to bypass it ("no bearish override"
   per the message)? Verdict: is the floor at the right level, given that during a real
   dump RSI is *always* < 45 — i.e. does this gate block *exactly when* T's doctrine says
   we must short ("every dump is a SHORT opportunity")? Respect the BANANA SHORT lesson
   (shorting *deep* oversold = falling-knife reversal) — distinguish "RSI 44 at start of
   dump" (good short) from "RSI 20 after -8%" (knife) and say where the line should sit.
3. **`misaligned SHORT (z/accel rising)` gate.** FIL dumped -5.5% and was still blocked
   for "rising" accel — verify what accel measures (over what window), where in code, and
   whether it is inverted, stale, or legitimately right.
4. **Asymmetry check.** How many LONG signals executed in the same 6h/24h window? If
   longs executed while the market dumped and shorts got zero, that asymmetry is the
   headline.
5. **Any other gate that fired on shorts tonight** that isn't in the list above
   (volatility gate v2, regime scanners, BTC chop gate, penalty engine/MIN_EXEC_CONFIDENCE,
   cooldowns) — check `decision_reason` exhaustively, not just the examples above.

## Verdict required

**Budget is ~30 min but a prior run died at 15 min with zero output. Print your full
answer by ~minute 22 even if secondary questions are unresolved — delivered beats
perfect.** Lead with: **"Yes/No, we are blocking shorts"** — then:
- Ranked list of what to change (each with the exact gate + suggested value + estimated
  impact), each recommendation **shadow-first per the automatic-implementation skill**
  (ship OFF, collect counterfactual, flip with T's approval). Do NOT propose blanket
  disables — route via regime/volatility gates.
- What NOT to touch (and why).
- Anything you find that contradicts the grounding above — say so plainly.

## Guardrails

- **READ-ONLY.** Recommend only; do not edit files, params, flags, or blacklists.
- Verify every number with your own query before citing it; cite `file:line` for every
  code claim. If you can't verify it, say so.
- Context: vacation mode ON, 7d WR 35.8%, PnL -$3.46, size-reduce active at 0.5×,
  0 open positions. Philosophy is non-negotiable: no time-of-day blocks, no blanket
  regime kills, every dump is a SHORT opportunity.

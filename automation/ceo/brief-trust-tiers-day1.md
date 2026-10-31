# Decision Request: Trust-Tier System — first-day findings + gate tuning

**Context:** You approved the giants-light/trust-tier build (shadow engine →
own leaderboard → T1 exact-mirror / T2 standard / T3 shadow-only). It has been
live since 2026-10-31 03:03 UTC, through four bug_hunter audit rounds (all
findings fixed). This brief presents the first-day findings and asks for five
verdicts.

---

## 1. Where we stand (verified numbers, 18:30 refresh)

- **Tiers: T1=29, T2=58, T3=4** (91 wallets in the 30d shadow replay)
- **T1 pool:** 46,560 shadow trades, **+$40,945** at our $11 sizing AFTER our
  60s latency — WR avg 96%, median 100%, min 74%; every wallet above the $5
  positivity floor. Their fills represent a $23M their-size pool.
- **T3 block working:** one wallet claiming 83% WR measures **0% (all real
  closes are losses)** — blocked. Two claimed-100% wallets have only 4-5 real
  fills after duplicate-row cleanup — blocked as thin.
- **Dedupe paid off:** source table had 42,871 exact-duplicate fill rows
  (10.6%) — a claimed-100% wallet's evidence halved from 9→4 real closes.
  Unique index now enforces it at ingest; 22 duplicates dropped live post-fix.
- **Dashboard fixed:** copy_trader.html was rendering only its stats bar
  (API was a zero-byte file since Aug 27 + my rebuild missed 7 html fields).
  Contract test now 34/34 fields, both crash sites clean.
- **Watch:** promotion-watch list has 26 T2 wallets near the T1 bar; nearest
  promotion candidate 0xa2ce501d at n=7 (needs 10 fills for T2 / 20+WR/pnl
  for T1).

## 2. THE problem to decide on: copy-side throughput ≈ zero

Since yesterday 21:31 UTC: **0 copy trades opened.** Today: 2 T1-stamped
signals, both died at approval:

```
#1698923 BTC SHORT (T1) → blocked@approval: oversold-knife   (RSI<35, global, never exempt)
#1699534 ETH SHORT (T1) → compaction_stale_10min             (never approved in window)
#1699082 BTC SHORT (T2) → blocked@approval: short-rsi-floor  (SOFT floor=45 — never carved out)
```

Every gate is individually defensible, but the aggregate is "29 proven
wallets, zero live output." The tension is sharpest around two gates:

**(a) Soft RSI floor vs Option D.** Option D carved out the HARD floor
(45→35 for giants) but NOT `SHORT_RSI_FLOOR=45` (soft). A T1-quality BTC
SHORT at RSI 35-44 dies at the soft floor. The BANANA lesson protects only
the <35 knife. **Recommendation on the table: carve the soft floor to 35 for
giant sources too (same pattern), knife stays global.**

**(b) Approval-death = terminal (our churn fix) vs throughput.** We made
approval-side deaths terminal to kill the 17×/3h combo-churn that caused 0
executions in 48h. Side effect: one unlucky compaction window retires a T1
fill permanently (freshness window means no other chance). **Options:**
   1. Keep terminal (churn stays dead; accept sparse output);
   2. Allow ONE bounded re-emission for T1-only after approval-death (not
      approval gates like knife/floor — only staleness-class deaths), still
      inside the 10-min freshness window;
   3. Lengthen the compactor's giant-signal survival window (touch the
      10-min staleness — the CEO-calibrated territory).

## 3. Other open items (informational or small)

- **hl-copy daemon cycle latency ≥3h37m** (was ~22min) with 37MB LOCK-WAIT
  log (HL 429 backoffs + info_rate FileLock contention). Restarted today —
  watching; if it stays pathological, needs a pacing fix (batch throttling),
  separate decision.
- `traders.account_value` is 0.0 for most wallets → dashboard "$0" cells
  (column never backfilled — cosmetic).
- `by_regime` div: html never reads it (dead since the html upgrade).
- `sniper-exit.timer` disabled + not T1-aware (flag if ever re-enabled).
- watchdog/PM HML ATR-vol-floor branch is dead code (pre-existing, shadow
  log only).

## 4. What we need from you

1. **Soft RSI floor carve-out for giant sources?** (A) carve to 35, knife
   <35 stays global — RECOMMENDED; or (B) leave as-is.
2. **Approval-death throughput fix?** (A) keep terminal; (B) one bounded
   T1-only re-emission for staleness-class deaths inside freshness; or
   (C) widen giant survival window in compactor.
3. **hl-copy daemon pacing:** authorize a throttling fix if post-restart
   cycle stays >60min? (429-driven; not caused by today's changes.)
4. **T1 thresholds:** keep (n≥20, wr≥65%, pnl≥$5 after latency, fresh≤14d,
   3-day demotion hysteresis) — or adjust given day-one board (96% avg WR
   suggests the bar may be *selecting* extreme bot styles — e.g. many 100%-WR
   pump-farm wallets).
5. **Partial-exit mirroring** (they trim 50% → we trim 50%): build it, or
   keep full-exit-only mirroring?

## Constraints noted
- All gate changes route through central helpers (directional_block /
  is_giant_source) — 12+ sites keep namespaces consistent.
- Bug_hunter completed FIVE rounds — round 5 verdict: all 8 fixes VERIFIED
  (node render harness ×2, contract 0 fails, rc-mask 3-state, 8-scenario
  skip harness, daemon mtime proof, zero regressions). Its residual finding
  (get_db() None → blind stop-move on PG outage, MED-LOW) was fixed and
  harness-proven: PG-outage → skip with 'verify failed (DB error)',
  healthy control → moves normally. LOW leftovers on record: 37MB
  LOCK-WAIT err.log (needs rotation/throttle), by_regime dead div + html
  deploy drift (live copy older than repo copy).
- Protected flags: you already authorized the giant-namespace carve-outs;
  item 4 touches T1 thresholds in hermes_constants (needs your explicit OK).

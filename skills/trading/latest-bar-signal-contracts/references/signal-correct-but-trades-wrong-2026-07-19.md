# When a Signal Looks Correct but Trades Still Go Wrong

This is a follow-on from `accel-300-rewrite-2026-07-19.md`. After
the latest-bar rewrite, the signal was demonstrably correct on
synthetic tests, historical replay, and live fresh-token scans —
yet the *abandoned trade class* (sub-60s stopouts, total PnL
**−$0.35 over 14 days, 26 trades, 25/26 with `atr_managed=TRUE`**)
kept appearing in the same `accel-300+` and `accel-300-` signal
rows. This is the diagnostic recipe to tell the difference between
"signal is broken" and "SL placement is broken downstream of a
correct signal."

## Step 1 — Distinguish the failure domain

Pull all closed trades for the suspect signal in the trailing
14 days:

```bash
python3 /root/.hermes/scripts/analysis/find_abandoned_trades.py --days 14
```

If the failing trades cluster in the abandoned class
(`duration < 60s`, `pnl_usdt` near zero, `exit_reason` in
`{atr_sl_hit, guardian_sl, guardian_tp}`), the signal is *not* the
problem. Move to step 2.

If the failing trades have normal durations (5min - 1h) but
wrong-side direction or large PnL losses, the signal IS the
problem. Re-run the `latest-bar-signal-contracts` four-pass
verification (synthetic RED tests → historical replay → live
fresh scan → random fuzz) on the signal.

## Step 2 — Verify signal accuracy in isolation

```bash
# Replay every historical signal-trade from PostgreSQL against
# the new detector and confirm direction correctness.
python3 - <<'PY'
import psycopg2, sys
sys.path.insert(0, '/root/.hermes/scripts')
sys.path.insert(0, '/root/.hermes/scripts/signals')
from signals.accel_300 import detect_accel_300
from hermes_constants import ACCEL_300_PERIOD, ACCEL_300_LOOKBACK_1M

pg = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
cur = pg.cursor()
cur.execute("""
    SELECT id, token, direction, open_time FROM trades
    WHERE signal LIKE 'accel%' AND close_time > NOW() - INTERVAL '14 days'
""")
import sqlite3
sq = sqlite3.connect('file:/root/.hermes/data/signals_hermes.db?mode=ro', uri=True)
mismatches = 0
for tid, tok, trade_dir, ot in cur.fetchall():
    ts = int(ot.timestamp())
    rows = sq.execute(
        "SELECT timestamp, price FROM (SELECT timestamp, price FROM price_history "
        "WHERE token=? AND timestamp<=? ORDER BY timestamp DESC LIMIT ?) "
        "ORDER BY timestamp",
        (tok, ts, ACCEL_300_LOOKBACK_1M),
    ).fetchall()
    if len(rows) < ACCEL_300_PERIOD + 3:
        continue
    sig = detect_accel_300(tok, [{'timestamp': t, 'price': p} for t, p in rows])
    closes = [p for _, p in rows]; last_gap = (closes[-1] - ema) / ema * 100
    if sig and sig['direction'] != trade_dir:
        mismatches += 1
        print(f"#{tid} {tok} trade={trade_dir} sig={sig['direction']} gap={last_gap:+.3f}%")
print(f'mismatches: {mismatches}')
PY
```

If mismatches = 0, the signal is correct. The failure is
downstream. Move to step 3.

## Step 3 — Audit SL placement

```bash
python3 /root/.hermes/scripts/analysis/abandoned_trade_root_cause.py --days 14
```

The output flags trades with:

- **Wrong-side SL**: `LONG: stop_loss > entry_price` OR
  `SHORT: stop_loss < entry_price`. The trade is opened with the
  SL already on the wrong side of the entry.
- **Tight SL**: `|sl_pct| < 0.10%` from entry. The SL is essentially
  the current price; any 1-tick adverse move triggers it.

Both are usually caused by the ATR trailing engine
(`tpsl_utils.compute_atr_sl_tp()`) using `highest_price` /
`lowest_price` as the SL anchor for the **initial** SL, instead of
`entry_price`. For a new trade with even one tick of price
reversal, the anchor becomes the spike peak, and the SL ends up
above current price for LONG or below for SHORT.

## Step 4 — Cross-reference with audit logs

```bash
# Confirm the SL was set by the ATR engine, not a fallback
grep -aE 'MORPHO|TOKEN' /root/.hermes/logs/sync-guardian.log | \
  grep -aE '2026-07-1[0-9]' | tail -20

# Look for the SL sequence showing the ratcheting pattern
# (1.999066 -> 1.997755 -> 1.997352 -> 1.999368 -> ...)
# Each step moves the SL toward the current price because the
# anchor (highest/lowest) is also moving.
```

## Step 5 — Single-trade deep dive

```bash
python3 /root/.hermes/scripts/analysis/trace_trade.py <trade_id>
```

This prints the trade row, the SL distance from entry, the price
history around open_time, and any audit-log mentions of that trade
ID. Use to confirm the exact sequence on one bad trade before
generalizing.

## Decision matrix

| Signal replay | SL placement | Diagnosis | Fix class |
|---|---|---|---|
| mismatches = 0 | wrong-side or tight | ATR engine bug, not signal | `atr-trailing-debug` skill |
| mismatches > 0 | any | Signal bug | `latest-bar-signal-contracts` skill (this umbrella) |
| mismatches = 0 | correct | Edge case — check slippage, race with guardian, or external API issue | `hl-trading-debug` skill |

## Common pitfall: the "obvious" answer is wrong

When a user reports "this signal is making bad trades," the
defensive move is to assume the signal is at fault and rewrite it.
After the 2026-07-19 latest-bar rewrite, the signal was demonstrably
correct (100k random fuzz = 0 contract violations, 41-trade replay
= 0 mismatches) but the abandoned class persisted. The bug was
**downstream in the SL engine**, not the signal. Don't skip step 2
just because step 1 looks suspicious.

## Companion scripts (in this skill's `scripts/`)

- `find_abandoned_trades.py` — pulls the abandoned class
- `abandoned_trade_root_cause.py` — flags wrong-side and tight SL
- `trace_trade.py` — single-trade deep dive

All three were authored in the same session that produced the
`accel-300-rewrite-2026-07-19.md` reference. They are reusable for
**any** signal in `signals/` — change the SQL filter and rerun.

## Where this fits in the four-pass verification pattern

`latest-bar-signal-contracts` defines the four-pass verification
pattern (synthetic RED → historical replay → live fresh → random
fuzz). This reference extends it with a **fifth pass**: downstream
SL placement audit. A signal can pass all four and still produce
abandoned trades if the SL engine is broken. Always run step 1-3
of this recipe before declaring a signal "fixed."

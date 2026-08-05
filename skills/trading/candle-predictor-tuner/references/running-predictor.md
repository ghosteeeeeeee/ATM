# Running candle_predictor.py — Operational Guide

How to actually invoke the predictor and read its output. The tuner skill covers
*analyzing* accuracy and *fixing* the script — this doc covers *running* it.

## Invocation

```bash
# Default: 4h candles
python3 /root/.hermes/scripts/candle_predictor.py --nowandb

# 15-minute mode (high-frequency, slower turnover)
python3 /root/.hermes/scripts/candle_predictor.py --nowandb --interval=15

# 1-hour mode
python3 /root/.hermes/scripts/candle_predictor.py --nowandb --interval=60

# With MiniMax post-prediction check (extra API call per token — adds latency)
python3 /root/.hermes/scripts/candle_predictor.py --nowandb --minimax
```

Always pass `--nowandb` in production/cron contexts to skip W&B logging (faster,
no network). `--interval` accepts 15 / 60 / 240.

## Runtime Expectations

| Interval | Tokens Predicted | Wall Time | Notes |
|----------|------------------|-----------|-------|
| 4h       | ~131             | ~6-8 min  | Default mode |
| 1h       | ~131             | ~12-15 min| |
| 15m      | ~117 (89%)       | ~20-22 min| Most tokens skipped due to low 15m accuracy history |

Observed runs:
- 117 tokens, 27 inverted, 21m14s (15:20:57 → 15:42:11)
- 117 tokens, 27 inverted, 21m52s (15:51:28 → 16:13:20) — concurrent with signals_runner + price_collector
- exit code 0, lock file released cleanly
- **116 tokens, 35 inverted, 19m15s (2026-07-14 01:31:31 → 01:50:46, exit 0)** — single transient `LLM error: HTTPConnectionPool(...) Read timed out (read timeout=30)` mid-loop; the predictor's internal retry succeeded and the run completed cleanly. One transient `Read timed out` is NOT an Ollama crash — see "Transient Ollama Timeout vs Crash" section below. Direction split that run: UP 111 / DOWN 5 (heavy UP-skew — normal output, but DOWN sample sizes get noisy).
- **117 tokens, 35 inverted, 20m10s (2026-07-14 06:06:23 → 06:26:33, exit 0)** — clean run, zero errors. Init reported `Overall accuracy: 67497/78760 = 85.7%`, `Inverted: 32670/35915 = 91.0%`. Per-token LLM latency ran ~10-25s (slightly slower end of normal range, well within the "<2 min variance" bound). Skipped 7 tokens for "very low accuracy" (INIT 15%/53, PURR 23%/730, SNX 24%/102 + persistent list) and 5 for "no price data" (BAT, THETA, VET, YFI, INIT double-flag). STRK was the lone DOWN inversion this round (UP-in-bullish dropped to 39.0% on n=59, just below the 40% threshold); everything else inverted to UP because DOWN in bearish/neutral is empirically 20-35% per REGIME_DOWN_ACCURACY. Direction split: heavily UP-skewed (UP-skew is the new normal at this market regime). Action: none — pattern matches prior healthy runs exactly.

Per-token LLM inference dominates wall time (~10s/token × N tokens).
Wall time is fairly stable across runs — varies <2 min because LLM
inference per-token is the bottleneck, not IO.

**Where the wall time goes (empirical, 15m run on 2026-07-13, 131 tokens):**
| Phase | Duration | Notes |
|-------|----------|-------|
| Startup + validation (30 resolved) | ~1s | First line after "Starting" |
| HL data fetch (9 funding + 3 OB + 9 vol) | **~3 min** | ThreadPoolExecutor w/ 12 workers — NOT 1-2s as docstring claims |
| Per-token predict loop (117 tokens) | ~22 min | ~10.5s/token, mostly Ollama qwen2.5:1.5b inference |
| Final summary + DB flush | <1s | Single batch write at end |

The HL fetch step will look "stuck" on `Fetching HL market data...` for
~3 min — this is **normal**, not a hang. The 12-thread pool waits on slow
HL API responses (per-token funding/orderbook/trade lookups fan out across
workers). See "Verifying It's Not Hung" below for the strace diagnostic
that distinguishes this from a real stall.

**The 15m run takes ~22 min.** NEVER run in foreground — it will exceed the
default 300s `terminal()` `timeout` parameter and kill the run mid-way.
Always use `terminal(background=True, notify_on_complete=True)`.

Pattern:
```python
terminal(command="python3 /root/.hermes/scripts/candle_predictor.py --nowandb --interval=15",
         background=True, timeout=600, notify_on_complete=True)
```

Then `process(action="wait")` in chunks — **`wait` clamps at 180s server-side
regardless of the `timeout` parameter you pass** (the param is documented as
user-requested, but Hermes's runtime hard-caps it at 180s). So even passing
`timeout=600` returns after 180s with a "timeout" status. Plan for ~8 chunks
of 180s each for a full 22-min 15m run. The run will almost always still
be running after the first `wait` — poll, don't expect a quick return.

**Distinguishing a killed-by-timeout run from a clean-exit run:**
- `exit_code: 0, status: "exited"` → clean completion, all predictions flushed
- `exit_code: 124, status: "exited"` → foreground `terminal()` timeout hit 300s
  and killed the Python process. Lock file is now stale — see
  "Stale Lock From Killed Run" below.
- `status: "timeout"` after `process wait` → 180s chunk elapsed, run is still
  in progress (NOT a failure — just call `wait` again or `poll`).

The exit_code-124 pattern is the canonical signature of "ran in foreground
and got SIGKILL'd at 300s" — if you see it on a 15m run, the run did NOT
complete and `/tmp/candle-predictor.lock` is stale. Always check before
assuming the predictions are safe.

## Output Format

Each prediction line looks like:
```
[2026-07-13 14:06:08] [INFO]   → BTC: UP conf=55 move=None (state=bullish regime=bullish) UP acc=100.0% >= 40% or n=440 < 20, keep UP
```

Fields:
- **Token**: ticker
- **Direction**: UP or DOWN (post-inversion)
- **conf=55**: confidence score (uniform in current impl — direction-only, no magnitude)
- **move=None**: direction-only call, no predicted % move
- **state=X**: momentum_state (bullish/bearish/neutral)
- **regime=Y**: market regime (bullish/bearish/neutral)
- **acc=XX%**: historical accuracy for this direction+state combo
- **`[INVERTED]` tag**: inversion logic flipped the raw LLM call because raw accuracy < threshold

Final summary line:
```
[INFO] === Predicted 117 tokens, 28 inverted ===
```

## Skip Reasons

The predictor skips a token with one of two WARN/INFO messages:

1. **`very low accuracy (XX%/N), skipping this round`** — historical accuracy below
   threshold on N prior predictions. Token still gets a chance next run if accuracy
   improves. Examples seen: ETH (22%/177), MATIC (0%/58), MKR (0%/58), PURR (23%/730).

2. **`no price data, skipping`** — local `signals_hermes.db` has no recent price
   history for this token. Either the token isn't being tracked by the price feed,
   or it was recently delisted. Examples: BAT, KAVA, THETA, VET, YFI.

**Note on MATIC/MKR skip behavior:** both are in `TOKEN_ACC_OVERRIDES` with
`always_invert: True`, but the "very low accuracy" check runs first and skips them
entirely. The override is effectively dead code for these — tuner should consider
either removing them from the override list or lowering the skip threshold.

### Persistent Skip Lists (observed across multiple runs)

Two skip lists are extremely stable — same tokens skip every run. Worth knowing
for capacity planning and for knowing when a "new" skip is actually a regression.

**Always skipped for low accuracy** (9 tokens, no fix available without more data):
`ETH` (22%/177), `ETHFI` (22%/111), `INIT` (15%/53), `KFLOKI` (22%/59),
`MATIC` (0%/58), `MEME` (17%/52), `MKR` (0%/58), `PURR` (23%/730), `SNX` (24%/102).

**Always skipped for missing price data** (5 tokens — coverage gap in
`signals_hermes.db`): `BAT`, `KAVA`, `THETA`, `VET`, `YFI`.

If a token appears in these lists for the first time, that's signal — either a
recent accuracy collapse or a price-feed outage. Don't treat skips as routine noise.

## Accuracy Baselines (from resolved predictions on startup)

Every run prints at startup:
```
[INFO]   Overall accuracy: 66694/77680 = 85.9%
[INFO]   Inverted predictions: 32403/35516 = 91.2% accuracy
```

- **Overall accuracy** is cumulative across all historical predictions. Numbers in
  the 80-90% range indicate healthy system.
- **Inverted accuracy** higher than overall = inversion logic is a net win. If
  inverted accuracy drops below overall, the inversion thresholds need tuning
  (this is exactly what `candle-predictor-tuner` watches for).

## Reading the Trend — Multi-Window Accuracy

The startup numbers are cumulative. For trend analysis, query `predictions.db`
with **multiple windows of different sizes** and compare. A common observation:

| Window | What it tells you |
|--------|-------------------|
| Last 50 resolved | Immediate pulse — most recent model behavior |
| Last 200 resolved | Short-term drift — directional accuracy by side |
| Last 500 resolved | Medium-term trend |
| All time | Baseline; dominated by old data |

**If last-50 accuracy drops sharply while last-500 is stable**, the recent
behavior diverged from the long-run baseline — investigate but don't panic.
A typical reading: last-50=56%, last-500=78% means the recent 50 are
underperforming but the broader system is still healthy. Don't tune based on
last-50 alone — that's noise-prone.

Direction split matters more than aggregate:
- `UP: 94.8% all-time, 55.4% last-200` → UP accuracy degrading is the real signal
- `DOWN: 25.5% all-time, 71.4% last-200` → DOWN accuracy improving, possibly because
  of the inversion logic recently starting to correctly invert bad DOWN calls

Per-direction split is the most actionable view for the tuner.

### Trend Query

```sql
-- Last 50 resolved, by direction
SELECT direction,
       COUNT(*) as n,
       SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END) as correct
FROM (
  SELECT direction, correct FROM predictions
  WHERE correct IS NOT NULL
  ORDER BY prediction_time DESC LIMIT 50
)
GROUP BY direction;
```

Inverted vs non-inverted accuracy is the canonical health check:
- **NORMAL accuracy > INVERTED accuracy** → inversion is hurting; tighten thresholds
- **INVERTED accuracy > NORMAL accuracy** (currently the case at 91.2% vs 81.3%)
  → inversion is working; keep or loosen

## HL Data Scope

The script fetches Hyperliquid data (funding rates, orderbook spread, recent trades)
and only gets useful data for tokens actively traded on HL. Expect ~9 majors:

`AVAX, ETH, LINK, DOT, BTC, ADA, DOGE, XRP, SOL`

Other tokens get technical indicators from local candle DB but no HL funding/OBI.
Don't expect HL-grounded predictions for long-tail tokens.

## What's Written

- `predictions.db` (table: `predictions`) — every prediction gets a row with
  `token, direction, confidence, was_inverted, momentum_state, regime,
  predicted_move_pct, actual_move_pct, correct, created_at`. This is the
  source of truth for accuracy stats.
- `signals_hermes_runtime.db` — does **NOT** receive candle_predictor output
  directly. The runtime DB has no `candle_predictor` table and no rows with
  source='candle_predictor'. If you grep that DB for predictor output, you'll
  find nothing. The signal pipeline consumes predictions via a separate path
  (likely the compactor scoring them against momentum, or via direct DB read).

The `predictions.db` schema does not currently store `interval_minutes` — there
is no way to query "how did my 15m predictions do" vs "how did my 4h predictions
do" from SQL alone. If you need that breakdown, add an `interval` column or
filter on `candle_time` alignment (but the latter requires wall-clock knowledge
of when the run happened).

**Batch write, not streaming:** all predictions for a run land in `predictions.db`
together near the end of the script. Killing the run mid-loop loses all work.
If you need crash-resilience, the tuner should consider adding a commit-per-token
flush.

## Common Pitfalls

- **Running in foreground** → default `terminal()` timeout is 300s, which
  kills any non-4h run mid-way. Always background with
  `notify_on_complete=True`. See "Stale Lock From Killed Run" below —
  foreground timeouts leave orphaned lock files that block the next run.
- **Expecting magnitude predictions** → `move=None` is correct, it's direction-only.
- **Expecting HL data for all tokens** → only ~9 majors. Others use local candles only.
- **Tokens "missing" from predictions** → check for skip reason before assuming bug.
  Skips are normal.
- **Confidence always 55** → not a bug in 15m mode, that's the current output format.
  Confidence calibration is a separate workstream.
- **Expecting log_total == db_total** → in current production (2026-07-15+),
  the two match exactly (observed 117/117, 115/115 across multiple
  recent 15m runs). The earlier "DB higher than log" observation was a
  one-off inversion-tracking side-effect row from early runs, not a
  stable pattern. Treat `db_total == log_total` as the healthy baseline;
  if DB starts exceeding log by >5 rows consistently, the inversion logic
  is back to writing side-effect rows and is worth investigating. The
  `=== Predicted X tokens ===` line is still the authoritative count
  for "how many tokens did this run actually call direction on" —
  use `prediction_time > run_start` for DB total.
- **Re-running after a previous run was killed/timed out** → ALWAYS check
  `pgrep -af candle_predictor` and `/tmp/candle-predictor.lock` first.
  A stale lock silently hangs the next run; if you skip the check you'll
  waste another 300s timeout before discovering it again.

### Log Parsing Gotcha

`/var/log/candle-predictor.log` is **append-only across runs** — every run's output
is appended, so a fresh log file is never created. A naive `grep -c "→" /var/log/candle-predictor.log`
returns the count for **all historical runs combined** (188k+ lines after weeks of
operation), not the current run.

To count predictions in the current run, filter by the run's start timestamp:
```bash
# Get the current run's "Starting" timestamp first
grep "Candle Predictor Starting" /var/log/candle-predictor.log | tail -1

# Then count tokens predicted AFTER that timestamp
START_TS="2026-07-13 15:20:57"
grep -A 9999 "$START_TS" /var/log/candle-predictor.log | grep -c "→"
```

Or use Python with a timestamp filter:
```python
import re
from pathlib import Path
log = Path('/var/log/candle-predictor.log').read_text()
# Find the LAST "Starting" block and slice from there
runs = log.split('Candle Predictor Starting')
last_run = 'Candle Predictor Starting' + runs[-1]
print(f"Tokens in last run: {last_run.count('→')}")
print(f"Inverted in last run: {last_run.count('INVERTED')}")
```

This gotcha cost ~30s of confusion when the agent first saw `grep -c` return
188244.

**Verify against `predictions.db`** — the log parsing above gives you the script's
own count, but if you want to confirm what actually landed in the DB, use the
run's start time as the filter (same logic as the log filter):
```bash
# Find this run's start timestamp from the log
START_TS=$(grep "Candle Predictor Starting" /var/log/candle-predictor.log | tail -1 | awk '{print $1" "$2}')

# Count predictions written after that start time
sqlite3 /root/.hermes/data/predictions.db \
  "SELECT COUNT(*) as run_total,
          SUM(was_inverted) as inverted,
          MIN(datetime(prediction_time,'unixepoch')) as first_pred,
          MAX(datetime(prediction_time,'unixepoch')) as last_pred
   FROM predictions
   WHERE prediction_time > strftime('%s','$START_TS');"
```
This should match the script's `=== Predicted X tokens, Y inverted ===` line
exactly. If the counts diverge, the script is dropping predictions between
log and DB flush — investigate before trusting the run.

## Post-Run Verification (one-shot)

After a clean-exit run (`exit_code: 0`), confirm everything actually landed
in ~10 seconds:

```bash
# 1. Confirm lock was released (script cleans up on success)
[ ! -f /tmp/candle-predictor.lock ] && echo "lock OK" || echo "lock STALE"

# 2. Get this run's start timestamp + totals from log + DB
START_TS=$(grep "Candle Predictor Starting" /var/log/candle-predictor.log | tail -1 | awk '{print $1" "$2}')
LOG_TOTAL=$(awk "/$START_TS/,0" /var/log/candle-predictor.log | grep -c "→")
LOG_INVERTED=$(awk "/$START_TS/,0" /var/log/candle-predictor.log | grep -c "INVERTED")

sqlite3 /root/.hermes/data/predictions.db <<EOF
SELECT
  COUNT(*) as db_total,
  SUM(was_inverted) as db_inverted,
  MAX(prediction_time) as latest_epoch,
  datetime(MAX(prediction_time),'unixepoch') as latest_utc
FROM predictions
WHERE prediction_time > strftime('%s','$START_TS');
EOF

# 3. Cross-check: db_total should be >= log_total (DB also includes
#    skipped-token writes from inversion-tracking side effects; can be higher).
#    If db_total < log_total, the batch flush at end-of-run was interrupted.
```

Healthy observation (15m run, 2026-07-13): log=117 predicted / 28 inverted,
db_total=138 (slightly higher — early-era inversion-tracking side-effect rows;
in current production this pattern has not repeated — see "Expecting log_total
== db_total" pitfall above), latest_utc ≈ the run's `=== Predicted ... ===`
line timestamp. In current production (post-2026-07-14), `db_total` should
match `log_total` exactly.

**Healthy observation (15m cron run, 2026-07-15 01:54, this session):**
log=117 / inverted=36 / errors=0 / wall=13m52s (01:54:59 → 02:08:51, exit 0).
Init reported `Overall accuracy: 68328/79690 = 85.7%`,
`Inverted: 32913/36214 = 90.9%`. **Fast run — under the 20-22m envelope by
~6 minutes** (no concurrent Ollama load observed — signals_runner quiet
during the predict loop). Skipped the same persistent list (9 low-acc:
ETH, ETHFI, INIT, KFLOKI, MATIC, MEME, MKR, PURR, SNX + 5 no-data: BAT,
KAVA, THETA, VET, YFI). DB total matched log exactly: 117/117, no
inversion-tracking side-effect rows this round. All 36 inverted predictions
came out of the persistent DOWN-anti-correct logic (DOWN-in-neutral/bearish
empirically 0-38% per REGIME_DOWN_ACCURACY). Confidence=55 across all
predictions (uniform — calibration is a separate workstream). Direction split
UP-skew continues (every kept prediction was UP — by inversion, not raw LLM
output). No errors, no warnings beyond the persistent skip list. **Use this
as the fast-end baseline**: when wall time drops below ~15 min, no action
needed — it's just an unloaded-Ollama run, not a model improvement.

## predictions.db Schema (verified 2026-07-13)

```sql
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT NOT NULL,
    direction TEXT NOT NULL,        -- 'UP' or 'DOWN' (post-inversion)
    confidence INTEGER,             -- currently 55 for all rows; calibration TBD
    predicted_move_pct REAL,        -- always NULL — direction-only model
    actual_move_pct REAL,           -- filled in when candle resolves
    correct BOOLEAN,                -- 1=correct, 0=wrong, NULL=pending
    prediction_time INTEGER,        -- unix epoch seconds — NOT 'ts' or 'created_at'!
    candle_time INTEGER,            -- unix epoch of the candle being predicted
    price_at_prediction REAL,
    momentum_state TEXT,            -- bullish/bearish/neutral
    regime TEXT,                    -- bullish/bearish/neutral
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    was_inverted BOOLEAN DEFAULT 0  -- 1 if inversion logic flipped the LLM call
);
```

**Gotchas when querying:**
- The timestamp column is `prediction_time` (INTEGER epoch), NOT `ts` or
  `created_at`. `created_at` is a separate `CURRENT_TIMESTAMP` field in
  human-readable form, not epoch.
- `correct` is tri-state — NULL = prediction pending (15m candles haven't
  resolved yet), 0/1 = resolved. Always filter `WHERE correct IS NOT NULL`
  for accuracy stats, otherwise you count pending predictions as wrong.
- There is no `interval_minutes` column — cannot distinguish 15m vs 4h vs
  1h predictions from SQL alone. If you need that breakdown, the tuner
  would need to add an `interval` column.

**`candle_time` is hardcoded to `prediction_time + 14400` (4h), regardless of `--interval`.**
Verified 2026-07-15 02:52 15m run: every single one of the 117 new rows has
`candle_time - prediction_time = 14400`, not 900. The model *does* use the
correct 15m OHLCV features for inference (log says "15m candles", predictions
reflect 15m-aggregated prices), but the persisted `candle_time` points to
the next 4h candle boundary. Consequence: any downstream accuracy check
that compares `actual_move_pct` (filled when the candle resolves) against
`candle_time` will look at the wrong 4h window for a 15m-mode run, silently
flipping the correct/wrong verdict for every prediction. This is a
**durable bug** in `candle_predictor.py` — confirmed across the full 117
rows, not a one-off. Two fixes possible (both require touching the script,
not just the schema): (a) store `interval_minutes` in the row and compute
`candle_time = prediction_time + interval_minutes * 60` at insert, or (b)
compute the next interval boundary from the actual `CANDLE_MINUTES` runtime
value (currently only the local OHLCV builder uses it; the DB insert path
hardcodes 4h). Flag for T before patching — the script is live and surgical
fixes are required per the trading rules.

**SQL timestamp-window gotcha (recovered 2026-07-15 02:52):** when filtering
predictions to "this run only" via SQL, use the run's first
`prediction_time` value as the lower bound AND the last `prediction_time`
as the upper bound (not the start/end wall-clock). `prediction_time` is
floored to the candle boundary (e.g. 15m runs floor to the next 15-min
mark), so the first row's `prediction_time` can be 30-60s AFTER the wall-
clock "Starting" line. Conversely the last row's `prediction_time` can be
60-120s BEFORE the `=== Predicted N tokens ===` summary line. Building
the SQL window from wall-clock timestamps is off by a minute or two,
which won't miss rows in a 117-row batch but will produce confusing
"0 rows in window" results if you accidentally swap the lower and upper
bounds or include the wrong minute. Safest: `SELECT MIN(prediction_time),
MAX(prediction_time) FROM (SELECT * FROM predictions ORDER BY id DESC
LIMIT 117)` to get the exact window the script just wrote.

## Ollama Crash Mid-Run (CRITICAL — recovery recipe)

Symptom: predictor log shows repeating `LLM error: HTTPConnectionPool ... Connection refused`
from `http://127.0.0.1:11434`. The Python process is still alive (it retries silently
in a loop) but produces zero new predictions — the run is effectively dead while the
lock file holds. Background `terminal()` will never notify_on_complete because the
process never exits on its own.

**Diagnosis first** — confirm Ollama is actually down, not just slow:
```bash
systemctl status ollama --no-pager | head -8   # Active: inactive (dead)?
curl -s --max-time 3 http://127.0.0.1:11434/api/tags   # Connection refused?
journalctl -u ollama --since "10 minutes ago" | tail -20   # last 500 + Stop event?
```

If Ollama is dead, the journal usually ends with a `POST /api/generate` 500 followed
by `Stopped ollama.service` — no OOM-killer message, just systemd taking it down
after a bad request. Likely causes seen in production:
- Long prompt context overflow on the LLM runner
- Transient llama runner crash
- MemoryMax=4G headroom pressure (see `/etc/systemd/system.control/ollama.service.d/50-MemoryMax.conf`)

**Recovery (in order — do not skip the lock cleanup):**
```bash
# 1. Stop the dead predictor (it will spin forever otherwise)
kill -TERM <PID>
sleep 2 && kill -KILL <PID> 2>/dev/null

# 2. Release the lock file (it contains the dead PID)
rm -f /tmp/candle-predictor.lock

# 3. Restart Ollama
systemctl start ollama
sleep 3 && systemctl status ollama --no-pager | head -5
curl -s --max-time 5 http://127.0.0.1:11434/api/tags | head -1   # should list models

# 4. Re-run the predictor (background, notify_on_complete=true)
```

**Detection tip while the run is in progress:** if you see a long string of
`[ERROR] LLM error: Connection refused` lines after token "K" or "M" in the log,
Ollama has likely died. Don't wait — kill, restart, re-run.

### Ollama Failure Modes — Transient Timeout vs Auto-Recovery Bounce vs Full Crash

Three failure modes look similar in the log but require different responses.
Misclassifying any of them as a crash wastes ~22 minutes of LLM inference
(predictor uses a single end-of-run batch write to predictions.db — **no
commit-per-token flush**).

| Symptom | Transient Timeout (recover) | Auto-Recovery Bounce (recover) | Full Ollama Crash (kill+restart) |
|---------|-----------------------------|--------------------------------|----------------------------------|
| Error lines | Single `Read timed out (read timeout=30)` | Pair: `Remote end closed connection without response` followed by `Connection refused` on retry | Repeated `Connection refused` with no recovery |
| Frequency | One line, then `→ TOKEN:` resumes within 1-2 min | 2 lines back-to-back, then `→ TOKEN:` resumes **after Ollama comes back** (~30s-3 min for systemd to respawn + model load) | Repeated indefinitely, no new `→ TOKEN:` for >5 min |
| Ollama service | Still `active (running)` (same PID, same start time) | Briefly `inactive (dead)` → systemd auto-restarts → `active (running)` with a **new** PID and **new** `ExecMainStartTimestamp` | Goes `inactive (dead)`, stays dead |
| Predictor process | Making progress between retries | Waiting on retry, resumes when Ollama returns | Spinning in retry loop, no progress |
| Action | **Let it continue** | **Let it continue** — confirm via journalctl that systemd auto-respawned Ollama | Kill predictor, restart ollama, re-run |

**How to tell Auto-Recovery Bounce from Full Crash in ~3 seconds:**

```bash
# The two-errors-in-a-row is the trigger. Now confirm the respawn.
systemctl show ollama -p ExecMainStartTimestamp   # was this timestamp recent?
journalctl -u ollama --since "10 minutes ago" | grep -E '(Stopped|Started)' | tail -5
```

If `ExecMainStartTimestamp` is **within the last few minutes** AND the journal
shows a `Stopped ollama.service` followed by `Started ollama.service`, Ollama
auto-respawned — it's the bounce pattern, not a crash. systemd's `Restart=`
policy (default `on-failure` on this host) handles transient runner crashes
without any manual intervention.

Observed example: **2026-07-14 21:00:45 → 21:24:49, exit 0** — single paired
error event at 21:16:26-27:
```
[21:16:26] LLM error: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
[21:16:27] LLM error: HTTPConnectionPool(host='127.0.0.1', port=11434): ... Connection refused
```
journalctl shows `Stopped ollama.service` then `Started ollama.service` with
`ExecMainStartTimestamp=Tue 2026-07-14 21:16:27 UTC`. Next successful
`POST /api/generate` at 21:19:10 (after ~3 min model reload — OpenCoder 1.5B
context load). Run resumed cleanly at ZEN/ZORA, completed all 115 tokens,
db_total=115 matched log=115 exactly, zero data loss. Errors in `log_health`: 2,
final accuracy trend normal.

**Rule of thumb:** if the next line after the error is a `→ TOKEN:` prediction
within ~5 min AND the Ollama `ExecMainStartTimestamp` advanced during the
gap, it's the bounce pattern — let it finish. Only escalate to the full
recovery recipe (kill + restart ollama + re-run) when `→ TOKEN:` lines are
absent for >5 min with Ollama still showing `inactive (dead)`.

Observed examples:
- 2026-07-14 01:47:04 — **Transient Timeout** — single `Read timed out`,
  next prediction 20s later, run completed clean.
- 2026-07-14 21:00:45 — **Auto-Recovery Bounce** — paired disconnect +
  refused, ~3 min gap (model reload), run completed clean.
- Full Crash pattern — see "Ollama Crash Mid-Run" section above.

**Prevention:** there is no permanent fix — Ollama occasionally crashes are
environmental. Recurring crashes warrant raising `50-MemoryMax.conf` (currently
`MemoryMax=4294967296` = 4GB) or shortening the LLM prompt context. The
proper long-term fix is a watchdog inside the predictor that aborts after N
consecutive connection-refused errors **AND checks whether Ollama
auto-recovered** (look at `ExecMainStartTimestamp` to distinguish a fresh
PID from a stalled one) before triggering the kill-restart procedure —
TODO for tuner.

## Stale Lock From Killed Run (CRITICAL — recovery recipe)

**Symptom:** predictor run hangs at startup and produces no log output, then
times out at 300s with no progress. The 300s timeout kills the foreground
process but `/tmp/candle-predictor.lock` is left behind, holding the
previous (now-dead) PID. A subsequent run will block on the lock the same
way — silent hang, no LLM calls, no log lines, exits only when its own
timeout hits.

This is the **same Pattern A** as `/tmp/hermes-pipeline.lock` documented in
`hermes-pipeline-debug`. The lock file persists when the holder is killed
without clean exit, and nothing in the current `candle_predictor.py` checks
whether the recorded PID is still alive before honoring the lock.

**Diagnosis — separate this from an Ollama crash:**

| Symptom | Ollama Crash | Stale Lock |
|---------|--------------|------------|
| Recent log lines | Repeated `Connection refused` errors | **No new log lines since the prior run died** |
| Predictor process alive | Yes, spinning in retry loop | **No** — `pgrep -af candle_predictor` returns empty |
| `/tmp/candle-predictor.lock` | Held by live PID | **Held by dead PID** (verify with `ps -p $(cat /tmp/candle-predictor.lock)`) |
| Ollama service | `inactive (dead)` | `active (running)` |

If the lock's recorded PID is not running and Ollama is healthy, it's a
plain stale lock. No Ollama restart needed.

**Recovery:**
```bash
# 1. Confirm the lock holder is dead
ps -p $(cat /tmp/candle-predictor.lock) 2>&1
# Expected: "PID ... not found" → lock is stale

# 2. Release the stale lock
rm -f /tmp/candle-predictor.lock

# 3. Re-run in background (NOT foreground — 22 min run will time out at 300s)
terminal(command="python3 /root/.hermes/scripts/candle_predictor.py --nowandb --interval=15",
         background=True, timeout=600, notify_on_complete=True)
```

**Why this happens:** `terminal()` foreground timeout sends SIGKILL/TERM at
300s. The Python interpreter exits, but the file at `/tmp/candle-predictor.lock`
is just a file containing a PID — it's not removed on signal. The next run
opens the file, sees a PID inside, and (depending on the script's lock check)
either trusts the file blindly or the kernel-level `fcntl` advisory is held
by another process. Either way, the new run can't acquire the lock.

**Prevention:** the proper fix is a lock-staleness check in `candle_predictor.py`
on startup — `os.kill(int(open(LOCK).read()), 0)` to test liveness, and if it
fails (`ProcessLookupError`), unlink and re-acquire. This is the same pattern
`run_pipeline.py` had to fix in Bug 17. TODO for tuner.

**Detection while running:** if you backgrounded a run and it's been
~5 min with zero new log lines AND no `→ TOKEN:` prediction lines appearing,
that's the stale-lock signature (or the Ollama crash signature). Run the
diagnostic above before assuming Ollama is down.

## Verifying It's Not Hung (strace diagnostic)

When a 15m run looks "stuck" (e.g. only shows `Fetching HL market data...`
for 2+ min, or no `→ TOKEN:` lines for 10+ min), distinguish normal slowness
from a real hang before killing the run. Three cheap signals:

**1. Process state + wchan** — confirm it's not deadlocked:
```bash
PID=$(pgrep -f candle_predictor | head -1)
cat /proc/$PID/wchan; echo       # "futex_wait_queue" = sleeping, normal
cat /proc/$PID/status | grep -E '^(State|Name)'
```
A sleeping process waiting on a futex is normal — Python's ThreadPoolExecutor
parks workers on `futex_wait` between jobs. A process stuck in `D` (uninterruptible
sleep, often waiting on disk/NFS) for minutes is a real problem.

**2. strace with -f** — see what threads are actually doing:
```bash
timeout 3 strace -p $PID -f 2>&1 | head -30
```
In a healthy run you'll see dozens of `futex(...)` lines (workers parked,
normal). If you see one thread stuck on `recvfrom` to a single peer for
>30s, that's the hung connection. If you see a single thread spinning in
`clock_nanosleep` with a far-future deadline (e.g. `tv_sec=2298154`), the
Ollama runner is waiting for its own cooldown — still working, just slow.

**3. Active outbound sockets** — confirm there's network activity:
```bash
ls /proc/$PID/fd/ | wc -l                          # should be >5
ss -tan | grep $PID | grep -v '127.0.0.1'          # outbound TCP
```
A normal run during HL fetch has 5-15 fds (DB connection, log file, + per-thread
sockets to HL API + Ollama). 5 fds with no outbound = the ThreadPoolExecutor
is parked waiting on a slow call, but the process itself is alive — wait it out.

**Threshold to actually worry:**
- No new log line AND no new `→ TOKEN:` for >15 min during the predict loop
- `wchan` is `D` state for >30s
- `ss -tan | grep $PID` shows 0 outbound connections for >5 min during HL fetch
  (means workers hit a DNS resolve or TLS handshake hang)

If none of those trip, the run is just slow — Ollama + HL + parallel workers
naturally produce lumpy progress. Don't kill a healthy run.

## Scheduled-Run Workflow (cron-friendly pattern)

When `candle_predictor` is invoked from a scheduled cron job (no human in the
loop), the agent must finish the job autonomously — there is no one to ask
"is this run OK?" Use this 4-step pattern. Total agent overhead: ~30s post-run
plus ~22 min wall-clock for the predictor itself.

### Step 1 — Preflight (~3s)

Before launching, verify the preconditions. A stale lock or dead Ollama at this
point wastes the entire run.

```bash
# Lock + process
pgrep -af '[c]andle_predictor.py' || echo "no predictor running"
if [ -f /tmp/candle-predictor.lock ]; then
  pid=$(</tmp/candle-predictor.lock)
  kill -0 "$pid" 2>/dev/null && echo "lock HELD by live pid=$pid" || echo "lock STALE pid=$pid (will overwrite)"
fi
# Ollama
systemctl is-active ollama
curl -sS -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:11434/api/tags
```

If `ollama` is `inactive` or API returns non-200, restart Ollama before launching
the run (see Ollama Crash recipe). If lock is held by a live PID, abort — another
run is in progress.

### Step 2 — Background launch (~5s of agent time)

```python
terminal(
  command="python3 /root/.hermes/scripts/candle_predictor.py --nowandb --interval=15",
  background=True,
  timeout=3600,        # harmless — actual cap is server-side
  notify_on_complete=True,
  workdir="/root",
)
```

Save the returned `session_id` — you'll need it for the post-run checks.

### Step 3 — Wait in chunks (loop until `status: "exited"`)

`process(action="wait")` clamps at 180s regardless of `timeout`. Loop:

```python
while True:
  r = process(action="wait", session_id=session_id, timeout=180)
  if r["status"] == "exited":
    break
  # status="timeout" → still running, just keep waiting
```

For a 15m run, expect ~6-8 chunks. Do NOT call `kill` unless the Ollama-crash
or stale-lock diagnostic above indicates the run is wedged.

### Step 4 — Verify and report (~10s)

Always run the post-run report script — it cross-checks log totals against
`predictions.db` and catches the "script claimed 116 but DB has 0" failure mode
caused by SIGKILL between log flush and DB commit.

```bash
python3 /root/.hermes/skills/trading/candle-predictor-tuner/scripts/post_run_report.py --pretty
```

Then in the cron delivery report include:
1. **Tokens predicted / inverted** (from `summary` field)
2. **Errors + warnings count** (from `log_health` field — escalate only if
   `errors > 0` repeats across runs)
3. **Accuracy trend** (latest-200 vs previous-200 from `trend_200_blocks` —
   flag a >10pt drop as a regression signal)
4. **Direction split health** (from `latest_200_direction` — flag DOWN acc
   below 50% when `n >= 15` as an inversion-tuning signal)

Cron-silent rule: if the run is fully clean (exit_code 0, no errors, no
regressions) and you're confident nothing has changed since the last report,
you may emit `[SILENT]` to suppress delivery. But err on the side of reporting
— scheduled runs that go silent for a week are how regressions sneak in.

**Healthy cron snapshot (2026-07-14 01:31 cron, 15m run):**
`log=116, db=116, errors=1 (transient timeout), inverted=35, latest_200=86.0%
(up from 74.0%), latest_200 UP=92.5% (n=186) DOWN=0.0% (n=14 — noisy, watch)`.
This was a successful run worth reporting — DOWN accuracy is the only soft flag.

**Healthy cron snapshot (2026-07-14 16:00 cron, 15m run, this session):**
`log=117, db=117, errors=0, inverted=37, latest_200=87.5% (down from
90.5%), latest_200 UP=89.7% (n=195) DOWN=0.0% (n=5 — too small to act),
latest_200_inversion NORMAL=90.5% (n=137) vs INVERTED=81.0% (n=63)` —
9.5pt NORMAL>INVERTED lead, **fourth consecutive 15m run where this
divergence persisted**. The trend-200 drift (-1.0 → -1.5 → -3.0 across
the last three runs) is mild but consistent. Use this as the baseline
when comparing future runs: any run with NORMAL < INVERTED in the
latest_200 window is a regime change worth investigating.

### Known pitfall — act-on-next-cycle drift (observed 11:10 → 15:30 → 16:00)

The SKILL.md Improvement Triggers table says ≥5pt NORMAL>INVERTED on
n≥50 each → tighten inversion thresholds, and the documented rule is
"when this trigger is satisfied for ≥2 consecutive runs, act on the
next cycle, don't wait for a third."

Observed drift across 11:10 → 15:30 → 16:00 cron sequence: trigger
fired first at 11:10, was confirmed at 15:30 (rule said "act on next
cycle"), and the 16:00 cycle collected another data point instead of
acting. Three failures of the same rule is not a transient observation
cycle anymore — it's a stale-guidance pattern where the cron is
treating "watch next 2 runs" as an indefinite license.

When you're the cron reading this rule: if the previous 1-2 reports
already noted "should act next cycle," and the current run again meets
the trigger, **stop reporting and act** — write the inversion
threshold change, log to candle-tuner.log, and let the next cron
verify the move. Don't burn a third confirmation cycle when the
evidence is already sufficient.

Why this happens: the cron pattern (4-step scheduled-run workflow
above) deliberately separates "report" from "modify" — Step 4 is
verify-and-report only, not act. So consecutive data-collection runs
are an emergent property of the workflow, not a bug in the trigger
table. The fix is either (a) Step 4 should also act when the trigger
threshold was previously flagged, or (b) the tuner needs a separate
"act" pass after the "report" pass. TODO for the tuner to wire into
candle_predictor auto-tuning.

**Healthy observation (15m cron run, 2026-07-15 02:52, this session) — first
agent-driven 15m run of the day + new bug discovery:**
log=117 / inverted=39 / errors=0 / wall=21m19s (02:52:13 → 03:13:32, exit 0).
Init reported `Overall accuracy: 68490/79870 = 85.8%`, `Inverted: 32952/36265
= 90.9%`. **The agent ran this in foreground first** (default 300s timeout)
and hit `exit_code: 124` exactly as "Distinguishing a killed-by-timeout run
from a clean-exit run" predicts — but unlike the 2026-07-15 02:23 session,
this time the agent **did not** follow the stale-lock recovery recipe; the
prompt was a one-shot cron instruction, so the killed foreground run
abandoned the predictions and the agent re-launched via
`terminal(background=True, timeout=900)` after the first 5-min timeout.
Re-launch completed cleanly: 117 predicted, 39 inverted, 0 errors, log
matches DB exactly (117/117). Persistent skip list unchanged (9 low-acc:
ETH, ETHFI, INIT, KFLOKI, MATIC, MEME, MKR, PURR, SNX + 5 no-data: BAT,
KAVA, THETA, VET, YFI). Direction split: UP 113 / DOWN 4 (extreme UP-skew
continues, 96.6% UP). All 39 inversions were DOWN→UP flips; only 2
native DOWN predictions survived (ATOM in bearish at 44.3% acc, BERA
in neutral at 38.5% — both above the keep threshold). **New finding**:
verified via `SELECT candle_time - prediction_time FROM predictions WHERE
prediction_time BETWEEN 1784083933 AND 1784085212` — every one of the
117 rows has delta=14400 (4h), not 900 (15m). See the "candle_time is
hardcoded to prediction_time + 14400" pitfall above for the full diagnosis
and the two patch options. This is now documented as a durable bug in
the script and flagged for T — the trading rules require surgical
fixes to the live predictor, so this is NOT a self-patch candidate.
**Use this as the reference for "agent cron received the task, ran in
foreground by mistake, hit the documented timeout, recovered, and
completed cleanly"** — and the first run that established the
candle_time bug as a 117-row-confirmed pattern (not a one-off row
anomaly).
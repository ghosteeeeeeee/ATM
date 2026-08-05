# Pipeline Running But Compactor Dead — Signals Stranded, Hot-Set Stuck Empty

**Symptom:** `hotset.json` is `{"hotset": [], "compaction_cycle": <big>}` indefinitely. WASP
keeps warning "hotset empty (Xs ago, <2m grace)". Meanwhile `signals.json` shows signals
being generated (pending/executed entries grow). No trades open.

## Diagnosis (5 checks, in order)

### 1. Confirm compactor is dead
```bash
ps -ef | grep signal_compactor | grep -v grep
# → EMPTY = compactor is NOT running
```

### 2. Verify cand date signal_compactor.log was last written
```bash
ls -la /root/.hermes/logs/signal-compactor.log
tail -3 /root/.hermes/logs/signal-compactor.log
# Check the timestamp. If it's days/weeks old, compactor has not run.
```

### 3. Check whether a systemd unit exists for it
```bash
systemctl list-units --type=service --all --no-pager | grep signal-compactor
systemctl list-timers --all --no-pager | grep signal-compactor
# Per SOUL.md: cron is forbidden, use systemd. If no unit exists, it was either
# never set up or got removed during a refactor.
```

### 4. Confirm signals IS being produced (without compactor)
```bash
python3 -c "
import json
d = json.load(open('/var/www/hermes/data/signals.json'))
print('updated:', d['updated'])
print('pending:', len(d['pending']))
print('executed:', len(d['executed']))
print('expired:', len(d['expired']))
print('hot_set:', len(d['hot_set']))
"
```

### 5. Identify which script is producing signals (and confirm it has no dedup)
```bash
ps -ef | grep -E "candle_predictor|signals_runner|signal_gen" | grep -v grep
```

## What Was Wrong in 2026-07-14

`sigdal-compactor.log` last wrote at **2026-05-30 06:31:36** (cycle **45243**). At
incident time, `hotset.json` showed `compaction_cycle=107401`. The cycle counter had been
incremented somewhere — possibly a manual write or a half-finished migration — but the
compactor was definitively dead for ≥ 6 weeks.

`candle_predictor.py --nowandb --interval=15` (PID 3016803, started 01:31) was running
hard, writing the same `(coin, type, direction)` signals to `signals.json` 4–6 times per
15-minute cycle (no dedup window). Result: 136 dup signals in the last 15 minutes before
the hot-set check, all stranded.

`signals_runner.py` (PID 3021976, started 01:47) was also running, executing standalone
signal scripts — also without compactor downstream, its output is stranded too.

`price_collector.py` (PID 3022138) was active and feeding `signals_hermes.db` /
`signals_hermes_runtime.db` correctly.

`hl-sync-guardian.py` and `metrics_collector.py` were running under systemd and healthy.

**Nothing in the pipeline connects signals.json → hotset.** That's the structural failure.

## Root-Cause Pattern

Three separate bugs compounded:

1. **`signal_compactor.py` was not supervised.** No systemd timer (`hermes-signal-compactor.timer`),
   no launcher script. It silently went down and stayed down.
2. **No signal deduplication upstream.** `candle_predictor.py --interval=15` writes one
   row per matched condition with no `(coin, type, direction, window_minutes)` window.
   Even with compactor alive, this would amplify signal volume ~5× and waste compactor
   cycles.
3. **`hotset.json compaction_cycle` is write-only and lacks validation.** A bumped
   counter (45,243 → 107,401) is not self-healing. Consider clamping `cycle` against
   `mtime` of the previous write — if mtime is weeks stale, cycle should NOT increase.

## Diagnostic for Trapped in This State Right Now

If a cron/wasp session hits this scenario, the diagnosis section above takes ~10 seconds.
The full triage command set:

```bash
# Quick "is the pipeline alive?" check
ps -ef | grep -E "signal_compactor|predictor|signals_runner|price_collector|hl-sync-guardian" | grep -v grep
echo "---"
ls -la /var/www/hermes/data/hotset.json /var/www/hermes/data/signals.json
echo "---"
systemctl list-units --type=timer --all --no-pager | grep signal-compactor
echo "---"
tail -10 /root/.hermes/logs/signal-compactor.log 2>&1
echo "---"
python3 -c "
import json, time
hs = json.load(open('/var/www/hermes/data/hotset.json'))
sig = json.load(open('/var/www/hermes/data/signals.json'))
print('hotset:', len(hs.get('hotset', [])), 'cycle:', hs.get('compaction_cycle'))
print('signals pending/executed/expired:', len(sig['pending']), len(sig['executed']), len(sig['expired']))
print('updated:', sig['updated'])
"
```

## Fix Path (do NOT execute — flag to T; trading path is surgical)

1. **Restore `signal_compactor.py` under a systemd timer.** Either re-attach the existing
   `hermes-signal-compactor.timer` if it exists in `/etc/systemd/system/`, or create one:
   ```ini
   # /etc/systemd/system/hermes-signal-compactor.timer
   [Timer]
   OnBootSec=2min
   OnUnitActiveSec=2min
   AccuracySec=10s

   [Install]
   WantedBy=timers.target
   ```
   Paired with a `hermes-signal-compactor.service` running
   `python3 /root/.hermes/scripts/signal_compactor.py`. 2-minute interval (not 1 — gives
   time for the 90-120s runtime seen on 2026-05-28 incident).

2. **Add signal deduplication.** Either in `candle_predictor.py` (the emitter) or
   in `signals_runner.py` (the orchestration layer):
   ```python
   DEDUP_WINDOW_MINUTES = 5  # suppress same (coin, type, direction) within window
   recent = json.load(open('/var/www/hermes/data/signals.json'))['signals']
   seen = {(s['token'], s['type'], s['direction']) for s in recent if age < window}
   # filter new signals against `seen` before appending
   ```

3. **Sanity-check `compaction_cycle` against file mtime.** In `signal_compactor.py`'s
   write step, add:
   ```python
   import os, time
   hotset_path = '/var/www/hermes/data/hotset.json'
   prev_mtime = os.path.getmtime(hotset_path) if os.path.exists(hotset_path) else 0
   gap = time.time() - prev_mtime
   if gap > 600:  # 10 minutes
       # Previous compactor missed multiple cycles — clamp the counter
       new_cycle = prev_cycle + 1
       print(f"[WARN] compactor gap {gap/60:.0f}min — clamping cycle {prev_cycle}→{new_cycle}")
   else:
       new_cycle = prev_cycle + 1
   ```

## What Would Have Caught This Earlier

- WASP already flags "hotset empty (within grace)" every cycle. A persistent empty is
  correctly surfaced as WARNING — **but only flagging does not fix it**. Without an
  auto-recovery path on the compactor service, every cron session will re-discover the
  same dead compactor.
- A `compactor.last_run_at` file (or DB row) updated on every successful run would let
  WASP produce a different WARNING: "compactor has not run in X minutes" instead of the
  indirect signal "hotset empty". The latter is currently the only proxy.

## Key File Paths (canonical, not duplicates)

| Purpose | Path |
|---|---|
| Hot-set output | `/var/www/hermes/data/hotset.json` |
| Signals output | `/var/www/hermes/data/signals.json` (structured dict, see below) |
| Compactor script | `/root/.hermes/scripts/signal_compactor.py` |
| Compactor log | `/root/.hermes/logs/signal-compactor.log` (also `.err.log`) |
| Compactor systemd unit | `/etc/systemd/system/hermes-signal-compactor.{service,timer}` |
| Pipeline services systemd dir | `/etc/systemd/system/hermes-*.{service,timer}` |
| Candle predictor (signal emitter) | `/root/.hermes/scripts/candle_predictor.py` (and the signals/ module) |
| Decider/position manager | `/root/.hermes/scripts/decider_run.py`, `position_manager.py` |

## signals.json Schema (Pitfall)

`signals.json` is **a dict, not a list**. Top-level keys:
```
{
  "updated": "YYYY-MM-DD HH:MM:SS",
  "total": int,
  "approved": [signal, ...],
  "executed": [signal, ...],
  "pending": [signal, ...],
  "skipped": [signal, ...],
  "expired": [signal, ...],
  "signals": [signal, ...],   # full history (capped at ~200)
  "stats": {...},
  "hot_set": [...]            # populated by signal_compactor, NOT signal emitters
}
```

Treating it as a flat list and doing `s['time']` on `[s for s in json.load(...)]` throws
`TypeError: string indices must be integers`. Always access
`data['signals'] + data['executed'] + ...` or pass
`if isinstance(s, dict) and 'time' in s` as a guard.

Each signal record has:
```
{token, direction, confidence, type, source, price, zscore, rsi, macd, decision, time}
```

`direction` is `LONG|SHORT`. `decision` is `PENDING|EXECUTED|EXPIRED|APPROVED|SKIPPED`.
`hot_cycle_count` and `compact_rounds` live in PostgreSQL `signals` table, not in
`signals.json`.

## Related References
- `hermes-pipeline-debug/SKILL.md` — Bug 17, 19, 20, 21 (lock/race/overlap patterns)
- `wasp-monitoring/SKILL.md` — "hotset empty" WARNING handling
- `candle-predictor-tuner/references/running-predictor.md` — stale-lock-on-killed-run

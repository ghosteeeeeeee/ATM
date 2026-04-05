# Plan: Diagnose & Fix Stale Signal Pipeline

## Goal
Get the Hermes signal pipeline running continuously so new PENDING signals are generated, reviewed, and approved in real-time — not 30+ minutes behind.

## Current Context / Assumptions

**Observed problem:**
- `hotset.json` is 26+ minutes old (last written before recent code changes)
- All signals in hot-set show `wave=neutral, mom=50` because the wave enrichment was added after the last ai_decider run
- `signals_hermes_runtime.db` has 498 PENDING signals, but only 6 APPROVED and 6 EXECUTED today
- Position count is 10/10 (maxed), so execution is blocked on capacity anyway — but the pipeline should still be cycling

**What should happen:**
1. `signal_gen.py` generates new signals every N minutes → PENDING
2. `ai_decider.py` compact_signals() reviews PENDING signals → writes enriched hot-set.json
3. `decider-run.py` reads hot-set.json → approves & executes

**What's broken:**
- ai_decider is not running on a cron (or not running at all since the lazy-load fix)
- decider-run.py blocks new approvals when hot-set is >120s stale
- Even though positions are full, the pipeline should still be running to build the next batch

## Proposed Approach

### Step 1: Diagnose — Why isn't ai_decider running?

**Files to inspect:**
- `~/.hermes/crons/` — check for ai_decider cron entries
- `/root/.hermes/scripts/ai_decider.py` — check the `if __name__ == '__main__':` guard and pipeline loop
- systemd timers: `systemctl list-timers` or check `/etc/cron.d/`
- Any runner script: `run_pipeline.py`, `pipeline_runner`, etc.

**Questions to answer:**
- Is there a cron job scheduled for ai_decider? What interval?
- Does ai_decider.py have a `while True:` loop with a sleep interval inside `if __name__ == '__main__':`?
- Or does something else call it (signal_gen.py post-generation hook)?
- Did the lazy-load fix break a startup path?

### Step 2: Fix the cron / scheduling

If no cron exists → set one up (every 2–5 minutes).

If ai_decider has a main loop → verify it writes to hotset.json and exits cleanly.

If something else triggers it → check that the trigger is still connected.

**Likely fix:** Add or restore a cron entry:
```
*/2 * * * * cd /root/.hermes/scripts && python3 ai_decider.py >> /root/.hermes/logs/ai_decider.log 2>&1
```

### Step 3: Verify live signal generation

- Run `signal_gen.py` manually → check DB for new PENDING signals with recent `created_at`
- If signal_gen also isn't running → fix its cron too

### Step 4: Validate wave enrichment

Once ai_decider runs:
- Check `hotset.json` timestamp is < 60s old
- Check that `wave_phase` values are NOT all "neutral"
- Check that `momentum_score` varies (not all 50)

## Files Likely to Change

- `~/.hermes/crons/` — add/restore ai_decider cron
- OR `/etc/cron.d/hermes` — if using system cron
- OR `systemd` timer file for ai_decider
- Possibly `signal_gen.py` — if it needs a post-generation hook to trigger ai_decider

## Tests / Validation

1. `ls -la /var/www/hermes/data/hotset.json` — timestamp should be < 60s old
2. `python3 -c "import json; hs = json.load(open('/var/www/hermes/data/hotset.json')); print(hs['hotset'][0].get('wave_phase'))"` — should NOT be `None`
3. `sqlite3 signals_hermes_runtime.db "SELECT COUNT(*) FROM signals WHERE created_at > datetime('now','-5 minutes')"` — should be > 0
4. `python3 ai_decider.py` (manual run) → should complete without error and update hotset.json

## Risks & Tradeoffs

- **Risk:** ai_decider takes 10–30s to run (was 11s import + full pipeline). With the lazy-load fix, import is 0.4s but full compaction may still be slow. A 2-minute cron may be too aggressive.
- **Tradeoff:** Faster cron = more CPU spend on Hyperliquid API calls. Balance at 3–5 min intervals.
- **Open question:** Does ai_decider need to run continuously (background loop) or just on cron? The `if __name__ == '__main__':` guard suggests it's designed to run-once per invocation. A cron calling it every 2–5 min is likely correct.

## Save Plan to
`.hermes/plans/2026-04-03_064126-run-the-ai-engineer-to-help-figure-this.md`

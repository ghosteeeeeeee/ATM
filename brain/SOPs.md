# SOPs — Standard Operating Procedures

Recurring procedures for the Hermes trading system. Follow these every time.

---

## 1. Make/Save a Plan

When: Before building any non-trivial feature or fix.

1. Analyze the problem (read data, trace code, find root cause)
2. Write the plan as a `.md` file in `plans/`
3. Filename format: `YYYY-MM-DD_topic.md` or `descriptive-name.md`
4. Include: Date, Status, Problem, Root Cause, Proposed Fix, Files to change, Parameters, Verification steps
5. Save to OpenMemory: `openmemory_openmemory_store(content="...", tags=["plan", "topic"])`
6. Commit: `git add -A && git commit -m "plan: description"`

---

## 2. Commit Changes

When: After every task that modifies files. Do not batch — commit after each logical unit.

```bash
git add -A
git commit -m "Category: brief description"
python3 /root/.hermes/skills/productivity/update-git/references/push_gh.py
```

**Categories:** `scripts`, `signals`, `skills`, `plans`, `memory`, `config`, `fix`, `backtest`

**Never use `git push` directly.** Always use the canonical push script above.

---

## 3. Create a New Signal

When: Adding a new trading signal to the pipeline.

1. Check `scripts/signals/` for existing similar signals
2. Add constants to `hermes_constants.py` (ALL tunables go here, never hardcode)
3. Create `scripts/signals/your_signal.py` with `run(prices_dict)` entry point
4. Register in `scripts/signals/__init__.py` (fast or slow list)
5. Add source gating in `scripts/signal_schema.py`
6. Test: `python3 scripts/signals/your_signal.py --token IMX --verbose`
7. Commit, then run `bug_hunter` subagent for verification

---

## 4. Run the Pipeline

When: Manual testing or re-running after changes.

```bash
python3 scripts/run_pipeline.py
```

Acquires lock at `/tmp/hermes-pipeline.lock`. Check if stuck: `cat /tmp/hermes-pipeline.lock`.

Logs: `tail -100 /var/www/hermes/logs/pipeline.log`

---

## 5. Debug a Signal

When: A signal isn't firing or is firing incorrectly.

1. Check if enabled: `grep 'YOUR_SIGNAL_ENABLED' hermes_constants.py`
2. Check source gating: `grep 'your_signal' signal_schema.py`
3. Check cooldowns: query `cooldown_tracker` in runtime DB
4. Run signal in isolation: `python3 scripts/signals/your_signal.py --token TOKEN --verbose`
5. Check recent signals: query `signals` table in `signals_hermes_runtime.db`

---

## 6. Post-Change Verification

When: After any major change (feature, bug fix, refactor).

1. Run `bug_hunter` subagent to audit the diff
2. Run lint/typecheck if available
3. Check logs for errors: `tail -50 /var/www/hermes/logs/pipeline.log`
4. Verify signal DB: query `signals` table for unexpected entries
5. Store summary in OpenMemory

---

## 7. Update Memory

When: End of every session. This is not optional.

```python
openmemory_openmemory_store(
    content="What was done: [summary]. Files changed: [list]. Decisions: [list].",
    tags=["topic", "date"],
    type="contextual"
)
```

---

## 8. Check Trade Performance

When: Reviewing how a signal or token is performing.

```bash
python3 scripts/signal_performance_report.py
```

Or query PostgreSQL brain DB for closed trade stats.

---

## 9. Update Dashboard

When: After any change to trades.html, signals.html, or coin_tracker.html.

1. Edit source file in `/root/.hermes/web/`
2. Copy to BOTH nginx locations:
   ```bash
   cp /root/.hermes/web/trades.html /var/www/hermes/trades.html
   cp /root/.hermes/web/signals.html /var/www/hermes/signals.html
   ```
3. Commit source: `git add web/ && git commit -m "dashboard: description"`

**Gotcha:** Nginx path is `/var/www/hermes/trades.html` — the `web/` subdirectory does NOT exist under `/var/www/hermes/`.

---

## Key Gotchas

- **Two data directories:** `HERMES_DATA=/root/.hermes/data` (local) and `WWW_DATA=/var/www/hermes/data` (served)
- **All paths** are defined in `scripts/paths.py` — import with `from paths import *`
- **Never hardcode constants** — everything goes in `hermes_constants.py`
- **ai_decider.py is DEFUNCT** — replaced by `signal_compactor.py`
- **LIVE_TRADING_ENABLED** is in `hermes_constants.py` — both that and the runtime kill switch must be True for real money
- **IMX is in the MACD cascade flip list** — special handling applies

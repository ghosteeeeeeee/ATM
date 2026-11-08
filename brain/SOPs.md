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

## 7. Copy Trading Philosophy

When: Always — this is a core system principle.

### 24/7 Live Trading
- We are **24/7 live** — markets never close, we never stop
- If LONG isn't working, SHORT should — don't block directions, improve entry quality
- Don't filter by time of day — improve the signal instead
- Every hour is an opportunity, not a risk

### Copy Trader Rules
1. **Track pro traders by recent performance**, not lifetime metrics
2. **Attribution matters** — every copy trade must have `trader_wallet` in `_signal_metadata`
3. **Stats must accumulate** — `trader_performance` table tracks our copy trade results
4. **Exit correlation** — when a pro trader exits, we should too (via `check_trader_exits`)
5. **Score is not skill** — high leaderboard score can mean old wins, not recent skill

### What Makes a Good Copy Trader
- Consistent recent HYPE performance (last 30 days)
- Position_trader pattern with high win rate
- Not a market maker (tiny fills at fixed prices)
- Active on multiple tokens (diversified)

---

## 10. Gate Proposal Claim Hygiene (CEO D3, 2026-10-12)

When proposing ANY new gate, filter, or hard veto — no exceptions:

1. **Episode-level counts** — dedupe consecutive log lines into episodes. Raw line counts inflate (one gate firing 50 lines in one minute ≠ 50 independent blocks).
2. **First-seen dates** — a gate younger than the analysis window cannot be a "top blocker over 2 weeks." Check `git log -S` or the registry before ranking.
3. **Null-model check** — for any "always / never / 99%" statistic, state what a null model expects. The deadlock episode: 99.7% both-dir-blocked *reproduces*, but three nulls all expect 100% — the stat was vacuous.
4. **Direction-signed counterfactual** — blocked cohort PnL in dollars, long/short signed, vs what the trade would have done. WR alone is not enough.
5. **Register the gate** — add/update the row in `brain/gate_registry.md` in the same change. New gates: shadow-first 14d before hard-veto trust.

Cautionary tale: plans/2026-10-12_gate-conundrum-deadlock-plan.md — a &lt;24h-old gate circulated as a 2-week top blocker; pincer "deadlock" was statistically vacuous. Claim hygiene is the filter that stops that class.

---

## Key Gotchas

- **Two data directories:** `HERMES_DATA=/root/.hermes/data` (local) and `WWW_DATA=/var/www/hermes/data` (served)
- **All paths** are defined in `scripts/paths.py` — import with `from paths import *`
- **Never hardcode constants** — everything goes in `hermes_constants.py`
- **ai_decider.py is DEFUNCT** — replaced by `signal_compactor.py`
- **LIVE_TRADING_ENABLED** is in `hermes_constants.py` — both that and the runtime kill switch must be True for real money
- **IMX is in the MACD cascade flip list** — special handling applies

---

## Locked Test Protocol

When: before tuning ANY constant (ATR_SL_MIN, ATR_TP_K_MULT, SIGNAL_FILTER_SPEED_MIN, k-multipliers, etc.).

1. **Split first.** Before changing the value, split available trade history into a train window + a locked out-of-sample (OOS) window. The OOS window must be **time-based** (e.g. last N days held out, or a pre-declared date boundary) — NEVER outcome-selected. "Pick the window where it looks fair" is banned.
2. **Look at OOS EXACTLY ONCE**, after the tune is frozen (train-window backtest + neighbor ±step test complete).
3. **Accept or revert — never retune against that window.** After seeing OOS results you may accept the tune or revert to the old value, but you may NEVER retune against that same window. A new tune requires a NEW OOS window or a new pre-declared date boundary.
4. **Record every tune:** constant name, old→new value, train-window dates, OOS-window dates, OOS verdict (accept/revert) — in the commit message AND in `automation/recent_changes.log`-compatible form.
5. **Tooling:** `python3 scripts/locked_test_split.py --oos-days 14` (or `--train-end YYYY-MM-DD`) prints train/OOS ranges + trade counts and marks the OOS window consumed in `HERMES_DATA/locked_test_state.json`, so a second look is detectable. `--reset` clears it (explicit flag required).

Why: the 2026 constant history (ATR_SL_MIN 1.3→1.5, ATR_TP_K_MULT 1.5→2.0, SIGNAL_FILTER_SPEED_MIN 30→40) was tuned and judged on the same data — no OOS, no ±step robustness. A prior CEO run had 4 failed analyses from survivorship bias / time-anchor bugs / unreproducible numbers. (transcript-mining ideas 1, 2)

---

## Rule-Change Loop

When: ANY threshold/constant change to a live rule — no exceptions.

**Banned pattern:** no threshold changes driven by a recent losing stretch. "ATR_SL widened again after a red 48h" is forbidden — a red 48h is an observation, not a change request. Every reactive widening/loosening after a losing stretch is a process violation regardless of outcome.

Every rule change must go through the full loop:

1. **Idea** — written down: hypothesis, constant name, current→proposed value.
2. **Full gates** — backtest on the train window (per Locked Test Protocol above) + neighbor ±step test (±1–2 steps around the proposed value must also work — an edge is a hill, not a spike) + OOS looked at exactly once.
3. **Paper/shadow** — ship in shadow mode via the `automatic-implementation` skill (staggered shadow→enforce rollout); collect counterfactual data for the pre-declared period.
4. **Swap-on with recorded pre-registered bar** — flip ON only after the shadow period passes the bar declared BEFORE it started; record the bar and the result alongside the tune record.

The old rule keeps trading until the new one earns the swap. Mirrors the `automatic-implementation` skill; this section is the gates document that skill was missing.

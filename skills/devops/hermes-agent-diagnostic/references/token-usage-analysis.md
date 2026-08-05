# Token usage analysis — Hermes Agent

Reusable patterns for "where are the tokens going" questions. Verified against Hermes Agent v0.18.2 with MiniMax provider on 2026-07-13.

## Entry point: `hermes insights`

```bash
hermes insights                    # last 30 days, all sources
hermes insights --days 7           # narrower window
hermes insights --days 1           # today only — useful when burn rate is high
hermes insights --source cron      # only cron jobs
hermes insights --source cli       # only CLI sessions
hermes insights --source subagent  # subagent delegation cost
```

Output sections: Overview, Models Used, Platforms (source breakdown), Top Tools, Top Skills, Activity Patterns, Notable Sessions.

## Pitfall 1 — The 30-day window is misleading

On 2026-07-13, `hermes insights` reported "Last 30 days" with 1,083 sessions and 285M tokens. But:

```sql
sqlite3 ~/.hermes/state.db "SELECT date(started_at,'unixepoch') day, COUNT(*) sessions, SUM(input_tokens+output_tokens+cache_read_tokens)/1000 tot_tokens_k FROM sessions WHERE started_at > strftime('%s','now','-14 days') GROUP BY day;"
```

Returned: only 2 active days (Jul 5 with 4.35M, Jul 13 with 56.9M and counting). **985 of 1,083 sessions happened today.**

**Rule:** Always check the date range inside the insights output (it shows "Period: X — Y" at the top). If the span is 1 day, frame the analysis as "today" not "30 days". Use `--days 1` for freshest data.

## Pitfall 2 — `actual_cost_usd` is always 0.0 with MiniMax

```sql
SELECT COUNT(*) sessions_with_cost, SUM(actual_cost_usd) total_cost
FROM sessions WHERE actual_cost_usd > 0;
-- Returns: 0 | (null)
```

Hermes doesn't get pricing back from the MiniMax SDK, so the cost column is always empty. Don't promise the user USD numbers — report token counts + per-provider + per-source breakdowns instead.

## Pitfall 3 — `insights` aggregates, doesn't show per-job cost

The Top Tools / Top Skills sections don't break down token usage per cron job. To find the top-burning cron job, query `state.db` directly:

```sql
-- Per-cron-job token totals (group by title prefix)
SELECT 
  CASE 
    WHEN title LIKE 'hermes-pipeline%' THEN 'hermes-pipeline'
    WHEN title LIKE 'profit-monster%' THEN 'profit-monster'
    WHEN title LIKE 'hype-paper-sync%' THEN 'hype-paper-sync'
    WHEN title LIKE 'wasp-health%' THEN 'wasp-health'
    WHEN title LIKE 'closed-trades%' THEN 'closed-trades-eval'
    WHEN title LIKE 'study-winning%' THEN 'study-winning-combos'
    WHEN title LIKE 'signals-compact%' THEN 'signals-compact'
    WHEN title LIKE 'Candle Predictor%' THEN 'candle-predictor-15min'
    ELSE title
  END as job,
  COUNT(*) as sessions,
  SUM(input_tokens+output_tokens+cache_read_tokens) as total_tokens,
  ROUND(AVG(input_tokens+output_tokens+cache_read_tokens),0) as avg_tok
FROM sessions
WHERE source='cron'
GROUP BY 1
ORDER BY total_tokens DESC;
```

## Pitfall 4 — Watch for individual session outliers

```sql
-- Top single cron sessions by token usage
SELECT 
  substr(id,1,24) as id,
  substr(title,1,45) as title,
  (input_tokens+output_tokens+cache_read_tokens) as tok,
  datetime(started_at,'unixepoch') as started
FROM sessions 
WHERE source='cron' AND (input_tokens+output_tokens) > 0
ORDER BY (input_tokens+output_tokens+cache_read_tokens) DESC
LIMIT 12;
```

Any single session > 1M tokens is unusual. > 5M is almost certainly either (a) a one-shot massive analysis, or (b) a context-explosion bug (loop accumulating context without compaction). Always check `~/.hermes/cron/output/<job-id>/` for the actual prompt when you see this.

## Pitfall 5 — Daily burn rate is the real metric

For cost projection, sum a single day's tokens and project forward:

```sql
SELECT 
  date(started_at,'unixepoch') as day,
  COUNT(*) as sessions,
  ROUND(SUM(input_tokens+output_tokens+cache_read_tokens)/1000.0, 0) as tot_tokens_k,
  ROUND(AVG(input_tokens+output_tokens+cache_read_tokens)/1000.0, 1) as avg_k
FROM sessions 
WHERE started_at > strftime('%s','now','-14 days')
GROUP BY day
ORDER BY day;
```

If today shows 50M+ tokens and yesterday was 0, the user is in a high-burn regime and rate limits / plan exhaustion are imminent.

## Baseline: per-cron-job token costs (captured 2026-07-13)

| Job | Sessions | Total Tokens | Avg/Session | Notes |
|---|---:|---:|---:|---|
| profit-monster | 452 | 12.87M | 28,466 | High-volume (1/min), but small per-run |
| hermes-pipeline | 372 | 10.22M | 27,462 | High-volume (1/min), small per-run |
| candle-predictor-15min | 18 | 7.69M | **427,037** | **15× average — biggest per-run cost** |
| wasp-health | 86 | 5.58M | 64,932 | 5/min cadence |
| hype-paper-sync | 42 | 1.22M | 29,160 | 10/min cadence |
| signals-compact | 1 | 124K | 124,072 | Daily, low volume |
| study-winning-combos | 3 | 119K | 39,739 | 4×/day |
| closed-trades-eval | 2 | 40K | 20,207 | Every 4h, paused 2026-07-13 (HTTP 429) |

**Outliers worth investigating:**
- `candle-predictor-15min` 427K avg — investigate per-tick context size
- 2× `Hermes Signal Audit` sessions at 13:57:23 (Jul 13): 5.0M + 4.3M = 9.3M in 130ms

## Cost-reduction levers (in priority order)

1. **Disable or throttle `candle-predictor-15min`** — 16% of total cron tokens from one job
2. **Set per-profile `agent.max_turns` lower for cron** — current default is 60, cron rarely needs more than 20
3. **Use `no_agent=True` for watchdog jobs** (wasp-health, pipeline-watch) — skip LLM entirely, just deliver script stdout
4. **Enable prompt caching aggressively** — `cache_write_tokens` exists in schema but doesn't appear heavily used
5. **Override model per job** — `hermes cron edit <id> --model anthropic/claude-haiku-4` for routine analysis
6. **Add per-job budget cap** — feature doesn't exist yet but is the obvious next ask

## Schema reference (sessions table)

Relevant columns in `~/.hermes/state.db.sessions`:
- `source TEXT NOT NULL` — `cli`, `cron`, `subagent`, `tui`, `gateway`, `telegram`, etc.
- `model TEXT` — `MiniMax-M3`, `MiniMax-M2.7`, etc.
- `input_tokens INTEGER DEFAULT 0`
- `output_tokens INTEGER DEFAULT 0`
- `cache_read_tokens INTEGER DEFAULT 0`
- `cache_write_tokens INTEGER DEFAULT 0`
- `reasoning_tokens INTEGER DEFAULT 0`
- `estimated_cost_usd REAL` — usually 0.0
- `actual_cost_usd REAL` — usually 0.0
- `started_at REAL` — Unix timestamp (use `datetime(started_at,'unixepoch')`)
- `title TEXT` — job name + timestamp for cron, free-form for others

## Useful one-shot queries

```sql
-- Today's token burn
SELECT SUM(input_tokens+output_tokens+cache_read_tokens) 
FROM sessions 
WHERE date(started_at,'unixepoch') = date('now');

-- Top 10 most expensive sessions of all time
SELECT title, model, (input_tokens+output_tokens) tok, 
       datetime(started_at,'unixepoch') started
FROM sessions 
WHERE input_tokens+output_tokens > 0
ORDER BY tok DESC LIMIT 10;

-- Token usage by model
SELECT model, COUNT(*) sessions, 
       SUM(input_tokens+output_tokens) total_tok
FROM sessions
WHERE input_tokens+output_tokens > 0
GROUP BY model
ORDER BY total_tok DESC;

-- Sessions with no token record (probably failed before LLM call)
SELECT COUNT(*) FROM sessions 
WHERE input_tokens = 0 AND output_tokens = 0 
AND started_at > strftime('%s','now','-7 days');
```

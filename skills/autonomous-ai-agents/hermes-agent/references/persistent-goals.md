# Persistent Goals — /goal Feature

Persistent Goals keep Hermes working on a task across multiple turns automatically — no need to re-prompt. Directly inspired by Codex CLI 0.128.0's `/goal` by Eric Traut (OpenAI).

## How It Works

1. You set a goal with `/goal <task>`
2. Hermes works on it for one turn
3. After each turn, a lightweight judge model checks: done or continue?
4. If not done, Hermes automatically takes the next turn — loops until done, paused, or budget runs out

```
Goal accepted — ⊙ Goal set (20-turn budget): <your goal>
Turn 1 runs — Hermes starts working
Judge runs — after the turn, the judge model decides done or continue
Loop fires if needed — ↻ Continuing toward goal (1/20): <judge's reason>
Terminates — eventually: ✓ Goal achieved or ⏸ Goal paused — N/20 turns used
```

## Command Reference

| Command | What it does |
|---------|-------------|
| `/goal <text>` | Set (or replace) the standing goal. Kicks off the first turn immediately. |
| `/goal` or `/goal status` | Show the current goal, its status, and turns used. |
| `/goal pause` | Stop the auto-continuation loop without clearing the goal. |
| `/goal resume` | Resume the loop (resets the turn counter to zero). |
| `/goal clear` | Drop the goal entirely. |
| `/subgoal <text>` | Append a new criterion to the active goal. Requires an active `/goal`. |
| `/subgoal` (no args) | Show the current numbered subgoal list. |
| `/subgoal remove <N>` | Remove the Nth subgoal (1-based). |
| `/subgoal clear` | Drop every subgoal but keep the original goal intact. |

## Turn Budget

- Default: **20 turns** (`goals.max_turns` in config.yaml)
- When budget is hit: `⏸ Goal paused — 20/20 turns used. Use /goal resume to keep going, or /goal clear to stop.`
- `/goal resume` resets counter to zero — can continue in measured chunks

## Judge Behavior

After every turn, Hermes calls an auxiliary model with:
- The standing goal text
- The agent's most recent final response (last ~4 KB)
- A system prompt telling the judge to reply with strict JSON: `{"done": <bool>, "reason": "<one-sentence rationale>"}`

**Judge is deliberately conservative** — marks done only when:
- Response explicitly confirms goal is complete
- Final deliverable is clearly produced
- Goal is unachievable/blocked (treated as DONE with block reason)

**Fail-open:** If judge errors (network blip, malformed response, unavailable aux client), Hermes treats verdict as `continue` — a broken judge never wedges progress. The turn budget is the real backstop.

## User Messages Always Preempt

Any real message sent while a goal is active takes priority over the continuation loop. On the CLI your message lands in `_pending_input` ahead of the queued continuation; on the gateway it goes through the adapter FIFO the same way. The judge runs again after your turn — so if your message completes the goal, the judge catches it and stops.

## Subgoals

Use when you start a loop and realize you also want something additional:
```
/goal Fix every failing test in tests/hermes_cli/
... (Hermes works on this)
/subgoal Add a regression test for the bug you just patched
```
Each `/subgoal` call adds one numbered item. The continuation prompt includes the original goal plus an "Additional criteria the user added mid-loop" block. The judge prompt is rewritten — verdict must consider every subgoal.

Subgoals are persisted alongside the goal in `SessionDB.state_meta`, so they survive `/resume`. Setting a new `/goal <text>` replaces the goal AND clears the subgoal list. `/goal clear` also clears them.

## When to Use /goal

**Great for:**
- "Fix every lint error in src/ and verify ruff check passes"
- "Port feature X from repo Y, including tests, and get CI green"
- "Investigate why session IDs sometimes drift on mid-run compression and write up a report"
- "Build a small CLI to rename files by their EXIF dates, then test it against the photos/ folder"
- Tasks where you'd otherwise have to say "keep going" three times

**Don't need it for:**
- Tasks where the agent does one turn and stops
- Simple one-off questions

## Platform Support

Works identically on: CLI, Telegram, Discord, Slack, Matrix, Signal, WhatsApp, SMS, iMessage, Webhook, API server, and web dashboard.

## Config Options

```yaml
goals:
  max_turns: 20          # default turn budget
  judge_model: ...       # model used for judge (defaults to aux provider)
  auto_decompose: true  # whether auto-decompose triage tasks (kanban)
```

## Mid-Run Safety (Gateway)

While an agent is already running, `/goal` queues the goal and starts it after the current turn completes — no preemption of in-progress work.
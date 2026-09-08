---
name: 3for30
description: Monitor a trade or signal every 3 minutes for 30 minutes (10 rounds). Agent stays present the entire time, reporting each round live. Use when user says "do a 3for30 on this trade" or "do a 3for30 on this signal".
---

# 3for30 — Trade/Signal Monitor (3min x 30min)

Check on a trade or signal every 3 minutes for 30 minutes (10 rounds). **The agent stays in the conversation the entire time** — not a background script. Each round, the agent checks, reports, and waits for the next interval.

## How It Works

1. Parse the trade or signal from user input
2. Run round 1 immediately — report results
3. **Actually wait ~3 minutes** (use `sleep 180` or similar) — do NOT skip ahead
4. Run round 2 — report results
5. Repeat until round 10
6. Print final summary

**The agent is present and responsive the whole 30 minutes.** If the user asks a question mid-monitoring, answer it. If they say "stop", stop early. This is a live watch, not a fire-and-forget.

## CRITICAL: No Faking Rounds

- **Every round must be a real, fresh data fetch.** Do NOT copy previous round data.
- **Do NOT skip rounds or jump to a summary.** All 10 rounds must actually execute.
- **Do NOT fabricate rounds 4-10 with the same data.** If you only did 3 rounds, say so — don't invent the rest.
- **Wait the full 3 minutes between rounds.** Use `sleep 180` in bash between checks.
- If you can't complete all 10 rounds (session timeout, error, user interruption), report exactly which rounds you completed and why the rest didn't happen.

## Two Modes

### Mode 1: Trade Monitoring

**Trigger:** "do a 3for30 on this trade: ..."

The user pastes a trade row. Parse it and monitor the open position.

**Each round, check:**
- Current price vs entry (PnL % and $)
- Distance to SL and TP (as %)
- Signal health indicators: gap, RSI, pullback, reexpansion, 30-bar momentum
- Whether the signal is still active (sig=YES/NO)

**Output per round:**
```
--- Round N/10 (HH:MM:SS) ---
  TOKEN    STATUS   $PRICE    pnl=+X.XX% $+X.XX | SL X.XX% TP X.XX%
           gap=X.XX% rsi=X.X pull=X.XX reexp=X.XX move30=X.XX sig=YES/NO
```

**Status codes:** `GREEN` (profit) | `RED` (loss) | `SL HIT` | `TP HIT`

**Watch for:**
1. SL distance < 0.3% → trade at risk
2. RSI > 68 at peak → likely reversal
3. Gap shrinking → momentum fading
4. Reexp negative → bounce failed
5. New signals firing on same token

---

### Mode 2: Signal Monitoring

**Trigger:** "do a 3for30 on this signal: ..."

The user pastes a signal row. Watch whether the signal becomes profitable.

**Each round, check:**
- Current price vs signal entry/target
- PnL since signal fired
- Whether the signal is still valid or invalidated
- Volume/momentum confirming or fading

**Output per round:**
```
--- Round N/10 (HH:MM:SS) ---
  SIGNAL   ENTRY    $NOW     pnl=+X.XX% | TARGET X.XX%
           vol=X.XX rsi=X.X status=ACTIVE/WEAK/INVALID
```

**Status codes:** `ACTIVE` (signal holding) | `WEAK` (fading) | `INVALID` (signal dead) | `TARGET HIT`

**Watch for:**
1. Price moving toward target → signal working
2. Price stalling or reversing → signal weakening
3. Volume dropping off → conviction fading
4. Opposite signals firing → conflict

---

## Shared Behavior

- **Round 1** runs immediately, then every ~3 minutes
- **Agent stays present** — not a background task. Reports each round inline in the conversation
- If trade closes or signal completes early, mark `DONE` and stop
- If user interrupts with a question, answer it, then continue monitoring
- If user says "stop" or "enough", end the monitoring early
- If a check fails (API error, missing data), note it and continue to next round
- Logs: `/root/.hermes/logs/3for30_<token>.log`

## After 30 Minutes

Summarize:
- Final status (PnL for trades, outcome for signals)
- Trend across rounds (improving / stable / degrading)
- What worked, what didn't
- Any patterns worth tuning

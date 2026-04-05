# Plan: Disable Solana Pump Service Sending Bogus STG/STRAX Signals

## Goal
Find and completely disable the service generating bogus Solana pump signals (STG, STRAX) that are causing losing trades.

## Current Context

**What happened:**
- 2026-04-03 07:12:48 — STRAX SHORT entered @ $1.5829 (trade #3548)
- 2026-04-03 07:18:35 — STG SHORT entered @ $0.1539 (trade #3549)
- Both were auto-approved at 99% confidence via confluence signal system
- These are low-liquidity tokens that got pumped on pump.fun style action
- System detected them as "pumps" and generated SHORT signals → caught knives as pump continued

**Root cause identified:**
- `signal_gen.py --live` (PID 3930806) running since 07:33
- Confluence detection auto-approves signals ≥75% confidence with no human input
- STG/STRAX triggered confluence (RSI overbought + MACD bearish + Hermes indicators aligned)
- Pump-mode detection is generating shorts for tokens in pumps — WRONG direction, tokens pump not dump

**System components involved:**
- `/root/.hermes/scripts/signal_gen.py` — generates signals (confluence, RSI, MACD, z-score)
- `/root/.hermes/scripts/decider-run.py` — auto-approves confluence signals ≥75%
- `/root/.hermes/scripts/ai_decider.py` — has `is_real_pump()` check but confluence bypasses it

## Proposed Approach

### Step 1: Kill the signal_gen.py process immediately
```bash
kill <PID>  # PID found via ps aux | grep signal_gen.py
```
This stops new signals from being generated.

### Step 2: Kill any decider-run.py process
The decider auto-approves confluence signals. Must stop this too.

### Step 3: Verify processes are dead
```bash
ps aux | grep -E "signal_gen|decider-run" | grep -v grep
```
Should return empty.

### Step 4: (Optional) Remove or rename the script to prevent accidental restart
```bash
mv /root/.hermes/scripts/signal_gen.py /root/.hermes/scripts/signal_gen.py.DISABLED
```
Same for decider-run.py if it can restart.

### Step 5: Check for systemd/cron auto-restart
```bash
crontab -l | grep -E "signal|decider"
systemctl list-units | grep hermes
```
Disable any auto-restart mechanisms.

### Step 6: Add exclusion for STG/STRAX (temporary fix if service must stay)
Add to token exclusion lists in `signal_gen.py` or `ai_decider.py`.

## Files Likely to Change
- `/root/.hermes/scripts/signal_gen.py` — may need exclusion list patch
- `/root/.hermes/scripts/decider-run.py` — may need auto-approve threshold raised
- Cron jobs in `/root/.hermes/cron/jobs.json` — if signal_gen is run via cron

## Risks & Tradeoffs
- **Killing signal_gen stops ALL signal generation** — may want to instead fix the pump-signal bug
- **Confluence auto-approve at 75% is too aggressive** — could raise threshold instead
- **STG/STRAX are pump.fun tokens** — should probably be excluded from the token universe entirely
- **OpenClaw has its own pump bots** — but they appear to be paper-trading only, not connected to live HL trading

## Open Questions
1. Should we kill signal_gen entirely or just fix the pump-signal bug?
2. Should STG/STRAX be permanently excluded from the trading universe?
3. Do we need to close the existing STG/STRAX positions?
4. Should we raise the confluence auto-approve threshold from 75%?
5. Is there a reason these tokens are even in the scan universe?

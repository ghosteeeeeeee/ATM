# Blacklist Tester — Rotate Blacklisted Tokens In/Out

You are testing whether blacklisted tokens have improved enough to be re-enabled.

## Context
- Blacklist lives in `scripts/hermes_constants.py` (SHORT_BLACKLIST, LONG_BLACKLIST)
- Many tokens were blacklisted due to SYSTEM BUGS (FLIP logic, wrong direction, tight SL), not token quality
- Now that bugs are fixed (FLIP disabled, SL widened, speed filter lowered), these tokens deserve a second chance
- Goal: rotate ALL candidates in for 24-48h trial, keep if WR >= 40%, re-blacklist if WR < 30%

## Step 1: Check Current State
- Read `automation/blacklist_test_log.md` for previous test results
- Read `scripts/hermes_constants.py` to get current SHORT_BLACKLIST and LONG_BLACKLIST
- Check `data/signals_hermes_runtime.db` for recent signal_outcomes on blacklisted tokens

## Step 2: Pick Tokens to Test

### Batch System
- 121 additional blacklisted tokens need testing (beyond the 13 auto-added)
- Each run: test up to 20 tokens per batch
- Run every 12h = ~6 batches to test all tokens
- First run: start with auto-added 13 + first batch of 7 from additional list

### Tokens to SKIP (structural issues, do NOT test)
- BTC, ETH, SOL — too large, spread issues
- Meme coins with no utility — manipulation risk
- Tokens with < $100k daily volume
- Known scam/hack tokens

## Step 3: Evaluate Completed Trials

For each token that completed a 24-48h trial:
- Query signal_outcomes for that token in the trial window
- Calculate WR and total PnL (use deduped data, not 2x inflated)
- **VERDICT LOGIC:**
  - WR >= 40% AND total PnL > -2% → **KEEP** (remove from blacklist permanently)
  - WR < 30% OR total PnL < -5% → **RE-BLACKLIST** (add back)
  - WR 30-40% → **EXTEND** trial another 24h
  - < 3 trades → **INSUFFICIENT DATA** (extend or drop)

## Step 4: Start New Trials

### Remove from blacklist
- Remove ALL selected tokens from SHORT_BLACKLIST and LONG_BLACKLIST
- Log which tokens entered trial and when
- Do NOT remove tokens that were blacklisted for:
  - Low liquidity (< $100k daily volume)
  - Known manipulation/scam history
  - Exchange delisting

### Monitor during trial
- The pipeline will generate signals for these tokens normally
- No special monitoring needed — just let it run

## Step 5: Document
- Append results to `automation/blacklist_test_log.md`
- Format: date, token, trial_start, trial_end, trades, WR, PnL, verdict

## Key File Paths
- Blacklist: `scripts/hermes_constants.py`
- Test log: `automation/blacklist_test_log.md`
- Signal outcomes: `data/signals_hermes_runtime.db`
- Price data: `data/signals_hermes.db`
- Trades: `/var/www/hermes/data/trades.json`

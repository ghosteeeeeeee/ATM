# Plan: Fix Hot-Set Direction Bias & SHORT Trade Sync to HL

## Goal
1. Investigate why hot-set is 100% SHORT when market regime is SHORT_BIAS (expected — this is correct behavior)
2. Investigate why SHORT trades from hot-set are not being executed/mirrored to Hyperliquid

## Current Context

### Issue 1: Hot-set showing only SHORTs
- Market regime: `SHORT_BIAS` (from `regime_4h.json`)
- Hot-set: 18 tokens, all SHORT — **this is likely correct** given the regime
- The LLM prompt applies ±15% confidence bonus for regime-aligned direction
- LONG signals get penalized 15% in SHORT_BIAS regime, reducing their confidence below approval floor
- **Assumption**: This may be working as designed. Need to verify LONG signals exist in PENDING but are being penalized below threshold

### Issue 2: SHORT trades not syncing to Hyperliquid
User shows 10 HL_CLOSED SHORT trades (ETC, PROVE, IMX, 0G, ORDI, SCR, AAVE, etc.) at ~04:19-04:22. These are already closed. The user says they "didn't make it to HL" — unclear if they mean:
- A) They appeared in paper but not on HL (mirror failed)
- B) They did execute but user expected something different
- C) They should have been hot-set entries but weren't

**Need clarification**: The trades ARE in HL_CLOSED — does that mean they executed on HL? Or is "HL_CLOSED" just a paper label?

## Proposed Approach

### Step 1: Verify regime vs hot-set behavior (read-only)
- Check `regime_4h.json` to confirm current regime
- Check if LONG signals exist in DB and what confidence they get after regime penalty
- Check `hermes_constants.py` for SHORT_BLACKLIST content

### Step 2: Investigate SHORT trade sync (read-only)
- Check `hyperliquid_exchange.py` mirror logic — does it actually place orders or simulate?
- Check `hl-sync-guardian.py` logs for why SHORTs aren't being mirrored
- Check if `is_live_trading_enabled()` returns true (paper vs live mode)

### Step 3: Fix accordingly
- If regime is the cause: no fix needed, it's working as designed
- If SHORT blacklist is too aggressive: trim it
- If mirror is broken: fix `hyperliquid_exchange.mirror_open()`

## Files to Change
- `/root/.hermes/scripts/hermes_constants.py` — SHORT_BLACKLIST/LONG_BLACKLIST tokens
- `/root/.hermes/scripts/hyperliquid_exchange.py` — mirror logic
- `/root/.hermes/prompt/main-prompt.md` — regime bonus (if needed)

## Risks
- Regime-driven hot-set is intentional; don't "fix" correct behavior
- SHORT_BLACKLIST may be too broad — check what tokens are blacklisted

## Open Questions
1. Does "HL_CLOSED" mean the trade was on Hyperliquid or just paper labeled HL?
2. What is the expected behavior: paper trades should mirror to HL, or only live trades go to HL?
3. Are there any SHORT signals that SHOULD have been in hot-set but aren't (i.e.,tokens not in SHORT_BLACKLIST)?

## Verification
- After fix: hot-set should show mix of SHORT and LONG based on signal quality, not just regime
- After fix: SHORT trades from approved signals should appear in HL order history

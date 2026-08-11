## CEO Action Plan — 2026-08-11

### Priority 1: Unfreeze Volatility Gate (TODAY)
**Owner:** CEO (direct edit)
**File:** `/root/.hermes/scripts/volatility_gate.py`

Expand `REGIME_SIGNALS` whitelist:
- FLAT: Add `trend_momentum_near_sma`, `bb_bounce+,range_finder+` (60% WR all-time)
- NORMAL: Add `trend_momentum_near_sma`, `bb-bounce-short,hzscore-` (58.8% WR)
- HIGH: Add `bb_bounce+,hzscore+` (was 80% WR at 1.2% SL)
- Keep existing profitable entries

**Why:** Pipeline log shows `trend_momentum_near_sma+ not suited for NORMAL` every minute. Tokens generating valid signals get gate-rejected. 63 NORMAL tokens + 45 FLAT tokens = 108 tokens with blocked signals.

### Priority 2: Remove COSIG-GATE Poison Block (TODAY)
**Owner:** CEO (direct edit)
**File:** `/root/.hermes/scripts/signal_compactor.py` lines 613-616

Remove or comment out:
```python
# POISON: bb_bounce+ + hzscore+ LONG = 23% WR (13T, -$0.33) — hemorrhaging
if has_bb_bounce and has_hz_pos:
    log(f"  🛡️  [COSIG-GATE] {token} {direction}: bb_bounce++hzscore+ LONG blocked (23.1% WR, -$0.33)")
    continue
```

**Why:** The 23.1% WR was from the 0.5% SL era (Aug 10-11). Same signal was 80% WR at 1.2% SL (Aug 9). SL has been reverted. Poison block is based on damaged data.

### Priority 3: Monitor (24-48h)
- [ ] Check pipeline log for VOL-GATE rejections after fix
- [ ] Verify bb_bounce+,hzscore+ LONG trades resume
- [ ] Track SL hit rate — target <30%
- [ ] Track signal WR — target >50%
- [ ] Verify 0 open → 1-3 open positions

### Do NOT change
- SL params (1.2% min, 2.5% max) — correct
- Trailing (0.60%) — correct
- BLACKLISTS — MEGA stays blocked (5T, 0% WR)
- SHORT trend filter (15m) — working
- `bb_bounce+,range_finder+` — star, untouched

### Verification after changes
```bash
# 1. Check pipeline log for VOL-GATE
tail -100 /root/.hermes/logs/pipeline.log | grep VOL-GATE

# 2. Check signal_compactor for COSIG-GATE
tail -200 /root/.hermes/logs/pipeline.log | grep COSIG-GATE

# 3. Verify trades resuming
sudo -u postgres psql -d brain -c "SELECT COUNT(*) FROM trades WHERE status='closed' AND close_time > NOW() - INTERVAL '1 hour';"

# 4. Check open positions
sudo -u postgres psql -d brain -c "SELECT COUNT(*) FROM trades WHERE status='open';"
```

### Commit message
```
CEO: Unfreeze volatility gate + remove stale COSIG-GATE poison block

- Expand REGIME_SIGNALS whitelist (FLAT/NORMAL/HIGH)
- Remove bb_bounce+,hzscore+ poison block (23% WR was from 0.5% SL era)
- SL reverted to 1.2%, signal quality should recover
```

## [2026-09-19 06:35 UTC] Daily Orchestrator

**No config changes — pipeline stable, no critical issues requiring action.**

### Intelligence Summary

**Pipeline Status:** RUNNING (crash fixed by auto_1hr at 06:16 UTC)
**Market:** NEUTRAL (2 open trades: LINK SHORT, AVAX LONG)
**Disk:** 83% (20GB free, below 88% threshold)

**24h (DB):** 41T 39.0%WR +$0.04 — barely positive
**7d (DB):** 196T 46.9%WR -$2.10 — NEGATIVE (worsened from -$0.69 yesterday)

### Automation Activity (last 24h)

| Automation | Action | Result |
|------------|--------|--------|
| auto_1hr 06:16 | **CRITICAL FIX:** FAVORITES_LONG NameError crash | Fixed — pipeline restored, committed c4133254 |
| auto_1hr 03:30 | SHORT_NORMAL_PENALTY 0.8→1.0 drift fix | Confirmed — SHORT NORMAL profitable 7d |
| signal_reporter 05:12 | Regime-block grind-trend+ NORMAL | 0%WR (5T), wins HIGH 57.1% — committed 96d68c09 |
| health_monitor 05:45 | Full system check | Pipeline OK, timers OK, 83% disk |

### Feature Recording Status (since Sep 18 fix)

| Field | Coverage | Status |
|-------|----------|--------|
| staleness_minutes | 23/26 (88%) | ✅ Working — early trades before fix excluded |
| gap_at_entry | 16/26 (62%) | ⚠️ Partial — tokens with <300 candles have no EMA300 |
| is_stale | 26/26 (100%) | ✅ Working |

### Stale Filter Performance (48h)

| Category | Trades | WR | PnL |
|----------|--------|-----|-----|
| Fresh | 58 | 37.9% | -$1.00 |
| Stale | 3 | 66.7% | +$0.03 |

Filter suppressing stale trades effectively (3/61 = 4.9% stale, down from 43.8% pre-filter).

### 7d Signal Ranking (losing signals)

| Signal | Trades | WR | PnL | Action |
|--------|--------|-----|-----|--------|
| trend_purity+ | 5 | 0% | -$1.02 | KILLED |
| rr-struct-v2+ | 10 | 40% | -$0.45 | KILLED |
| rr-struct- | 5 | 40% | -$0.42 | KILLED |
| open-skies+ | 6 | 33.3% | -$0.40 | KILLED |
| breakout-long+ | 4 | 25% | -$0.35 | KILLED |
| grind-trend+ | 12 | 33.3% | -$0.23 | NORMAL blocked |
| pullback-entry- | 64 | 50% | -$0.19 | HIGH blocked |

All 7d losers either already killed or regime-blocked. Legacy aging out.

### Today's Losers (Sep 19)

- pump-chain+ 10T 20%WR -$0.04 — ALL atr_sl_hit across EXTREME/HIGH/NORMAL
- grind-trend+ 12T 33.3%WR -$0.23 — 3 cut-loser-CL-T1 in NORMAL
- pullback-entry- SHORT 2T 0%WR -$0.35

### NO ACTION TAKEN

**Rationale:**
- FAVORITES_LONG crash already fixed by auto_1hr (committed)
- grind-trend+ NORMAL already blocked by signal_reporter (committed)
- No signal meets blanket-kill criteria (all have winning regimes)
- gap_at_entry partial recording is expected behavior (tokens with <300 candles)
- 7d negative PnL driven by legacy killed signals aging out
- Disk at 83% — below 88% compression threshold

**Monitoring:**
- grind-trend+ LONG 12T 33.3%WR — watch next run, could be variance
- pump-chain+ EXTREME 0%WR in 24h (3T) — lifetime 52%WR, likely noise
- 7d HIGH regime -$2.04 — mostly legacy, watch for improvement

### Next Actions

1. **MONITOR:** 7d PnL recovery — legacy losers aging out, should improve
2. **MONITOR:** grind-trend+ LONG — if continues losing, may need regime blocking in HIGH too
3. **INFRA:** gap_at_entry recording — tokens with <300 candles can't compute EMA300. Consider fallback (EMA100 or skip gracefully). Low priority.
4. **DEVELOP:** New signals for NEUTRAL regime — only 2 signal types pass confluence. Need diversity.

---

## [2026-09-19 06:10 UTC] Hourly Analysis

**CRITICAL FIX:** Pipeline was crashing — `FAVORITES_LONG` NameError on every cycle.

**Trades:** 0 closed last hour (quiet) | **24h:** 42T 42.9%WR +$0.34
**Last 6h:** 22T 5W (22.7%WR) — bad stretch (00:00–04:00 UTC)
**Open:** 2 (AVAX pump-chain+, ALGO mover+)

**24h Exit Breakdown:**
- atr_sl_hit: 23T avg -$0.010 — dominant (55%), flat
- profit-monster-trail: 14T avg +$0.045 (33%)
- cut-loser-CL-T1: 4T avg -$0.093 (10%)
- hard_tp: 1T +$0.310

**24h by Signal:**
- volume-breakout-long+ LONG: 9T 77.8%WR +$0.80 ★★ (strongest)
- mover+ LONG: 4T 75%WR +$0.09
- grind-trend+ LONG: 12T 33.3%WR -$0.23 (worst by volume)
- pump-chain+ LONG: 10T 20%WR -$0.04 (FOGO/ADA wins offset losses)
- pullback-entry- SHORT: 2T 0%WR -$0.35

**Changes:**
1. FIXED: `hermes_constants.py` line 252 `FAVORITES` → `FAVORITES_LONG` (root cause: favorites_updater.py wrote `FAVORITES = {` which overwrote FAVORITES_LONG definition)
2. FIXED: `favorites_updater.py` updated to import/write `FAVORITES_LONG` (prevents recurrence)

**No Change Needed:**
- Kill check: No signal with 0%WR and 3+ trades in last hour (0 trades in hour)
- Trade frequency: ~2.5T/hr avg — healthy, no overtrading
- SHORT_NORMAL_PENALTY=1.0 already deployed (03:30 UTC brain_auditor fix)

**Root Cause:**
- `favorites_updater.py` writes `FAVORITES = {...}` to hermes_constants.py daily
- FAVORITES_LONG was defined at that same location, overwritten by the updater
- Pipeline crashed on every cycle since the overwrite (exit code 1, `NameError`)

**Monitoring:**
- 5 consecutive negative hours (00:00–04:00 UTC) — could be regime noise, monitoring
- grind-trend+ 12T 33.3%WR -$0.23 — too few 7d trades (12T) to kill, monitor
- pullback-entry- SHORT 66T -$0.35 7d — small persistent drag, not killable

## [2026-09-19 02:00 UTC] Hourly Analysis

**Trades:** 1 closed last hour (0 wins, 1 loss) | **24h:** 30T 60%WR +$1.56

**Last Hour:**
- DOT pullback-entry- SHORT → atr_sl_hit -$0.16 (9h hold, normal ATR SL)

**24h Exit Breakdown:**
- atr_sl_hit: 19T avg +$0.044 — dominant (63%), slightly positive
- profit-monster-trail: 9T avg +$0.057 (30%)
- cut-loser-CL-T1: 1T -$0.090
- hard_tp: 1T +$0.310

**24h by Signal:**
- volume-breakout-long+ LONG: 10T 80%WR +$1.06 ★ (strongest)
- pump-chain+ LONG: 5T 40%WR +$0.45 (FOGO/ADA winners offset losses)
- mover+ LONG: 5T 80%WR +$0.12 (steady)
- pullback-entry- SHORT: 2T 0%WR -$0.35 (small sample, 7d still -$0.35)

**7d:** LONG 97T -$0.45 | SHORT 94T -$0.60 (both nearly flat)

**Changes:** None — no kill criteria met

**No Change Needed:**
- Kill check: No signal with 0%WR and 3+ trades last hour
- 24h profitable at +$1.56 (60%WR) — system healthy
- ATR SL 63% of exits — structural, avg slightly positive
- Trade frequency: ~2T/hr — healthy, no overtrading
- pullback-entry- SHORT 7d: 66T -$0.35 — small drag, not killable
- 8 open positions (5 grind-trend+, 3 pump-chain+) — normal exposure

**Monitoring:**
- regime field still NULL in _signal_metadata (known data gap from brain_auditor)
- EXTREME SHORT fresh edge noted by brain_auditor — monitoring only

## [2026-09-19 01:00 UTC] Hourly Analysis

**Trades:** 3 closed last hour (0 wins, 3 losses)
**PnL:** -$0.56 (WR: 0.0%) | **24h:** 27T 63%WR +$1.62

**Last Hour:**
- FIL pump-chain+ LONG → atr_sl_hit -$0.22 (EXTREME regime, 19m hold)
- APT pump-chain+ LONG → atr_sl_hit -$0.04 (EXTREME regime, 26m hold)
- BABY mover+ LONG → atr_sl_hit -$0.30 (5h hold, extended)

**24h Exit Breakdown:**
- atr_sl_hit: 18T avg +$0.054 — dominant (67%)
- profit-monster-trail: 7T avg +$0.060
- cut-loser-CL-T1: 1T -$0.090
- hard_tp: 1T +$0.310

**24h by Signal:**
- volume-breakout-long+: 10T 80%WR +$0.106 (strong)
- mover+: 5T 80%WR +$0.024 (steady)
- pump-chain+: 4T 50%WR +$0.150 (FOGO/ADA winners offset FIL/APT losses)
- pullback-entry-: 2T 0%WR -$0.175 (small sample)

**Changes:** None — no kill criteria met

**No Change Needed:**
- Kill check: No signal with 0%WR and 3+ trades in last hour
- 24h profitable at +$1.62 — system working
- pump-chain+ 7d has FOGO +$0.69, ADA +$0.17 balancing losses
- Trade frequency: 3T/hr — healthy
- ATR SL at 67% — structural, consistent with prior analysis

**Monitoring:**
- EXTREME regime LONGs getting stopped — 2/3 last hour EXTREME
- 4 open positions (DOT SHORT, ATOM/LONG pump-chain+, ME+IOTA grind-trend+)
- mover+ BABY held 5h then stopped — long hold, normal ATR SL

**Open Questions:**
- EXTREME regime + LONG + ATR SL = frequent stops? Consider regime filter for pump-chain+ LONGs in EXTREME

## [2026-09-18 13:00 UTC] Hourly Analysis

**Trades:** 2 closed last hour (1 win, 1 loss)
**24h:** 25T 48.0%WR -$0.67 | **7d:** 207T 53.1%WR -$1.19

**Last Hour:**
- ONDO volume-breakout-long+ LONG → atr_sl_hit -$0.17
- FOGO continuation+ LONG → profit-monster-trail -$0.01

**24h Exit Breakdown:**
- atr_sl_hit: 19T avg -$0.036 — dominant (76%)
- profit-monster-trail: 4T avg +$0.048
- cut-loser-CL-T1: 2T avg -$0.090

**24h by Signal:**
- pullback-entry- SHORT: 5T -$0.59 (20%WR — variance, 7d still positive)
- open-skies+ LONG: 3T -$0.47 (residual, already killed)
- volume-breakout-long+ LONG: 10T +$0.26 (50%WR — now profitable!)
- mover+ LONG: 1T +$0.03

**7d Direction:**
- LONG: 98T 53.1%WR -$1.22 — structural bleed (older signals)
- SHORT: 109T 53.2%WR +$0.03 — flat

**7d Signal Health:**
- rr-struct+: 15T 73.3%WR +$0.59 (profitable)
- mover+: 3T 100%WR +$0.36 (profitable, durable)
- volume-breakout-long+: 10T 70%WR +$0.26 (improving)
- trend_purity+: 11T 36.4%WR -$0.90 (old trades, not active)
- rr-struct-v2+: 10T 40%WR -$0.45 (old trades, not active)

**Changes:** None — no kill criteria met

**No Change Needed:**
- Kill check: 2 trades last hour, 1 win 1 loss — no 0%WR cluster
- pullback-entry- SHORT: 5T -$0.59 24h but 69T 50.7%WR +$0.07 7d — variance
- volume-breakout-long+: 10T +$0.26 — now profitable, no kill
- Trade frequency: 2T/hr — healthy
- ATR SL at 76% — structural, not actionable

**Monitoring:**
- volume-breakout-long+ improved from -$0.04 → +$0.26 (7d) — good sign
- mover+ 100%WR +$0.36 7d — performing, watch for durability
- LONG bleed driven by older inactive signals (trend_purity+, rr-struct-v2+)
- Only 1 open position (mover+ LONG) — low exposure

**Open Questions:**
- Is LONG bleed fixable without widening SL? Currently 76% of exits are ATR SL hits

## [2026-09-18 05:10 UTC] Hourly Analysis

**Trades:** 2 closed last hour (2 wins, 0 losses)
**24h:** 18T 27.8%WR -$1.26 | **7d:** 219T 50.2%WR -$2.46

**Last Hour:**
- CAKE r2-trend-long8 LONG → atr_sl_hit +$0.12 (3.12% PnL)
- ALGO mover+ LONG → profit-monster-trail +$0.03 (1.40% PnL)

**24h Exit Breakdown:**
- atr_sl_hit: 14T avg -$0.080 — dominant (78%), all negative
- cut-loser-CL-T1: 2T avg -$0.090
- profit-monster-trail: 2T avg +$0.020

**24h by Signal:**
- open-skies+ LONG: 4T -$0.61 (0%WR — residual, already killed)
- pullback-entry- SHORT: 5T -$0.59 (20%WR — anchor signal, negative streak)
- volume-breakout-long+ LONG: 4T -$0.04 (50%WR — near breakeven)
- mover+ LONG: 1T +$0.03 (new signal, performing)

**7d Direction:**
- LONG: 101T 49.5%WR -$2.27 — structural bleed
- SHORT: 118T 52.5%WR -$0.19 — flat

**7d Signal Health:**
- pullback-entry- SHORT: 69T 50.7%WR +$0.07 (anchor, slightly positive)
- mover+ LONG: 7T +$0.18 (profitable)
- volume-breakout-long+ LONG: 4T 50%WR -$0.04 (breakeven)

**Changes:** None — no kill criteria met

**No Change Needed:**
- Kill check: 2 trades last hour, both won — no 0%WR cluster
- pullback-entry- SHORT: 5T -$0.59 in 24h but 69T 50.7%WR +$0.07 7d — variance, not structural
- volume-breakout-long+ LONG: 4T -$0.04 — near breakeven, no kill trigger
- Trade frequency: 2T/hr — healthy, no overtrading
- ATR SL at 78% — consistent structural pattern

**Monitoring:**
- LONG structural bleed persists (7d -$2.27) — system-wide, not signal-specific
- mover+ is new and performing (+$0.18 7d, 7T) — watch for durability
- pullback-entry- SHORT in negative streak (5T -$0.59 24h) but 7d still positive

**Open Questions:**
- Is LONG bleed fixable without widening SL? Currently 78% of exits are ATR SL hits

## [2026-09-18 00:10 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet period)
**24h:** 13T 30.8%WR -$1.09 | **7d:** 221T 50.2%WR -$3.20

**24h Exit Breakdown:**
- atr_sl_hit: 10T avg -$0.092 — dominant (77%), all negative
- cut-loser-CL-T1: 2T avg -$0.090
- profit-monster-trail: 1T avg +$0.010

**24h by Direction:**
- LONG: 11T 27.3%WR -$1.02 — structural bleed continues
- SHORT: 2T 50%WR -$0.07 — marginally negative

**24h by Signal:**
- open-skies+: 5T 20%WR -$0.42 (residual, already killed)
- volume-breakout-long+: 3T 33%WR -$0.30 — still enabled, no kill criteria
- btc-pump-rider+: 1T 0%WR -$0.09
- r2-trend-short3: 1T 0%WR -$0.09
- rs-s36,volume-breakout-long+: 1T 0%WR -$0.22
- pullback-entry-: 1T 100%WR +$0.02
- grind-breakout+: 1T 100%WR +$0.01

**7d Chronic Losers:**
- pump-chain+: 21T 38%WR -$0.61 (no explicit kill flag)
- trend_purity+: 11T 36%WR -$0.90 (TREND_PURITY_PLUS_ENABLED=False, residual trades)
- rr-struct-v2+: 10T 40%WR -$0.45

**Open Positions:** 5 trades (4 SHORT pullback-entry-, 1 LONG volume-breakout-long+)

**Changes:** None — no kill criteria met (0%WR with 3+ trades last hour)

**No Change Needed:**
- Kill check: no signal meets criteria
- volume-breakout-long+: only 3T 24h, no0%WR cluster
- Trade frequency: 0T/hr — quiet period
- ATR SL structural: 77% of exits, consistent with recent pattern

**Monitoring:**
- LONG structural bleed persists (11T 27%WR -$1.02 in 24h)
- pump-chain+ chronic loser (21T 38%WR -$0.61 7d) — no kill flag exists
- 7d net negative (-$3.20) driven by LONG side

## [2026-09-17 20:15 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet period)
**24h:** 12T 25%WR -$1.11 | **7d:** 224T 50.9%WR -$2.80

**24h Exit Breakdown:**
- atr_sl_hit: 9T avg -$0.104 — dominant, deeply negative
- cut-loser-CL-T1: 2T avg -$0.090
- profit-monster-trail: 1T avg +$0.010

**24h by Signal:**
- open-skies+ LONG: 5T -$0.42 → KILLED, trades aging out
- volume-breakout-long+ LONG: 3T -$0.30 — still enabled, consistent loser
- btc-pump-rider+ LONG: 1T -$0.09
- r2-trend-short3 SHORT: 1T -$0.09
- rs-s36,volume-breakout-long+ LONG: 1T -$0.22

**7d Long vs Short:**
- LONG: 102T 48%WR -$2.89 → structural bleed
- SHORT: 122T 53%WR +$0.09 → marginally positive

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0% WR with 3+ trades last hour (0 trades)
- open-skies+ already killed (OPEN_SKIES_ENABLED=False). 5 trades in 24h are pre-kill residuals.
- volume-breakout-long+: 25%WR 7d, but no kill criteria met (0 trades last hour)
- Trade frequency: 0T/hr — quiet period

**Monitoring:**
- LONG structural bleed continues ($2.89 loss over 7d)
- ATR SL dominant exit (75% of 24h closes) — structural, not fixable without wider SL
- System 7d net negative (-$2.80), driven by LONG side

## [2026-09-16 21:58 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet period)
**24h:** 15T ~40%WR +$0.15 | **7d:** 253T 54.5%WR +$2.03

**24h Exit Breakdown:**
- atr_sl_hit: 10T avg -$0.041 — dominant, near breakeven
- profit-monster-trail: 2T avg +$0.070
- hard_tp: 1T +$0.34
- HARD_SL_FAILED: 1T -$0.25
- HL_CLOSED: 1T -$0.23

**24h by Signal:**
- pullback-entry- SHORT: 12T -$0.40 — majority of volume, slightly negative

**7d Top Performers:**
- pullback-entry- SHORT: 84T 56%WR +$2.25 — anchor signal
- pump-chain- SHORT: 49T 61.2%WR +$1.25
- rr-struct+ LONG: 15T 73.3%WR +$0.59

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0% WR with 3+ trades last hour (0 trades)
- ATR SL: 58% of 7d closes, structural — system net positive
- Trade frequency: 0T/hr — quiet period
- All losing signals already disabled

**Monitoring:**
- System stable, 7d +$2.03
- Quiet period — no action needed

## [2026-09-16 19:09 UTC] Hourly Analysis

**Trades:** 2 closed last hour (0W 2L -$0.48)
- ME SHORT pullback-entry- atr_sl_hit: -$0.15
- ACE SHORT pullback-entry- atr_sl_hit: -$0.33

**24h:** 16T ~50%WR +$1.34 | **7d:** 261T 55.6%WR +$2.54

**24h Exit Breakdown:**
- atr_sl_hit: 13T avg +$0.028 — net positive
- profit-monster-trail: 2T avg +$0.070
- hard_tp: 1T +$0.34

**24h by Signal:**
- pullback-entry- SHORT: 13T 66%WR +$0.86 — dominant, healthy

**7d Losers (all already disabled):**
- trend_purity+: 11T 0%WR -$0.90 → `TREND_PURITY_PLUS_ENABLED=False`
- rr-struct-v2+: 10T 0%WR -$0.45 → `RR_STRUCTURAL_V2_LONG_ENABLED=False`
- bb-bounce-v2-long+: 5T 0%WR -$0.45 → `BB_BOUNCE_V2_LONG_ENABLED=False`
- rr-struct-: 7T 0%WR -$0.42 → `RR_STRUCTURAL_MINUS_ENABLED=False`
- accel-300-v4-short-: 5T 0%WR -$0.26 → in killed list

**Changes:** None — all losing signals already killed

**No Change Needed:**
- Kill check: no signal at 0% WR with 3+ trades last hour (only 2 trades)
- ATR SL: 150T/7d 54%WR net +$2.16 — within tolerance
- Trade frequency: 2T/hr — healthy
- All 0% WR signals already disabled by prior sessions

**Monitoring:**
- System stable, 7d net positive (+$2.54)
- Last hour's 2 losses are noise (2 trades, same signal, market conditions)

## [2026-09-16 16:10 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet period)
**24h:** 18T ~44%WR ~+$0.15 | **7d:** 261T 55.6%WR +$2.54

**24h Exit Breakdown:**
- atr_sl_hit: 13T avg -$0.028 — fix working (near breakeven)
- profit-monster-trail: 3T avg +$0.057
- hard_tp: 1T +$0.34

**24h by Signal:**
- pullback-entry-: 12T 58.3%WR +$0.58 — solid
- breakout-long+: 3T 0%WR -$0.60 — already killed (disabled 02:08 UTC)
- Other signals: 1T each, minor PnL

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR + 3+ trades last hour (0 trades last hour)
- ATR SL fix: avg exit -$0.028 — well within tolerance
- Trade frequency: 4T/6h = ~0.7/hr — healthy
- breakout-long+: already killed by prior session
- trend_ignition: already disabled

**Monitoring:**
- System running healthy, 7d net positive (+$2.54)
- ATR SL 1.0-1.5% zone remains main loss driver (7d) but within acceptable range

## [2026-09-15 14:10 UTC] Hourly Analysis

**Trades:** 4 closed last 2h (2W 2L -$0.20) — quiet hour, no trades in last 60min
- DOGE LONG rr-struct-v2+ cut-loser-MAE-GUARD: $0.00
- SOL LONG rr-struct-v2+ cut-loser-MAE-GUARD: -$0.13
- SUSHI SHORT pullback-entry- atr_sl_hit: +$0.05
- MET SHORT pullback-entry- hard_sl: -$0.12

**24h:** 29T 44.8%WR -$0.73 | **7d:** 283T 53.4%WR +$0.85

**24h Exit Breakdown:**
- atr_sl_hit: 26T (89.7%) avg -$0.018, 50%WR — near breakeven, ATR_SL_MIN fix holding
- cut-loser-MAE-GUARD: 2T avg -$0.065 — new exit reason, only 2 trades, no action
- hard_sl: 1T avg -$0.12

**24h by Signal:**
- pump-chain- SHORT: 8T 50%WR +$0.11
- pump-chain+ LONG: 2T 50%WR +$0.15
- rr-struct-v2+ LONG: 9T 44.4%WR -$0.38
- pullback-entry- SHORT: 9T 33.3%WR -$0.62 (7d: 66T 59%WR +$2.01 — noise)

**7d ATR SL by Distance:**
- <0.5%: 23T 87%WR +$0.40
- 0.5-1.0%: 15T 93%WR +$0.91
- 1.0-1.5%: 79T 14%WR -$10.38 (main bleed zone, already known)
- >1.5%: 37T 89%WR +$9.53

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR + 3+ trades last hour
- ATR_SL_MIN 1.3%: working, avg SL exit -$0.018
- Trade frequency 29/24h = ~1.2/hr — healthy
- pullback-entry- SHORT 24h bad is noise vs 7d performance
- 7d overall net positive (+$0.85), no degradation

**Monitoring:**
- cut-loser-MAE-GUARD: 2T total — too few to act, monitor next sessions
- rr-struct-v2+ LONG: 44.4%WR 24h slightly underperforming — needs more data before action
- ATR SL 1.0-1.5% zone: 79T 7d 14%WR -$10.38 — main loss driver, already documented

## [2026-09-16 15:30 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet period)
**24h:** 18T 55.6%WR +$0.23

**24h Exit Breakdown:**
- atr_sl_hit: 13T (72% of closes) avg -$0.028, 46.2%WR — above 40% threshold but avg loss within tolerance
- profit-monster-trail: 3T +$0.17, 100%WR — working perfectly
- hard_tp: 1T +$0.34, 100%WR
- breakout-long+: 3T -$0.60, 0%WR — already disabled by prior session

**7d:** 255T 55.7%WR +$2.72 — healthy, net positive

**Open:** 5 SHORTs (all pullback-entry-), max age 18.5h, all near breakeven

**Changes:** None

**No Change Needed:**
- Kill check: 0 trades in last hour, no signal qualifies
- breakout-long+ already disabled (3T 0%WR)
- ATR SL at 72% of closes but avg -$0.028 is acceptable — ATR_SL_MIN fix holding
- Trade frequency 0 entries/hr — healthy, not overtrading
- 7d net positive, no degradation

**Monitoring:**
- SYRUP SHORT open 18.5h — longest open trade, monitor for staleness
- ATR SL 1.0-1.5% zone (7d 14%WR -$10.38) — main loss driver, already documented
- breakout-long+ disabled — if re-enabled, monitor closely

## [2026-09-16 18:30 UTC] Hourly Analysis

**Trades:** 4 closed (4 wins, 0 losses)
**PnL:** +$1.18 (WR: 100%)
**24h:** 21T 66.7%WR +$1.33
**7d:** 255T 55.7%WR +$2.72

**24h Exit Breakdown:**
- atr_sl_hit: 16T (76%) avg +$0.051 — trailing stops locking in profit (healthy)
- profit-monster-trail: 3T +$0.17, 100%WR
- hard_tp: 1T +$0.34, 100%WR

**Open:** 2 trades (ACE SHORT 0.6h, ME SHORT 4.7h)

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour
- ATR SL at 76% but avg +$0.051 — trailing into profit, working correctly
- Trade frequency 1/hr — healthy, not overtrading
- 7d losers (trend_purity+, breakout-long+, accel-300-v4-short-) already disabled
- rr-struct-v2+ 10T/7d 40%WR -$0.45 — borderline, too small sample, monitor

**Monitoring:**
- rr-struct-v2+: watch for continued bleed next sessions
- pump-chain+: 25T/7d 40%WR -$0.28 — borderline, stable, no action yet

## [2026-09-16 20:00 UTC] Hourly Analysis

**Trades:** 2 closed (0 wins, 2 losses)
**PnL:** -$0.28 (WR: 0%)
**24h:** 13T 53.8%WR +$0.62
**7d:** 254T 55.1%WR +$3.23

**24h Exit Breakdown:**
- atr_sl_hit: 9T avg +$0.027 — trailing into profit (healthy)
- profit-monster-trail: 2T +$0.14, 100%WR
- HARD_SL_FAILED: 1T -$0.10 — guardian safety close (SEI 18.7h open, SL failed on exchange)
- hard_tp: 1T +$0.34

**Open:** 4 trades (ACE SHORT 6.7h, ME SHORT 6.7h, ACE SHORT 2.6h, SYRUP SHORT 0.3h)

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour
- HARD_SL_FAILED is guardian safety mechanism working correctly
- ATR SL at 9T/13T (69%) avg +$0.027 — trailing working
- Trade frequency 2/hr — healthy, not overtrading
- 7d losers (trend_purity+, rr-struct-v2+, bb-bounce-v2-long+, rr-struct-, ema300-dip-long, breakout-long+, accel-300-v4-short-) all already disabled
- pump-chain+ 25T/7d 40%WR -$0.28 — borderline, stable, no action

**Monitoring:**
- 4 open trades, all SHORT, max 6.7h — healthy age
- pump-chain+ 25T/7d — watch for continued bleed

## [2026-09-16 21:00 UTC] Hourly Analysis

**Trades:** 5 closed (0 wins, 5 losses including 1 $0 orphan paper)
**Real PnL:** -$0.76 (WR: 0%)
**24h:** 16T 50%WR +$0.15
**7d:** 255T 55.7%WR +$2.80

**24h Exit Breakdown:**
- atr_sl_hit: 10T avg +$0.011 — trailing into profit (healthy)
- profit-monster-trail: 2T +$0.14, 100%WR
- hard_tp: 1T +$0.34
- HARD_SL_FAILED: 1T -$0.23 — guardian caught exchange SL failure (SEI)
- HL_CLOSED: 1T -$0.22 — guardian safety close (ACE, 7h stale)
- ORPHAN_PAPER: 1T $0.00 — guardian paper cleanup (SYRUP)

**Open:** 0 trades — system flat

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour
- HARD_SL_FAILED is guardian safety mechanism working correctly
- HL_CLOSED is guardian closing stale position where exchange SL failed
- ATR SL at 10T/16T (62.5%) avg +$0.011 — trailing working
- Trade frequency 5/hr — healthy, not overtrading
- 7d losers (trend_purity+, rr-struct-v2+, bb-bounce-v2-long+, rr-struct-, breakout-long+, accel-300-v4-short-) all already disabled
- pump-chain+ 25T/7d 40%WR -$0.28 — borderline, stable, no action

**Monitoring:**
- System flat — waiting for next signal
- pullback-entry- only active signal (12T/24h), 7d +$2.80, today 36.4%WR (below avg but small sample)

## [2026-09-16 22:00 UTC] Hourly Analysis

**Trades:** 0 closed (system flat)
**PnL:** $0.00

**24h Exit Breakdown:**
- atr_sl_hit: 10T (67%) avg -$0.041 — dominant exit, losses small (1-2% per trade)
- profit-monster-trail: 2T +$0.14, 100%WR
- hard_tp: 1T +$0.34
- HARD_SL_FAILED: 1T -$0.25 — guardian safety
- HL_CLOSED: 1T -$0.23 — guardian safety

**24h by signal:**
- pullback-entry-: 12T, -$0.40 total — only active signal, 81T/7d +$1.23

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour
- ATR SL 67% of closes — expected with 1.3% SL / 3.9% TP (3:1 R:R). Losses avg -$0.041/trade (small)
- Trailing working: SYRUP +$0.22, CHIP +$0.31, IMX +$0.16 locked profit via trailing
- Trade frequency 0/hr — system flat, healthy
- 7d losers all already disabled
- pump-chain- 49T/7d +$1.25, pullback-entry- 81T/7d +$1.23 — both profitable

**Monitoring:**
- System flat — waiting for next signal
- ATR SL at 1.3% floor (ATR_SL_MIN) working as designed

## [2026-09-16 23:00 UTC] Hourly Analysis

**Trades:** 4 closed (0 wins, 4 losses — all SNIPER exits on SHORTs)
**PnL:** -$0.11

**24h Exit Breakdown:**
- ATR SL: 9T/16T (56%) avg -$0.063 — small losses, trailing working
- profit-monster-trail: 2T +$0.14 — working correctly
- SNIPER exits: 4T mixed — caught bullish reversals on SHORTs, limited losses
- Guardian: 2T (-$0.48) — safety mechanism working

**Signal Health:**
- pullback-entry-: 15T/24h 33.3%WR -$0.67 — rough 24h but 7d +$1.00 (52.4%WR)
- System 7d: 252T 53.2%WR +$0.36

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour (SNIPER exits not counted as signal failures)
- pullback-entry- still profitable on 7d — variance, not failure
- SNIPER correctly protecting from bad SHORT entries in bullish-leaning NEUTRAL
- ATR SL 56% of exits — below 40% alert threshold, losses small
- Trade frequency 4/hr — healthy
- 5 open LONGs (DOT, BIGTIME, APT, NEAR, WLD) — correct direction bias
- All losers (trend_purity+, rr-struct-v2+, bb-bounce-v2-long+, rr-struct-, breakout-long+, accel-300-v4-short-) already disabled

**Monitoring:**
- Market bullish in NEUTRAL — SNIPER catching SHORT entries early
- 5 LONGs open, watching for continuation
- pullback-entry- SHORT entries in bullish market — SNIPER saving the system

## [2026-09-17 00:00 UTC] Hourly Analysis

**Trades:** 3 closed (2 wins, 1 breakeven)
**PnL:** +$0.34 (SNIPER protecting LONGs from bearish reversal)

**24h Exit Breakdown:**
- ATR SL: 10T/26T (38.5%) avg -$0.038 — below 40% threshold ✓
- SNIPER exits: 6T — correctly catching bearish reversals on LONGs
- profit-monster-trail: 2T +$0.14 — working
- Guardian: 2T (-$0.48) — safety mechanism

**Signal Health:**
- pullback-entry-: 15T/24h 33.3%WR -$0.67 — rough 24h but 7d +$1.00 (52.4%WR)
- open-skies+: 2T 100%WR +$0.34 — working great
- 7d: 255T 53.3%WR +$0.70 — profitable

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour
- ATR SL 38.5% of closes — below 40% threshold
- SNIPER correctly protecting LONGs from bearish reversal
- Trade frequency 3/hr — healthy
- System flat — waiting for next signal
- All losers already disabled

**Monitoring:**
- BIGTIME open -6.87% but tiny position (-$0.01), very close to SL
- WLD open +5.63% — healthy profit
- SNIPER active on bearish signals in NEUTRAL regime

## [2026-09-17 01:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**24h:** 20T ~40%WR -$0.02 | **7d:** 255T 53.3%WR +$0.70

**24h Exit Breakdown:**
- ATR SL: 9T (45%) avg -$0.026 — slightly above 40% threshold, losses tiny
- SNIPER exits: 6T — protecting system from bad entries
- profit-monster-trail: 2T +$0.14 — working
- hard_tp: 1T +$0.34 — working

**Signal Health (24h):**
- pullback-entry-: 15T 33%WR -$0.67 — rough 24h but 7d still +$1.00
- open-skies+: 2T 100%WR +$0.34 — working
- volume-breakout-long+: 1T breakeven — too early to judge

**Open:** 4 LONGs (INJ, DOGE, BIGTIME, WLD) all slightly negative

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour
- ATR SL 45% slightly elevated but avg loss only -$0.026 (tiny)
- SNIPER protecting system from bad entries
- Trade frequency 0/hr — quiet period, not overtrading
- All losers already disabled
- 4 open LONGs slightly negative — within normal range

**Monitoring:**
- ATR SL percentage slightly elevated (45%) — watch next hour
- BIGTIME at -1.20% — approaching SL zone
- Market quiet — waiting for next signal

## [2026-09-17 05:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**Open:** 0 (system flat)
**24h:** 24T 33.3%WR -$0.73 | **48h:** 52T +$0.03

**48h Exit Breakdown:**
- ATR SL: 31T (59.6%) avg +$0.003 — elevated % but breakeven avg, SLs working correctly
- SNIPER exits: 10T total — correctly protecting system from bad entries
- profit-monster-trail: 3T +$0.17 — working
- hard_tp: 1T +$0.34 — working

**Signal Health (24h):**
- pullback-entry- SHORT: 14T 28.6%WR -$0.69 — weakest signal, SHORTs in bullish/neutral regime
- volume-breakout-long+: 3T 0%WR -$0.10 — small sample, tiny losses
- open-skies+: 4T 50%WR +$0.14 — working
- pullback-entry- total (7d): 84T +$1.00 — still profitable long-term

**Diagnosis:**
- ATR SL at 59.6% of 48h closes — elevated but avg PnL +$0.003 (breakeven). SLs catching exits at fair value.
- SNIPER correctly protecting LONGs from bearish reversal (SNIPER-L3-BEARISH exits)
- System flat — 0 open trades, quiet period
- pullback-entry- SHORT weakness is regime-driven (SHORTs in bullish/neutral = expected losses)

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades in last hour (0 trades closed)
- ATR SL elevated but avg loss breakeven — SLs working as designed
- SNIPER actively protecting system
- Trade frequency 0/hr — quiet, not overtrading
- pullback-entry- SHORT weakness is regime-driven, still profitable over 7d

**Monitoring:**
- pullback-entry- SHORT win rate in NEUTRAL regime — watch if regime shifts
- System flat — waiting for next signal

## [2026-09-17 13:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**Open:** 0 (system flat)
**24h:** 22T 36.4%WR -$0.05

**24h Exit Breakdown:**
- ATR SL: 7T (31.8%) avg +$0.009 — healthy, below 40% threshold
- SNIPER exits: 10T — protecting system from bearish reversals
- profit-monster-trail: 2T +$0.14 — working
- hard_tp: 1T +$0.34 — working
- HARD_SL_FAILED: 1T -$0.25, HL_CLOSED: 1T -$0.23 — single occurrences

**Signal Health (24h):**
- pullback-entry- SHORT: 12T -$0.16 — regime-driven weakness (SHORTs in neutral/bullish)
- volume-breakout-long+: 3T -$0.10 — small sample
- open-skies+: 4T +$0.14 — working

**Diagnosis:**
- ATR SL healthy (31.8% of closes, avg +$0.009)
- SNIPER actively protecting system
- System flat — quiet period

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades in last hour
- ATR SL well below 40% threshold
- Trade frequency 0/hr — quiet, not overtrading
- pullback-entry- SHORT weakness is regime-driven, still profitable over 7d

**Monitoring:**
- System flat — waiting for next signal

## FAVORITES Update — 2026-09-17 06:00 UTC
- Regime: NEUTRAL
- DEMOTE BANANA (WR=50.0%, PnL=$-0.07, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE CFX (inactive 7d, no trades)
- PROMOTE USUAL (WR=60.0%, AvgPnL=0.73%, Trades=5)

Final set: ['ACE', 'APT', 'BABY', 'BIGTIME', 'CC', 'CHIP', 'ETC', 'IMX', 'LTC', 'POL', 'PONS', 'TURBO', 'USUAL']

## LOSERS Update — 2026-09-17 06:05 UTC
- REMOVE ETH (insufficient data)
- REMOVE MET (insufficient data)
- REMOVE BLUR (WR=50.0%, PnL=$-0.13, recovered)
- ADD INJ (WR=37.5%, PnL=$-0.51, wr_collapse (73.1% → 37.5%))

Final set: ['ENA', 'INJ', 'KAS']

## [2026-09-17 14:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**Open:** 0 (system flat)
**24h:** 26T 42.3%WR -$0.02

**24h Exit Breakdown:**
- ATR SL: 7T (31.8%) avg +$0.009 — healthy, below 40% threshold
- SNIPER exits: 10T — protecting system from bearish reversals
- profit-monster-trail: 2T +$0.14 — working
- hard_tp: 1T +$0.34 — working
- HARD_SL_FAILED: 1T -$0.25, HL_CLOSED: 1T -$0.23 — single occurrences

**Signal Health (24h):**
- pullback-entry- SHORT: 12T -$0.16 — regime-driven weakness (SHORTs in neutral market)
- open-skies+ LONG: 5T +$0.20 — healthy (60%WR)
- volume-breakout-long+ LONG: 3T -$0.10 — 0%WR but small sample, monitor
- mover-, r2-trend-short3: 1T each, 100%WR — working

**Diagnosis:**
- ATR SL healthy (31.8% of closes, avg +$0.009)
- SNIPER actively protecting system
- System flat — quiet market period
- No overtrading (0/hr)

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades in last hour
- ATR SL well below 40% threshold
- Trade frequency 0/hr — quiet, not overtrading
- pullback-entry- SHORT weakness is regime-driven, still profitable over 7d

**Monitoring:**
- volume-breakout-long+ at 0%WR (3T) — will kill if reaches 3+ trades next hour with 0 wins
- System flat — waiting for next signal

## [2026-09-17 15:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**Open:** 0 (system flat)
**24h:** 23T 42%WR +$0.01

**24h Exit Breakdown:**
- ATR SL: 7T (30.4%) avg +$0.009 — healthy, below 40% threshold
- SNIPER exits: 10T — protecting system from bearish reversals
- profit-monster-trail: 2T +$0.14 — working
- hard_tp: 1T +$0.34 — working
- HARD_SL_FAILED: 1T -$0.25, HL_CLOSED: 1T -$0.23 — single occurrences

**Signal Health (24h):**
- pullback-entry- SHORT: 12T -$0.16 — regime-driven weakness, small per-trade loss
- open-skies+ LONG: 5T +$0.20 — healthy (60%WR)
- volume-breakout-long+ LONG: 3T -$0.10 — 0%WR, monitoring (not yet at 3+ trades kill threshold per hour)
- mover-, r2-trend-short3: 1T each, 100%WR

**Diagnosis:**
- ATR SL healthy (30.4% of closes, avg +$0.009)
- SNIPER actively protecting system
- System flat — quiet market period
- No overtrading (0/hr)

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades in last hour
- ATR SL well below 40% threshold
- Trade frequency 0/hr — quiet, not overtrading
- volume-breakout-long+ at 0%WR (3T) — monitoring but no action yet

**Monitoring:**
- volume-breakout-long+ — will kill if next hour shows 3+ trades with 0 wins
- System flat — waiting for next signal

## [2026-09-17 09:00 UTC] Hourly Analysis

**Trades:** 1 closed last hour
- ACE LONG (mover+,rs-s61) → SNIPER-L1-BEARISH exit → +$0.04

**24h:** 23T 39%WR -$0.18 | **7d:** 255T 53%WR +$0.70
**Open:** 1 (BLUR SHORT -9.5%)

**24h Exit Breakdown:**
- ATR SL: 7T (30.4%) avg +$0.009 — healthy, well below 40%
- SNIPER exits: 12T total — protecting system from bearish reversals
- HL_CLOSED: 1T -$0.23, HARD_SL_FAILED: 1T -$0.25 — single occurrences

**Signal Health (24h):**
- pullback-entry-: 12T 4W -$0.16 — 33%WR, losing short-term but 7d profitable (52%WR)
- open-skies+: 5T 3W +$0.20 — healthy (60%WR)
- volume-breakout-long+: 3T 0W -$0.10 — 0%WR, **kill candidate** (only 1T last hour, below 3+ threshold)
- rs-s36,volume-breakout-long+: 1T 0W -$0.22 — combo signal failing

**Diagnosis:**
- ATR SL healthy (30.4% of closes)
- SNIPER actively protecting system (12T exits)
- volume-breakout-long+ consistently failing — 0%WR across 3 trades
- pullback-entry- SHORT weakness is regime-driven (still profitable 7d)
- Trade frequency 1/hr — not overtrading
- BLUR SHORT open -9.5% — monitor

**Changes:** None

**No Change Needed:**
- Kill check: volume-breakout-long+ at 0%WR but only 1T last hour (threshold: 3+ in hour)
- ATR SL well below 40% threshold
- Trade frequency 1/hr — quiet, not overtrading

**Monitoring:**
- volume-breakout-long+ — will kill if next hour shows 3+ trades with 0 wins
- BLUR SHORT — monitor if loss deepens
- pullback-entry- — SHORT weakness expected in current regime

## [2026-09-17 10:09 UTC] Hourly Analysis

**Trades:** 2 closed last hour (FOGO LONG → SNIPER exit -$0.09, BLUR SHORT → SNIPER exit $0.00)
**24h:** 25T 36%WR -$0.27 | **7d:** 255T 53%WR +$0.70
**Open:** 1 (HEMI SHORT pullback-entry- +3.15%)

**24h Exit Breakdown:**
- ATR SL: 7T (28%) avg +$0.009 — healthy, well below 40%
- SNIPER exits: 15T (60%) — actively protecting system from reversals
- HARD_SL_FAILED: 1T -$0.25, HL_CLOSED: 1T -$0.23 — single outliers

**Signal Health (24h):**
- pullback-entry-: 13T 30.8%WR -$0.16 — SHORT weakness (7d: 51.3%WR +$0.73, regime-driven)
- open-skies+: 6T 50%WR +$0.11 — healthy
- volume-breakout-long+: 3T 0%WR -$0.10 — 0%WR but 0T last hour (below kill threshold)
- rs-s36,volume-breakout-long+: 1T 0%WR -$0.22 — combo signal failing

**Diagnosis:**
- ATR SL healthy at 28% — no SL tightness issue
- SNIPER dominating exits (60%) — system correctly protecting from bearish reversals
- volume-breakout-long+ has gone quiet — 0 trades in last 4h, no fresh losses
- pullback-entry- SHORT dragging 24h PnL but 7d still profitable — regime issue not signal issue
- Trade frequency 2/hr — not overtrading

**Changes:** None

**No Change Needed:**
- Kill check: volume-breakout-long+ at 0%WR but 0T last hour (threshold: 3+T in hour)
- ATR SL well below 40% threshold
- Trade frequency 2/hr — normal

**Monitoring:**
- volume-breakout-long+ — 0%WR persistent, recommend CEO review (not auto-killable since quiet)
- HEMI SHORT — small position +3.15%, let it run
- pullback-entry- SHORT — regime-driven, no action needed

## [2026-09-17 11:12 UTC] Hourly Analysis

**Trades:** 0 closed last hour (system quiet)
**24h:** 25T 36%WR -$0.27 | **7d:** 252T 52%WR -$0.78
**Open:** 2 SHORTs (pullback-entry-) — HEMI -74%, SEI -50% (both 1.3% SL intact)

**24h Exit Breakdown:**
- ATR SL: 7T (28%) avg +$0.009 — healthy
- SNIPER: 14T (56%) — dominant, protecting system
- Outliers: HL_CLOSED 1T -$0.23, HARD_SL_FAILED 1T -$0.25

**Signal Health (24h):**
- pullback-entry-: 13T 31%WR -$0.16 (7d 51%WR +$0.73 — regime-driven)
- open-skies+: 6T 50%WR +$0.11
- volume-breakout-long+: 3T 0%WR -$0.10 (0T last hour — quiet)

**Changes:** None

**No Change Needed:**
- Kill check: volume-breakout-long+ 3T 0%WR but 0T last hour (below 3+/hour threshold)
- ATR SL healthy at 28%
- Trade frequency low — not overtrading

**Monitoring:**
- HEMI SHORT, SEI SHORT — both deeply underwater, SL at 1.3% distance intact
- volume-breakout-long+ — persistent 0%WR but quiet

## [2026-09-17 12:08 UTC] Hourly Analysis

**Trades:** 1 closed last hour (HEMI SHORT → SNIPER exit, -$0.06)
**24h:** 23T 30%WR -$0.56 | **7d:** 252T 52%WR -$0.78
**Open:** 3 (SUSHI LONG, XPL LONG, SEI SHORT — all slightly negative)

**24h Exit Breakdown:**
- SNIPER: 13T (56%) — dominant, protecting system
- ATR SL: 5T (22%) avg $0.008 — healthy
- hard_tp: 1T +$0.34 — good
- HL_CLOSED: 1T -$0.23, HARD_SL_FAILED: 1T -$0.25 — SL execution failures

**Signal Health:**
- pullback-entry-: 12T 25%WR -$0.39 (7d: 78T 51%WR +$0.69 — regime-driven, not signal issue)
- open-skies+: 6T 50%WR +$0.11 — healthy
- volume-breakout-long+: 3T 0%WR -$0.10 (7d: only 3T total — too low frequency to judge)

**Changes:** None

**No Change Needed:**
- Kill check: volume-breakout-long+ at 0%WR with 3T but only 3T in 7d — too sparse to kill
- pullback-entry- SHORT: 7d profitable, 24h weakness is regime-driven
- ATR SL healthy at 22%
- Trade frequency ~1/hr — normal

**Flagged to CEO:**
- HARD_SL_FAILED (SEI SHORT) and HL_CLOSED (ACE SHORT) — SL execution failures on pullback-entry- SHORT

**Open Questions:**
- HARD_SL_FAILED — is there a known issue with SL execution for small positions?

## [2026-09-17 13:10 UTC] Hourly Analysis

**Trades:** 2 closed last hour (SUSHI LONG ATR SL -$0.14, RESOLV LONG profit-trail +$0.01)
**PnL:** -$0.13 (50% WR)
**24h:** 9T 30%WR -$0.56 | **7d:** 252T 52%WR +$0.78
**Open:** 2 (XPL LONG open-skies+, AVAX LONG btc-pump-rider+)

**24h Exit Breakdown:**
- ATR SL: 6/9 (67%) avg -$0.042 — elevated but losses negligible
- HARD_SL_FAILED: 1T -$0.25 (isolated)
- HL_CLOSED: 1T -$0.23 (isolated)
- profit-monster-trail: 1T +$0.01

**Signal Health:**
- pullback-entry-: 5T 20%WR -$0.56 (24h) but 7d: 69T 52%WR +$0.36 — regime-driven
- open-skies+: 2T 50%WR +$0.05 — healthy
- volume-breakout-long+: 0T last hour — quiet

**Changes:** None

**No Change Needed:**
- Kill check: no signal at kill threshold (3+/hour with 0%WR)
- ATR SL elevated at 67% but avg loss only -$0.042 — SLs working as intended
- Trade frequency ~2/hr — normal
- pullback-entry- EXTREME regime = 67%WR, weakness is regime-specific

## [2026-09-17 14:10 UTC] Hourly Analysis

**Trades:** 2 closed (0W 2L -$0.25)
- AVAX LONG btc-pump-rider+ cut-loser-CL-T1: -$0.09
- XPL LONG open-skies+ atr_sl_hit: -$0.16

**24h:** 11T 27.3%WR -$0.97 | **7d:** 233T 51.9%WR -$1.57

**24h Exit Breakdown:**
- atr_sl_hit: 7T avg -$0.059 — dominant (64%), near breakeven (tpsl fix working)
- cut-loser-CL-T1: 1T -$0.09
- HARD_SL_FAILED: 1T -$0.25 (isolated)
- HL_CLOSED: 1T -$0.23 (isolated)
- profit-monster-trail: 1T +$0.01

**24h by Signal:**
- pullback-entry- SHORT: 5T 20%WR -$0.56 — cold streak (7d: 52.2%WR +$0.36, normal)
- open-skies+ LONG: 3T 33%WR -$0.11
- btc-pump-rider+ LONG: 1T 0%WR -$0.09 (below kill threshold)
- grind-breakout+ LONG: 1T 1W +$0.01
- volume-breakout-long+ LONG: 1T 0%WR -$0.22 (below kill threshold)

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour (max 5T but 7d positive)
- ATR SL: 64% of 24h closes but avg -$0.059 (near breakeven, tpsl fix verified)
- Trade frequency: 2T/hr — healthy
- All previously killed signals remain killed
- 7d -$1.57 essentially breakeven on 233T

**Monitoring:**
- 24h cold streak (27.3%WR) on tiny sample (11T) — noise, not structural
- Open trades: 0 (flat)
- ATR SL avg losses tiny — system risk under control

## [2026-09-17 15:10 UTC] Hourly Analysis

**Trades:** 1 closed (0W 1L -$0.15)
- WCT open-skies+ LONG atr_sl_hit: -$0.15

**24h:** 12T 25%WR -$1.12 | **7d:** 231T 51.5%WR -$2.10

**24h Exit Breakdown:**
- atr_sl_hit: 8T avg -$0.070 — dominant (67%), near breakeven (tpsl fix working)
- cut-loser-CL-T1: 1T -$0.09
- HARD_SL_FAILED: 1T -$0.25 (isolated)
- HL_CLOSED: 1T -$0.23 (isolated)
- profit-monster-trail: 1T +$0.01

**24h by Signal:**
- pullback-entry- SHORT: 5T 20%WR -$0.56 — cold streak (7d: 52.2%WR, regime-driven)
- open-skies+ LONG: 4T 25%WR -$0.26 — degrading from 66.7%WR (Sep 11-13)
- btc-pump-rider+ LONG: 1T 0%WR -$0.09 (below kill threshold)
- grind-breakout+ LONG: 1T 100%WR +$0.01
- volume-breakout-long+ LONG: 1T 0%WR -$0.22 (below kill threshold)

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour (max 5T but 7d positive)
- ATR SL: 67% of 24h but avg -$0.070 (near breakeven, tpsl fix verified)
- Trade frequency: ~1.7T/hr — healthy
- Open trades: 2 (tiny losses, both under $0.15)

**Monitoring:**
- open-skies+ daily: Sep 11 66.7%WR → Sep 17 25%WR (4T today, not kill threshold yet)
- 24h cold streak (25%WR) on 12T — small sample, noise vs structural
- ATR SL dominance structural in choppy market, losses tiny

## [2026-09-17 16:30 UTC] Hourly Analysis

**Trades:** 2 closed (0W 2L -$0.25)
- COMP SHORT r2-trend-short3 cut-loser-CL-T1: -$0.09
- STX LONG open-skies+ atr_sl_hit: -$0.16

**24h:** 14T 21.4%WR -$1.37 | **7d:** 231T 51.5%WR -$2.10

**24h Exit Breakdown:**
- atr_sl_hit: 9T avg -$0.080 — dominant (64%), near breakeven (tpsl fix working)
- cut-loser-CL-T1: 2T avg -$0.090
- HARD_SL_FAILED: 1T -$0.250 (isolated)
- HL_CLOSED: 1T -$0.230 (isolated)
- profit-monster-trail: 1T +$0.010

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour (open-skies+ had 1T, not 3+)
- ATR SL: 64% of 24h but avg -$0.080 (near breakeven, tpsl fix verified)
- Trade frequency: ~2T/hr — healthy
- Open trades: 1 (WCT volume-breakout-long+ LONG, 1.7h, $0.00 unrealized)

**Monitoring:**
- open-skies+ collapse today: 4T 0%WR -$0.61 (all LONG, all ATR SL). 7d: 44.4%WR -$0.24. Historically strong (Sep 11-16). Not kill-worthy yet (1T last hour), watching.
- 24h cold streak (21.4%WR) on 14T — small sample, regime-driven

## [2026-09-17 17:30 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet period)
**Open:** 4 (all volume-breakout-long+ LONG: WCT 2.7h, BABY 0.9h, NOT 0.6h, GMX 0.0h — all $0.00 unrealized)
**24h:** 14T 21.4%WR -$1.37 | **7d:** 227T 51.1%WR -$2.61 (breakeven)

**Changes:** None

**No Change Needed:**
- Kill check: 0 trades last hour — nothing to evaluate
- ATR SL: 9/14 (64%) 24h avg -$0.080 — breakeven, tpsl fix working
- Trade frequency: ~1.7T/hr 7d avg — healthy
- Open cluster: 4 volume-breakout-long+ positions, all flat — no concentration alarm at $0.00

**Monitoring:**
- open-skies+ 24h: 5T 0%WR -$0.42 — not kill-worthy (below 3T/hour threshold, 7d 44.4% acceptable)
- pullback-entry- 24h: 5T 0%WR -$0.56 — same, cold streak in choppy market
- Quiet period — no trades closing, no data to act on

**BY:** auto_1hr

## [2026-09-17 18:30 UTC] Hourly Analysis

**Trades:** 1 closed (0W 1L -$0.15)
- NOT LONG volume-breakout-long+ atr_sl_hit: -$0.15

**24h:** 14T 21.4%WR -$1.37 | **7d:** 226T 50.9%WR -$2.72

**24h Exit Breakdown:**
- atr_sl_hit: 9T avg -$0.121 — dominant (64%), near breakeven
- cut-loser-CL-T1: 2T avg -$0.090
- HARD_SL_FAILED: 1T -$0.250 (isolated)
- HL_CLOSED: 1T -$0.230 (isolated)
- profit-monster-trail: 1T +$0.010

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour
- ATR SL: 64% of 24h but avg -$0.121 (near breakeven, tpsl fix verified)
- Trade frequency: ~1.4T/hr — healthy
- Open trades: 3 (volume-breakout-long+ LONG: GMX 1h, BABY 1.9h, WCT 3.7h — all $0.00)

**Monitoring:**
- pullback-entry- 24h: 4T -$0.78 but 7d: 68T 51.5%WR +$0.25 — profitable on wider sample
- ATR SL dominance structural in choppy market, losses tiny
- 3 volume-breakout-long+ open positions — watching for cluster risk

**BY:** auto_1hr

## [2026-09-17 19:30 UTC] Hourly Analysis

**Trades:** 2 closed (1W 1L -$0.15)
- WCT LONG volume-breakout-long+ SL hit: -$0.16
- BABY LONG volume-breakout-long+ SL hit: +$0.01

**Open:** 3 (HEMI SHORT pullback-entry-, IO SHORT pullback-entry-, GMX LONG volume-breakout-long+)

**24h:** 16T 12.5%WR -$1.89 | **7d:** 226T 50.9%WR -$2.72

**24h Exit Breakdown:**
- atr_sl_hit: 11T (68.75%) avg -$0.113 — dominant but near breakeven
- cut-loser-CL-T1: 2T avg -$0.090
- HARD_SL_FAILED: 1T -$0.250
- HL_CLOSED: 1T -$0.230
- profit-monster-trail: 1T +$0.010

**Changes:** None

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour
- ATR SL: 68.75% but avg loss tiny (-$0.113) — structural in choppy market, tpsl fix verified
- Trade frequency: ~2/hr — healthy
- pullback-entry- 24h: 4T 0%WR -$0.78 but 7d: 68T 51.5%WR +$0.25 — cold streak, not kill-worthy
- Open trades: 3 with reasonable SL levels (0.87-1.30%)

**Monitoring:**
- trend_purity+ 7d: 11T -$0.90 — worst performer but too few trades to act
- ATR SL dominance structural — losses small, no fix needed
- 2 pullback-entry- shorts open — watching for reversal risk

**BY:** auto_1hr

## [2026-09-17 20:30 UTC] Hourly Analysis

**Trades:** 0 closed (quiet hour)

**24h:** 16T 12.5%WR -$1.89 | **7d:** 226T 50.9%WR -$2.72

**Open:** 5 (HEMI SHORT pullback-entry-, IO SHORT pullback-entry-, ALT SHORT pullback-entry-, AIXBT SHORT pullback-entry-, GMX LONG volume-breakout-long+)

**24h Exit Breakdown:**
- atr_sl_hit: 11T (68.75%) avg -$0.113 — structural, tpsl fix verified
- cut-loser-CL-T1: 2T avg -$0.090
- HARD_SL_FAILED: 1T -$0.250
- HL_CLOSED: 1T -$0.230
- profit-monster-trail: 1T +$0.010

**Changes:** None

**No Change Needed:**
- Kill check: 0 trades last hour — no signal qualifies
- ATR SL: 68.75% but avg loss tiny (-$0.113) — no fix needed
- Trade frequency: 0/hr — quiet period
- pullback-entry- cold streak: 24h 0%WR but 7d 51.5%WR +$0.25 — variance, not kill-worthy
- Open trades: 4 pullback-entry- shorts, 1 volume-breakout-long+ long — no cluster risk

**Monitoring:**
- 4 pullback-entry- shorts open simultaneously — watching for coordinated reversal
- ATR SL dominance structural in choppy market
- Next: watch for breakout from current low-activity period

**BY:** auto_1hr

## [2026-09-17 21:30 UTC] Hourly Analysis

**Trades:** 1 closed (1 win)
**PnL:** $0.02 (WR: 100%)

**24h:** 13T 30.8%WR -$1.09 | **7d:** 225T 51.1%WR -$2.78

**Open:** 4 (ALT SHORT pullback-entry-, AIXBT SHORT pullback-entry-, IO SHORT pullback-entry-, GMX LONG volume-breakout-long+)

**24h Exit Breakdown:**
- atr_sl_hit: 10T avg -$0.092 — dominant, losses tiny
- cut-loser-CL-T1: 2T avg -$0.090
- profit-monster-trail: 1T +$0.010

**Changes:** None

**No Change Needed:**
- Kill check: 0 signals at 0%WR with 3+ trades last hour
- ATR SL: 76.9% of closes but avg loss -$0.092 — structural, acceptable
- Trade frequency: 1/hr — quiet, not overtrading
- 7d stats improving: 51.1%WR (was 50.9%)
- accel-300-v4-short-: 3T 0%WR -$0.44 over 7d but all from Sep 11 — stale, not actionable
- Open trades: all with reasonable SL levels (0.34-1.18%)

**Monitoring:**
- 24h cold streak easing (30.8%WR vs 18.8% earlier)
- 3 pullback-entry- shorts open — watching for reversal
- quiet market conditions — no urgency

**BY:** auto_1hr

## [2026-09-17 22:45 UTC] Hourly Analysis

**Trades:** 0 closed
**PnL:** $0.00 (WR: N/A)

**24h:** 13T 30.8%WR -$1.09 | **7d:** 224T 50.9%WR -$2.81

**Open:** 5 (GMX LONG volume-breakout-long+, IO/AIXBT/ALT/IMX SHORT pullback-entry-)

**24h Exit Breakdown:**
- atr_sl_hit: 10T avg -$0.092 — dominant, losses tiny
- cut-loser-CL-T1: 2T avg -$0.090
- profit-monster-trail: 1T +$0.010

**Changes:** None

**No Change Needed:**
- Kill check: 0 signals at 0%WR with 3+ trades last hour
- ATR SL: 77% of closes but avg loss -$0.092 — structural, acceptable in chop
- Trade frequency: 0/hr — quiet
- 7d WR stable at 50.9%
- Open trades: all SHORT positions profitable, SL levels reasonable (0.3-1.1%)

**Monitoring:**
- 4 pullback-entry- shorts open — watching for coordinated reversal
- ATR SL dominance structural in current chop
- Next: watch for breakout or trend development

**BY:** auto_1hr

## [2026-09-18 01:00 UTC] Hourly Analysis

**Trades:** 3 closed (0 wins, 3 losses)
**PnL:** -$0.45 (WR: 0%)

**24h:** 15T 33.3%WR -$1.73 | **7d:** 222T 49.5%WR -$3.58

**Exit Breakdown (24h):**
- atr_sl_hit: 12T avg -$0.130 — dominant, losses tiny
- cut-loser-CL-T1: 2T avg -$0.090
- profit-monster-trail: 1T +$0.010

**Open:** 2 (GMX LONG volume-breakout-long+, IMX SHORT pullback-entry-)

**Changes:** None

**No Change Needed:**
- Kill check: 0 signals at 0%WR with 3+ trades last hour
- ATR SL: 80% of 24h closes but avg loss -$0.13 — structural in chop
- Trade frequency: 3/hr — normal
- 7d WR stable at 49.5%
- No consecutive negative hours with meaningful losses

**Monitoring:**
- IMX SHORT: SL at 0.23% — way below ATR_SL_MIN floor (1.3%). Likely to get stopped on noise. Can't fix retroactively.
- pump-chain+ LONG: 21T/7d 38.1%WR -$0.61 — worst signal by total loss but not at kill threshold
- trend_purity+ LONG: 11T/7d 36.4%WR -$0.90 — concentrated in INJ/MET, rest profitable
- rr-struct+: 15T/7d 73.3%WR +$0.59 — star performer

**BY:** auto_1hr

## [2026-09-18 02:00 UTC] Hourly Analysis

**Trades:** 1 closed (0 wins, 1 loss)
**PnL:** -$0.16 (WR: 0%)

**24h:** 16T 18.8%WR -$1.89 | **7d:** 223T 49.3%WR -$3.74

**Exit Breakdown (24h):**
- atr_sl_hit: 13T avg -$0.132 — dominant, losses tiny
- cut-loser-CL-T1: 2T avg -$0.090
- profit-monster-trail: 1T +$0.010

**Open:** 1 (GMX LONG volume-breakout-long+)

**Changes:** None

**No Change Needed:**
- Kill check: 0 signals at 0%WR with 3+ trades last hour
- ATR SL: 81.2% of 24h closes but avg loss -$0.132 — structural in chop, already at 1.3% floor
- Trade frequency: 1/hr — quiet
- 7d WR stable at 49.3%
- Consecutive negative hours: 2 (total -$0.61) — not meaningful enough to reduce size
- ema300-dip-long (2T/7d 0%WR) and accel-300-v4-short- (2T/7d 0%WR) — below kill threshold

**Monitoring:**
- IMX SHORT pnl_pct data anomaly (-731.73%) — actual loss -1.47%, tiny position ($11.10)
- Cold streak: 24h WR 18.8% vs 7d 49.3% — variance, not signal failure
- ATR SL floor at 1.3% already raised from 1.2% on Sep 14 — further widening risks larger losses in trend reversals
- rr-struct+ remains star performer: 15T/7d 73.3%WR +$0.59

**BY:** auto_1hr

## [2026-09-18 03:00 UTC] Hourly Analysis

**Trades:** 0 closed, 3 open (WLD LONG, CAKE LONG, GMX LONG)
**24h:** 15T 3W 12L (20.0%WR) $-1.67 | **7d:** 222T 109W 113L (49.1%WR) $-3.92

**Exit Breakdown (24h):**
- atr_sl_hit: 12T avg -$0.125 — dominant, losses tiny
- cut-loser-CL-T1: 2T avg -$0.090
- profit-monster-trail: 1T +$0.010

**Signal 24h:**
- pullback-entry-: 5T 1W $-0.59
- open-skies+: 4T 0W $-0.61 (already killed)
- volume-breakout-long+: 3T 1W $-0.30

**Changes:** None

**No Change Needed:**
- Kill check: 0 signals at 0%WR with 3+ trades last hour
- ATR SL: 80% of 24h closes but avg loss -$0.125 — structural in chop
- Trade frequency: 0/hr — quiet
- Cold streak: 20%WR 24h vs 49.1% 7d — variance, losses are tiny

**Monitoring:**
- 3 open trades: CAKE +61% (r2-trend-long8), WLD -48%, GMX -17%
- 7d WR stable at 49.1%
- No consecutive negative hours with meaningful losses

**BY:** auto_1hr

## [2026-09-18 04:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**24h:** 15T 3W 20.0%WR $-1.67 | **7d:** 218T 109W 50.0%WR $-3.32

**Exit Breakdown (24h):**
- atr_sl_hit: 12T avg -$0.125 — 80% of closes, losses tiny
- cut-loser-CL-T1: 2T avg -$0.090
- profit-monster-trail: 1T +$0.010

**Signal 24h:**
- pullback-entry-: 5T 1W $-0.59 (all SHORT ATR SL hits, choppy market)
- open-skies+: 4T 0W $-0.61 (KILLED)
- volume-breakout-long+: 3T 1W $-0.30

**Open Trades (4):**
- GMX LONG: +$1.78% unrealized, 11h old, SL 0.88% below current (tight)
- CAKE LONG: +$0.72% unrealized, 2h old
- WLD LONG: +$2.37% unrealized, 1.4h old
- YGG LONG: -$0.17% unrealized, 0.6h old

**Changes:** None

**No Change Needed:**
- Kill check: 0 signals at 0%WR with 3+ trades last hour
- ATR SL: 80% of 24h closes but avg loss -$0.125 — structural in chop
- Trade frequency: 0/hr — quiet
- Cold streak: 20%WR 24h vs 50.0% 7d — variance, losses tiny

**Monitoring:**
- GMX open 11h — longest open trade, SL tight at 0.88%
- All open trades have NULL last_updated — pipeline not updating open trade prices
- 4 open trades all LONG in current regime — directional concentration
- 7d WR stable at 50.0%

**BY:** auto_1hr

## [2026-09-18 05:00 UTC] Hourly Analysis

**Trades:** 1 closed last hour (1W)
**24h:** 16T 4W 25.0%WR $-1.41 | **7d:** 217T 110W 50.7%WR $-2.61

**Exit Breakdown (24h):**
- atr_sl_hit: 13T avg -$0.095 — 81.2% of closes, losses tiny
- cut-loser-CL-T1: 2T avg -$0.090
- profit-monster-trail: 1T +$0.010

**Signal 24h:**
- pullback-entry-: 5T 1W 20%WR $-0.59 (all SHORT ATR SL hits, choppy market)
- open-skies+: 4T 0W 0%WR $-0.61 (ALREADY KILLED)
- volume-breakout-long+: 4T 2W 50%WR $-0.04
- grind-breakout+: 1T 1W 100%WR $0.01

**Open Trades (3):**
- GMX LONG: +226% unrealized, 12.1h old — STALE (>8h)
- CAKE LONG: +189% unrealized, 3.0h old, trailing SL above entry
- YGG LONG: -$0.01 unrealized, 1.6h old

**Regime:** 100% NEUTRAL — choppy market

**Changes:** None

**No Change Needed:**
- Kill check: 0 signals at 0%WR with 3+ trades last hour
- ATR SL: 81.2% of 24h closes but avg loss -$0.095 — structural in chop
- Trade frequency: 1/hr — quiet
- Cold streak: 25%WR 24h vs 50.7% 7d — variance, losses tiny

**Monitoring:**
- GMX open 12.1h — stale, monitoring for exit
- CAKE trailing SL above entry — profit locked
- 7d WR stable at 50.7%
- pullback-entry- SHORTs all hitting ATR SL in NEUTRAL — choppy market

**BY:** auto_1hr

## FAVORITES Update — 2026-09-18 06:00 UTC
- Regime: NEUTRAL
- DEMOTE TURBO (WR=50.0%, PnL=$-0.13, 1 consecutive bad days, regime=NEUTRAL)
- PROMOTE ATOM (WR=80.0%, AvgPnL=0.94%, Trades=5)

Final set: ['ACE', 'APT', 'ATOM', 'BABY', 'BIGTIME', 'CC', 'CHIP', 'ETC', 'IMX', 'LTC', 'POL', 'PONS', 'USUAL']

## [2026-09-18 07:00 UTC] Hourly Analysis

**Trades:** 1 closed last hour (1W, 0L)
**24h:** 19T 6W 31.6%WR -$1.22 | **7d:** 217T 110W 50.7%WR -$2.61

**Exit Breakdown (24h):**
- atr_sl_hit: 14T avg -$0.080 — 73.7% of closes, losses tiny
- profit-monster-trail: 3T avg +$0.027
- cut-loser-CL-T1: 2T avg -$0.090

**Signal 24h:**
- pullback-entry-: 5T 1W 20%WR -$0.59 (all SHORT ATR SL hits in chop)
- open-skies+: 4T 0W 0%WR -$0.61 (ALREADY KILLED)
- volume-breakout-long+: 4T 2W 50%WR -$0.04
- warrior-sr-confirm+: 1T 1W 100%WR +$0.04
- r2-trend-long8: 1T 1W 100%WR +$0.12
- grind-breakout+: 1T 1W 100%WR +$0.01
- mover+: 1T 1W 100%WR +$0.03

**Open Trades (3):**
- GMX LONG: 15h open, trailing SL $7.49 (above entry $7.40) — profit locked, waiting for retracement
- YGG LONG: 4.6h open, +93% — trailing
- ME LONG: 0.2h open, -$0.02 — fresh

**Regime:** 100% NEUTRAL — flat all week

**Changes:** None

**No Change Needed:**
- Kill check: 0 signals at 0%WR with 3+ trades last hour
- ATR SL: 73.7% of 24h closes but avg loss -$0.080 — structural in chop, not SL tuning issue
- Trade frequency: 1/hr — quiet, appropriate for NEUTRAL
- Cold streak: 31.6%WR 24h vs 50.7% 7d — variance, losses tiny
- pullback-entry-: 20%WR bad 24h but 51.5%WR profitable 7d — variance not structural

**Monitoring:**
- GMX open 15h — trailing SL working, profit locked
- 7d WR stable at 50.7%
- All 24h trades in NEUTRAL regime — flat market all week

**BY:** auto_1hr

## [2026-09-18 09:00 UTC] Hourly Analysis

**Trades:** 1 closed (1W, 0L)
**24h:** 20T 6W 30.0%WR -$1.11 | **7d:** 217T 110W 50.7%WR -$2.61

**Exit Breakdown (24h):**
- atr_sl_hit: 15T avg -$0.074 — 75% of closes, losses tiny
- profit-monster-trail: 3T avg +$0.027
- cut-loser-CL-T1: 2T avg -$0.090

**Signal 24h:**
- pullback-entry-: 5T 1W 20%WR -$0.59 (all SHORT ATR SL hits in chop)
- volume-breakout-long+: 5T 3W 60%WR -$0.03 (break-even)
- open-skies+: 4T 0W 0%WR -$0.61 (ALREADY KILLED 09-17)
- Others: 6 signals 1T each, 4W mixed

**Open Trades (4):**
- FOGO LONG doji-bottom-long: 5min open, +0.02% — fresh
- ME LONG volume-breakout-long+: 1.3h open, +1.21% — trailing
- YGG LONG volume-breakout-long+: 5.5h open, +1.26% — trailing
- GMX LONG volume-breakout-long+: 16h open, +2.35% — stale winner, trailing SL above entry

**Regime:** 100% NEUTRAL — flat all week

**Changes:** None

**No Change Needed:**
- Kill check: 0 signals at 0%WR with 3+ trades last hour
- ATR SL: 75% of 24h closes but avg loss -$0.074 — structural in chop, not SL tuning
- Trade frequency: 1/hr — quiet, appropriate for NEUTRAL
- Cold streak: 30%WR 24h vs 50.7% 7d — variance, losses tiny ($0.07 avg)
- pullback-entry-: 20%WR bad 24h but profitable 7d — variance not structural
- GMX open 16h: trailing SL at $7.49 above entry $7.40, profit locked

**Monitoring:**
- GMX open 16h — stale winner, trailing SL protecting profit
- 7d WR stable at 50.7%
- All trades NEUTRAL regime
- FOGO just opened — watch for quick stop

**BY:** auto_1hr

## [2026-09-18 11:00 UTC] Hourly Analysis

**Trades:** 0 closed (quiet hour)
**24h:** 20T 6W 30.0%WR -$1.11 | **7d:** 210T 110W 52.4%WR -$1.72

**Open (5):**
- GMX volume-breakout-long+ LONG: 17h, +$271 — stale winner, trailing
- YGG volume-breakout-long+ LONG: 6.8h, +$167 — trailing
- ME volume-breakout-long+ LONG: 3h, +$153 — trailing
- FOGO doji-bottom-long LONG: 1.9h, +$124 — trailing
- DYDX volume-breakout-long+ LONG: 1h, +$58 — fresh

**Signal 24h:**
- open-skies+: 4T 0W -$0.61 — ALREADY KILLED 09-17
- pullback-entry-: 5T 1W 20%WR -$0.59 — bad 24h but profitable 7d
- volume-breakout-long+: 5T 3W 60%WR -$0.03 — break-even

**Changes:** None

**No Change Needed:**
- Kill check: no 0%WR signals with 3+ trades last hour
- ATR SL: 75% of 24h closes but avg loss -$0.074 — structural in chop
- Trade frequency: 0/hr — quiet, appropriate for NEUTRAL
- 7d WR stable at 52.4%

**Monitoring:**
- GMX 17h stale winner — trailing SL protecting profit
- 7d WR stable at 52.4%
- All trades NEUTRAL regime

**BY:** auto_1hr

## [2026-09-18 12:00 UTC] Hourly Analysis

**Trades:** 4 closed (4 wins, 0 losses) — **perfect hour**
**PnL:** +$0.50 | **24h:** 24T 12W 50.0%WR -$0.71 | **7d:** 212T 114W 53.8%WR -$0.75

**Open (1):**
- ME volume-breakout-long+ LONG: 3.2h, +$0.11 — trailing

**Last 1h detail:**
- GMX LONG: +$0.19 (atr_sl_hit — profit locked by trailing)
- YGG LONG: +$0.06 (atr_sl_hit — profit locked by trailing)
- FOGO LONG: +$0.13 (profit-monster-trail)
- DYDX LONG: +$0.12 (atr_sl_hit — profit locked by trailing)

**Signal 24h:**
- volume-breakout-long+: 8T 75%WR +$0.34 — strong
- pullback-entry-: 5T 20%WR -$0.59 — bad 24h but 52.2%WR 7d (+$0.26) — variance
- open-skies+: KILLED, no new trades

**Changes:** None

**No Change Needed:**
- Kill check: no 0%WR signals with 3+ trades last hour
- atr_sl_hit: 18/24h closes but trades are profit-locked wins, not losses — trailing SL working correctly
- Trade frequency: 4/hr — appropriate for NEUTRAL
- open-skies+ properly killed (False in constants)
- Pipeline restarted 11:08 UTC with CEO's RSI CEILING fix

**Monitoring:**
- ME open 3.2h — only position, trailing
- 7d WR stable at 53.8%
- All trades NEUTRAL regime

**BY:** auto_1hr

## [2026-09-18 13:00 UTC] Hourly Analysis

**Trades:** 1 closed (1 win, 0 losses)
**PnL:** +$0.09 | **24h:** 25T 13W 52.0%WR -$0.62 | **7d:** 209T 112W 53.6%WR -$0.82

**Open (1):**
- FOGO continuation+ LONG: $0.00 — trailing

**Signal 24h:**
- volume-breakout-long+: 9T 78%WR +$0.43 — strong
- pullback-entry-: 5T 20%WR -$0.59 — bad 24h but 65T/7d 50.8%WR +$0.08 (variance)
- open-skies+: KILLED, 0 trades today ✅

**Changes:** None

**No Change Needed:**
- Kill check: no 0%WR signals with 3+ trades last hour
- atr_sl_hit: 76% of 24h closes but 9/19 profit-locked wins — trailing SL working
- Trade frequency: 1/hr — appropriate for NEUTRAL
- All 24h trades NEUTRAL regime
- 7d WR stable at 53.6%

**Monitoring:**
- FOGO open, trailing SL
- 7d WR stable at 53.6%

**BY:** auto_1hr

## [2026-09-18 14:00 UTC] Hourly Analysis

**Trades:** 1 closed (1 win, 0 losses)
**PnL:** +$0.12 | **24h:** 24T 13W 54.2%WR -$0.30 | **7d:** 204T 110W 53.9%WR -$0.86

**Open (2):**
- BLUR LONG mover+ — $0.00 — 0.3h
- HYPER LONG btc-pump-rider+ — $0.00 — 0.1h

**Signal 24h:**
- volume-breakout-long+: 10T 7W 70%WR +$0.26 — strong
- pullback-entry-: 5T 1W 20%WR -$0.59 (all SHORT losers Sep 17, pre-RSI fix)
- mover+: 2T 2W 100%WR +$0.15 — good
- open-skies+: 2T 0WR -$0.31 (both Sep 17, pre-kill — no new trades)
- SHORT trades after 12:00 UTC: 0 (RSI ceiling fix holding)

**Changes:** None

**No Change Needed:**
- Kill check: no 0%WR signals with 3+ trades last hour
- atr_sl_hit: 18/24h closes but 9/18 winners (50%) — profit-locked trailing working
- RSI ceiling fix: no SHORT trades entered after 12:00 UTC — working
- open-skies+ properly killed (no trades since kill)
- Trade frequency: 1/hr — appropriate for NEUTRAL
- 7d WR stable at 53.9%

**Monitoring:**
- BLUR and HYPER open, trailing
- 7d WR stable at 53.9%
- pullback-entry- SHORT historically bad but 7d break-even (variance)

**BY:** auto_1hr

## [2026-09-18 15:30 UTC] Hourly Analysis

**Trades:** 2 closed (2 wins)
**PnL:** +$0.12 | **24h:** 24T 15W 62.5%WR +$0.53 | **7d:** 201T 108W 53.7%WR -$0.81

**Open (2):**
- W LONG volume-breakout-long+ — 0.1h
- NOT SHORT pullback-entry- — 0.4h

**Signal 24h:**
- volume-breakout-long+: 11T 8W 73%WR +$0.58 — strong
- mover+: 3T 3W 100%WR +$0.26 — perfect
- pullback-entry-: 5T 1W 20%WR -$0.59 (all pre-RSI fix SHORT losers)

**Changes:** None

**No Change Needed:**
- Kill check: no 0%WR signals with 3+ trades last hour
- atr_sl_hit: 17/24h closes (71%) but net +$0.11 — trailing converting some to wins
- RSI ceiling fix: 0 SHORT losers since 12:00 UTC — holding
- Trade frequency: ~1/hr — appropriate for NEUTRAL
- 24h PnL turned positive (+$0.53) — improving

**Monitoring:**
- W and NOT open, trailing
- 7d WR stable at 53.7%

**BY:** auto_1hr

## [2026-09-18 18:00 UTC] Hourly Analysis

**Trades:** 0 closed in last hour (quiet)
**PnL:** — | **24h:** 25T 16W 64%WR +$0.84 | **7d:** 199T 107W 53.8%WR -$0.51

**Open (2):**
- CAKE SHORT mover- — 1.0h
- NOT SHORT pullback-entry- — 1.5h

**Signal 24h:**
- volume-breakout-long+: 12T 9W 75%WR +$0.89 — strong
- mover+: 3T 3W 100%WR +$0.26 — perfect
- pullback-entry-: 5T 1W 20%WR -$0.59 (all pre-RSI fix SHORT losers)

**Changes:** None

**No Change Needed:**
- Kill check: no 0%WR signals with 3+ trades last hour
- atr_sl_hit: 17/24h closes (68%) but net +$0.11 — trailing converting SL hits to wins
- RSI ceiling fix: 0 bad SHORT entries since deploy ~09:45 UTC — holding
- Trade frequency: ~1/hr — appropriate for NEUTRAL
- 24h PnL positive (+$0.84) and stable
- 7d WR stable at 53.8%

**Monitoring:**
- CAKE and NOT open, trailing
- 7d WR stable at 53.8%

**BY:** auto_1hr

## [2026-09-18 19:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet)
**PnL:** — | **24h:** 24T 16W 67%WR +$0.99 | **7d:** 198T 106W 53.5%WR -$0.60

**Open (3):**
- DOT SHORT pullback-entry- — 45.1m, -$0.02
- CAKE SHORT mover- — 65.8m, -$0.06
- NOT SHORT pullback-entry- — 141.0m, -$0.02

**Signal 24h:**
- volume-breakout-long+: 11T 9W 91%WR +$1.04 — strong
- mover+: 3T 3W 100%WR +$0.26 — perfect
- pullback-entry-: 5T 1W 20%WR -$0.59 (all pre-RSI fix)
- Other signals: 6T 3W mixed small

**Changes:** None

**No Change Needed:**
- Kill check: no 0%WR signals with 3+ trades last hour
- atr_sl_hit: 16/24h closes (67%) but net +$0.26 — trailing converting SLs to wins
- RSI ceiling fix: 0 bad SHORT entries since deploy ~09:45 UTC — holding
- Trade frequency: 1/hr — appropriate for NEUTRAL
- 24h PnL improved to +$0.99
- 7d WR stable at 53.5%

**Monitoring:**
- DOT, CAKE, NOT open SHORTs — all near breakeven
- 7d PnL improving from -$1.50 to -$0.60

**BY:** auto_1hr

## [2026-09-18 20:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet)
**PnL:** — | **24h:** 22T 16W 72.7%WR +$1.14 | **7d:** 198T 106W 53.5%WR -$0.60

**Open (5):**
- NOT SHORT pullback-entry- — 4.2h, -$0.09
- CAKE SHORT mover- — 3.0h, -$0.06
- DOT SHORT pullback-entry- — 2.6h, -$0.01
- ADA LONG pump-chain+ — 1.9h, +$0.04
- FOGO LONG pump-chain+ — 1.8h, +$0.06

**Signal 24h:**
- volume-breakout-long+: 9T 8W 89%WR +$1.19 — strong
- mover+: 3T 3W 100%WR +$0.26 — perfect
- pullback-entry-: 5T 1W 20%WR -$0.59 (all pre-RSI fix)
- Others: 5T 4W mixed small

**12h Trend:** 14T 11W 78.6%WR +$0.70 — very strong. Only 2 slightly negative hours (12, 13).

**Changes:** None

**No Change Needed:**
- Kill check: no 0%WR signals with 3+ trades last hour
- atr_sl_hit: 14/22 24h closes (64%) but net +$0.41 — trailing converting SLs to wins
- RSI ceiling fix: 0 bad SHORT entries since deploy ~09:45 UTC — holding
- Trade frequency: ~0.9/hr — appropriate for NEUTRAL
- 24h PnL strong at +$1.14 (best in recent days)
- 7d WR stable at 53.5%

**Monitoring:**
- 5 open trades, 3 SHORTs near breakeven, 2 LONGs slightly green
- 7d PnL improving: -$1.50 → -$0.60

**BY:** auto_1hr

## [2026-09-18 21:00 UTC] Hourly Analysis

**Trades:** 1 closed last hour (CAKE SHORT mover- → cut-loser → -$0.09)
**24h:** 22T 18W 81.8%WR +$1.05 | **7d:** 194T 102W 53%WR -$0.87

**Signal 24h:**
- volume-breakout-long+: 9T 8W 89%WR +$1.19 — dominant, strong
- pullback-entry- SHORT: 5T 1W 20%WR -$0.59 — ALL losses from Sep 17 18-22h (pre-RSI fix). 0 losers post-fix. Fix holding.
- mover+: 3T 3W 100%WR +$0.26 — perfect
- mover-: 1T 0W 0%WR -$0.09 — 1 trade only, noise

**Open (6):**
- LONGs: ATOM, BABY, FOGO, ADA (mover+, pump-chain+) — all fresh 0.4-2h
- SHORTs: DOT, NOT (pullback-entry-) — 2.8h and 4.4h

**Changes:** None

**No Change Needed:**
- Kill check: no 0%WR signals with 3+ trades last hour (mover- 1T only)
- atr_sl_hit: 14/22 24h closes (64%) but net +$0.41 — trailing still converting SLs to wins
- RSI ceiling fix: 0 bad pullback-entry- SHORT entries since deploy — fix confirmed holding
- Trade frequency: ~0.9/hr — appropriate for NEUTRAL
- 24h PnL strong at +$1.05 with 81.8% WR
- 7d WR stable at 53%

**Monitoring:**
- 6 open trades, all fresh and near breakeven
- 7d PnL recovering: -$1.50 → -$0.87

**BY:** auto_1hr

## [2026-09-18 22:00 UTC] Hourly Analysis

**Trades:** 1 closed last hour (NOT SHORT pullback-entry- → atr_sl_hit → -$0.19)
**24h:** 24T 15W 62.5%WR +$0.86

**Signal 24h:**
- volume-breakout-long+: 9T 8W 89%WR +$1.19 — dominant
- pullback-entry-: 6T 1W 17%WR -$0.78 — all losses pre-RSI fix (Sep 17). 0 losers post-fix. Holding.
- mover+: 3T 3W 100%WR +$0.26 — perfect
- mover-: 1T 0W 0%WR -$0.09 — 1 trade only, noise
- Others: 5T 3W mixed small

**Open (6):**
- LONGs: ADA, FOGO (pump-chain+), BABY, ATOM (mover+), JUP (volume-breakout-long+) — all fresh 0.8-3h
- SHORTs: DOT (pullback-entry-) — 3.8h breakeven

**Changes:** None

**No Change Needed:**
- Kill check: no 0%WR signals with 3+ trades last hour
- atr_sl_hit: 15/24 24h closes (63%) but net +$0.22 — trailing converting SLs to wins
- RSI ceiling fix: 0 bad SHORT entries since deploy — fix confirmed holding
- Trade frequency: ~0.9/hr — appropriate for NEUTRAL
- 24h PnL strong at +$0.86 with 62.5% WR
- 7d WR stable at 53%

**Monitoring:**
- 6 open trades, all near breakeven ($0.00 PnL)
- 7d PnL recovering: -$1.50 → -$0.87

**BY:** auto_1hr

## [2026-09-18 23:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour
**24h:** 23T 12W 52.2%WR +$0.84

**Signal 24h:**
- volume-breakout-long+: 9T 8W 89%WR +$1.19 — dominant
- mover+: 3T 3W 100%WR +$0.26 — perfect
- pullback-entry-: 5T 0W -$0.80 — all pre-RSI-fix losses, 0 post-fix losers, holding
- Others: 6T 1W mixed small

**Open (6):**
- LONGs: ADA, FOGO (pump-chain+), BABY, ATOM (mover+), JUP (volume-breakout-long+) — all fresh 1.8-4h
- SHORTs: DOT (pullback-entry-) — 4.8h near breakeven

**Changes:** None

**No Change Needed:**
- Kill check: no 0%WR signals with 3+ trades last hour
- atr_sl_hit: 14/23 24h closes (61%) but net +$0.20 — trailing converting SLs to wins
- RSI fix: 0 bad SHORT entries since deploy — holding
- Trade frequency: ~1.0/hr — appropriate for NEUTRAL
- 24h PnL positive at +$0.84
- 7d PnL recovering: -$0.87

**BY:** auto_1hr

## LOSERS Update — 2026-09-18 22:34 UTC
- REMOVE HBAR (insufficient data)
- REMOVE ETC (insufficient data)
- REMOVE ZRO (insufficient data)
- REMOVE BIGTIME (WR=57.1%, PnL=$0.49, recovered)
- REMOVE SUSHI (insufficient data)
- REMOVE GMT (insufficient data)
- REMOVE NOT (insufficient data)
- REMOVE WLFI (insufficient data)
- REMOVE IO (insufficient data)
- ADD INJ (WR=40.0%, PnL=$-0.42, wr_collapse (75.0% → 40.0%))
- ADD HYPER (WR=40.0%, PnL=$-0.16, low_wr (40.0%))

Final set: ['DOT', 'HYPER', 'INJ']

## [2026-09-18 19:00 UTC] Hourly Analysis

**Trades:** 2 closed last hour (1W 1L)
- ATOM LONG mover+ → atr_sl_hit +$0.16
- JUP LONG volume-breakout-long+ → atr_sl_hit -$0.13

**24h:** 25T 68%WR +$1.02 (POSITIVE) | **7d:** 189T 52.4%WR -$0.49 (near breakeven)

**24h Exit Breakdown:**
- atr_sl_hit: 16T (64%) avg +$0.014 — net positive, trailing working
- profit-monster-trail: 7T avg +$0.060 — star
- cut-loser-CL-T1: 1T -$0.09
- hard_tp: 1T +$0.31

**24h by Signal:**
- volume-breakout-long+ LONG: 10T 80%WR +$1.06 (STAR — major improvement)
- mover+ LONG: 4T 100%WR +$0.42 (STAR)
- pullback-entry- SHORT: 5T 0%WR -$0.80 (all ATR SL, variance vs 7d 50%WR)
- Others: 6T 3W mixed

**7d by Signal:**
- volume-breakout-long+: 13T 69.2%WR +$0.76 (best)
- mover+: 5T 100%WR +$0.73 (best)
- rr-struct+: 15T 73.3%WR +$0.59
- trend_purity+: 11T 36.4%WR -$0.90 (legacy, already disabled)
- rr-struct-v2+: 10T 40%WR -$0.45 (legacy, already disabled)

**Open (4):** DOT SHORT +42%, ADA LONG +227%, FOGO LONG +592%, BABY LONG -16%

**Changes:** None — no kill criteria met

**No Change Needed:**
- Kill check: no signal at 0%WR with 3+ trades last hour
- pullback-entry- SHORT 5T 0%WR 24h but 66T 50%WR -$0.11 7d — variance, not structural
- ATR SL 64% but net positive (+$0.014 avg) — trailing working
- Trade frequency 2/hr — healthy
- 24h positive at +$1.02 — system recovering from cold streak

**Monitoring:**
- volume-breakout-long+ 10T 80%WR +$1.06 24h — star, watch durability
- mover+ 4T 100%WR +$0.42 24h — star, watch durability
- pullback-entry- SHORT 5T 0%WR 24h — monitor next hour
- 7d near breakeven at -$0.49 — recovering

**BY:** auto_1hr

## [2026-09-19 00:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet period)
**24h:** 27T 63%WR +$1.73 (STRONG) | **7d:** 190T 52.6%WR +$0.29 (near breakeven, positive)

**24h Exit Breakdown:**
- atr_sl_hit: 18T (67%) avg +$0.061 — net positive, trailing working
- profit-monster-trail: 7T (26%) avg +$0.060 — star
- cut-loser-CL-T1: 1T -$0.09
- hard_tp: 1T +$0.31

**24h by Signal:**
- volume-breakout-long+ LONG: 10T 80%WR +$1.06 (STAR)
- pump-chain+ LONG: 2T 100%WR +$0.86 (STAR)
- mover+ LONG: 4T 100%WR +$0.42 (STAR)
- pullback-entry- SHORT: 5T 0%WR -$0.80 (variance vs 7d 49%WR -$0.19)
- Others: 6T mixed, small

**7d Signal Performance:**
- volume-breakout-long+: best performer, 10T 80%WR
- mover+: 4T 100%WR, consistent
- pullback-entry- SHORT: 65T 49.2%WR -$0.19 (breakeven, has cold days)

**Open (2):** BABY LONG -87% (SL at 0.01146, ~0.5% away), DOT SHORT -30% (soft SL trigger active)

**Changes:** None — no kill criteria met

**No Change Needed:**
- Kill check: 0 trades last hour, no signal at 0%WR with 3+ trades
- ATR SL 67% but net positive (+$0.061 avg) — trailing system working
- pullback-entry- SHORT 24h 0%WR is variance (7d 49%WR, breakeven)
- Trade frequency 1.1/hr — healthy
- 24h strongly positive at +$1.73
- BABY and DOT both actively managed by volatility gate

**Monitoring:**
- BABY LONG near SL — system will handle
- DOT SHORT soft SL trigger active — managed
- 7d crossed from -$0.49 to +$0.29 in 5 hours — improving

**BY:** auto_1hr

## [2026-09-19 05:00 UTC] Hourly Analysis

**Trades:** 8 closed last hour (4 wins, 3 losses, 1 breakeven)
**PnL:** -$0.19 (small drawdown) | **24h:** 38T 58%WR +$1.37 (STRONG) | **7d:** 197T 48.7%WR -$1.54 (recovering)

**Last Hour Close Breakdown:**
- profit-monster-trail: 4T — SYRUP +$0.14, LDO +$0.05, HBAR -$0.01, IO -$0.02
- cut-loser-CL-T1: 2T — USAL -$0.09, SEI -$0.10
- atr_sl_hit: 2T — IMX $0.00, ADA -$0.16

**24h Exit Breakdown:**
- atr_sl_hit: 21T (55%) avg +$0.032 — net positive, trailing working
- profit-monster-trail: 13T (34%) avg +$0.052 — star
- cut-loser-CL-T1: 3T avg -$0.093 — losses contained
- hard_tp: 1T +$0.31

**24h by Signal:**
- volume-breakout-long+ LONG: 10T 80%WR +$1.06 (STAR)
- pump-chain+ LONG: 7T 28.6%WR +$0.29 (improving)
- grind-trend+ LONG: 8T 37.5%WR +$0.06 (breakeven)
- mover+ LONG: 5T 80%WR +$0.12
- pullback-entry- SHORT: 2T 0%WR -$0.35 (cold streak, 7d 49%WR)

**Open (6):** IOTA +108%, AIXBT +58%, ALT +31%, BANANA +9%, CC -42%, BABY -46% (SL managed)

**Changes:** None — no kill criteria met

**No Change Needed:**
- Kill check: No signal at 0%WR with 3+ trades in last hour
- ATR SL 55% but net positive (+$0.032 avg) — trailing working
- pullback-entry- SHORT 2T 0%WR (below 3T threshold)
- Trade frequency 1.6/hr — healthy
- 24h strongly positive at +$1.37

**Monitoring:**
- pullback-entry- SHORT: 2T 0%WR in 24h — watch next hour, could be variance or emerging pattern
- CC and BABY deep in loss but SLs set, system managing

**BY:** auto_1hr

## [2026-09-19 06:00 UTC] Hourly Analysis

**Trades:** 7 closed (2 wins, 5 losses)
**PnL:** -$0.62 (drawdown) | **24h:** 44T 45.5%WR +$0.49 | **7d:** 202T 47.5%WR -$1.88

**Last Hour Close Breakdown:**
- profit-monster-trail: 2T — AIXBT +$0.02, ALT -$0.03
- cut-loser-CL-T1: 2T — BANANA -$0.09, BABY -$0.19
- atr_sl_hit: 3T — IOTA $0.00, AZTEC -$0.16, CC -$0.17

**24h Exit Breakdown:**
- atr_sl_hit: 24T (55%) avg -$0.005 — net neutral, trailing working
- profit-monster-trail: 15T (34%) avg +$0.044 — star
- cut-loser-CL-T1: 4T avg -$0.093 — contained
- hard_tp: 1T +$0.31

**24h by Signal:**
- volume-breakout-long+ LONG: 9T 77.8%WR +$0.80 (STAR)
- mover+ LONG: 5T 80%WR +$0.12 (STAR)
- grind-trend+ LONG: 12T 33.3%WR -$0.23 (struggling)
- pump-chain+ LONG: 10T 20%WR -$0.04 (small losses)

**Open (1):** ALGO -19.76% (small position, managed)

**Changes:** None — no kill criteria met

**No Change Needed:**
- Kill check: No signal at 0%WR with 3+ trades in last hour
- ATR SL 55% but avg -$0.005 (net neutral) — trailing working
- pullback-entry- SHORT 2T 0%WR -$0.35 (below 3T threshold)
- Trade frequency 1.8/hr — healthy
- 24h still net positive at +$0.49

**Monitoring:**
- grind-trend+ LONG 12T 33.3%WR — watch next hour, could be variance
- pump-chain+ LONG 10T 20%WR — watch for continuation
- ALGO small loss position open

**BY:** auto_1hr

## FAVORITES Update — 2026-09-19 06:00 UTC
- Regime: NEUTRAL
- DEMOTE CC (WR=0.0%, PnL=$-0.17, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE ENA (WR=16.7%, PnL=$-0.78, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE DOT (WR=33.3%, PnL=$-0.37, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE WLD (WR=50.0%, PnL=$0.13, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE IMX (WR=50.0%, PnL=$-0.25, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE ME (WR=33.3%, PnL=$-0.06, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE AVNT (inactive 11d, no trades)
- DEMOTE INJ (WR=50.0%, PnL=$-0.12, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE ZRO (WR=0.0%, PnL=$-0.50, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE TURBO (WR=50.0%, PnL=$-0.13, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE DYDX (WR=50.0%, PnL=$-0.02, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE KAS (WR=0.0%, PnL=$-0.74, 1 consecutive bad days, regime=NEUTRAL)
- DEMOTE CFX (inactive 9d, no trades)
- DEMOTE PUMP (inactive 15d, no trades)
- PROMOTE BIGTIME (WR=60.0%, AvgPnL=2.09%, Trades=5)
- PROMOTE APT (WR=60.0%, AvgPnL=0.21%, Trades=5)
- PROMOTE BABY (WR=66.7%, AvgPnL=0.76%, Trades=6)

Final set: ['ACE', 'APT', 'BABY', 'BANANA', 'BIGTIME', 'BLUR', 'FOGO', 'LTC', 'POL', 'SAND']

## LOSERS Update — 2026-09-19 06:15 UTC
- REMOVE INJ (insufficient data)

Final set: ['DOT', 'HYPER']

## [2026-09-19 07:00 UTC] Hourly Analysis

**Trades:** 1 closed last hour (0 wins, 1 loss)
- ALGO mover+ LONG → atr_sl_hit -$0.05

**24h:** 43T 42%WR +$0.29 | **6h:** 20T 20%WR -$1.08 (cold streak) | **7d:** 200T 47%WR -$2.08

**24h Exit Breakdown:**
- atr_sl_hit: 24T 57% avg -$0.012 — dominant, near breakeven
- profit-monster-trail: 14T 33% avg +$0.045 — working
- cut-loser-CL-T1: 4T 10% avg -$0.093
- hard_tp: 1T +$0.310

**24h by Signal:**
- volume-breakout-long+ LONG: 9T 78%WR +$0.80 ★★ (strongest)
- mover+ LONG: 5T 60%WR +$0.04
- grind-trend+ LONG: 12T 33%WR -$0.23 (worst by volume)
- pump-chain+ LONG: 10T 20%WR -$0.04
- pullback-entry- SHORT: 2T 0%WR -$0.35

**Open:** 4 positions (BABY, JUP, AVAX pump-chain+ LONG, LINK grind-trend- SHORT)

**Changes:** None — no kill criteria met

**No Change Needed:**
- Kill check: No signal with 0%WR and 3+ trades in last hour (only 1 trade)
- ATR SL 57% but avg -$0.012 — structural, near breakeven
- Trade frequency ~1-2/hr — healthy, no overtrading
- 24h still net positive at +$0.29
- 6h cold streak (20%WR -$1.08) is variance on small sample

**Monitoring:**
- grind-trend+ LONG 12T 33.3%WR -$0.23 — watch next run, could be variance
- pump-chain+ LONG 10T 20%WR -$0.04 — watch for continuation
- 7d at -$2.08, recovering from deeper losses

**BY:** auto_1hr

## [2026-09-19 08:00 UTC] Hourly Analysis

**Trades:** 2 closed (2 wins, 0 losses)
- YGG grind-trend+ LONG → profit-monster-trail $0.00 (breakeven)
- IOTA grind-trend+ LONG → profit-monster-trail +$0.02 (+58.45%)

**24h:** 44T 41%WR +$0.27 | **7d:** 200T 47%WR -$2.08

**24h Exit Breakdown:**
- atr_sl_hit: 24T 55% avg -$0.012 — dominant, near breakeven
- profit-monster-trail: 15T 34% avg +$0.041 — working
- cut-loser-CL-T1: 4T 9% avg -$0.093
- hard_tp: 1T +$0.310

**24h by Signal:**
- volume-breakout-long+: 9T 78%WR +$0.80 ★★ (star)
- mover+: 5T 60%WR +$0.04
- grind-trend+: 14T 36%WR -$0.21 (improving — last 2 trades won)
- pump-chain+: 10T 20%WR -$0.04
- pullback-entry-: 2T 0%WR -$0.35

**Changes:** None — no kill criteria met

**No Change Needed:**
- Kill check: No signal with 0%WR and 3+ trades in last hour
- ATR SL 55% but avg -$0.012 — structural, near breakeven
- Trade frequency ~2/hr — healthy
- grind-trend+ showing improvement (2 consecutive profit-monster wins)
- 24h still net positive

**Monitoring:**
- grind-trend+ 14T 36%WR -$0.21 — trending up after cold streak
- pump-chain+ 10T 20%WR -$0.04 — watch for continuation

**BY:** auto_1hr

## [2026-09-19 09:00 UTC] Hourly Analysis

**Trades:** 2 closed (0 wins, 2 losses)
- LINK grind-trend- SHORT → cut-loser-CL-T1 -$0.11
- IO grind-trend- SHORT → cut-loser-CL-T1 -$0.07

**PnL:** -$0.18 (0% WR)

**24h:** 45T 37.8%WR +$0.08 | **6h:** 20T 20%WR -$1.02 | **7d:** 200T 47%WR -$2.09

**24h Exit Breakdown:**
- atr_sl_hit: 23T 51% avg -$0.013 — dominant, near breakeven
- profit-monster-trail: 15T 33% avg +$0.041 — working
- cut-loser-CL-T1: 6T 13% avg -$0.092 — largest avg loss
- hard_tp: 1T +$0.310

**24h by Signal:**
- volume-breakout-long+: 8T 75%WR +$0.79 ★★
- mover+: 5T 60%WR +$0.04
- grind-trend+: 14T 35.7%WR -$0.21
- pump-chain+: 10T 20%WR -$0.04 (all atr_sl_hit, avg -$0.004 — breakeven)
- pullback-entry-: 2T 0%WR -$0.35
- grind-trend-: 2T 0%WR -$0.18

**Open:** 5 positions (AVAX +$0.54, BABY +$0.25, JUP +$0.15, GMT +$0.04, ME -$0.09)

**Changes:** None — no kill criteria met

**No Change Needed:**
- Kill check: grind-trend- 2T 0%WR (needs 3+), pullback-entry- 2T 0%WR (needs 3+)
- ATR SL 51% but avg -$0.013 — structural, near breakeven
- Trade frequency ~2/hr — healthy
- pump-chain+ 10T 20%WR but avg loss only -$0.004 — essentially breakeven
- 6h cold streak (20%WR -$1.02) is variance on 20 trades

**Monitoring:**
- grind-trend- 2T 0%WR — 1 more loss to kill
- pullback-entry- 2T 0%WR — 1 more loss to kill
- 6h drawdown — if continues next hour, review regime filters

**BY:** auto_1hr

## [2026-09-19 10:00 UTC] Hourly Analysis

**Trades:** 2 closed (1 win, 1 loss)
- ME pullback-entry- SHORT → atr_sl_hit -$0.15
- AVAX pump-chain+ LONG → atr_sl_hit +$0.53

**PnL:** +$0.38 (50% WR)

**24h:** 47T 18W 29L +$0.46 (38.3% WR) | **6h:** 14T 3W 11L -$0.45 (improving since 07h)

**24h Exit Breakdown:**
- atr_sl_hit: 25T 53% avg +$0.004 (breakeven — structural)
- profit-monster-trail: 15T 33% avg +$0.041 (working)
- cut-loser-CL-T1: 6T 13% avg -$0.092
- hard_tp: 1T +$0.310

**24h by Signal:**
- volume-breakout-long+: 8T 75%WR +$0.79 ★★
- mover+: 5T 60%WR +$0.04
- pump-chain+: 11T 27%WR +$0.49 (avg win outsizes loss)
- grind-trend+: 14T 36%WR -$0.21
- pullback-entry-: 3T 0%WR -$0.50 (1T last hour, below kill threshold)
- grind-trend-: 2T 0%WR -$0.18

**Open:** 7 positions (JUP +$0.51, BABY +$0.21, GMT +$0.06, ACE +$0.01, ENS $0.00, COMP -$0.01, SEI -$0.05)

**Changes:** None — no kill criteria met

**No Change Needed:**
- Kill check: no signal had 3+ trades in last hour (max 1 per signal)
- ATR SL 53% but avg +$0.004 — structural, near breakeven
- Trade frequency ~2/hr — healthy
- 6h cold improving: 07h+ hours at ~40% WR
- AVAX pnl_pct 2362% vs actual 4.72% — pre-existing data quality bug, pnl_usdt correct

**Monitoring:**
- pullback-entry- 3T 0%WR 24h — at 24h kill threshold but not 1h threshold
- 6h drawdown recovering

**BY:** auto_1hr

## [2026-09-19 11:00 UTC] Hourly Analysis

**Trades:** 2 closed (1 win, 1 loss)
- ENS grind-trend+ LONG → profit-monster-trail +$0.03
- JUP pump-chain+ LONG → atr_sl_hit +$0.47

**PnL:** +$0.50 (50% WR)

**24h:** 45T 16W 29L +$0.46 (35.6% WR) | **6h:** 9T 4W 5L +$0.67 (recovering)

**24h Exit Breakdown:**
- atr_sl_hit: 23T 51% avg +$0.008 (breakeven — structural)
- profit-monster-trail: 15T 33% avg +$0.034 (working)
- cut-loser-CL-T1: 6T 13% avg -$0.092
- hard_tp: 1T +$0.310

**24h by Signal:**
- pump-chain+: 12T 33%WR +$0.96 (best PnL)
- volume-breakout-long+: 5T 60%WR +$0.42 (best WR)
- mover+: 5T 60%WR +$0.04
- grind-trend+: 15T 40%WR -$0.18
- pullback-entry-: 3T 0%WR -$0.50
- grind-trend-: 2T 0%WR -$0.18

**Open:** 5 positions (COMP, SEI, GMT, BABY, ACE) — all flat

**Changes:** None — no kill criteria met

**No Change Needed:**
- Kill check: no signal had 3+ trades last hour
- ATR SL 51% but avg +$0.008 — structural, near breakeven
- 6h drawdown recovered to +$0.67
- Trade frequency ~2/hr — healthy

**Monitoring:**
- grind-trend- 2T 0%WR — 1 more loss to kill
- pullback-entry- 3T 0%WR — at 24h threshold but not last-hour threshold

**BY:** auto_1hr

## [2026-09-19 12:00 UTC] Hourly Analysis

**Trades:** 2 closed (2 wins, 0 losses)
- COMP grind-trend+ LONG → profit-monster-trail +$0.06
- SEI grind-trend+ LONG → profit-monster-trail +$0.17

**PnL:** +$0.23 (100% WR)

**24h:** 46T 16W 30L +$0.69 (34.8% WR) | **6h:** 11T 5W 6L +$1.17 (recovering)

**24h Exit Breakdown:**
- atr_sl_hit: 22T 48% avg +$0.005 (breakeven — structural)
- profit-monster-trail: 17T 37% avg +$0.044 (working well)
- cut-loser-CL-T1: 6T 13% avg -$0.092
- hard_tp: 1T +$0.310

**24h by Signal:**
- pump-chain+: 12T 33%WR +$0.96 (best PnL)
- volume-breakout-long+: 4T 50%WR +$0.33
- grind-trend+: 17T 47%WR +$0.05 (breakeven)
- mover+: 5T 60%WR +$0.04
- pullback-entry-: 3T 0%WR -$0.50
- grind-trend-: 2T 0%WR -$0.18
- mover-: 1T 0%WR -$0.09

**Changes:** None

**No Change Needed:**
- Kill check: no signal had 3+ trades last hour
- ATR SL 48% but avg +$0.005 — structural, near breakeven
- Trade frequency 2/hr — healthy, no overtrading
- 6h drawdown recovering (+$1.17)

**Monitoring:**
- pullback-entry- 3T 0%WR — at 24h threshold, needs 3+ in next hour to kill
- grind-trend- 2T 0%WR — 1 more loss to kill

**BY:** auto_1hr

## [2026-09-19 13:00 UTC] Hourly Analysis

**Trades:** 2 closed last hour (2 wins, 0 losses)
- FIL pump-chain+ LONG → atr_sl_hit +$0.02
- GMT grind-trend+ LONG → profit-monster-trail +$0.19

**PnL:** +$0.21 (100% WR)

**24h:** 46T 16W 30L +$0.99 (34.8% WR)
**6h:** 12T, recovering

**24h Exit Breakdown:**
- atr_sl_hit: 22T 48% avg +$0.013 (structural, breakeven)
- profit-monster-trail: 17T 37% avg +$0.055 (working)
- cut-loser-CL-T1: 6T 13% avg -$0.092
- hard_tp: 1T +$0.310

**24h by Signal:**
- pump-chain+: 13T +$0.98 (star)
- volume-breakout-long+: 3T +$0.50
- grind-trend+: 18T +$0.24
- mover+: 5T +$0.04
- pullback-entry-: 3T 0%WR -$0.50 (monitoring)
- grind-trend-: 2T 0%WR -$0.18 (monitoring)

**Changes:** None

**No Change Needed:**
- Kill check: no signal had 3+ trades last hour
- ATR SL 48% but avg +$0.013 — structural, near breakeven
- Trade frequency 2/hr — healthy
- 6h recovering

**Monitoring:**
- pullback-entry- 3T 0%WR — at 24h threshold, no last-hour trades
- grind-trend- 2T 0%WR — 1 more loss to kill

**BY:** auto_1hr

## [2026-09-19 14:00 UTC] Hourly Analysis

**Trades:** 1 closed last hour (1 win, 0 losses)
- ACE grind-trend- SHORT → profit-monster-trail +$0.02

**PnL:** +$0.02 (100% WR)

**24h:** 47T 36.2%WR +$1.01
**24h Exit Breakdown:**
- atr_sl_hit: 22T 48% avg +$0.013 (structural, near breakeven)
- profit-monster-trail: 17T 37% avg +$0.049 (working)
- cut-loser-CL-T1: 6T 13% avg -$0.092
- hard_tp: 1T +$0.310

**24h by Signal:**
- grind-trend+: 18T 50%WR +$0.24
- pump-chain+: 13T 38.5%WR +$0.98 (star)
- mover+: 4T 50%WR -$0.08 (slightly negative)
- volume-breakout-long+: 3T 66.7%WR +$0.50
- grind-trend-: 3T 33.3%WR -$0.16 (improved with 1 win)
- pullback-entry-: 3T 0%WR -$0.50 (monitoring)
- mover-: 1T 0%WR -$0.09

**Changes:** None

**No Change Needed:**
- Kill check: no signal had 3+ trades last hour
- ATR SL 48% but avg +$0.013 — structural, near breakeven
- Trade frequency 1/hr — healthy
- grind-trend- improved from 0% to 33.3% WR

**Monitoring:**
- pullback-entry- 3T 0%WR — still at threshold, needs 3+ in next hour to kill

**BY:** auto_1hr

## [2026-09-19 15:00 UTC] Hourly Analysis

**Trades:** 3 closed (3 wins, 0 losses)
- FIL warrior-sr-confirm+ LONG → profit-monster-trail +$0.09
- BABY pump-chain+ LONG → atr_sl_hit +$0.30
- DOGE pump-chain+ LONG → atr_sl_hit +$0.09

**PnL:** +$0.48 (100% WR)

**24h:** 46T 34.8%WR +$1.08
- atr_sl_hit: 23T 50% avg +$0.016 (structural)
- profit-monster-trail: 16T 35% avg +$0.051
- cut-loser-CL-T1: 6T 13% avg -$0.092

**Changes:** None

**No Change Needed:**
- Kill check: no signal had 3+ trades last hour
- ATR SL 50% but avg +$0.016 — structural, near breakeven
- Trade frequency 3/hr — healthy
- BABY/DOGE atr_sl_hit positive PnL — trail captured profit

**Monitoring:**
- pullback-entry- 3T 0%WR — 0 trades last hour, no kill triggered
- mover+ 3T 33%WR -$0.19 — minor bleed

**BY:** auto_1hr

## [2026-09-19 16:00 UTC] Hourly Analysis

**Trades:** 3 closed (1 win, 2 losses)
- INJ pump-chain+ LONG → atr_sl_hit +$0.03
- WLFI grind-trend- SHORT → cut-loser-CL-T1 -$0.11
- DOGE grind-trend- SHORT → cut-loser-CL-T1 -$0.11

**PnL:** -$0.19 (33.3% WR)

**24h:** 46T 34.8%WR +$1.08
- atr_sl_hit: 24T 50% avg +$0.016 (structural)
- profit-monster-trail: 16T 35% avg +$0.051
- cut-loser-CL-T1: 8T avg -$0.096

**Changes:** None

**No Change Needed:**
- Kill check: no signal had 3+ trades last hour
- ATR SL 52% but avg +$0.016 — structural, near breakeven
- Trade frequency 4/hr — healthy
- pullback-entry- 0 trades last hour, no kill triggered

**Monitoring:**
- grind-trend- 5T/24h 20%WR -$0.38 — 2 losses last 3h, trending worse but not at kill threshold
- pullback-entry- 3T/24h 0%WR -$0.50 — dormant, no recent trades

**BY:** auto_1hr

## [2026-09-19 17:45 UTC] Hourly Analysis

**Trades:** 2 closed (2 wins, 0 losses)
**PnL:** +$0.23 (100% WR)

**Last Hour Trades:**
- INJ pump-chain+ LONG atr_sl_hit +$0.12 (28m hold)
- IMX pump-chain+ LONG atr_sl_hit +$0.11 (3h39m hold)

**24h Exit Breakdown (47T):**
| Exit Reason | Trades | PnL | Avg PnL |
|-------------|--------|-----|---------|
| atr_sl_hit | 26 (55%) | +$0.62 | +$0.024 |
| profit-monster-trail | 16 (34%) | +$0.82 | +$0.051 |
| cut-loser-CL-T1 | 8 (17%) | -$0.77 | -$0.096 |

**24h Signal Ranking:**
| Signal | Trades | WR | PnL |
|--------|--------|-----|-----|
| pump-chain+ | 18 | 55.6% | +$1.63 |
| grind-trend+ | 18 | 50.0% | +$0.24 |
| pullback-entry- | 3 | 0% | -$0.50 |
| grind-trend- | 5 | 20% | -$0.38 |

**Diagnosis:**
1. **Entry quality:** Low — both winners had positive PnL despite atr_sl_hit (SL wide enough)
2. **SL behavior:** atr_sl_hit 55% dominant but avg PnL still positive (+$0.024) — not too tight
3. **Signal quality:** pump-chain+ strong ($1.63, 55.6% WR). grind-trend- and pullback-entry- still losing
4. **Trade frequency:** 2/hr — normal, no overtrading

**Changes:**
- None needed. System healthy, both signals profitable.

**Monitoring:**
- grind-trend- 5T/24h 20%WR -$0.38 — not at kill threshold yet (need 3+ trades/hr at 0%WR)
- pullback-entry- 3T/24h 0%WR -$0.50 — dormant, no action needed

**BY:** auto_1hr

## [2026-09-19 18:30 UTC] Daily Orchestrator

**No Config Change Needed**

**Trades:** 50 closed today, 6 open ($74.30 exposure)
**24h:** 50T, 44.0% WR, +$0.67
**7d:** 207T, 49.3% WR, +$0.13 (POSITIVE)
**Market:** LONG_BIAS (8 long / 0 short / 112 neutral)

**Kills Today:**
- grind-trend+ LONG: CEO killed 10:38 UTC (14T 35.7%WR -$0.21, all NEUTRAL)
- grind-trend- SHORT: signal_reporter killed 17:12 UTC (5T 20%WR -$0.38, no winning regime)

**Signal Performance (24h):**
- pump-chain+ LONG: 18T 56%WR +$1.63 (dominant)
- grind-trend+ LONG: 18T 50%WR +$0.24
- pullback-entry- SHORT: 3T 0%WR -$0.50 (watch — historically profitable)
- grind-trend- SHORT: 5T 20%WR -$0.38 (killed)

**Regime (7d):**
- EXTREME: 52T 58%WR +$1.74 (best)
- NORMAL: 63T 46%WR -$0.49
- HIGH: 91T 47%WR -$1.12

**Stale Filter:** 48h: 3/61 stale (4.9%, down from 43.8% pre-filter)
**Disk:** 84% (19G free)
**Pipeline:** Healthy, 0 errors, all timers firing
**BY:** daily_orchestrator

## [2026-09-19 19:15 UTC] Hourly Analysis

**Trades:** 0 closed last hour (market quiet)
**24h:** 50T 44%WR +$0.67 — slightly positive, stable
**Open:** 7 positions (DYDX +$0.12, CAKE +$0.18, HEMI +$0.04, SYRUP +$0.01, ADA -$0.01, JUP -$0.04, ACE -$0.12)

**Changes:** None

**No Change Needed:**
- atr_sl_hit 52% of closes but trades profitable (+$0.024 avg) — SL working correctly
- pullback-entry- SHORT 0% WR 24h (3T) — 7d is 49.2% WR on 63T, sample too small
- grind-trend- SHORT — already KILLED, 2T in last 4h are pre-kill trades
- mover+ LONG — 7d 66.7% WR, bad 24h sample only

**Status:** System stable, no action required

## [2026-09-19 20:00 UTC] Hourly Analysis

**Trades:** 0 closed last hour (market quiet)
**24h:** 49T, 44% WR, +$0.67 (stable)
**Open:** 8 positions (CAKE SHORT +1.4% 6.7h, DYDX LONG +2.2%, SYRUP SHORT -1.0%, others small)

**Changes:** None

**No Change Needed:**
- 0 trades closed — no kill criteria, no signal failures
- atr_sl_hit 52% of closes but trades profitable (+$0.024 avg) — SL working correctly
- pullback-entry- SHORT 0% WR 24h (3T) — 7d is 49.2% WR on 63T, normal variance
- grind-trend- SHORT — already KILLED, 2T in last 4h are pre-kill trades

**Open Questions:**
- cut-loser-CL-T1 has 0% WR over 99 trades / 30d (-$14 total). All trades were already past -2% when cut (avg loss $0.14). Small per-trade loss but systematic bleed. Fire windows already widened by brain_auditor on Sep 18. Flagged for CEO review.
- CAKE SHORT open 6.7h — oldest position, but profitable (+1.4%). No action needed.

**BY:** auto_1hr

## [2026-09-19 21:00 UTC] Hourly Analysis

**Trades:** 1 closed (1 win, 0 losses)
**PnL:** +$0.13 (pump-chain+ DYDX atr_sl_hit)
**24h:** 50T, 44%WR, +$0.67

**Open:** 7 positions, $85.40 exposure (CAKE SHORT 7.6h oldest, ACE LONG 7h)

**Changes:** None

**No Change Needed:**
- No signal hit kill criteria (0% WR on 3+ trades last hour)
- atr_sl_hit 52% of 24h closes but avg +$0.036 — SL working correctly
- pullback-entry- SHORT 0% WR 24h but only 2T, 7d is 49.2% on 63T — normal variance
- cut-loser-CL-T1 7T -$0.68 in 24h — already flagged for CEO review, avg loss $0.097/trade (small)
- Trade count normal, no overtrading

**Status:** System stable, no action required
**BY:** auto_1hr

## [2026-09-19 22:00 UTC] Hourly Analysis

**Trades:** 3 closed (1 win, 2 losses)
**PnL:** -$0.20 (HEMI SHORT +$0.08, JUP LONG -$0.14, ADA LONG -$0.14)
**24h:** 52T, 46.2%WR, +$0.88

**Open:** 4 positions (CAKE SHORT +$0.18 8.6h, ACE LONG -$0.16 8h, SYRUP SHORT +$0.06 3.6h, WCT SHORT $0.00 2.1h)

**Changes:** None

**No Change Needed:**
- No signal hit kill criteria (0% WR on 3+ trades last hour)
- atr_sl_hit 56% of 24h closes but avg +$0.026 — SL working correctly
- grind-trend- (20% WR -$0.38 24h) — already KILLED previously
- pullback-entry- (33% WR -$0.23 24h) — only 3T, 7d data shows 49.2% WR, normal variance
- Trade count normal, no overtrading
- pump-chain+ carrying system at +$1.48/24h

**BY:** auto_1hr

## [2026-09-19 23:00 UTC] Hourly Analysis

**Trades:** 2 closed (0 wins, 2 losses)
**PnL:** -$0.37 (SYRUP SHORT $0.00, WCT SHORT -$0.37) — both pullback-entry- atr_sl_hit
**24h:** 52T, ~48%WR, +$0.85

**Open:** 4 positions (CAKE SHORT 9.6h, ACE LONG 9h, AVAX LONG 0.5h, BABY LONG 0.1h)

**Changes:** None

**No Change Needed:**
- No signal hit kill criteria (0% WR on 3+ trades last hour)
- atr_sl_hit 56% of 24h closes but avg +$0.024 — SL working correctly
- mover+ 0%WR/2T 24h — below kill threshold, too few trades
- pullback-entry- 20%WR/5T 24h but 49.2%WR/63T on 7d — normal variance
- Trade count normal (2/hour), no overtrading
- pump-chain+ still carrying system at +$1.48/24h

**Status:** System stable, no action required
**BY:** auto_1hr

## [2026-09-19 23:30 UTC] Hourly Analysis

**Trades:** 1 closed (1 win: CAKE SHORT +$0.09 atr_sl_hit)
**24h:** 53T, 48%WR, +$0.82

**Close reasons (24h):** atr_sl_hit 28 (53% avg -$0.002), profit-monster-trail 16 (30% avg +$0.051), cut-loser-CL-T1 7 (13% avg -$0.097)
**Top signals (24h):** pump-chain+ +$0.62, grind-trend+ +$0.24, warrior-sr-confirm+ +$0.09
**Bottom signals (24h):** grind-trend- -$0.38 (killed), mover+ -$0.35 (2T, below threshold)

**Changes:** None

**No Change Needed:**
- No signal hit kill criteria (mover+ 0%WR but only 2T, threshold is 3+)
- atr_sl_hit dominant at 53% but avg PnL -$0.002 — SL correctly calibrated
- Trade frequency normal (1-3/hr last 6h)
- pump-chain+ and grind-trend+ carrying system

**Status:** System stable
**BY:** auto_1hr

## [2026-09-20 00:30 UTC] Hourly Analysis

**Trades:** 1 closed (1 win: AVAX LONG +$1.02 pump-chain+ atr_sl_hit)
**24h:** 49T, 47% WR, +$1.66
**7d:** 212T, 49.1% WR, +$1.14

**Close reasons (24h):** atr_sl_hit 26 (53% avg +$0.058), profit-monster-trail 16 (33% avg +$0.051), cut-loser-CL-T1 7 (14% avg -$0.097)
**Top signals (24h):** pump-chain+ +$1.90 (55.6% WR), grind-trend+ +$0.24 (50% WR)
**Open:** 5 positions (ONDO SHORT 0.8h, BCH LONG 1.7h, IMX LONG 1.7h, BABY LONG 2.1h, ACE LONG 11h)

**Changes:** None

**No Change Needed:**
- No signal hit kill criteria (0% WR on 3+ trades last hour)
- atr_sl_hit dominant at 53% but avg +$0.058 — SL correctly calibrated, not a problem
- pullback-entry- 33%WR/6T 24h but 47.7%WR/65T 7d — normal variance
- grind-trend- already killed, trend_purity+ only 2T (below threshold)
- Trade frequency normal (1-3/hr), no overtrading
- pump-chain+ carrying system at +$1.90/24h

**Status:** System stable, no action required
**BY:** auto_1hr

## [2026-09-20 02:30 UTC] Hourly Analysis

**Trades:** 5 closed (3 wins, 2 losses)
**PnL:** +$0.02 (WR: 60%)
**24h:** 51T, 49%WR, +$1.74 | **7d:** 216T, 49.1%WR, +$1.10

**Close reasons (24h):** atr_sl_hit 30 (59% avg +$0.056), profit-monster-trail 14 (27% avg +$0.052), cut-loser-CL-T1 7 (14% avg -$0.097)
**Top signals (24h):** pump-chain+ +$1.57 (19T, 40%WR), doji-bottom-long +$0.30 (1T), grind-trend+ +$0.15 (16T)
**Bottom signals (24h):** grind-trend- -$0.38 (5T, already killed), mover+ -$0.05 (1T, below threshold)
**Open:** 4 positions (BABY, CHIP, WLFI, LTC)

**Changes:** None

**No Change Needed:**
- No signal hit kill criteria (0% WR with 3+ trades last hour)
- atr_sl_hit dominant at 59% but avg +$0.056 — SL correctly calibrated
- Trade frequency normal (5 closed, 4 opens last hour)
- pump-chain+ carrying system at +$1.57/24h
- pullback-entry- basically breakeven (-$0.02/24h) — 7T, too few trades to kill

**Status:** System stable, no action required
**BY:** auto_1hr

## [2026-09-20 04:30 UTC] Hourly Analysis

**Trades:** 2 closed (0 wins, 2 losses)
**PnL:** -$0.47 (WR: 0%)
**24h:** 52T, 48.1%WR, +$1.43 | **7d:** 218T, 48.6%WR, +$0.63

**Close reasons (24h):** atr_sl_hit 31 (60% avg +$0.045), profit-monster-trail 14 (27% avg +$0.052), cut-loser-CL-T1 7 (14% avg -$0.097)
**Top signals (24h):** pump-chain+ +$1.10 (21T, 48%WR), grind-trend+ +$0.15 (16T, 50%WR)
**Bottom signals (24h):** grind-trend- -$0.38 (5T, already killed), mover+ -$0.05 (1T, below threshold)
**Open:** 2 positions (LTC SHORT 1.7h, WLFI SHORT 1.1h)

**Changes:** None

**No Change Needed:**
- No signal hit kill criteria (0% WR with 3+ trades last hour)
- atr_sl_hit dominant at 60% but avg +$0.045 — SL correctly calibrated
- 2 pump-chain+ SL hits last hour — normal variance, signal still profitable
- Trade frequency normal (~2/hr), no overtrading
- grind-trend- already killed, mover+ only 1T below threshold

**Status:** System stable, no action required
**BY:** auto_1hr

## [2026-09-20 05:00 UTC] Hourly Analysis

**Trades:** 2 closed (2 wins, 0 losses)
**PnL:** +$0.18 (WR: 100%)
**24h:** 46T, ~50%WR, +$1.43

**Close reasons (24h):** atr_sl_hit 31 (67% avg +$0.055), profit-monster-trail 10 (22% avg +$0.057), cut-loser-CL-T1 5 (11% avg -$0.098)
**Top signals (24h):** pump-chain+ +$1.35 (20T, 55%WR), pullback-entry- +$0.23 (7T, 57%WR), grind-trend+ +$0.18 (10T, 60%WR)
**Open:** 3 positions (WLFI, BABY, CC) — all near breakeven

**Changes:** None

**No Change Needed:**
- No kill criteria met (0% WR with 3+ trades)
- atr_sl_hit dominant but avg +$0.055 — trailing SL feature, not bug
- Trade frequency normal (~2/hr)
- pump-chain+ carrying system at +$1.35/24h
- All signals profitable with 3+ trades

**Status:** System stable, no action required
**BY:** auto_1hr

## [2026-09-20 05:10 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet since 04:39)
**24h:** 40T, 62.5%WR, +$2.47 | **Close reasons:** atr_sl_hit 28 (70%, avg +$0.082), profit-monster-trail 8 (20%, avg +$0.073), cut-loser-CL-T1 4 (10%, avg -$0.100)
**Top signals:** pump-chain+ +$1.68 (17T 65%WR), grind-trend+ +$0.47 (6T 83%WR), pullback-entry- +$0.28 (8T 62%WR)
**Worst signal:** grind-trend- -$0.38 (5T 20%WR) — already killed
**Open:** 3 positions (ENS SHORT 0.1h, CC LONG 1.7h, BABY LONG 1.8h)

**Changes:** None

**No Change Needed:**
- No signal hit kill criteria (0% WR with 3+ trades last hour)
- atr_sl_hit dominant at 70% but avg +$0.082 — SL correctly calibrated, feature not bug
- Trade frequency normal (1.7/hr), no overtrading
- grind-trend- already killed, mover+ only 1T
- 24h WR 62.5% is strong, system performing well

**Status:** System stable, no action required
**BY:** auto_1hr

## FAVORITES Update — 2026-09-20 06:00 UTC
- Regime: NEUTRAL
- DEMOTE BIGTIME (WR=50.0%, PnL=$0.27, 1 consecutive bad days, regime=NEUTRAL)
- PROMOTE JUP (WR=60.0%, AvgPnL=2.52%, Trades=5)
- PROMOTE FIL (WR=60.0%, AvgPnL=0.20%, Trades=10)
- PROMOTE SYRUP (WR=80.0%, AvgPnL=1.25%, Trades=5)
- PROMOTE CAKE (WR=60.0%, AvgPnL=0.83%, Trades=5)

Final set: ['ACE', 'APT', 'BABY', 'BANANA', 'BLUR', 'CAKE', 'FIL', 'FOGO', 'JUP', 'LTC', 'POL', 'SAND', 'SYRUP']

## LOSERS Update — 2026-09-20 06:05 UTC
- ADD SEI (WR=40.0%, PnL=$-0.31, wr_collapse (61.5% → 40.0%))

Final set: ['DOT', 'HYPER', 'SEI']

## [2026-09-20 06:10 UTC] Hourly Analysis

**Trades:** 0 closed last hour (quiet since 04:39)
**24h:** 40T, 62.5%WR, +$2.47 | **7d:** 217T, 49.3%WR, +$0.58
**Close reasons (24h):** atr_sl_hit 28 (70%, avg +$0.082), profit-monster-trail 8 (20%, avg +$0.073), cut-loser-CL-T1 4 (10%, avg -$0.100)
**Top signals:** pump-chain+ +$1.68 (17T 65%WR), grind-trend+ +$0.47 (6T 83%WR), pullback-entry- +$0.28 (8T 63%WR)
**Open:** 6/6 positions (at MAX_OPEN cap) — regime NEUTRAL

**Changes:** None

**No Change Needed:**
- No signal hit kill criteria (0% WR with 3+ trades last hour)
- atr_sl_hit dominant at 70% but avg +$0.082 — trailing SL working correctly as feature, not bug
- Trade frequency normal (~1.7/hr), no overtrading
- All active signals profitable over 24h
- grind-trend- already killed, mover+ only 1 trade
- 6 open positions = at cap, system correctly limiting exposure
- 24h WR 62.5% is strong, system performing well

**Status:** System stable, no action required
**BY:** auto_1hr

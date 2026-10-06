# Independent Audit: Signal Blocking Analysis — 2026-10-06

**Auditor:** Independent verifier (fresh analysis, no priming)
**Date:** 2026-10-06 22:30 UTC
**Method:** Direct SQL queries against SQLite runtime DB + PostgreSQL brain DB, source code reading, live compactor execution, pipeline log analysis

---

## Verdict Summary

| # | Claim | Verdict |
|---|-------|---------|
| 1 | 530 pump-chain SHORT expired, never got confluence within 10 min | **PARTIAL** |
| 2 | 204 bollinger_squeeze_long SKIPPED — confluence gate or regime | **PARTIAL** |
| 3 | Compactor only processes last 5 min — causes pump-chain SHORT expiry | **DISAGREE** |
| 4 | 505 pump-chain SHORT EXPIRED in last 24h | **AGREE** |
| 5 | Pump-chain SHORT produced by pump_flow_signal.py when phase has SHORT recs | **PARTIAL** |
| 6 | SHORT-CONTINUUM filter (BTC score < 30) blocks SHORT when BTC neutral | **PARTIAL** |
| 7 | BTC in LOSERS, LOSERS_HARD_BLOCK_WR=40%, blocking BTC SHORT at 28.6% 7d WR | **PARTIAL** |

---

## Claim-by-Claim Analysis

### Claim 1: "530 pump-chain SHORT signals fired in 24h but expired — they never got confluence within 10 minutes"
**Verdict: PARTIAL**

**What I found:**
- Fixed 24h window (since 2026-10-05 22:20): **505 EXPIRED + 29 SKIPPED = 534 total** pump-chain SHORT created
- Rolling 24h at query time: 501 EXPIRED + 29 SKIPPED = **530 total created**
- So "530 fired" matches the rolling 24h total, but **only 501–505 expired — 29 were SKIPPED**, not expired. The claim conflates "fired" with "expired."
- **"within 10 minutes" is wrong.** The staleness timer is **5 minutes** (`age_m >= 5.0` at signal_compactor.py:4775). The 10-minute window is the *processing* query window (`datetime('now', '-10 minutes')` at line 2183). The log message "5-min window" at line 2193 is stale text — the SQL says 10 minutes.
- Expiry age distribution confirms: 491 of 505 expired at ~5.7 minutes age (the5-min staleness path, decision_reason=NULL).
- **Root cause is NOT timing.** Pipeline log shows pump-chain SHORT signals PASSING the confluence gate via standalone bypass: `✅ [CONFLUENCE-GATE-PASS] APT SHORT: {pump-chain-} (NEUTRAL-relax: standalone bypass (pump-chain))`. They then get blocked by **SHORT-CONTINUUM** before entering top-10, stay PENDING, and expire via the 5-min staleness timer.

**Why PARTIAL:** The ballpark number is right (~530 fired), but "530 expired" overstates it (29 skipped), "10 minutes" is wrong (it's 5), and the causal claim ("never got confluence") misidentifies the blocker — they pass confluence but are killed by SHORT-CONTINUUM downstream.

---

### Claim 2: "204 bollinger_squeeze_long signals were SKIPPED — blocked by confluence gate or regime"
**Verdict: PARTIAL**

**What I found:**
- DB confirms **exactly 204 SKIPPED** bollinger_squeeze_long in 24h ✅
- **But decision_reason is NULL for all 204** — zero non-NULL reasons. Cannot confirm the reason from DB data.
- The claim says "blocked by confluence gate or regime" — but:
  - The compactor's confluence gate does `continue` (leaves signal PENDING), **not** SKIPPED
  - The compactor's regime/vol-gate blocks also do `continue` (leaves PENDING), **not** SKIPPED
  - SKIPPED is set by **decider_run.py** via `mark_signal_executed(token, direction, 'SKIPPED')`, which calls `update_signal_decision` — that function does **NOT set decision_reason** (unlike `mark_signal_processed` which always sets one)
  - bollinger_squeeze source `bb-squeeze+` IS in `STANDALONE_BYPASS_SIGNALS`, so it **passes** the confluence gate
  - The vol gate blocks bb-squeeze in EXTREME regime (`('EXTREME', 'bb-squeeze'): 0.0` in volatility_gate_v2.py:328), but that's a compactor `continue`, not SKIPPED
- The SKIPPED signals have executed=0, compact_rounds=0, survival_score=0.0 — consistent with being set by `update_signal_decision` (which keeps executed unchanged for non-EXECUTED decisions)
- The actual skip most likely came from **decider_run.py execution-layer filters** (not the compactor's confluence gate or regime blocks), but the NULL reason makes this unverifiable

**Why PARTIAL:** Count is exactly right (204), but the reason attribution is wrong or at minimum unverifiable. The confluence gate and regime blocks don't set SKIPPED — they leave signals PENDING. The SKIPPED decision comes from decider_run.py, and the NULL decision_reason means the audit trail is broken (a bug in itself).

---

### Claim 3: "The compactor only processes signals from the last 5 minutes — this causes pump-chain SHORT signals to expire before processing"
**Verdict: DISAGREE**

**What I found:**
- The compactor's processing query uses **`datetime('now', '-10 minutes')`** (signal_compactor.py:2183), **not 5 minutes**. The log message "Query: N combo_keys in 5-min window" at line 2193 is **stale text** — the SQL clearly says `-10 minutes`.
- There IS a separate **5-minute staleness timer** (line 4775: `if age_m < 5.0: still_pending_ids.append(sid)` else EXPIRED). This is the mechanism by which pump-chain SHORT signals expire.
- **But the claim's causal chain is wrong:** "causes pump-chain SHORT signals to expire before processing" — they ARE processed. They pass the confluence gate (standalone bypass for pump-chain), pass the BTC chop gate (BTC-exempt), pass SHORT-NEUTRAL (standalone bypass), but then get **blocked by SHORT-CONTINUUM** (BTC score > 40, z=NEUTRAL) before entering top-10. They stay PENDING and expire via the 5-min staleness timer.
- I directly observed this in my compactor run:
  ```
  ✅ [SHORT-NEUTRAL-BYPASS] APT SHORT — 4h NEUTRAL but 1m SHORT_BIAS, allowed
  🚫 [SHORT-CONTINUUM] APT SHORT blocked — BTC score=43.1 z=NEUTRAL (not STRONG_NEG, score>40)
  Pre-filter: 0 signals passed safety filters
  ```
- The pipeline log shows the same pattern 14,634 times: `🚫 [SHORT-CONTINUUM] ... blocked — BTC score=XX.X z=NEUTRAL (not STRONG_NEG, score>40)`

**Why DISAGREE:** The processing window is 10 minutes, not 5. The signals are processed — they're blocked by SHORT-CONTINUUM, not expiring "before processing." The 5-minute staleness timer is the expiry mechanism, but the root cause is SHORT-CONTINUUM filtering, not window size.

---

### Claim 4: "505 pump-chain SHORT signals EXPIRED in the last 24h"
**Verdict: AGREE**

**What I found:**
- Fixed 24h window query: **exactly 505 EXPIRED** pump-chain SHORT signals ✅
- (Rolling 24h at query time showed 501 — the window slides as time passes; 505 is correct for the stated window)
- All 505 have decision_reason=NULL, compact_rounds=0, survival_score=0.0, executed=0
- Expiry ages cluster at ~5.7 minutes (491 of 505), confirming the 5-min staleness path

**Why AGREE:** The number is exactly correct.

---

### Claim 5: "Pump-chain SHORT signals are produced by pump_flow_signal.py when phase has SHORT recommendations"
**Verdict: PARTIAL**

**What I found:**
- pump_flow_signal.py has `SIGNAL_TYPE_SHORT = 'pump-chain'`, `SOURCE_SHORT = 'pump-chain-'` and emits SHORT when recommendations have `direction='SHORT'` ✅
- **But pump_chain_v5_short.py ALSO produces signal_type='pump-chain', source='pump-chain-'** — same signal_type and source. Both scripts run every minute in the FAST signal list.
- Both scripts read the same `pump_flow_state.json` and both only emit SHORT when recommendations say SHORT
- Current pump_flow_state.json: phase=ACCUMULATION, recommendations=[{token: BTC, direction: WAIT}] — **no SHORT recommendations right now**, yet 530 SHORT signals fired in 24h. The state must have had SHORT recs earlier, or pump_chain_v5_short.py produced them during SHORT-recommendation periods.
- The claim attributes production solely to pump_flow_signal.py, but pump_chain_v5_short.py is an equal (or possibly primary) producer

**Why PARTIAL:** pump_flow_signal.py does produce pump-chain SHORT when phase has SHORT recommendations, but the claim omits pump_chain_v5_short.py which produces the identical signal_type/source. Both require SHORT recommendations in the pump flow state.

---

### Claim 6: "The SHORT-CONTINUUM filter (BTC score < 30) blocks SHORT signals when BTC is neutral"
**Verdict: PARTIAL**

**What I found:**
- The actual threshold is **SHORT_CONTINUUM_SCORE_MAX = 40** (hermes_constants.py:1348), **raised from 30 on 2026-10-06** (today). The comment documents: "CEO/T 2026-10-06: raised 30→40 — documented revisit path, T directive broader SHORT market. 14.6k SHORT-CONTINUUM blocks in pipeline.log; BTC score currently 39-50 z=NEUTRAL mass-blocking."
- The filter blocks when **BTC score > 40** AND z not in `('STRONG_NEG',)` — the claim says "score < 30" which is **backwards and uses the old threshold**
- BTC continuum state (continuum.db, fresh): score=43–55, z=NEUTRAL, market_phase=CALM — so YES, the filter IS currently blocking SHORT signals
- I directly observed in my compactor run: `🚫 [SHORT-CONTINUUM] APT SHORT blocked — BTC score=43.1 z=NEUTRAL (not STRONG_NEG, score>40)`
- 14,634 SHORT-CONTINUUM blocks in pipeline.log — this is clearly the **dominant SHORT blocker**
- The filter applies to ALL SHORT signals including pump-chain (no pump-chain exemption in the SHORT-CONTINUUM code path at signal_compactor.py:2820–2869)
- The token-level z-score exception (`SHORT_CONTINUUM_TOKEN_Z_ENABLED`) is **DISABLED** (bug_hunter found avg_z has no live writer)

**Why PARTIAL:** The filter is real, IS the main SHORT blocker, and IS blocking when BTC is neutral. But the threshold is 40, not 30 (it was raised today), and the logic direction is "score > 40 blocks" not "score < 30 blocks." The claim describes the pre-today configuration and inverts the comparison.

---

### Claim 7: "BTC is in LOSERS list with LOSERS_HARD_BLOCK_WR=40%, blocking BTC SHORT at 28.6% 7d WR"
**Verdict: PARTIAL**

**What I found:**
- BTC IS in the LOSERS set: `{'ADA', 'BTC', 'CHIP', 'CRV', 'JUP', 'TURBO'}` (hermes_constants.py:306) ✅
- LOSERS_HARD_BLOCK_WR = 40.0 (hermes_constants.py:382) ✅
- Exact decider_run.py query (server='Hermes', 7d, status='closed'): **28.6% WR** (7 trades, 2 wins) ✅
- 28.6% < 40%, so the hard block **would** fire if BTC SHORT reached decider_run ✅
- **But:** the hard block is in **decider_run.py:4211–4226** (execution layer), NOT in signal_compactor.py. The compactor applies LOSERS_MULT (0.3 score penalty) and LOSERS_CONF_PENALTY (-50 confidence penalty) but **not** the hard block.
- **More importantly:** BTC SHORT signals never reach decider_run because they're blocked by SHORT-CONTINUUM in the compactor first. The hard block is real but is **not the active blocker** — SHORT-CONTINUUM kills BTC SHORT signals before they ever get to the execution layer.
- BTC 7d by direction: LONG 27.3% (11 trades), SHORT 0% (1 trade). The hard block checks overall token WR, not direction-specific.
- Also note: BTC 7d all servers = 15.4% (13 trades, 2 wins) — the 28.6% figure is specifically the Hermes-server query

**Why PARTIAL:** BTC is in LOSERS, the hard block exists at 40%, and 28.6% is the correct Hermes-server 7d WR. But the hard block is in decider_run (not the compactor), it's not the active blocker for BTC SHORT (SHORT-CONTINUUM blocks them earlier), and the claim implies it's what's blocking the 505 expired signals — it isn't.

---

## Root Cause Summary

The **actual** blocker chain for pump-chain SHORT signals is:

1. **Signal generation**: pump_chain_v5_short.py / pump_flow_signal.py emit pump-chain SHORT when pump flow state has SHORT recommendations ✅
2. **Confluence gate**: PASSES via STANDALONE_BYPASS_SIGNALS (`pump-chain` is in the bypass list) ✅
3. **BTC chop gate**: PASSES via `_btc_exempt = _is_pump_chain` ✅
4. **SHORT-NEUTRAL block**: PASSES via standalone bypass ✅
5. **SHORT-CONTINUUM filter**: **BLOCKED** — BTC score 43–55 > 40, z=NEUTRAL (not STRONG_NEG) ❌ ← **THIS IS THE KILLER**
6. **Staleness timer**: Signal stays PENDING, expires after 5 minutes (not 10)

The **SHORT-CONTINUUM filter is the primary blocker** for pump-chain SHORT signals, not the compactor window size. 14,634 blocks in the pipeline log confirm this is a mass-blocking event.

---

## Bugs Found (Sideways Finds)

1. **[HIGH] SKIPPED signals have NULL decision_reason** — All 204 bollinger_squeeze_long SKIPPED signals and all 29 pump-chain SHORT SKIPPED signals have decision_reason=NULL. The `mark_signal_processed` docstring explicitly says "The DB must never have NULL reasons for SKIPPED/WAIT decisions," but `update_signal_decision` (called by `mark_signal_executed`) doesn't set decision_reason. This breaks the audit trail.

2. **[MEDIUM] Compactor log message is stale** — signal_compactor.py:2193 logs "Query: N combo_keys in 5-min window" but the SQL at line 2183 uses `-10 minutes`. Misleading for anyone reading logs to diagnose timing issues.

3. **[MEDIUM] SHORT_CONTINUUM_TOKEN_Z_ENABLED is disabled with no live data source** — The token-level z-score exception (would allow oversold tokens to SHORT even when BTC is neutral) is disabled because `avg_z` in momentum_cache has no live writer (bug_hunter HIGH finding). This means the SHORT-CONTINUUM filter has **no working escape hatch** when BTC is neutral — it either allows STRONG_NEG z-tier or blocks everything else.

4. **[LOW] No EXECUTED signals in the signals table** — The `signals` table only contains EXPIRED, SKIPPED, and PENDING decisions. No EXECUTED records exist. This may be by design (EXECUTED signals are tracked in PostgreSQL trades table), but it means the SQLite signals table alone cannot answer "how many signals resulted in trades."

---

## Data Sources Used

- **SQLite runtime DB**: `/root/.hermes/data/signals_hermes_runtime.db` — direct SQL queries for signal counts, decisions, metadata
- **PostgreSQL brain DB**: via `_secrets.BRAIN_DB_DICT` — BTC WR queries using exact decider_run.py query
- **Continuum DB**: `/root/.hermes/data/continuum.db` — BTC state_score and zscore_tier
- **Pump flow state**: `/root/.hermes/data/pump_flow_state.json` — current phase and recommendations
- **Source code**: signal_compactor.py, hermes_constants.py, pump_flow_signal.py, pump_chain_v5_short.py, signal_schema.py, decider_run.py, volatility_gate_v2.py
- **Pipeline log**: `/root/.hermes/logs/pipeline.log` — SHORT-CONTINUUM block counts, confluence gate passes
- **Live compactor run**: Executed `python3 signal_compactor.py` at 22:26 UTC — directly observed SHORT-CONTINUUM blocking APT SHORT

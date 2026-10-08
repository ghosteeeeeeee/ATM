# 2026-10-08 | CEO Decision: REJECT velocity-based detection bypass in pump_chain_long

**Decision: REJECT (option 3)** — do NOT add momentum_cache velocity-based detection to `pump_chain_long.py`.

**Decision maker:** CEO (delegated session)
**Date:** 2026-10-08 ~01:10 UTC
**Proposal under review:** Fire pump-chain+ LONG when momentum_cache shows velocity > 0.10 and phase LONG_BIAS, even when pump_flow engine is in ACCUMULATION — so we get "more trades like CRV".

---

## Why rejected — verified facts (not opinion)

### 1. The proposal's premise is factually wrong (live data at 2026-10-08 01:04 UTC)

| Claim in proposal | Verified live state |
|---|---|
| pump_flow stuck in ACCUMULATION (conf=0.32) | **MARKUP, conf=0.764** (`/var/www/hermes/data/pump_flow_data.json`, updated 2026-10-08T01:04:04Z) |
| Only rec = BTC WAIT | **9 LONG recommendations:** JUP 0.478, CHIP 0.408, LDO 0.370, APT 0.359, CAKE 0.354, BIGTIME 0.351, GRASS 0.348, IOTA 0.347, HBAR 0.347 |
| pump_chain_long produces 0 signals | **Firing normally today:** pump-chain+ LONG on CRV 00:24:11, LDO 00:26:11, CHIP 01:04:29 (signals_hermes_runtime.db) |
| 12+ coins velocity > 0.10 + LONG_BIAS | **7 coins only:** ACE +0.668, W +0.451, CRV +0.236, AR +0.178, JUP +0.161, AEVO +0.144, IMX +0.118 |
| PURR +0.154, APT +0.111, ATOM pumping | **PURR +0.065, APT phase=NEUTRAL +0.017, ATOM +0.087** — all three FAIL the proposed >0.10 gate |

The ACCUMULATION stall was transient. The engine already recovered. The problem the proposal solves no longer exists.

### 2. The filter inverts the winning entry profile

Winning CRV trade (PostgreSQL brain.trades, open 2026-10-07 22:17:44):
- `signal='pump-chain+'`, entry 0.35971, status open, +9.1% at query time
- `_signal_metadata`: **rsi_14 = 52.17**, z_score = 2.5764, bb_position = 1.1441, gap_at_entry = 1.1884, btc_regime = RANGING_BEAR, volume_spike = 0.41, wave_phase = accelerating

CRV **now**: momentum_cache RSI 99.44, velocity +0.236, LONG_BIAS.

A velocity>0.10 + LONG_BIAS detector fires *after* the move, at RSI 99. The trade that won entered at RSI 52. The proposal selects for the condition opposite to the one that produced the winner.

Downstream, `signal_compactor.py:2926-2932` already blocks pump-chain LONG at RSI > PUMP_CHAIN_LONG_RSI_MAX (85), logged as *"overbought chase, 23.5%WR at RSI>=70/14d"*. So velocity-fired CRV/W/ATOM/APT signals would either:
- (a) be killed downstream anyway (wasted scan slots, log noise, false expectation), or
- (b) only fire if we also bypass the RSI gate — booking trades our own data puts at ~23.5% WR.

### 3. Velocity-based pump detection already exists — and it loses

`pump_chain_v5.py` = velocity + continuum-oscillator filters applied **on top of** pump_flow state (it does not bypass it). Documented thesis: "Token is rising (positive 30m velocity)". Live PostgreSQL performance:

| Window | Closed | WR | PnL |
|---|---|---|---|
| pump-chain-v5 24h | 1T | 0% | -$0.06 |
| pump-chain-v5 14d | 11T | 36.4% | **-$0.27** |

History: v4 killed 2026-09-22 ("pump-chain+ LONG 15.4%WR -$1.51 24h. ALL regimes lose. NEVER_REENABLE"). v5 re-enabled by CEO 2026-10-07 citing "68.3% WR all-time bare form" — live 7-14d data disagrees and the 2026-10-07 23:13 trading log already flagged it.

The proposal is the third iteration of the same pattern, with an extra failure mode: v5 at least still consumes pump_flow recommendations (keeps chain evidence, BTC filter, move-done filter, phase context). The proposal throws all of that away and generates from raw momentum_cache velocity.

### 4. Bypassing pump_flow strips the protections that make pump-chain work

What pump_chain_long would lose by going momentum_cache-direct:
- **chain_evidence** (capital rotation confirmation — the actual thesis of the signal)
- **BTC 1h filter** (PUMP_FLOW_BTC_FILTER_THRESHOLD = -0.1; backtest noted in code: 81%→89% WR)
- **Move-already-done filter** (pump_flow_signal.py: `LONG blocked if 30m vel > PUMP_FLOW_MOVE_DONE_THRESHOLD` — "move over, pullback likely"). CRV +7.75% / RSI 99 is *exactly* this regime.
- **flow_score-based confidence** — velocity-only candidates have no flow_score/chain fields, so confidence model breaks or must be invented unbacktested.

What remains is momentum chasing at extremes. Trading philosophy ("never fade momentum") does not mean "buy RSI 99"; AGENTS.md BANANA lesson: wrong extreme entries are entry-condition failures, not timing failures.

### 5. Base rate does not justify expanding this signal

PostgreSQL `trades.signal='pump-chain+' AND direction='LONG'`:

| Window | Closed | W | WR | PnL |
|---|---|---|---|---|
| 24h | 4 | 1 | **25.0%** | **-$0.20** |
| 7d / 14d | 14 | 8 | 57.1% | +$0.89 |
| 30d (= full window with `signal` populated) | 94 | 41 | 43.6% | +$1.84 |

Recent 14d pump-chain+ LONG losers: FOGO -$0.06, LDO -$0.14, IMX -$0.07, INJ -$0.22, ACE -$0.27, JUP -$0.07 (all hard_max_loss / dead-money exits). CRV is 1 open winner out of 5 recent trades in this signal. "More trades like CRV" without an entry-quality change means more trades like ACE/INJ/LDO.

CRV's own last 7d non-pump-chain entries were losses (mover+ -$0.14, volume-breakout-long+ -$0.11, SHORT -$0.11, trail -$0.02). The coin is not the edge; the entry profile (RSI 52, z 2.58, accelerating wave) is.

### 6. Duplicate-signal risk is already real

- Three files emit source `pump-chain+`: `pump_chain_long.py`, `pump_flow_signal.py` (LONG path currently skipped in code), `pump_chain_v4.py` (flag-killed).
- Same-tick dual emissions already observed: CRV 00:24 (pump-chain+ AND pump-chain-v5), CHIP 01:04 (both), bollinger_squeeze_long tagged `bb-squeeze+,pump-chain+`.
- Cooldown is keyed (token, direction) and **shared across the pump-chain family** — a velocity-fired LONG sets cooldown that suppresses the pump_flow-driven signal for that token, and vice versa. Two uncoordinated detectors would fight over slots.
- `PUMP_FLOW_MAX_PER_CYCLE = 3` and `PUMP_FLOW_MAX_POSITIONS = 4`: 7 simultaneous velocity candidates blow through cycle caps and concurrent-position limits into guardian/risk territory.

---

## What IS approved (separate work, not this proposal)

1. **Root-cause the pump_flow phase lag.** Why did the engine report ACCUMULATION conf=0.32 while 15m_regime_scanner momentum_cache showed broad LONG_BIAS? Phase detection is the bottleneck. Fix the engine; do not bypass it.
2. **Consistency fix (low risk, worth doing):** `pump_chain_long.py:158` hard-blocks on `phase_conf < PUMP_FLOW_MIN_PHASE_CONFIDENCE` with no escape, while `pump_flow_signal.py:211` allows through when `max_rec_conf >= 0.80`. Mirror the escape hatch. Note: with live rec confidences 0.35-0.48 this would NOT have fired during the ACCUMULATION window — it is a consistency fix, not an opportunity fix.
3. **If velocity coverage is wanted later:** new signal type (e.g. `pump-momentum-long`) with its own `*_ENABLED` flag in hermes_constants, RSI cap ≤ 85 (aligned to PUMP_CHAIN_LONG_RSI_MAX), BTC 1h filter, move-done filter, max-per-cycle 2, and the staleness reject ported from pump_flow_signal. **Independent backtest required before enabling** (AGENTS.md mandate; own backtest is not sufficient).
4. **Resolve pump-chain-v5 first.** Do not launch a second overlapping velocity experiment while v5 is live at 14d -$0.27 / 36.4% WR. Either fix v5's entry profile or kill it, then evaluate one velocity idea at a time.
5. **No hermes_constants gate changes** without T's explicit sign-off (file header rule).

---

## Sideways findings (unrelated issues spotted during review)

| Severity | Finding | Suggested fix |
|---|---|---|
| **Medium** | `pump_chain_long.py::_load_state()` has **no staleness check** — `pump_flow_signal.py` rejects state > 600s old; pump_chain_long will happily read dead state and keep firing on old recommendations | Port the `MAX_STATE_AGE_SECS` reject into pump_chain_long (and v5, same gap) |
| Low | `pump_flow_signal.py:341-342` — dead code after `continue` (unreachable duplicated SHORT log lines) | Delete lines 341-342 |
| Low | `pump_chain_v5.py:43` — hardcoded `PUMP_FLOW_V5_BTC_FILTER = -0.1` (violates "no hardcoded constants" convention) | Move to hermes_constants.py (with T's sign-off) |
| Low-Med | PostgreSQL `signal`/`strategy` columns only populated ~30d back (all-time stats == 30d); `signal_reason` NULL on recent rows | Analytics on older pump-chain history undercounts; note in any future backtest |
| Info | Trading log 2026-10-07 23:13 already flagged pump-chain-v5 7d negative post-re-enable — consistent with PG numbers above | CEO owns v5 re-enable; kill-check when 3T-0%WR or WR < 50% on 7d per existing monitor rule |

---

## Revisit

- Pump_flow phase-lag root cause: 2026-10-10
- pump-chain-v5 keep/kill at next kill-check window
- Any velocity-signal proposal: only with independent backtest attached

**Owner:** CEO

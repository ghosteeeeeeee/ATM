# Pump-Chain V6 Spec — "Keep the Winners, Ditch the Losers"

**Date:** 2026-10-08
**Status:** SPEC — awaiting approval before implementation
**Author:** Hermes analysis (data-driven, 260 closed trades, 60d, IS/OOS validated)
**Skills followed:** `signal-lab` (thesis → entry → exit → backtest), `add-signal` (full integration checklist)

---

## 1. Executive Summary

Pump-chain's core thesis — capital rotates from leaders into laggards, and the chain
correlation is the alpha — **still works**. What failed in every previous version is the
*entry-timing gates* around it: they were either derived from tiny in-sample samples, read
data from the wrong place (previous trades' metadata), or stopped working as the regime
shifted.

V6 is a single clean signal (BOTH directions, one file) whose gates were selected by one
rule: **the gate must improve PnL and WR in the full sample AND in an out-of-sample time
split, and the blocked basket must be net-negative.** Two gates survived that test:

| Direction | Gates | Full 60d (n=260 base) | OOS (last 30%) |
|-----------|-------|----------------------|----------------|
| LONG | block RSI<40 or RSI>70 or momentum=flat | 43.7% WR +$2.59 → **56.1% WR +$4.96** | 48.6% +$1.80 → **65.0% +$2.66** |
| SHORT | block RSI<40 or momentum=flat | 50.4% WR −$0.52 → **53.5% WR +$1.54** | 39.0% −$0.77 → **41.2% −$0.06** |

Blocked baskets are net-negative in BOTH splits (LONG blocked: 15W/38L −$2.37;
SHORT blocked: 25W/30L −$2.06) — i.e., the filters remove losers, they don't just
shrink the sample.

**V6 does not replace the live `pump_chain_long` immediately** (see §8): it ships in
parallel under a new `signal_type='pump-chain-v6'` with independent outcome stats, and the
old variants retire only after v6 proves itself on live paper trades.

---

## 2. Why Every Previous Version Failed (Pitfall Register)

| Version | Claim | Delivered | Root cause | V6 fix |
|---------|-------|-----------|------------|--------|
| V1 | pure pump-flow momentum | 57.5% WR, losers > winners | No entry-timing gates | velocity/RSI/momentum gates |
| V2 spec | "93.5% WR verified" | ~45% WR live | Overfit on 73 in-sample trades; promised WR from tiny n | All v6 claims validated IS **and** OOS; spec ships with min-n + kill criteria |
| V4 | BTC oscillator block >80 | 15.4% WR −$1.51, NEVER_REENABLE | Filtered on a BTC-only indicator that regime-shifted | **No BTC-score blocking in v6.** BTC context only via existing `volatility_gate` routing |
| V5 | velocity + "block bottoming" | 33.3% WR −$0.42, killed 3× | (a) read wave_phase/momentum_state from **the token's last CLOSED TRADE's metadata** — a stale, cross-contaminated snapshot; (b) "bottoming" is now a WINNER band (65.6% WR, +$1.28); (c) 90% WR claim was n=10 | All v6 gates computed from **live candle data at detection time**; no wave_phase blocking; no trade-history-derived state |
| V5 SHORT | accel/rising + BB blocks | breakeven, still live | filters on 2-trade "0% WR" cells | v6 SHORT gates validated on n=141 with OOS split |

Cross-cutting pitfalls fixed in V6:

1. **Confidence is not an edge.** 90+ confidence bucket: n=155, 50.3% WR (coin flip),
   PnL ≈ ±$0.00. 60-70 bucket is *positive*. Confidence stays as a **ranking** input only —
   never a hard gate above the existing floor.
2. **Instant-chase execution loses.** LONG trades opened <2 min after the signal: 32.7% WR
   (n=55, −$1.86) — and this holds in ALL THREE time terciles (28.6/30.8/36.4% WR).
   Trades opened ≥2 min: ~50%+ WR, +$4.45. Mechanically: executing the instant the pump
   registers buys the local top; a small delay gets a cooled-off fill. → execution-layer
   min-age guard (§6.4).
3. **Source-string zoo.** Old sources embed chain evidence (`chain(ADA(1.73x),ZRO(1.52x))`)
   directly in the source string, fragmenting Layer-2 matching, compactor weights and
   exit routing. V6 uses **fixed source strings only**; chain evidence goes in `value`
   and the debug log, never in `source`.
4. **NULL metadata rows (39/260 have NULL rsi_14).** Gate on missing data must be an
   explicit decision, not an accident: v6 **fails open** on missing features and logs it
   (blocking on data-collection gaps would be arbitrary; n is too small to block on).
5. **Detection/execution gap** (known system gotcha): v6 gates fire at detection time;
   `decider_run.py` re-validates live RSI at execution (SHORT hard floor already exists).
   The min-age guard in 2 partially mitigates for LONG.

---

## 3. Thesis (signal-lab Step 1)

**Capital-rotation continuation:** when capital rotates from leaders into laggards
(detected by the pump-flow engine's chain evidence: leader → follower lift), the follower's
move is real flow, not noise — and continues. But the flow is only tradeable **while the
move is mid-cycle**:

- Enter LONG while the token is in the *middle* of its RSI range (40–70) with live
  momentum not flat — the pump has started but is not spent. RSI<40 means the pump never
  started (or already died); RSI>70 means v6 would be buying the top of the spike.
  Both bands are net losers (LONG RSI<40: 15.4% WR −$1.01; RSI>70: 33.3% WR −$0.52).
- Enter SHORT only when the token is *not* already crushed (RSI≥40) and momentum is
  actually turning (not flat). SHORT RSI<40 = shorting into oversold = −$1.65 on n=25
  (the BANANA lesson, quantified).
- **`momentum_state='flat'` is the one state that loses in both directions**
  (LONG flat: 26.1% WR −$1.75; consistent −PnL in all three splits). Flat = no flow =
  the chain thesis is not in play.

Everything else we tested and REJECTED is listed in §7 so it doesn't get re-proposed.

---

## 4. Entry Conditions (signal-lab Step 2) — exact, testable

**Data source unchanged:** `pump_flow_engine.py` → `pump_flow_data.json` recommendations
(chain_evidence, flow_score, suggested_direction). Engine is NOT modified.

Per recommendation (token, direction), ALL of:

```
G0  Engine gates:  phase confidence ≥ PUMP_FLOW_MIN_PHASE_CONFIDENCE
                   direction ∈ {LONG, SHORT} (WAIT ignored)
                   confidence ≥ PUMP_FLOW_MIN_CONFIDENCE (ranking floor, not edge)
G1  Freshness:     price_age_minutes ≤ PUMP_FLOW_MAX_PRICE_AGE
                   token_speeds.is_stale = false
G2  Risk:          token not in LONG_BLACKLIST / SHORT_BLACKLIST; cooldown clear
G3  RSI gate:      RSI(14) from candles_5m at DETECTION time
                   LONG:  40 ≤ RSI ≤ 70        (block <40 and >70)
                   SHORT: RSI ≥ 40             (block <40)
                   missing RSI → fail open + DEBUG log
G4  Momentum gate: momentum_state computed LIVE from candles_5m using the EXACT
                   signal_schema.py:494-497 definition (5-bar velocity:
                   rising if vel > +0.1, falling if vel < -0.1, else flat)
                   Block 'flat' in BOTH directions. Missing candles → fail open + log.
```

**Why this momentum definition:** it is the same formula that produced the historical
`momentum_state` in `_signal_metadata` (signal enrichment) — so the validated evidence
(n=260) applies with **zero calibration gap**, unlike v5 which read the *previous trade's*
snapshot. No new state machinery needed.

Chain evidence (leader, lift) is logged and passed via `value` for audit — it is NOT a
gate (no validated threshold; `chain evidence count` had no stable relationship to outcome).

---

## 5. Exit Plan (signal-lab Step 3)

No new exit engine. V6 routes into the **existing, tuned** per-direction exits:

| Source | Exit engine | Rationale |
|--------|-------------|-----------|
| `pump-chain-v6+` | `pump_exit` | Momentum exit works for pump-chain LONG (existing routing) |
| `pump-chain-v6-` | `rr_engine` | Tighter SL needed for SHORT (CASHCAT lesson: −6.4% with pump_exit) |

`PROFIT_MONSTER_BYPASS_SIGNALS` += v6 sources (pump_exit manages LONG; PM Trail would
cut winners at 0.5–2% before momentum plays out). R:R floor is enforced by the existing
rr_engine / ATR SL stack — unchanged.

---

## 6. Implementation Plan (add-signal checklist, every step)

### 6.1 New signal script — `scripts/signals/pump_chain_v6.py`
- One file, both directions. `SIGNAL_TYPE = 'pump-chain-v6'` (NEW type → clean,
  independent `signal_outcomes` stats for the decay detector and this spec's kill criteria).
- `SOURCE_LONG = 'pump-chain-v6+'`, `SOURCE_SHORT = 'pump-chain-v6-'` — fixed strings,
  no chain evidence embedded.
- Reuses `pump_chain_long._load_state()` normalization and confidence computation
  (ranking only).
- RSI + momentum computed from `candles_5m` via read-only SQLite connection, closed in
  `finally`. Staleness from `token_speeds` (read-only URI, same as pump_chain_long).
- `run()` with no params (reads DB directly — no wasteful `get_all_latest_prices` loop;
  price fetched once per cycle).

### 6.2 Constants — `hermes_constants.py` (no hardcoded numbers in the script)
```python
PUMP_CHAIN_V6_ENABLED = True          # master
PUMP_CHAIN_V6_PLUS_ENABLED = True     # LONG
PUMP_CHAIN_V6_MINUS_ENABLED = True    # SHORT
PUMP_CHAIN_V6_LONG_RSI_MIN = 40
PUMP_CHAIN_V6_LONG_RSI_MAX = 70
PUMP_CHAIN_V6_SHORT_RSI_MIN = 40
PUMP_CHAIN_V6_BLOCK_FLAT_MOMENTUM = True
```
Existing PUMP_FLOW_* shared constants (min confidence, cooldown, max per cycle, price age,
velocity/chain/phase bonuses) are reused, not duplicated.
Exit routing (§5) and `PROFIT_MONSTER_BYPASS_SIGNALS` entries added.
`STANDALONE_BYPASS_SIGNALS` += `pump-chain-v6+`, `pump-chain-v6-` (chain correlation fires
solo; existing pump-chain sources already bypass).

### 6.3 Registration & enforcement (the two-mandatory-location rule)
- `signals/__init__.py`: import + registry entry; **not** a slow signal (single state-file
  read + per-rec candle lookups, same cost class as pump_chain_long).
- `signal_schema.py` `add_signal()` component checks for `pump-chain-v6+`/`pump-chain-v6-`.
- `signal_schema.py` `is_component_disabled()`: constants added to ITS import block
  (missing this = NameError kills ALL compaction).
- `signal_compactor.py` `SIGNAL_SOURCE_WEIGHTS` += v6 entries (1.0).
- `volatility_gate.py` `REGIME_SIGNALS`:
  - LONG → NORMAL, HIGH, EXTREME (60d evidence: EXTREME carries all PnL +$3.03;
    no basis to block HIGH for LONG — v4-style regime blocking failed before)
  - SHORT → NORMAL, EXTREME (**skip HIGH**: HIGH is the confirmed SHORT bleed regime,
    PUMP_CHAIN_SHORT_HIGH_BLOCK evidence 2026-10-07)
- Not in `_DEAD_SIGNALS`; validate with `validate_source()`.

### 6.4 Execution-layer min-age guard (fixes instant-chase, §2.2)
In `decider_run.py` (or the existing staleness guard path): for `pump-chain-v6+`,
block execution when signal age < `PUMP_CHAIN_V6_MIN_AGE_MIN = 2` minutes —
but ONLY when doing so does not violate the existing
`SIGNAL_STALENESS_MAX_AGE_MIN = 5` ceiling (window is 2–5 min). SHORT has no min-age
(SHORT staleness bands show 5m+ is the *best* SHORT band: 58.1% WR +$0.97 — age helps
SHORTs; do not impose LONG's pattern on it).

### 6.5 Verification (add-signal Step 6)
py_compile all changed files → import-chain check (registry, REGIME_SIGNALS, is_component_disabled)
→ `--dry` run → log check → pre-flight checklist from the skill (DB connections, no magic
numbers, source consistency, blacklist, cooldown, bypass lists).

---

## 7. Tested and REJECTED (do not re-propose without new data)

| Candidate | Result | Verdict |
|-----------|--------|---------|
| Block `wave_phase='bottoming'` (v5) | bottoming is now +EV: 65.6% WR +$1.28 (n=32) | **Reversed** — v5 filter would block winners |
| Block `wave_phase='accelerating'` | +PnL in all splits (low WR but pays) | No |
| z-score filters (LONG <−1.5 / SHORT >+1.5) | ZERO trades blocked in 60d — dead code | No |
| speed_percentile bands | sign flips across splits | No |
| volume_spike | IS: winners 2.8 vs losers 0.5; OOS: sign REVERSES | No |
| Confidence > threshold | 90+ conf = 50.3% WR coin flip (n=155) | Ranking only |
| BTC oscillator block (v4) | 15.4% WR, NEVER_REENABLE | No |
| Block SHORT momentum flat alone | blocked basket +$0.25 in IS (kills winners) | Only as part of RSI combo |
| Block LONG RSI>70 alone | blocked basket +$0.32 full-sample | Kept only inside the validated extremes combo |

Statistical honesty: the LONG combo's blocked-basket edge is consistent (3/3 splits,
PnL negative every split); SHORT's is weaker (OOS improvement is directionally right but
small, n=41). SHORT ships with tighter monitoring (§8 kill criteria).

---

## 8. Deployment & Kill Criteria (signal-lab Steps 5–6)

1. **Do NOT disable the current `pump_chain_long`** (`pump-chain+`): it is currently its
   healthiest in weeks — 14d: 22T, 59.1% WR, +$2.21. V6 ships alongside under a new
   signal_type, so outcomes are tracked independently.
2. **Paper phase: 2 weeks.** V6 fires signals through the normal pipeline; Layer-3 gates,
   regime routing and min-age guard all apply; monitor `signal_outcomes` by
   `signal_type='pump-chain-v6'`.
3. **Kill criteria (any one):** WR < 45% after 20 closed trades; or PnL < −$1.00 over any
   rolling 10; or decay_detector flags it. Kill = `PUMP_CHAIN_V6_ENABLED=False` +
   NEVER_REENABLE review by CEO (v4/v5 precedent: repeated failed re-enables need fresh
   backtest + approval).
4. **Promotion:** after 5+ trades, self_learner starts tuning combo weights automatically.
   If v6 ≥ 55% WR on 50 trades → old `pump_chain_long` / `pump_chain_v5_short` flags go
   False, sources stay in NEVER_REENABLE if they can't beat v6.
5. **After commit: restart the pipeline** (system gotcha — detection-time filters are only
   live after reload).
6. **Independent verification before ANY of the above** (AGENTS.md mandate):
   `own-conclusions` audit of this spec's numbers (scripts in §9 are the reproducible
   source), then `bug_hunter` on the implementation diff before commit.

---

## 9. Reproducibility

Every number in this spec comes from these scripts (re-runnable, no memory):

- `scripts/analysis/pump_chain_v6_analysis.py 60` — winners-vs-losers, p-values, IS/OOS split
- `scripts/analysis/pump_chain_v6_round2.py` — RSI×direction, staleness×tercile, flow/conf buckets, top winner/loser profiles
- `scripts/analysis/pump_chain_v6_round3.py` — candidate-filter time-split validation (the §1 table)

Data: PostgreSQL `brain.trades` (closed, `signal LIKE '%pump-chain%'`, `_signal_metadata`
attached), 60-day window as of 2026-10-08.

Known data caveat: 39/260 rows have NULL `rsi_14` in metadata (feature-recording gap);
v6 gates fail open on these and log. `momentum_state` was never NULL in this sample.

# CEO Consult: Pair Anatomy — What Makes Best Pairs Work

## Context

T asked to investigate what makes the best look-back pairs work: hmacd+pump-chain (WR 64.3%), bb+ichimoku (WR 88.9%), ichimoku_short+pump-chain (WR 65.1%), pump-chain-v6+sr (WR 76.9%).

Previous CEO consult caught the look-forward bias flaw. The re-run with look-back window showed confluence hypothesis is FALSE — single-source signals are actually better. But these 4 specific pairs still show positive edge in look-back. So we investigated their anatomy.

## Key Findings

### 1. PM Trail is the Magic Exit — 100% WR Across ALL Pairs

| Pair | PM Trail n | WR% | Avg PnL |
|------|-----------|-----|---------|
| hmacd+pump-chain | 29 | **100%** | +0.532% |
| bb+ichimoku | 7 | **100%** | +0.868% |
| ichimoku_short+pump-chain | 26 | **100%** | +0.504% |
| pump-chain-v6+sr | 10 | **100%** | +0.489% |

### 2. Hard Max is the Killer — 0% WR Across ALL Pairs

| Pair | Hard Max n | WR% | Avg PnL |
|------|-----------|-----|---------|
| hmacd+pump-chain | 9 | **0%** | -0.794% |
| bb+ichimoku | 1 | **0%** | -0.800% |
| ichimoku_short+pump-chain | 13 | **0%** | -0.794% |
| pump-chain-v6+sr | 3 | **0%** | -0.800% |

**Pattern:** These pairs work because PM Trail catches winners. Hard_max kills losers at -0.8% before PM Trail can work. The edge is in the EXIT, not the entry.

### 3. Time Gap Sweet Spot: 15-45 Minutes

| Pair | Best Gap Bucket | WR% | Avg PnL |
|------|----------------|-----|---------|
| hmacd+pump-chain | **30-45m** | **78.6%** | **+0.682%** |
| bb+ichimoku | 30-45m | 100% | +1.162% |
| ichimoku_short+pump-chain | **15-30m** | **67.7%** | +0.073% |
| pump-chain-v6+sr | **15-30m** | **77.8%** | +0.165% |

Too fast (<5m) = noise. Too slow (>45m) = move already happened.

### 4. Direction-Specific

| Pair | Direction | N |
|------|-----------|---|
| hmacd+pump-chain | **SHORT only** | 54 SHORT / 2 LONG |
| bb+ichimoku | **LONG only** | 9 LONG / 0 SHORT |
| ichimoku_short+pump-chain | **SHORT only** | 43 SHORT / 0 LONG |
| pump-chain-v6+sr | **LONG mostly** | 12 LONG / 1 SHORT |

Each pair has natural directional bias.

### 5. Token Concentration Risk

| Pair | Top Token | % of Trades |
|------|-----------|-------------|
| hmacd+pump-chain | **CHIP** | 31/56 = **55%** |
| bb+ichimoku | **SYRUP** | 6/9 = **67%** |
| ichimoku_short+pump-chain | spread | top=7/43=16% |
| pump-chain-v6+sr | spread | top=2/13=15% |

**Red flag:** First two pairs are essentially single-token strategies. Edge might be token-specific, not pair-specific.

### 6. Trigger Pattern — Second Signal is the Trigger

| Pair | Trigger Fires 2nd | % |
|------|-------------------|---|
| hmacd+pump-chain | hmacd_mtf | 77% |
| bb+ichimoku | ichimoku_long | 67% |
| ichimoku_short+pump-chain | ichimoku_short | **100%** |
| pump-chain-v6+sr | support_resistance | **100%** |

Clear pattern: first signal = confirmation, second signal = entry trigger.

### 7. Winners vs Losers

| Pair | Winners avg_gap | Losers avg_gap | Winners avg_hold | Losers avg_hold |
|------|----------------|----------------|------------------|-----------------|
| hmacd+pump-chain | 26.8m | 27.6m | 45m | 19m |
| bb+ichimoku | 35.7m | 51.9m | 22m | 35m |
| ichimoku_short+pump-chain | 25.7m | 26.7m | 34m | 49m |
| pump-chain-v6+sr | 26.3m | 21.2m | 36m | 8m |

No consistent pattern on gap. Hold time mixed (some pairs winners hold longer, some shorter).

---

## Synthesis

**What actually makes these pairs work:**

1. **PM Trail exit is the real edge** — the entry pair just needs to be good enough to not hit hard_max before PM Trail kicks in
2. **15-45 minute confirmation window** — signals within this window are confirming the same move
3. **Hard_max at -0.8% is too tight** — it's killing winners before PM Trail can work (aligns with wider SL shadow trial)
4. **Token concentration** — hmacd+pump-chain is basically a CHIP strategy, bb+ichimoku is basically SYRUP

**Alignment with existing work:**

- Wider SL shadow trial: `SHADOW_TRIAL_CUT_LOSER=-6.00`, `SHADOW_TRIAL_ATR_SL_MAX=4.0` — already testing wider stops
- CEO verdict on risk budget: "Do NOT loosen HML... Fix entry quality and exit trailing instead"
- PM Trail is already the primary exit engine for these signals

---

## Questions for CEO

1. **Wider hard_max for pair trades:** Should we test skipping hard_max entirely for these specific pairs (hmacd+pump-chain, bb+ichimoku, ichimoku_short+pump-chain, pump-chain-v6+sr) and going straight to PM Trail? The data shows hard_max has 0% WR — it's only killing winners before PM Trail can work.

2. **Token-specific edge:** hmacd+pump-chain is 55% CHIP, bb+ichimoku is 67% SYRUP. Should we:
   a. Treat these as token-specific strategies (CHIP SHORT via hmacd+pump-chain, SYRUP LONG via bb+ichimoku)
   b. Investigate if the edge exists on other tokens (sample too small: only 25 non-CHIP hmacd trades, 3 non-SYRUP bb+ichimoku trades)
   c. Abandon these pairs as survivorship bias on specific tokens

3. **15-45m window implementation:** If we implement pair-specific entry triggers (first signal = confirmation, second signal = entry), should we:
   a. Build a temporal pair gate that waits for confirmation
   b. Keep it in shadow mode first (7d counterfactual)
   c. Only apply to the 4 proven pairs, not all combinations

4. **Exit engine override:** Should these pairs get a custom exit config that:
   a. Skips hard_max entirely, goes straight to PM Trail
   b. Uses wider hard_max (-2% or -3% instead of -0.8%)
   c. Uses the existing wider SL shadow trial config (CUT_LOSER=-6.00, ATR_SL_MAX=4.0)

5. **Priority vs existing work:** We have CONF_FLOOR=30 shipping Oct 23, wider SL shadow trial collecting data, shadow_signals_runner collecting Stage A/C data. Should this pair-specific work:
   a. Wait until those ship and stabilize
   b. Add to shadow mode now (parallel collection)
   c. Deprioritize — the edge is small (n=9 to n=56 per pair) and token-concentrated

## Constraints

- Sample sizes: n=9 (bb+ichimoku), n=13 (pump-chain-v6+sr), n=43 (ichimoku_short+pump-chain), n=56 (hmacd+pump-chain)
- Token concentration: CHIP=55%, SYRUP=67% of respective pair trades
- 15-day data window (Oct 7-22)
- Shadow trades use first_exit engine only (not all 10 engines)
- Look-back window (implementable), not look-forward
- Existing wider SL shadow trial: SHADOW_TRIAL_CUT_LOSER=-6.00, SHADOW_TRIAL_ATR_SL_MAX=4.0, LONG only
- CEO verdict: "Do NOT loosen HML... Fix entry quality and exit trailing instead"
- Vacation mode: automation team running, 1% daily target (CEO reset to 0.3% until WR ≥35%)
- Current system: 7d WR ~34-35%, guardrail at 50% size

## Full Data

Analysis scripts: `/tmp/pair_anatomy.py`, `/tmp/confluence_lookback.py`
Confluence report: `reports/20261022-confluence-window-analysis.md` (commit `712acec2`)

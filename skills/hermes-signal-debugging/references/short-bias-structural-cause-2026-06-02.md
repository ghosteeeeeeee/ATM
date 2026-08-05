# SHORT Bias Structural Analysis — 2026-06-02

## Summary

System is NOT malfunctioning — working as designed. Market regime + signal architecture create a structural SHORT skew.

---

## Root Cause Chain

### 1. Market Regime is SHORT_BIAS

`regime_5m.json` (2026-06-02 02:30):
- 5 tokens in SHORT_BIAS (ORDI, MOVE, HEMI, 2Z, FET)
- 0 tokens in LONG_BIAS
- 93 tokens NEUTRAL
- **Overall: SHORT_BIAS**

`regime_15m.json`:
- 0 LONG_BIAS, 0 SHORT_BIAS, 105 NEUTRAL → overall NEUTRAL

---

### 2. Signal Generation is SHORT-Heavy by Design

Raw signal counts (from signals.json, last 24h):

| Signal Type | SHORT | LONG | Ratio |
|-------------|-------|------|-------|
| accel_300 (accel-300-) | 121 | 8 | **15:1** |
| support_resistance (rs-s-broken) | 183 | 7 | **26:1** |
| rs-r+touch (LONG) | 0 | ~5 | — |
| All others | ~22 | ~3 | ~7:1 |

**Key insight:** In a downtrending market, `rs-s-broken` fires constantly — every broken support = SHORT signal. The mirror for LONG (rs-r+touch) barely fires because resistance rarely holds in a downtrend.

---

### 3. Confluence Gate Blocks Most LONGs

Cosine gate requires **2+ distinct signal types** per token+direction.

LONG signals that exist:
- `accel-300+` alone = 1 unique type → **BLOCKED** (stays PENDING)
- `rs-s2352` alone = 1 unique type → **BLOCKED** (stays PENDING)
- `accel-300+,rs-s36` = 2 types → would PASS but barely fires

In SHORT_BIAS market there's nothing to pair LONG signals with — the complementary sources don't exist.

---

### 4. Source Weights Favor SHORT

```
('accel_300_short', 'accel-300-'):  1.00  # SHORT
('accel_300_long',  'accel-300+'):  0.80  # LONG — 20% less weight
```

Additionally, cosine gate blocks specific LONG combos:
- `accel-300+ + ma-cross-5m+` → blocked (16.7% WR)
- `accel-300+ + pct-hermes+` → blocked (35.7% WR, catches knives)

But `accel-300-` has NO symmetric gate blocking its combos. The gate only fires on problematic LONG combos.

---

### 5. What Actually Executes

From signals.json executed (last 24h):
- **33 SHORT trades executed**
- **3 LONG trades executed** (XMR, ME, DYDX — high-confidence single signals that apparently passed at the time)

Current pending: **95 SHORT vs 3 LONG stuck in PENDING** — all LONGs have only 1 source and can't clear confluence.

---

## Architecture-Level Issue

**The cosine gate is asymmetric by construction.** It was designed to block specific bad LONG combos (catching knives, low WR) but the market regime creates a natural SHORT flood that the gate doesn't filter — because those SHORT combos aren't on the block list.

In SHORT_BIAS regime:
1. accel-300- fires frequently (121 SHORT vs 8 LONG)
2. rs-s-broken fires constantly (183 SHORT signals from broken support)
3. These pair naturally → `accel-300-,rs-s-broken` passes confluence easily
4. No equivalent for LONG — the complementary sources don't fire in downtrend

---

## Market Regime Effect on Signal Fire Rates

| Regime | accel-300 | rs-s-broken | rs-r+touch | Result |
|--------|------------|-------------|------------|--------|
| SHORT_BIAS | accel-300- fires | constantly | rarely | SHORT flood |
| LONG_BIAS | accel-300+ fires | rarely | fires | LONG flood |
| NEUTRAL | balanced | balanced | balanced | balanced |

The system is designed to be regime-aware, but the signal generation from accel_300.py and rs.py automatically skews based on market direction. The confluence gate then amplifies this skew because it requires 2 sources, and in a given regime only one direction's sources are plentiful.

---

## Not a Bug — Design Consequence

This is working as designed. The SHORT bias would ease if:
1. Market flips to LONG_BIAS or NEUTRAL (support breaks less often, resistance rejections fire more)
2. More LONG signals get generated (accel-300+ fires more in uptrend)
3. Cosine gate thresholds relaxed for LONG in SHORT_BIAS regime
4. Counter-regime signals explicitly de-escalated (not blocked) per T's preference

---

## Diagnostic Commands

```bash
# Check regime state
cat /var/www/hermes/data/regime_5m.json | python3 -c "import json,sys; d=json.load(sys.stdin); a=d['aggregate']; print(f'{a[\"overall\"]} long={a[\"long_bias\"]} short={a[\"short_bias\"]} neutral={a[\"neutral\"]}')"

# Check signal direction distribution in DB
sqlite3 /root/.hermes/data/signals_hermes_runtime.db "SELECT direction, COUNT(*) FROM signals WHERE created_at >= datetime('now', '-24 hours') GROUP BY direction;"

# Check hot-set direction
cat /var/www/hermes/data/hotset.json | python3 -c "import json,sys; d=json.load(sys.stdin); from collections import Counter; dirs=Counter(e.get('direction') for e in d.get('items',[])); print(dict(dirs))"
```

---

## Related Files

- `signals/rs.py` — rs-s-broken fires SHORT when support breaks (line 520-543)
- `signals/accel_300.py` — accel-300- fires SHORT when below EMA300 with growing gap (line 407-410)
- `signal_compactor.py` — cosine gate at line ~495, regime multiplier at line 290-303
- `hermes-hot-set` skill — hot-set pipeline overview
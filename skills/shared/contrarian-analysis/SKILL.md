---
name: contrarian-analysis
description: Use when analyzing BTC or major crypto setups. Adds a contrarian lens to technical analysis. Triggers on "contrarian view", "what could go wrong", "devil's advocate", "reverse analysis", "BTC will do the opposite".
---

# Contrarian Analysis Skill

**Core lesson: BTC does the opposite of what you think is going to happen.**

Every technical setup has a contrarian interpretation. This skill forces you to see both sides before entering a trade.

## The Pattern (Verified 2026-10-16)

**Our analysis said:**
- MACD bullish crossover ✅
- Higher low since 11:30 ✅
- Volume surge on dip (buying) ✅
- Range expanding ✅
- RSI healthy ✅

**What actually happened:**
- Dumped from $82,409 to $81,583 (-4.99%)
- Hard max loss exit
- Bought the exact peak

**Why it failed:** Every retail trader saw the same bullish signals. The "obvious" trade is the crowded trade. Smart money fades consensus.

## The Contrarian Checklist

Before entering ANY trade, ask these questions:

### 1. "What would a short seller see right now?"
- Is the bullish setup TOO obvious?
- Are all retail indicators aligned? (crowded trade)
- Is there a bearish divergence hiding underneath?

### 2. "Where is the stop loss cluster?"
- Most LONG stops are below swing lows
- Most SHORT stops above swing highs
- Price hunts clusters, not individual stops
- If everyone's stop is at $81,850, price goes to $81,800

### 3. "What is the market maker's incentive?"
- If most retail is LONG → market maker profits from dumping
- If most retail is SHORT → market maker profits from pumping
- Check funding rates, open interest if available

### 4. "Is this a trap?"
- Bull flag that breaks UP then dumps = bull trap
- Bear flag that breaks DOWN then pumps = bear trap
- MACD crossover at resistance = fakeout
- MACD crossover at support = fakeout

### 5. "What is the OPPOSITE setup?"
- If you see a perfect LONG setup, what does the SHORT setup look like?
- Is the SHORT setup actually stronger?
- Which side has more fuel (stops to hunt)?

## Contrarian Indicators

### Bearish Signs Hiding in Bullish Setups:
- Price makes higher high but volume DECLINES (divergence)
- MACD crossover happens at a KEY RESISTANCE level
- RSI is 65+ when the "signal" fires (overbought chase)
- The setup is discussed on social media / appears in scans
- Multiple signals fire on the same coin simultaneously (crowded)

### Bullish Signs Hiding in Bearish Setups:
- Price makes lower low but volume DECLINES
- MACD bearish crossover at KEY SUPPORT
- RSI is 30- (oversold — bounce zone)
- Everyone is bearish (capitulation)
- Funding rates deeply negative (shorts crowded)

## How to Factor This Into Analysis

### Step 1: Do your normal analysis
- MACD, RSI, EMAs, volume, support/resistance

### Step 2: Flip the analysis
- "If I were shorting here, what would my thesis be?"
- "Where are the stops clustered?"
- "What would make this trade fail?"

### Step 3: Check the contrarian score
- **High contrarian risk:** All indicators aligned, obvious setup, crowded trade
- **Medium contrarian risk:** Some indicators aligned, some divergence
- **Low contrarian risk:** Contrarian view is WEAKER than your view

### Step 4: Size accordingly
- High contrarian risk → smaller size or skip
- Medium contrarian risk → normal size with tight SL
- Low contrarian risk → normal size

## Example: The Failed LONG (2026-10-16)

**Bullish analysis:**
- MACD crossover at 14:10
- Higher low: $81,868 vs $81,690
- Volume spike on dip: 2.1x
- RSI 55 (healthy)

**What contrarian analysis would have caught:**
- MACD crossover happened AFTER a +0.5% bounce from lows (late entry)
- Price was approaching resistance at $82,488 (11:30 high)
- Volume spike was on the DIP, not on the recovery (buying the dip, not confirming trend)
- RSI went from 32 to 68 in 20 minutes (overbought chase)
- We were the 3rd LONG attempt today (SMART MONEY FADES REPEAT ATTEMPTS)

**Contrarian score:** HIGH RISK — should have skipped or sized down.

## Integration with Existing Analysis

Use this skill IN ADDITION to:
- `ai_trader_precheck.py` — technical gates
- `trade_watchdog` — regime context
- `brain auditor` — signal quality

The contrarian view doesn't replace technical analysis — it ADDS a layer of "what if I'm wrong?"

## The Golden Rule

**When the setup looks perfect, it's probably not.**

The best trades have:
- Some indicators aligned ✅
- Some indicators conflicting ⚠️
- A clear reason why the contrarian view is WRONG ✅

If there's no reason the contrarian view is wrong, the contrarian view might be right.

## Date
Created 2026-10-16 after BTC LONG failed at $82,409 despite "perfect" bullish setup. -4.99% loss. The MACD crossover, higher low, and volume surge were all real — but they were the trap.

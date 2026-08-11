# Trading Improvement Plan — Using Book Skills

## Overview

Leverage 15 trading book skills to improve Hermes trading system performance through better signal filtering, risk management, and systematic execution.

---

## Skills & Books Reference

### Technical Analysis Skills
| Skill | Book | Focus Area |
|-------|------|------------|
| [book_price_action](/root/.config/opencode/skills/book_price_action/SKILL.md) | How to Trade Price Action — Galen Woods | Candlestick patterns, chart patterns, trading setups |
| [book_divergence](/root/.config/opencode/skills/book_divergence/SKILL.md) | The Power of Divergence — David Carli | RSI/MACD divergence, reversal signals |
| [book_advanced_strategies](/root/.config/opencode/skills/book_advanced_strategies/SKILL.md) | 9 Advanced Strategies — Roman Sadowski | Momentum, MA crossover, Heikin-Ashi, Bollinger |
| [book_profitable_strategies](/root/.config/opencode/skills/book_profitable_strategies/SKILL.md) | 10 Profitable Strategies — Nikhil Porwal | Inside Bar, Doji, Engulfing, Darvas Box |
| [book_wyckoff](/root/.config/opencode/skills/book_wyckoff/SKILL.md) | The Day Trader's Bible — Richard Wyckoff | Tape reading, accumulation/distribution |

### Trading Methodology Skills
| Skill | Book | Focus Area |
|-------|------|------------|
| [book_first_trading_manual](/root/.config/opencode/skills/book_first_trading_manual/SKILL.md) | The First Trading Manual — Trader Tom | Foundations, technical analysis basics |
| [book_day_trading](/root/.config/opencode/skills/book_day_trading/SKILL.md) | Complete Guide to Day Trading — Markus Heitkoetter | Intraday setup, market selection, 7-step system |
| [book_day_trading_beginners](/root/.config/opencode/skills/book_day_trading_beginners/SKILL.md) | Day Trading Guide — Warrior Trading | Order types, chart reading, beginner basics |
| [book_swing_trading](/root/.config/opencode/skills/book_swing_trading/SKILL.md) | Practical Swing Trading — Larry Swing | Multi-day holds, The Master Plan |
| [book_short_swing](/root/.config/opencode/skills/book_short_swing/SKILL.md) | Short Swing Trading — David Graeme-Smith | SST methodology, systematic swing |

### Risk & Psychology Skills
| Skill | Book | Focus Area |
|-------|------|------------|
| [book_trading_psychology](/root/.config/opencode/skills/book_trading_psychology/SKILL.md) | Mastering Trading Psychology — Andrew Aziz | Mindset, emotional discipline, cognitive biases |
| [book_trading_volatility](/root/.config/opencode/skills/book_trading_volatility/SKILL.md) | Trading Volatility — Colin Bennet | Options, volatility hedging, derivatives |
| [book_liquidity_markets](/root/.config/opencode/skills/book_liquidity_markets/SKILL.md) | Liquidity, Markets and Trading — Ozenbas et al. | Market microstructure, execution costs |

### System Development Skills
| Skill | Book | Focus Area |
|-------|------|------------|
| [book_system_development](/root/.config/opencode/skills/book_system_development/SKILL.md) | Intro to Trading System Development — David Cardoza | Backtesting, Monte Carlo, systematic approach |
| [book_complete_guide_trading](/root/.config/opencode/skills/book_complete_guide_trading/SKILL.md) | The Complete Guide to Trading — CFI | Market structure, fundamentals, asset classes |

---

## Implementation Plan

### Phase 1: Risk Management (Week 1)
**Source Skills**: book_trading_psychology, book_day_trading, book_complete_guide_trading

| Change | File | Skill Source |
|--------|------|--------------|
| Add 1% max risk per trade | `signal_compactor.py` | book_trading_psychology |
| Add daily loss limit (3 losses = stop) | `run_pipeline.py` | book_day_trading |
| Implement ATR-based position sizing | `position_sizer.py` | book_complete_guide_trading |
| Add max portfolio heat (10% total risk) | `hermes_constants.py` | book_trading_psychology |

### Phase 2: Signal Filtering (Week 2)
**Source Skills**: book_price_action, book_divergence, book_wyckoff

| Change | File | Skill Source |
|--------|------|--------------|
| Add RSI divergence confirmation | `signals/` modules | book_divergence |
| Require volume confirmation on entries | `signal_compactor.py` | book_wyckoff |
| Add 200 MA trend filter | `signal_compactor.py` | book_price_action |
| Implement engulfing/inside bar confirmation | `signals/` modules | book_price_action |

### Phase 3: Entry/Exit Optimization (Week 3)
**Source Skills**: book_advanced_strategies, book_swing_trading, book_profitable_strategies

| Change | File | Skill Source |
|--------|------|--------------|
| Implement ATR-based trailing stops | `exit_manager.py` | book_advanced_strategies |
| Add multiple timeframe confirmation | `signal_compactor.py` | book_swing_trading |
| Implement measured move targets | `exit_manager.py` | book_profitable_strategies |
| Add pattern-based entries (Inside Bar, Engulfing) | `signals/` modules | book_profitable_strategies |

### Phase 4: Market Regime (Week 4)
**Source Skills**: book_wyckoff, book_liquidity_markets, book_system_development

| Change | File | Skill Source |
|--------|------|--------------|
| Add Wyckoff phase detection | `regime_detector.py` | book_wyckoff |
| Implement market regime filter (trending/ranging) | `signal_compactor.py` | book_system_development |
| Add liquidity filter (volume threshold) | `signal_compactor.py` | book_liquidity_markets |
| Backtest all changes with Monte Carlo | `backtester.py` | book_system_development |

---

## Quick Reference: When to Use Each Skill

### For Signal Generation
```
Ask: "Should I enter this trade?"
Skills: book_price_action, book_divergence, book_wyckoff
Check: Trend direction, pattern confirmation, divergence
```

### For Position Sizing
```
Ask: "How much should I risk?"
Skills: book_trading_psychology, book_complete_guide_trading
Rule: Max 1% per trade, max 10% portfolio heat
```

### For Exit Management
```
Ask: "When should I take profit or cut loss?"
Skills: book_advanced_strategies, book_swing_trading
Method: ATR trailing stop, measured move targets
```

### For Market Selection
```
Ask: "Should I trade this market/instrument?"
Skills: book_liquidity_markets, book_day_trading
Filter: Volume, spread, volatility, trend clarity
```

### For Psychological Discipline
```
Ask: "Am I following my rules?"
Skills: book_trading_psychology
Check: Daily loss limit, revenge trading, overconfidence
```

---

## Expected Outcomes

| Metric | Current | Target | Improvement Source |
|--------|---------|--------|-------------------|
| Win Rate | ~50% | 55-60% | book_divergence, book_price_action |
| Risk-Reward | 1:1.5 | 1:2+ | book_advanced_strategies, book_swing_trading |
| Max Drawdown | ~25% | <15% | book_trading_psychology, position sizing |
| Profit Factor | ~1.3 | 1.8+ | All skills combined |
| Trades/Day | ~10 | 5-7 (selective) | book_profitable_strategies |

---

## Verification Commands

```bash
# List all book skills
ls /root/.config/opencode/skills/book_*/

# Verify each skill has required sections
for skill in /root/.config/opencode/skills/book_*/SKILL.md; do
  name=$(basename $(dirname $skill))
  sections=$(grep -c "Entry Rules\|Exit Rules\|Position Sizing" $skill)
  echo "$name: $sections sections"
done

# Check skill count
ls /root/.config/opencode/skills/book_*/SKILL.md | wc -l
# Should return 15
```

---

*Created: 2026-08-11*
*Source: 15 trading books converted to skills*
*Status: Ready for implementation*

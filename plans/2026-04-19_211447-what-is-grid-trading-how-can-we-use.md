# Grid Trading — What It Is & How Hermes Can Use It

## 1. What Is Grid Trading?

Grid trading is a **market-neutral, range-bound strategy** that places a series of buy/sell orders at evenly spaced price levels (the "grid"). The trader profits from price oscillations within a defined range — each buy order fills at one grid level, and a corresponding sell order later fills at a higher grid level, capturing the spread.

### Core Mechanics
- **Define a price range**: Upper bound and lower bound
- **Divide into N grid levels**: E.g., range = $100–$110, 10 grids → each level is $1 apart
- **Place buy orders below price, sell orders above price**: At each grid level
- **When price drops and bounces**: Buy orders fill, sell orders profit
- **Accumulate on both sides**: Buy low → sell high → repeat

### Types
| Type | Description | Directional? |
|------|-------------|--------------|
| **Arithmetic Grid** | Equal $ spacing between levels | Market-neutral |
| **Geometric Grid** | Equal % spacing (logarithmic) | Market-neutral |
| **One-sided Grid** | Only buy or only sell side | Directional bias |
| **Inverse Grid** | Short on the way down, long on the way up | Market-neutral |

---

## 2. How Does It Differ from Surfing (Hermes' Current Approach)?

| Dimension | Surfing (Momentum/Trend) | Grid Trading |
|-----------|------------------------|--------------|
| **Market condition** | Trending markets | Ranging/sideways markets |
| **Signal type** | MACD crossovers, momentum acceleration | Price crossing grid levels |
| **Position management** | ATR TP/SL, trailing stops | Fixed grid levels, no SL |
| **Profit target** | Asymmetric (let winners run) | Small, frequent (spread per grid) |
| **Drawdown risk** | Concentrated in one direction | Spread across multiple levels |
| **Win rate** | Lower (cut losses, let winners run) | Higher (many small wins) |
| **Capital efficiency** | Depends on leverage | Locked across all grid levels |

---

## 3. How Could Hermes Use Grid Trading?

### 3.1 Dual-Mode System (Surfing + Grid)
Hermes already has a strong momentum system. Grid could be a **second mode** activated when:
- ADX is low (< 25) → no trend, sideways market
- RSI is in neutral zone (40–60 range)
- Price has been oscillating in a tight range (Bollinger Band width indicator)

### 3.2 Use Cases for Hermes

**A. Range-Bound Accumulation Mode**
- Pre-configure a grid in a coin you want to accumulate
- As price oscillates, buy at lower levels, sell at upper levels
- Net result: accumulate the coin while earning the spread

**B. Volatility-Adaptive Grid**
- Dynamically adjust grid spacing based on ATR
- Wide grids in high volatility, tight grids in low volatility
- Hermes already has ATR data — easy to plug in

**C. Overlay on Existing Surfing Signals**
- During a trend, grid can help accumulate on pullbacks
- Buy on grid levels during dips, sell back on trend continuation
- Provides mechanical entry points instead of discretionary timing

**D. Market-Making Mode**
- Place buy orders slightly below mid, sell slightly above
- Capture spread with small grid, provided T has the inventory

---

## 4. Proposed Implementation Plan

### Phase 1: Research & Design
- [ ] Define grid parameters in config (range, grid count, order size per level)
- [ ] Design the grid activation logic (when to switch modes)
- [ ] Define data structures: `grid_config`, `grid_state` (active levels, filled orders)
- [ ] Decide grid arithmetic type: arithmetic vs geometric spacing

### Phase 2: Signal Generation
- [ ] Create `grid_signals.py` module
- [ ] Detect range-bound market (ADX + BB width + RSI)
- [ ] Generate buy signals at lower grid levels, sell signals at upper grid levels
- [ ] Integrate with existing hot-set signal pipeline

### Phase 3: Order Execution
- [ ] Implement grid order sizing per level
- [ ] Track which grid levels have been filled
- [ ] Route grid orders through existing guardian execution path
- [ ] Handle partial fills and order cancellation on grid level exit

### Phase 4: Portfolio & Risk
- [ ] Define max capital allocated to grid mode (e.g., 30% of portfolio)
- [ ] Add global grid position limit
- [ ] Prevent grid orders from exceeding per-coin open position limits
- [ ] Graceful exit: flatten all grid orders if price exits range

### Phase 5: Backtesting & Tuning
- [ ] Backtest grid strategy on historical data for top coins (BTC, ETH)
- [ ] Optimize: grid count, spacing (arithmetic vs geometric), range width
- [ ] Compare Sharpe, win rate, max drawdown vs Surfing mode

### Phase 6: Paper Trading Validation
- [ ] Enable paper trading for grid mode
- [ ] Run for 1–2 weeks to validate signal accuracy
- [ ] Monitor fill rate, spread capture, and capital utilization

---

## 5. Files Likely to Change

| File | Change |
|------|--------|
| `brain/trading.md` | Add grid trading philosophy section |
| `signals/` (signal generation) | New `grid_signals.py` module |
| `guardian/` (execution) | Grid order handling in guardian pipeline |
| `config/` | New `GRID_*` config parameters |
| `hot-set.json` | Grid signals compete with existing signal sources |
| `brain/surfing.md` | Clarify dual-mode (Surfing vs Grid) market conditions |

---

## 6. Key Open Questions

1. **Capital allocation**: Should grid trades compete with surfing trades for capital, or run in a separate sleeve?
2. **Grid spacing**: ATR-based (adaptive) or fixed percentage?
3. **Range detection**: Who/what defines the grid range — manual input, auto-detected from recent range, or configurable per coin?
4. **Exit on range break**: When price exits the grid range, should all orders be cancelled or held?
5. **Leverage**: Should grid use leverage? A grid in a volatile coin with 10x leverage could blow up.

---

## 7. Risks & Tradeoffs

| Risk | Mitigation |
|------|-----------|
| Price gaps through grid range (no fills on bounces) | Wide range + stop out below lower bound |
| Capital locked in losing side of grid | Limit grid levels (e.g., max 5 levels per side) |
| Grid vs trend conflict | Grid only activates when trend indicators say "sideways" |
| Complexity creep | Keep grid as a separate mode, not entangled with surfing |

---

## 8. Quick Win: Simple Manual Grid (No Code Change)

Before any implementation, T can manually run a grid on Hyperliquid:
1. Pick a coin in a range (e.g., check if ADX < 25)
2. Set buy orders at 5 price levels evenly spaced below current price
3. Set sell orders at 5 price levels evenly spaced above current price
4. Each order is equal size
5. Monitor — as price bounces, fills happen automatically
6. Stop: if price breaks below lowest grid level or above highest

This can be tested RIGHT NOW without any code change.

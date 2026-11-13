---
name: manual-trade-override
description: Use when the CEO wants to manually open a trade bypassing signal gates. Triggers on "open X manually", "force trade", "manual override", "open X now". ONLY use when CEO is present and explicitly requests it.
---

# Manual Trade Override

Open trades directly on Hyperliquid, bypassing signal gates. **ONLY use when CEO is present and explicitly requests it.**

## When to Use

- CEO says "open X manually" or "force trade X"
- Signal gates are blocking a trade the CEO wants
- Testing/debugging trade execution
- Market conditions require immediate action

## When NOT to Use

- Automated trading (watchdog/pipeline handles this)
- When CEO is not present
- Without explicit CEO confirmation

## Command

```bash
cd /root/.hermes/scripts && python3 brain.py trade add COIN DIRECTION AMOUNT ENTRY --real --manual --signal ai-trader-manual --strategy ai-trader --confidence 70 --leverage 5 --sl STOP_LOSS --target TAKE_PROFIT
```

**`--manual` flag**: Bypasses the vacation guardrail pause marker. Without it, manual trades are blocked when the guardrail auto-pauses (7d WR < 35%). The guardrail still gates automated signal execution — only direct CEO commands with `--manual` pass through.

## Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `COIN` | ✅ | Token symbol (uppercase) | `GRASS` |
| `DIRECTION` | ✅ | `long` or `short` | `long` |
| `AMOUNT` | ✅ | USDT amount (before leverage) | `11.10` |
| `ENTRY` | ✅ | Current market price | `0.86897` |
| `--real` | ✅ | Real trade (not paper) | `--real` |
| `--manual` | ✅ | Bypass vacation pause marker | `--manual` |
| `--signal` | ✅ | Signal source tag | `ai-trader-manual` |
| `--strategy` | ✅ | Strategy name | `ai-trader` |
| `--confidence` | ✅ | Confidence 0-100 | `70` |
| `--leverage` | ✅ | Leverage 1-10 | `5` |
| `--sl` | ✅ | Stop loss price | `0.8437` |
| `--target` | ✅ | Take profit price | `0.8853` |

## Pre-Trade Checklist

**ALWAYS run the precheck before opening:**
```bash
cd /root/.hermes/scripts && python3 ai_trader_precheck.py COIN DIRECTION
```

The precheck is ADVISORY for CEO trades (2026-10-22 standing rule): a FAIL never blocks, but it MUST be reported to the CEO, never hidden. It tells you:
- RR engine verdict (context only — the RR engine does NOT manage CEO trades, see THE CONTRACT below)
- RSI position — direction sanity vs extremes: never short an extreme oversold / long an extreme overbought (BANANA lesson: entry at RSI 10.53 was the fault, not the timing)
- Volatility (is there room for SL/TP?)
- 30d winrate (is this coin a known loser?)

**Before hitting enter — the three mandatory checks:**
1. **Explicit levels**: `--sl` and `--target` ALWAYS set — bare opens are never acceptable
2. **Leverage**: 5x in chop (≥2 EMA300 flips/24h), 10x max, 40x only ever TREND + volume (#16307: a -0.53% sweep cost -21.4% margin at 40x)
3. **Fill sanity**: current price vs the level you're entering at — if price has already blown through your SL zone, the trade is dead on arrival (#16350: filled 488pt deep, below its own SL, closed on the first tick)

## Example: Open GRASS LONG

```bash
# 1. Precheck
cd /root/.hermes/scripts && python3 ai_trader_precheck.py GRASS LONG

# 2. Get current price
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/candles.db')
cur = conn.cursor()
cur.execute('SELECT close FROM candles_5m WHERE token=\"GRASS\" ORDER BY ts DESC LIMIT 1')
print(cur.fetchone()[0])
conn.close()
"

# 3. Open trade (example: $11 USDT, 5x leverage, SL 3% below, TP 4% above)
python3 brain.py trade add GRASS long 11.10 0.86897 --real --manual \
    --signal ai-trader-manual --strategy ai-trader --confidence 70 \
    --leverage 5 --sl 0.8437 --target 0.8853
```

## What Happens After Opening

1. **Trade opens on Hyperliquid** — mirrored position
2. **PostgreSQL records trade** — `signal='ai-trader-manual'`, `atr_managed=False`
3. **Dashboard shows trade** — via trades.json (updated every minute)
4. **Exit management activates** — `manual_exit_manager.py` is the SOLE exit authority for this trade (THE CONTRACT below): your predefined SL/TP + one close trail, nothing else rewrites levels
5. **Guardian protection** — safety nets only (hard caps, max-hold, staleness)

## Exit Management

CEO trades do NOT use the rr_engine/ATR exit path — **THE CONTRACT below is
authoritative** (this section said "same as AI trader signals" before
2026-10-22; that was pre-contract and is wrong). Summary: your predefined
SL/TP are honored exactly as set, one close trail (0.40% activate / 0.20%
distance / ratchet-only), guardian safety nets on top, and the
`manual_sl_hit`/`manual_tp_hit`/`manual_trail_hit` labels are the ownership
receipt.

## Exit Management for CEO Trades — THE CONTRACT (manual / pending / auto)

**`scripts/manual_exit_manager.py` is the SOLE exit authority for these
trades** (CEO directive 2026-10-22). The rules:

1. **Predefined SL/TP are honored exactly as set.** You set them at open
   (`--sl` / `--target`); NOTHING structurally rewrites them. Every other
   SL actor is excluded for these signals: the RR engine (was moving them
   — #16306 81990→82486, #16317 83150→82965), sl_zones tighten, the soft
   peak-trigger, the ATR level manager, the watchdog `move_stop` auto-exec,
   the pump/ride gates, and profit-monster (`ai-trader` substring
   bypass). Auto signal trades
   (ai-trader+/pump-chain etc.) keep all their engines — the exclusion is
   CEO-trade-only.
2. **Dynamic SL in profit** (CEO-approved 2026-10-23/24) — two steps,
   CAS-protected (your concurrent edits always win), TP never moves:
   - **BREAKEVEN LOCK at +0.10%** (PM_BREAKEVEN_LOCK_PCT): SL → entry.
     Turns chop-wiggles into scratches — #16353 −1.53% / #16358 −1.03%
     max-hold exits would both have been 0.00%. 3-trade backtest: net
     +4.65% vs +2.09% without it.
   - **TIERED PEAK TRAIL from +0.40%** (PM_TRAIL_ACTIVATE_PCT): the profit
     floor = PEAK − giveback tier (**MANUAL_TRAIL_TIERS**, roomier than
     profit-monster's on purpose — CEO directive 2026-10-24: "survive
     slightly bigger pullbacks", sized ~1.1x 1h ATR so a #16381-class
     bounce off the peak doesn't clip the trade):
     peak <1.5% → **0.50%** giveback · ≥1.5% → 0.70% · ≥3.0% → 1.00% ·
     ≥5.0% → 1.40%. Floor never below breakeven; the TP stays the
     giant-candle backstop. Tier boundaries intentionally LOOSEN the
     floor on our own stops (PM semantics); a stop you tightened by hand
     is only ever improved, never relaxed.
   - **WATCHDOG STRUCTURE-FOLLOW (30-min) — coexists with the trail**
     (CEO synthesis 2026-11-10: "trailing so we book profits... fluid
     enough to survive chop unless structure is broken... the watchdog
     adjusting stops as the trade progresses"): every watchdog cycle
     the full-analysis tweak adjusts the stop fluidly — risk-side stops
     (wrong side of entry) ALIGN to the 15m swing ±0.10 ATR (survival
     IS structure, either direction), profit-side stops only DEEPEN
     (never relax — cannot undo what the trail booked). Trail books on
     2-min pipeline cycles, watchdog follows structure on 30-min;
     CAS + improve-only on both sides means they never fight.
     Conditional orders carry the fluid trail profile by default
     (skip_be/giveback/min_lock) unless `dynamic_sl: false`
     (structure-only — tweak governs alone).
3. **Safety nets remain**: guardian hard caps, max-hold, staleness checks
   still apply — safety, not exit management. Guardian hard-stop closes
   relabel to `manual_*` too (bug_hunter F-1 fix 2026-10-24 — the label
   race that recorded 2 CEO trades as `hard_tp`).
4. **Exit labels are the ownership receipt:**
   - `manual_sl_hit` — your predefined stop did its job
   - `manual_tp_hit` — your predefined target hit
   - `manual_trail_hit` — the close trail took profit
   - Seeing `rr_engine_*` or `atr_*` on one of these trades = a routing
     bug — report it immediately.
5. **OPEN ITEM (bug_hunter 2026-10-22, pending CEO ruling):** structural
   CLOSE actors — `wave_turn`, MACD cascade flips — can still exit these
   trades. They don't write SLs (contract item 1 holds) but they are a
   third exit philosophy. `cut_loser`/`stale_exit`/weather-vane are
   treated as safety. Ruling pending: leave / exclude the structural two
   / strict safety-only.

### Setting/adjusting manual SL

After opening, move SL freely (e.g. to breakeven) — your write wins:

```bash
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
import psycopg2
from _secrets import BRAIN_DB_DICT
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute('UPDATE trades SET stop_loss = %s WHERE id = %s AND status = %s', (NEW_SL, TRADE_ID, 'open'))
conn.commit()
conn.close()
print('SL moved to', NEW_SL)
"
```

**When to set manual SL:**
- Trade is in profit and you want to make it risk-free
- You have a specific level in mind (support/resistance)
- You want to override for any reason — trailing resumes from YOUR level
  once profit ≥ 0.40%, ratcheting only tighter

## Verification

After opening, verify — **levels included, and compare them to what you set**:
```bash
# 1. PostgreSQL (source of truth) — must show your exact SL/TP/leverage
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
import psycopg2
from _secrets import BRAIN_DB_DICT
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute('SELECT id, direction, entry_price, stop_loss, target, leverage, signal, status FROM trades WHERE token=%s AND status=%s ORDER BY id DESC LIMIT 1', ('COIN', 'open'))
for row in cur.fetchall():
    print(f'#{row[0]} {row[1]} entry={row[2]} SL={row[3]} TP={row[4]} lev={row[5]}x signal={row[6]} status={row[7]}')
conn.close()
"
# 2. Exchange side (verify, don't trust) — DB and HL must agree
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import get_open_hype_positions
print(get_open_hype_positions())
"
```
Mismatch between DB levels and what you set = fix before walking away.
Also note the FILL vs your entry price (adverse slip in fast tape — see
arming rule 9) — report it, it feeds the slip-buffer sizing.

## Safety Notes

- **This bypasses signal gates** — the trade will open even if RSI, RR engine, or other filters would normally block it
- **Exit management still applies** — via `manual_exit_manager` (THE CONTRACT): your predefined SL/TP + one close trail; guardian safety nets on top — NOT the rr_engine path
- **Use appropriate position sizing** — manual trades should be same size as signal trades ($11-20 USDT)
- **Log the reason** — include why you're overriding in the `--signal` or notes

## Conditional (Pending) Orders — arming rules

Config: `/root/.hermes/data/pending_orders.json`. **Execution cadence:
the pipeline runs `pending_order_monitor` FIRST every ~1 minute** (CEO
directive 2026-11-08: fills within the minute, not on the watchdog
clock) — it shares trade_watchdog's monitor/execute path and autopilot
gate; the 30-min watchdog cycle monitors too (one-shot state makes the
double caller safe). Fires via `brain.py trade add` with
`ai-trader-pending` (NO `--manual` → vacation pause still gates) plus
`--force` for CEO tranches. One-shot: fires once, never re-arms — state
is cross-process LOCKED (flock; pipeline 1-min + watchdog 30-min share
it, fail-closed on corrupt); orphaned `triggered` state surfaces as an
urgent steer after 15min (re-arm = delete the state entry). **Verify any
armed order with the engine on a temp state AND temp config path — never
the live ones** (bug_hunter incident 2026-11-09: a probe patched only
the state path, clobbered the live config, and the pipeline filled it →
duplicate real trade #16832).

**The arming lessons (all paid for in real money, 2026-10-19/20):**

1. **Cushion the trigger beyond the level — the cushion IS your wick
   filter.** The engine fires on price CROSS, not candle close, so a
   trigger AT the level is a wick-catcher. Trigger at an 83,439 peak fired
   on every poke; the fix was 83,500 — ~60pts beyond the peak (CEO number
   for BTC at 0.4-0.5% ATR). Cushion = recent wick depth, floor ~50-60pts
   on BTC; the far overshoot (83,560) costs breakout catches, so size the
   cushion to the wick, not beyond it. R:R always re-quoted after cushioning.
2. **Triggers near fresh minor support/resistance = sweep-catchers.** A
   trigger 70pts under a just-formed ascending-lows shelf (#16317 SHORT
   -2.13%) fired on the LIQUIDITY GRAB below the shelf — buyers were
   stacked right there (full-analysis §11). Breakdown/breakout triggers go
   at MAJOR structure: the 1h/4h swing levels from structure_analysis.py,
   never a shelf formed in the last few bars.
3. **SLs need wick room: 200+ pts in BTC chop.** A 70pt SL got slipped;
   a 226pt SL got slipped 208pts (#16273); a fast-tape fire slipped 281pt
   adverse on the fill (#16353, 2026-10-22). Quote REAL R:R with a
   100-200pt slip buffer — if real R:R < 1.0, deepen the TP or don't arm.
4. **Both-sides brackets must be verified non-overlapping** — each order's
   SL must sit between the other's trigger path, so neither can be open
   when the other fires (no same-coin hedge/netting surprise).
5. **Same-coin tranches merge on HL** — first level hit closes the whole
   position; align TPs when a runner should run (#16306/16307: staged TPs
   were void, the lower one clipped everything).
6. **Leverage: 5-10x ceiling in chop** — 40x turned a -0.53% sweep into
   -21.4% margin (#16307). Max leverage is for TREND + volume, never chop.
7. **Precheck runs and its FAIL reasons go in the order `note`** — advisory
   for CEO trades, never hidden.
8. **Direction mapping is printed back and confirmed BEFORE the config is
   written** (full-analysis §12): **lower break = SHORT, upper break =
   LONG** — the mapping, at the CEO's own levels. 2026-10-22 miss: an
   analyst proposal wired BOTH bracket legs LONG; at the 84,240 break a
   LONG fired while the CEO expected a SHORT — the 1,100-pt decline went
   the wrong way. When the CEO writes the level together with the
   direction ("short below X, long above Y"), that sentence IS the
   confirmation — quote it back and arm.
9. **After a fire, verify the FILL against the trigger and the SL.**
   #16350: filled 488pt deep — already through its own SL, dead on
   arrival, closed on the first tick. #16353: 281pt adverse slip in a
   fast tape (still a live, workable trade — entry 281pt worse, SL/TP
   unchanged). Report the slip; a fill ALREADY beyond the SL is a bug
   event — stop and report (fill-sanity engine guard pending CEO ruling).
10. **The TP must be reachable within the 8h max-hold at prevailing ATR.**
    `UNIVERSAL_MAX_HOLD_MINUTES = 480` force-closes every trade by TIME —
    a thesis-true trade still exits at whatever price the clock finds.
    #16353: TP 80,300 sat 839pts (~1.6x 1h ATR) below entry in 8-flip
    chop; MFE in 8 hours was 91pts, max-hold closed it −1.53% (SL never
    hit, exit still beat holding). Contrast #16351: 732pt TP filled in
    2h17m on fresh momentum. Rule: in chop/mixed scale TP to ≈1x 1h ATR
    of realistic momentum travel; deep-shelf TPs are for TREND + volume.
    **Corollary (from #16358, −1.03%): the TP goes at the FIRST opposing
    structure level, never past it.** #16358's MFE touched the 82,034
    coil top EXACTLY — that was the first opposing level and it would
    have filled; the armed 82,400 deep-shelf TP sailed past the only
    structure the tape actually reached in 8 hours. When the first
    opposing level can't pay real R:R ≥ 1.0 after buffers, the trade is
    too close to the level to arm — don't reach for a deeper TP to fix
    the math, skip or re-shelve further away.
11. **Count the impulse BEFORE arming a continuation.** If the move that
    motivated the trigger has ALREADY traveled ≥ 1x 1h ATR, the
    "continuation" entry is the mid-flush knife (§11-5) — the market has
    spent the leg and your TP needs a second move that rarely comes.
    #16377 (−3.42%): the coil breakdown traveled 605pts (81,118→80,513)
    before the 80,840 trigger fired; the TP needed 679 more; MFE was
    27pts and the 81,200 retest of the broken floor — the textbook
    structure — was the stopper. When late: wait for the RETEST of the
    broken level with a reclaim/fail confirmation, never arm the flush
    itself.
12. **Break-continuation entries: `"dynamic_sl": false` + the structure
    stop** (CEO 2026-11-09, #16827 + #16834). The BE/trail stack tightens
    INTO the retest zone — it stopped #16827 at breakeven-ish 45 minutes
    before the move resolved. Order field `dynamic_sl: false` hands SL
    authority to the watchdog's full-analysis tweak (every 30-min cycle):
    the stop sits just BEYOND the 15m swing (retest ceiling/floor) and
    **exits only when structure ACTUALLY breaks** — no entry-relative
    cap (the ±0.5% cap was REMOVED by CEO 2026-11-09 17:00: it forced
    #16834's stop into the noise, 130pts above structure, and the move
    then ran +691 without us; structure IS the risk bound). Since
    2026-11-12 the watchdog's **STRUCTURE-LAG trailing** is the stop
    authority on managed trades: state remembers the last **15m** swing
    — structure unchanged → stop untouched; a FAVORABLE new swing
    (short: lower high) → bump to the now-OLD swing ±0.10 ATR (one
    behind, so only a REAL structure break hits — interior retests
    can't, #16871); an ADVERSE new swing (short: HIGHER high) → NEVER
    chase the stop with it — keep it, or at most RAISE it to the new
    structure so a crossing = a break at the real line (#16882: the
    72224 bounce made the old code drop the stop 72327 → 71771 under
    price and exit 71789 while the CEO's 72500 line was never
    touched); birth = RE-ANCHOR (2026-11-13, supersedes the earlier
    seed-only rule): an interior stop — above the major-floor-reclaim
    zone (sl1h+0.6·ATR15) and below the ceiling line — moves to the
    major line at birth; floor-zone/dictated stops and stops already
    at/behind the line are kept (#16879-class note: its 73010 would
    have re-anchored to ~73674 — harmless, price never returned). The stop therefore TRAILS DOWN
    on shorts as 15m LHs print (proven: 73112 → 72919 across two
    formations), locking profit with structure. **EXITS ARE STRUCTURE-
    BREAK ONLY — the standing doctrine, restated emphatically by the
    CEO (2026-11-13): "unless structure is broken we don't exit — how
    can structure be broken if something is going straight down?"**:
    the watchdog NEVER moves a TP, and a TP is NEVER a take-profit —
    it is a DISASTER circuit breaker set at ≥3·ATR1h depth (rule-10
    snap removed earlier for booking loss-"TPs"; 2026-11-13: TP caps
    during directional travel cost the difference between **7
    fragmented trades Nov-11 19:00 → Nov-13 = +16.0% margin** and
    **ONE structure-held ride from the same timestamp = +37.3% to the
    cited low (+39.5% to the span low 68,608)** —
    every cap during a straight-down move is that ≈23pt-of-margin
    gap ≈59% of the ride itself). Guardian/max-hold still apply.
    (Counterfactual noted honestly:
    on #16827 itself the trail's exit beat the structure stop by
    ~1.7pts-of-margin — the fake-out resolved UP; the rule is for when
    the retest precedes the REAL leg.)
13. **ALWAYS arm the short ladder — readiness is the default**
    (CEO 2026-11-10: "there is always a short we want to be ready for...
    it is about probabilities, anything can happen"). **LADDER KEEPER
    (2026-11-13, auto) — BOTH SIDES:** `auto_trader._ladder_keeper` runs
    every watchdog cycle: (a) no unfired **BTC** short rung WITHIN REACH
    (≤3·ATR1h below price — a far-below rung does NOT count) → derive at
    the **1h MAJOR floor** (trigger = sl1h − 60, reclaim SL = sl1h +
    0.6·ATR15, TP = trigger − 3·ATR1h disaster depth AT ARM TIME;
    loop-safe: a derived trigger outside reach — including price already
    at/below it — is skipped); (b) no
    unfired BTC long rung
    WITHIN REACH (≤3·ATR1h above price — stacked 72k+ rungs do NOT count,
    a rubberband snap from 68k would leave them behind) → derive at the
    **1h-major-ceiling reclaim** (trigger = sh1h + 60, SL = sh1h −
    0.6·ATR15, TP = trigger + 3·ATR1h AT ARM TIME). All keeper legs
    `serial` + `dynamic_sl:false`. **POSITION SIZING (CEO 2026-11-13:
    "add on winners, remove from losers")** — derived rungs size at
    **2× base ($22.20) when the side's last-5 closed BTC trades net
    positive**, base ($11.10) otherwise; the HL $11 min-notional floor
    means losers cannot shrink below base — "removing from losers" is
    expressed as no pyramid + serial cuts, not smaller notional. The
    ladder is never empty on either side after a fire/TP (CEO: "you
    better be ready for the longs too — rubberband snapping back").
    Single-writer: only run_cycle. **Ride doctrine
    (CEO: "we ride the trend till it is over — the trend is your friend,
    till it ends"):** the structure-lag trail IS the ride mechanism —
    entries are the rungs, exits are structure breaks, nothing else.
    Never report "no
    short armed" or ask the CEO for short levels — derive the ladder
    from the chart yourself and arm it: **rung 1** = local-low break
    (quick-move, own tight TP/SL, local structure OK per §13 quick-leg),
    **rung 2** = trendline break (the CEO's trendline touches — fit the
    line from the touch points, trigger cushioned under it, SL above the
    touch zone, TP into the void with disclosure), **rung 3** = major-low
    break (SL = reclaim of the low band, TP = measured move into the
    void, disclosed). Each rung gets its OWN TP/SL. Legs carry
    `serial: true` — the monitor's stacking guard fires them rung-after-
    rung (only when flat: no merge, no state burn, no double-size).
    Longs mirror the same way. The real-R:R gate still REPORTS (run like
    the 73,350 leg run at real 0.55 — disclosed in the note as a CEO
    ladder override); probability weighting decides which rung matters,
    not whether to arm.

**Tranche adds to an existing position:** brain.py's duplicate guard blocks
a second same-coin open — for a CEO-directed add pass `--force`
(manual-only; the pipeline never passes it — the pending engine now does,
CEO-configured orders only, 2026-10-24). Remember same-coin tranches
MERGE on Hyperliquid (rule 5): first level closes the whole position, so
align TPs before adding.

**⚠️ The flat check BEFORE arming any same-coin add (learned from #16384,
2026-10-24):** if a PIPELINE position is open on the coin, the add merges
into it and — pre-fix — the pipeline's exit stack (profit-monster trail)
governed the whole merged position: #16384 was trailed out at PM's 0.20%
giveback 90 seconds after opening, its own BE-lock/tiered trail never
acted (`HL_CLOSED`), and both rows re-synced to a blended entry (§11-7
attribution corruption; the visible +2.72% was the OTHER row's ride).
Fixes shipped: profit_monster + cut_loser now skip any token holding an
`ai-trader-manual/pending/auto` row (token-level CEO guard — exit
authority follows the contract, not the row). Procedure still stands:
**check the coin is flat first** — the pipeline row's ATR SL/TP still
participates on a merged position, and attribution corrupts either way.

## Related Skills

- `signal-lab` — for testing signal logic
- `signal-backtest` — for backtesting before manual entry
- `trade-analysis` — for analyzing trade outcomes

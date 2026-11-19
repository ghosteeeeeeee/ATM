# Kill Lines — per-signal-source pre-committed lines (item I, SHADOW)

**Authorization:** CEO deep-run decision `20261108T023937Z` row **I** — OAK, SHADOW
("record distance-to-line + alert, no auto-remove"). Built by D5 for run
`20261119T141548Z`. **Log-only: zero trading-path behavior change, ever, in this phase.**

Machine-readable registry: **`brain/kill_line_registry.json`** (tracked in git — lines
change only via a committed `--derive` refresh, never at runtime). Runtime distance log
(gitignored): `data/kill_line_shadow.jsonl`. Monitor: `scripts/kill_line_shadow.py`
(systemd timer `hermes-kill-line-shadow.timer`, hourly).

## What a kill line is (as pre-registered)

> line = **2 × the source's worst drawdown in its tested/training baseline**
> (`KILL_LINE_MULT = 2.0`, decision row I).

## ⚠️ Provenance — READ BEFORE TRUSTING ANY LINE

- **These are REALIZED lines, not TESTED lines.** The brief said "2× worst *backtested*
  DD", but this repo has **no per-source backtested drawdown** — only realized trade
  history (PostgreSQL brain `trades`, `status='closed'`). The baseline here is derived
  from the source's realized **cumulative-PnL drawdown** over a stated window.
- **Split mirrors `scripts/streak_analysis.py`** (fresh, well-verified, SELECT-only):
  90d window → **first 60d = train (derive), last 30d = validate**, split data-anchored
  on the last close_time (not wall clock). Anchor for this registry:
  `2026-11-19 12:29:10.021132`, split `2026-10-20 12:29:10.021132`.
- **Every line is PROVISIONAL until a backtest baseline exists.** `provisional: true`
  is stamped on every registry source.
- **A historical max is NEVER a hard bound** (Wallace mining rule): the next drawdown may
  exceed anything seen in train — the validate column already shows this for
  `r2v2-long3` (train DD 0.23 → line 0.46, but validate DD 0.66 already exceeds the
  line). Crossing a line is an *alert*, not proof of a broken source.
- **Thin sources get no line:** `n_train < 10` → skipped (254 sources
  this run — mostly 1-2-trade confluence combo strings). Sources with all trades inside
  the validate window (e.g. `jup_yolo_mirrored`, `atr-trend±` — labels live only since
  late Oct/early Nov) have **no train baseline → no line → reported as UNREGISTERED**
  by the monitor until a future `--derive` gives them 10+ train trades.
- One source (`continuum_engine`) had **zero** train drawdown → line 0.0 → monitor
  reports `NO-LINE` (division guard), needs re-derive.

## Registry (derived 2026-11-19, n=45 lines)

| signal source | kill line (USDT) | train max DD (60d) | n_train | validate DD (30d) |
|---|---:|---:|---:|---:|
| `ct_hot` | **9.24** | 4.62 | 59 | 0.0 |
| `pullback-entry-` | **6.06** | 3.03 | 119 | 0.0 |
| `hl_copy_trader` | **3.78** | 1.89 | 73 | 0.51 |
| `ema300_dip` | **3.42** | 1.71 | 55 | 0.0 |
| `pump-chain+` | **3.38** | 1.69 | 142 | 0.7 |
| `mover+` | **3.36** | 1.68 | 23 | 0.0 |
| `accel_300_v3_long` | **3.28** | 1.64 | 39 | 0.0 |
| `ema300_dip_short` | **3.28** | 1.64 | 24 | 0.0 |
| `pump-chain-` | **3.06** | 1.53 | 171 | 0.38 |
| `slow_grind` | **3.04** | 1.52 | 27 | 0.0 |
| `pump_chain` | **2.94** | 1.47 | 43 | 0.0 |
| `volume-breakout-long+` | **2.72** | 1.36 | 40 | 0.0 |
| `trend_purity+` | **2.44** | 1.22 | 11 | 0.0 |
| `bb-bounce-v2-long+` | **2.26** | 1.13 | 61 | 0.66 |
| `bb_bounce` | **2.26** | 1.13 | 39 | 0.0 |
| `sma20_dip` | **2.14** | 1.07 | 19 | 0.0 |
| `ai-trader+` | **2.1** | 1.05 | 29 | 0.0 |
| `bb-squeeze+` | **2.1** | 1.05 | 73 | 0.61 |
| `doji-bottom-long` | **1.94** | 0.97 | 36 | 0.0 |
| `bb_bounce_v2_long` | **1.9** | 0.95 | 73 | 0.0 |
| `coiled_spring` | **1.72** | 0.86 | 21 | 0.0 |
| `accel_300_v2_long` | **1.68** | 0.84 | 21 | 0.0 |
| `mover-` | **1.62** | 0.81 | 12 | 0.0 |
| `accel_300_v` | **1.54** | 0.77 | 78 | 0.0 |
| `bb-bounce-v3-long+` | **1.48** | 0.74 | 20 | 0.0 |
| `bb_bounce_short` | **1.46** | 0.73 | 65 | 0.0 |
| `open-skies+` | **1.46** | 0.73 | 11 | 0.0 |
| `macd_div` | **1.38** | 0.69 | 37 | 0.0 |
| `r2_trend_long` | **1.32** | 0.66 | 19 | 0.0 |
| `pump-chain-v5` | **1.26** | 0.63 | 12 | 0.0 |
| `continuation` | **1.24** | 0.62 | 11 | 0.0 |
| `bb_bounce_long` | **1.22** | 0.61 | 25 | 0.0 |
| `open_skies` | **1.22** | 0.61 | 19 | 0.0 |
| `rr-struct-v2+` | **1.08** | 0.54 | 10 | 0.0 |
| `pump_catcher` | **1.06** | 0.53 | 21 | 0.0 |
| `grind-trend+` | **0.96** | 0.48 | 18 | 0.0 |
| `hzscore` | **0.96** | 0.48 | 10 | 0.0 |
| `rr-struct+` | **0.8** | 0.4 | 15 | 0.0 |
| `tl_break_short` | **0.74** | 0.37 | 16 | 0.0 |
| `accel_300_v2_short` | **0.72** | 0.36 | 11 | 0.0 |
| `r2_trend_short` | **0.7** | 0.35 | 20 | 0.0 |
| `ai-trader-manual` | **0.52** | 0.26 | 13 | 0.17 |
| `r2v2-long3` | **0.46** | 0.23 | 10 | 0.66 |
| `ichimoku_,rs_r` | **0.42** | 0.21 | 11 | 0.0 |
| `continuum_engine` | **0.0** | 0.0 | 11 | 0.0 |

Exact query used (printed by every run, `n` = params[0]):

```sql
SELECT close_time, signal, pnl_usdt FROM trades WHERE status = 'closed' AND close_time > NOW() - make_interval(days => %s) ORDER BY close_time ASC
```
SQL bind param: `(90,)` (single `n` = window days). Registry derivation params:
`days=90, train_days=60, min_train_n=10, multiplier=2.0`
(window: trailing 90d, status=closed, ordered by close_time ASC)

## Shadow monitor behavior (Phase 1 — what is actually wired)

- `python3 scripts/kill_line_shadow.py` — computes each registered source's current
  cumulative-PnL drawdown over a trailing window (default **30d**, `--window-days`),
  logs `pct_consumed = current_dd / line` per source to `data/kill_line_shadow.jsonl`
  **every run** (distance history for the eventual enforce read).
- **`ALERT` line when ≥ 80% of the line is consumed** (pre-registered "shadow logs
  approach always" limb) + `CROSS` at ≥ 100% — printed `[KL-SHADOW]` and appended to
  `automation/error_alerts.md` (24h per-source dedup, freq_deviation_shadow convention
  → lands on the CEO dashboard consumer chain).
- **Nothing is ever disabled, blocked, or imported by the trading path.** SELECT-only,
  cursors closed in `finally`, fail-open (exit 0), no `hermes_constants` import.
- First live reading (2026-11-19): **`r2v2-long3` CROSS at 143.5%** (dd 0.66 vs line
  0.46, n=26) — logged + alerted, **no action taken** (correct: shadow phase). Highest
  healthy consumption otherwise: ai-trader-manual 32.7%, bb-bounce-v2-long+ 29.2%,
  bb-squeeze+ 29.0%.

## ENFORCE limb — pre-registered, never unattended (automatic-implementation wiring)

Per decision row I, auto-disable of a source may happen **only** when ALL of:
1. **actual kill line CROSS** (pct_consumed ≥ 100% in `data/kill_line_shadow.jsonl`), **AND**
2. **negative PnL over that source's next 10 closed trades** (`pnl_usdt`, PG), **AND**
3. **explicit CEO approval** — never unattended, never automatic.

Wired to surface **automatically on 2026-12-03 (~14d)** via two registered entries:
- `data/checkpoint_registry.json` → `kill-line-enforce-review-20261203` (pending;
  `hermes-checkpoint-watch` timer surfaces a DUE/OVERDUE packet into
  `automation/ceo/ceo_kanban.md` + `error_alerts.md` → lands in a CEO run).
- `data/shadow_disposition.json` → `kill-line-shadow-enforce` (kind=shadow,
  deadline 2026-12-03; the daily `hermes-shadow-disposition` runner emits the
  decision-due / default packet. **Default action = KEEP SHADOW log-only.**)

Neither entry carries `auto_flip_flag` — no code path can flip enforcement itself.

## Reproduce / refresh

```bash
python3 scripts/kill_line_shadow.py --selfcheck     # math asserts, no DB
python3 scripts/kill_line_shadow.py --derive        # re-derive lines (commit the diff)
python3 scripts/kill_line_shadow.py                 # one shadow evaluation
python3 scripts/kill_line_shadow.py --window-days 7 # shorter measurement window
```

Rollback: `systemctl disable --now hermes-kill-line-shadow.timer`, delete script +
units + registry — log-only, no DB or trading-path state was ever written.

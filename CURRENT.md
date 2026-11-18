# Current State — brain_auditor #277 2026-11-18 20:57 UTC
**Last Updated: 2026-11-18 20:57 UTC**
**Updated by: brain_auditor #277. Prior: #276 2026-11-18 08:55 UTC (preserved in git history).**

## HEADLINE — ROOT-CAUSE BUG: bare `HERMES_DATA` in brain.py was silently killing two live paths

1. **The bug:** `brain.py` only did `import paths` — never the name `HERMES_DATA`. Two sites used the bare name inside `try/except Exception: pass`: the **guardian race-marker write** before `mirror_open` (dead for every non-decider fill = ai-trader-pending + manual skill trades; the decider path wrote the same file itself, hiding the gap) and the **vacation size-reduce read** on the fallback-size branch (the 2026-10-21 bug_hunter HIGH fix was inert; no live impact only because the file is currently absent = 1.0x). Fixed with one import line.
2. **Second ship:** BTC tape-state stamp in `add_trade` — `btc_ema300_*` coverage was 154/192 (80%) of 14d closes; the 38 missing are **100% ai-trader-pending** (trade_watchdog passes no `--signal-metadata-json`; #117 backfill stamps rsi_14 only). This blinded the pre-registered **tape-at-long re-measure (due 11-29)** to a fifth of the book. Now ~99%, write-only (no gate reads these keys, repo-verified), guard skips when decider already stamped. bug_hunter verdict **SHIP** (0 HIGH / 0 MED / 3 LOW).
3. **AMPLIFY why-not (rule 3):** all 6 n>=10 net>0 30d winner cells covered by open entries or WINNER_CELLS_VALIDATED 3/3 → no new proposal; Flip-KPI 0 this week (chase = mult-150 CEO label since 11-04).

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d / 14d / 30d | 11T 54.5% **-0.17** / 109T 50.5% **+0.66** / 192T 49.0% -1.38 / 657T 51.0% -4.71 |
| 7d chop-bleed dollar | **98.0%** (48/49, -4.74/-4.79) |
| 14d exit families | TRAIL/FAM 83T 95.2% **+4.83** vs CHOP/STOP 63T 1.6% **-6.80** |
| mfe-arm 7d | LONG **42.9%** (<50) / SHORT **61.7%** (>55) — tripwire BOTH LEGS **6th cycle**, CEO flag |
| kill screen 14d n>=15 sub-50 net<0 | **ZERO rows** |
| watchdog steer-001 | rider 3-loss streak → **MONITOR** (n=8<15; never-armed chop cluster; auto-kill prior art reverted twice) |

### 2. AUTOPSY (48h, recovery_replay adverse-first, selfcheck PASS)
- n=13 = 1 never-adverse / 9 recovered / **3 NEVER** (ALGO atr-trend- · RENDER warrior+ · WLD hl_copy) → **WRONG-SIDE REFUTED 128th** (#61 p=0.116, #84 t=-0.04).

### 3. SHADOW (3/6, all fresh this run)
| Source | Status |
|---|---|
| contrarian join | **RE-RAN 20:30Z** (mandate) — overall flip 46.3% n=1919; pc- **63.0% LIVE**; rider 45.5% do-NOT (chi2 p=2.4e-36 HETEROGENEOUS) |
| floor join | fresh 12:31Z — p=0.0927 COLLECT, 11-15 NO-SHIP stands |
| shadow_trader --report | 20:33Z — gates all block negative-EV cohorts; exit A/B pm_trail +17,929 vs hard_max -23,173 |
| oscillator / wyckoff / rr | archived / retired / orphaned |

### 4. REJECTED-WITH-DATA (never re-propose)
- **TRANSITIONING-long block** — 30d fisher **p=0.905**, split-half sign-flip (+0.10 → -0.98).
- **momentum_state=falling-long block** — #191 prior art p=0.55; 30d 48.2% vs 48.9% no separation.
- **ema300-BELOW-long block** — 30d p=0.896; AT leg already under eval tape-at-long-remeasure-1129 (11-29).

### 5. LAST-RUN VERIFY (#276) + DRIFT
- #276: 0 config changes → nothing to verify; slope ledger standing; hl_copy fix holding; constants EMPTY; lock absent; checkpoint_registry 0 pending.
- **FIXED this run:** brain.py bare-HERMES_DATA (above) · tape stamp coverage 80% → ~99%.
- **LOW:** cascade_flip(_v2) read `os.environ.get('HERMES_DATA')` — different var than paths' `HERMES_DATA_DIR`, defaults match so no live bug · data/gate_shadow.db 0-byte orphan (carried).
- **MED carried:** gate_shadow vs shadow_trader gate-EV sign disagreement · session_brain dup 18th.

### 6. READINESS (2026-11-18 20:57 UTC)
**0 open / 1 steer dispositioned (monitor) / portfolio good.** Regime SHORT_BIAS 15m+4h, continuum **BELOW**, tape **BELOW EMA300 dist -0.77% STRONG_DOWN** (~1306 duration), wyckoff MARKDOWN, market_phase CALM. **FLAT is correct: no fresh counter-trend LONGs into the below-tape; trail-family first; SHORTs only with 4h aligned; size 1.0x (size-reduce file absent).**

**Queue:** **11-20** compaction-stale + hotset-pin + warrior (n=6<10) → **11-21** batch of 12 (jup-short-walk, atrtrail-clip-12, reentry-study, prearm-BE, cell-conf-tilt, bbsqueeze-module, structure-flip, slope-jup, r2v2-clonehunt, pcv6, ceiling-85, short-rsi-hard-floor) → **11-22** ai-trader NORMAL SHORT cell (7d +1.53) → **11-25** watch-contrarian + pcfade re-read → **11-29** tape-at-long-remeasure (now ~99% coverage) → **11-30** hl-copy-plus.
CEO: **LONG arm tripwire 6th cycle** · exitstack dual-read · **mult-150 label (since 11-04)** · slippage BUILD #1 (14th).

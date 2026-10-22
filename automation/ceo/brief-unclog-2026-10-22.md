# CONSULT: Unclog the system — zero positions while the market trades

**Budget ~30 min, but print your full answer by ~minute 22 — delivered beats perfect.
Every number must be re-queried by you. Cite file:line for every code claim.**

## T's directive (verbatim, 2026-10-22 ~14:39 UTC)

> "looking at the btc prices, only been going down, alts crashing, we're sitting with
> zero positions all the time. **you're grinding the system to a complete stop, shadow
> data is coming in every minute, use it, unclog the system.**"

This is an authorization, not a question. Your job: produce the **UNCLOG LIST** — a
ranked, evidence-backed list of gates to open NOW, each explicitly labeled
**CEO-APPROVED-TO-FLIP** or **KEEP-SHADOWING** (with the flip threshold) or **KILL**.
Each item must carry exact `file:line`, old→new value, and the shadow counterfactual
numbers that justify it. This consult's APPROVED labels ARE the CEO approval the
automatic-implementation skill requires — items labeled APPROVED will be implemented
immediately after this run, so label conservatively but do not withhold what the data
supports.

## Verified grounding (re-verify, don't trust)

**The stop:**
- **0 open positions, 0 fills in the last 6h** (PostgreSQL brain, open_time), now
  14:39 UTC. Last night's dump window had exactly 1 fill (a long, $0.00).
- Execution layer is ALIVE: `hype_live_trading.json` = true, no vacation_pause marker,
  systemd pipeline `active`, pipeline.log mtime 14:40 (fresh). **So the stop is upstream
  of HL — in the gates/decider — unless your funnel analysis proves otherwise.**
- Active modifiers: `vacation_size_reduce.json` 0.5× (since 10-20, auto-clears on WR
  recovery); HL min notional $11 incl. leverage (at 0.5×, positions must be ≥$22 base
  to fire — check whether size-reduce + $11 floor is silently eating fills).
- **vacation_mode.json rules (T set, 10-16): `shadow_first, no_enforcement_flips,
  no_constants_change, no_signal_enable_disable`.** T's message above directly
  conflicts with the no-flip/no-constants rules. Your call: for every APPROVED item,
  state exactly which rule T's directive waives and how it should be recorded
  (recommend exact wording for vacation_mode.json), OR recommend an approach that
  unclogs without touching constants (lists, JSON state, bypass entries — decide if
  those even count under the rule). Do not pretend the conflict doesn't exist.

**This morning's verdict (consult-20261022T030217Z + follow-up run, full text in
logs/ceo/consult-*.jsonl):** YES we block shorts — 948 short-block lines / 14 gates in
the 00:00–02:59 dump window; top 3 = vol-gate `('EXTREME','pump-chain-'):0.0` (325),
RSI-45 floor ×3 layers (265), PUMP-CHAIN-SHORT-HIGH (201). Ranked recs were:
#1 conditional RSI floor (bear override is dead code: both floors=45),
#2 vol-gate EXTREME pump-chain- 0.0→conditional on confirmed dump,
#3 fix oversold-bypass/exec contradiction (bypass can never survive exec),
#4 accel hair-trigger 0.005→0.01, #5 short-side STANDALONE_BYPASS audit (116
confluence blocks), #6 stale comments + regime-source desync. **You may assume those
findings; now decide which become FLIP-NOW using shadow evidence.**

## Shadow inventory (verified with freshness — use ALL of it)

| Stream | Size | Last write | What it counterfactuals |
|---|---|---|---|
| `brain/gate_shadow.db` events | 5.7 MB | 14:00 | blocked-gate census: CONFLUENCE-GATE-BLOCK 6196, SHORT-CONTINUUM 3467, LONG-NEUTRAL 2041, CONTINUUM-BLOCK 2026, PUMP-CHAIN-SHORT-HIGH 1783, SHORT-NEUTRAL 1667, CONTINUUM-BULL 1581, PUMP-CHAIN-RSI-MAX 1439, VOL-GATE-BYPASS 1258, CTX-GATE 1250 |
| `data/floor_admit_shadow.jsonl` | 1461 rows | **14:37 (1 min ago)** | penalty-floor counterfactual: exec_conf vs floor_0.3 vs pp_cond; `floor_admitted` flag streaming per minute |
| `data/contrarian_shadow.json` | 754 events | 14:00 | pump-chain- SOAK: 308 eval, **56.2% WR, +31.04 pct-sum, 8.7d**; btc-pump-rider+ 173 eval 28.3% WR −75.67 |
| `data/wyckoff_shadow.jsonl` | 71 KB | 10:22 | wyckoff+ LONG counterfactuals (WYCKOFF_SHADOW_MODE=True) |
| `data/temporal_confluence_shadow_offset.txt` | — | 14:30 | TEMPORAL_CONFLUENCE_SHADOW=True: bypass is LOGGED BUT NOT APPLIED — confluence gate kept blocking 116 shorts last night while this soaked |
| `data/relative_regime_shadow.json` | 2 KB | 10-21 | relative-regime gate shadow |
| `data/contrarian_shadow.jsonl` | 221 KB | 09:17 | raw contrarian events |
| `data/oscillator_shadow.json` / `rr_shadow_audit_7d.json` | — | **10-01 / 10-04 STALE** | check if these are dead collectors (dead shadow = report it) |

Shadow flags live in code: `CHASE_RATIO_SHADOW`, `BB_BOUNCE_TRAIL_ARM_TIMEOUT_SHADOW`,
`ICHIMOKU_LONG_BYPASS_SHADOW`, `TEMPORAL_CONFLUENCE_SHADOW` (hermes_constants.py:4129),
`RR_ENGINE_SHADOW` (:4141 — log-only, RR engine currently does NOT block),
`WYCKOFF_SHADOW_MODE`; `REP_SHADOW_MODE=False`.

## Questions

1. **Choke-point funnel (last 12h, both directions):** signals created → per-gate
   blocks → decider SKIPs → approval → execution attempts → HL rejects/fills. Give the
   numbers at each stage. Name the choke point(s). If size-reduce×$11 notional,
   hotset cooldown, MIN_EXEC_CONFIDENCE, decider-loop starvation, or a dead component
   contributes, quantify it — gates may not be the whole story.
2. **UNCLOG LIST:** iterate every shadow stream + every gate from the morning census +
   this funnel. For each: FLIP-NOW (label CEO-APPROVED-TO-FLIP, exact old→new +
   file:line + shadow n/WR/PnL), KEEP-SHADOWING (what threshold still needs to be
   met), or KILL (collector or gate is dead/wrong). The three morning recs deserve
   first votes. For `TEMPORAL_CONFLUENCE_SHADOW` specifically: 8.7d of soak exists —
   does its data justify enforcing the bypass (note: enforcement = flip to False, which
   is an enforcement flip under vacation rules — handle explicitly)?
3. **Expected effect:** for each APPROVED item, estimate gates reopened per day /
   fills per day from the shadow counters. The plan must plausibly produce positions
   today. End with: expected fills/24h post-unclog vs the 1-per-6h current state.
4. **What stays shut:** protected flags (CONFLUENCE_REQUIRED, LIVE_TRADING_ENABLED,
   CEO_PROTECTED_FLAGS), SHORT_MIDBAND, RSI ceiling, PUMP-CHAIN-SHORT-HIGH-in-HIGH —
   confirm or overturn each from morning's "don't touch" list with data.

## Guardrails

- READ-ONLY: you produce labels and exact values; implementation happens after you.
- Doctrine: no blanket regime kills, no time-of-day blocks — route via regime/vol gates.
- If two shadow streams disagree, show both numbers and pick, don't hedge.
- If your funnel proves the stop is NOT in the gates (execution/config side), say so
  first and skip the gate list — wrong-layer fixes waste the run.

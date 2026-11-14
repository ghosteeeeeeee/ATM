# full-analysis v2 — always-on engine + dash  (SPEC v2.1, 2026-11-14)
# Consolidated after bug_hunter plan-verdict (bug-hunter-full-analysis-v2-
# plan-2026-11-14: NOT build-ready as v1 — every finding below is folded in).
# CEO goal: the picture always ready as it forms; all timeframes/indicators/
# structural levels; ALWAYS a long AND a short entry ready; BTC first,
# other coins later; all existing pieces under one roof.

## 0. Architecture

    scripts/full_analysis.py  (--coin BTC, stdlib, LOCAL reads only)
    ├─ REUSE (import — verify-at-build; verdict signatures confirmed):
    │   auto_analysis.build_decision(...)  → regime/flips/scores/
    │       structure_detail{15m,1h}/bracket-or-None (token kwarg exists;
    │       NOTE: bracket is None when positions are open → §12 completion
    │       is sourced from THE BOOK + DB hypotheticals, not the bracket)
    │   A.tf_indicators(coin, tf)         → MTF RSI/MACD/z/vol/ema50
    │       (separate call — NOT inside build_decision's return; F6)
    │   structure_analysis.analyze(token,tf) → per-TF state — RETURNS A
    │       DISPLAY STRING (parse for state/tags/SH/SL/slope, or lift the
    │       zigzag core into a dict-returning helper at build time; F6)
    │   adx_atr_analysis.lifecycle(tf,token) + backtest_trend_momentum_v3
    │       .compute_adx (import-safe, path verified)
    │   continuum_data.json fields: ema300_position/zscore_val/
    │       velocity_val/acceleration_val/volume_ratio_val — READ WITH
    │       RETRY (mid-write JSONDecodeError observed live → retry once,
    │       never silent STAND_DOWN; LOW)
    │   ai_trader_precheck — PARSE STDOUT (exit code is ALWAYS 0 on FAIL,
    │       verified; or import precheck() if callable)
    │   brain PG — READ-ONLY CONNECTION: psycopg2 with
    │       options='-c default_transaction_read_only=on' + Phase-5
    │       assert (all default connects are writer-capable; F9)
    │   pending_orders.json + state — THE BOOK (replicate the keeper's
    │       exact _unfired predicate: status not in ('fired','error') —
    │       a 'triggered' status counts unfired, matching the keeper)
    ├─ NEW — algorithms that exist NOWHERE in the repo (they live only
    │   in conversation heredocs — Phase-1 task 0 is transcription, F7):
    │   shelves(coin)        → S/R: distinct hi/lo clusters from 1h+15m
    │                           (last N closed bars) + round levels
    │   divergence(coin)     → §3 taxonomy: 150 closed closes, Wilder-ish
    │                           14-RSI, ±3-bar local extremes, TYPE-1
    │                           conditions per TF (15m/1h)
    │   adx_trendline(coin)  → rule 5: ADX series (compute_adx), local
    │                           minima line-fit, touch log, peak-vs-cross
    │                           semantics, split-read (TF floor vs arc-high)
    │   + rule 4 (ADX divergence at price extreme: new extreme + ADX peak
    │     similar/lower + ATR-at-peak + MACD/RSI-low companions) — F8,
    │     implemented from compute_adx series (lifecycle only has 1-3)
    └─ VERDICT LAYER (skill = spec of record; code mirrors)
    writes: data/full_analysis_v2.json + www/data/full_analysis_v2.json
    (atomic tmp+replace; engine takes its OWN run-lock: timer-only
     cadence, NO watchdog trigger — single-writer per pass-2 #3)

## 1. Cadence & staleness (F4 — declared, CEO-visible)

    systemd hermes-full-analysis.timer  every 5 min (local, no API)
    page polls JSON every 60s + DATA-AGE badge
    Known staleness: fires land in pending state ~1min, arms ~30min,
    engine ~5min → book can lag a fresh fire by up to ~6min. The badge
    shows it; acceptable unless CEO says otherwise.

## 2. Sections (the JSON = the skill's Output Template + declared extras)

    step0      positions + recent closes + exit-reason attribution
               ("who called it": CEO/system/keeper/engine) + TWO-LINES
               per open trade (skill §0) + routing-bug alert
               (rr_engine_*/atr_* on manual trades = flag; F5)
    chop       regime + flips_24h + chop-adjust note
    mtf        5 TFs × RSI/MACD/z/vol/ema50 (tf_indicators)
    structure  per-TF state/tags/SH/SL/slope (analyze; string→dict lift)
    adx_atr    lifecycle rules 1-4 (1-3 from lifecycle(); rule 4 new) +
               COMBINED flags
    trendline  rule 5 (new)
    continuum  ema300/z/vel/accel/vol + PIN STATE (§14) + pre-bounce
               curl flag
    s_r        shelves + rounds
    divergence §3 taxonomy labels per TF
    contrarian THE CHECKLIST (skill §4: what-if-long/what-if-short +
               net) — NOT the shadow contrarian-monitor (F2)
    scores     long/short + regime adjustment
    verdict    two-part DIRECTION + ENTRY + rationale[] (rules-as-code:
               thresholds from skill; §12 bracket completion from THE
               BOOK + DB hypotheticals — see §0 note)
    book       see §3 below
    alerts     see §4 below
    bb, ema200 Key-Indicator sections from the skill (Bollinger position,
               EMA200) — were missing from v1's list (F5 missed-req)

## 3. THE BOOK panel + READY invariant (F3 — full spec)

    Columns per side (LONG | SHORT): every unfired BTC rung —
    trigger / SL / TP / size / source (keeper|CEO|engine) /
    distance-to-trigger (price-based, % and pts) / dedupe-coverage
    (engine proposal covered by our rung? show covered/unique).
    Also: OPEN same-side positions (entry/SL/TP/live-pnl) and the
    most-recent closed trade per side.

    READY — THREE STATE per side:
      READY-GREEN  = (a) an OPEN position on THAT side, OR
                     (b) ≥1 unfired rung within reach, where reach =
                         price ± 3·structure_detail['1h'].atr
                         (SAME source the keeper uses — 1h ATR, not 15m)
      READY-AMBER  = ITM-wait: (short) no rung derivable because the
                     derived trigger (sl1h−60) ≥ price — price is AT/UNDER
                     the floor (you are likely already short via (a), or
                     the level is being made); (long) mirror:
                     derived trigger (sh1h+60) ≤ price.
      RED          = none of the above — a side with no position, no
                     reachable rung, and no ITM-wait = the rule-13
                     violation → loud badge + alert.
    CROSS-SIDE OVERLAP CHECK (the invariant): for every unfired short S
    and unfired long L: require S.sl < L.trigger AND L.sl > S.trigger.
    Violation → RED badge naming the pair. (Spec was undefined in v1/F3.)
    Note: an OPEN position does NOT count as ready for the OTHER side.

## 4. Alerts (Phase 1 = badges on the dash; Phase 3 = events)

    box-tax      box = CHOP + 1h in-range% at a band extreme; counts
                 structure/exits inside the box this session (badge in
                 Phase 1 — resolves the v1 Phase-1-vs-Phase-3 conflict)
    pin          EMA300-pin state + minutes pinned
    keeper-empty any side RED (above)
    structure-flip  any TF state change since last engine run
    adx-events   dual-peak / exhaustion / rule-4 / rule-5 triggers
    fragmentation ride-cost accounting when exits clustered in a trend
    routing-bug  manual trade carrying engine exit labels (from step0)

## 5. Forming bars + fixtures (F1 — the quality gates, rewritten)

    FORMING LABEL: a bar is forming iff ts + period > now. Live output
    labels every forming read (skill §4); the engine NEVER uses a
    forming bar's close as a settled value in the verdict.
    GOLDEN FIXTURE: a frozen row-snapshot — candles (ts/high/low/close)
    as-of a FIXED cut ts, committed as a fixture file; expected outputs
    generated ONCE from that slice. Tests replay the slice, not live
    DB (is_closed=1 includes forming rows — empirically proven; and
    stale is_closed=0 rows exist for bars closed in time → last-closed
    queries can miss). As-of read rule: closed iff ts+period ≤ cut.

## 6. Parity test (F2 — rewritten scope)

    SET-A = the Output Template's 10 blocks (step0, chop, mtf,
            structure, adx_atr+trendline, continuum, s_r, divergence,
            contrarian, scores, verdict) — note: §0-14 PROSE sections
            are the spec, the 10 blocks are the payload.
    SET-B = declared dash-only keys (book, alerts, data-age, badges,
            distances) — an explicit allowlist in code.
    Test: every SET-A block has a JSON key AND every JSON key ∈ SET-A ∪
    SET-B, both directions → doc-drift = failing test (the "grep").

## 7. Multi-coin (Phase 4 — scope stated honestly)

    Engine: --coin everywhere (candles token ✓, brain token ✓,
    precheck COIN ✓, pending coin field ✓).
    KEEPER is BTC-hardcoded today (coin=='BTC' ×4 sites, token='BTC'
    candle query, btc-auto-ladder-* ids, get_open_btc, coin_whitelist)
    → Phase 4 must either generalize it (ids/queries/dedupe) or keep
    ladders BTC-only while analysis extends — CEO decision.
    Continuum is BTC-only end-to-end (current.token/export) → ETH PIN
    needs a regime_source label; also add the skill's OWN-TREND /
    BTC-DRIVEN coupling label for non-BTC coins.

## 8. Build order (Phase 1 start = the verdict's must-fix list)

    1a. Transcribe the three algorithms + rule 4 into the engine (F7/F8)
        — they exist nowhere in the repo; also flag (separate cleanup)
        the broken backtest_v4_short _check_rsi_divergence import.
    1b. Fixture infrastructure (frozen cut + forming-label helper) FIRST
        — every later number is tested against it (F1).
    1c. Assemble sections (§2 list) + verdict rules + book panel with
        the three-state READY + overlap check (F3) + alerts (§4).
    1d. Parity test (§6) + golden replay + PG read-only connect (F9).
    2.  API writer + web/full_analysis.html + nginx (EDIT THE LIVE
        /etc/nginx/sites-enabled/trading — the repo's web/nginx-
        trading.conf is STALE, 54 locations, editing it does nothing)
        + timer.
    3.  Alerts → events.
    4.  Multi-coin per §7.
    5.  bug_hunter: single-writer (API never writes), read-only PG
        assert, fixture reproducibility, parity, staleness badge.

## 9. Ops findings from the plan review (not plan scope, tracked)

    - continuum dash mid-write read → JSONDecodeError → silent
      STAND_DOWN (observed live) — needs read-retry (listed §0)
    - web/nginx-trading.conf stale vs live config (§8-2)
    - backtest_v4_short.py dead (ImportError _check_rsi_divergence)
    - precheck exit code always 0 (§0)
    - pending monitor reads prices.json['BTC'] entry (BTC-only input)

## 10. Decisions for CEO (recs unchanged unless noted)

    1. Cadence 5min / 60s poll + data-age badge — REC (staleness §1
       declared: up to ~6min after a fire)
    2. Dash verdict = advisory only; keeper/watchdog = only writers — REC
    3. Alerts in-page first — REC
    4. BTC-only until perfect; keeper generalization deferred to Phase 4
       — REC (flagged §7)
    5. Fixture policy: frozen row-snapshot as-of fixed cut (F1) — REC

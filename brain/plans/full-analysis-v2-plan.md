# full-analysis v2 — always-on engine + dash  (SPEC v2.2, 2026-11-14)
# v2.2 = v2.1 (bug_hunter plan-verdict folded in) + CEO spec-deepening:
#   (1) CADENCE EVERY MINUTE (CEO), (2) dash shows LIVE TP/SL of open
#   positions, (3) LEVEL PROVENANCE — the structural values that produced
#   every level displayed. Single consolidated spec — no pass appendices.
# CEO goal: picture always ready as it forms; all TFs/indicators/levels;
# ALWAYS a long AND short entry ready; BTC first, expand later; one roof.

## 0. Architecture

    scripts/full_analysis.py  (--coin BTC, stdlib, LOCAL reads only)
    ├─ REUSE (signatures verified by plan-verdict):
    │   auto_analysis.build_decision(...) → regime/flips/scores/
    │       structure_detail{15m,1h}/bracket-or-None (token kwarg;
    │       bracket is None when positions open → §12 completion
    │       sourced from THE BOOK + DB hypotheticals)
    │   A.tf_indicators(coin, tf)  → MTF (separate call, F6)
    │   structure_analysis.analyze(token,tf) → per-TF (returns a
    │       DISPLAY STRING — parse it or lift a dict helper in Phase 1)
    │   adx_atr_analysis.lifecycle + backtest_trend_momentum_v3.compute_adx
    │   continuum_data.json (READ WITH RETRY: mid-write JSONDecodeError
    │       observed live → retry once, never silent STAND_DOWN)
    │   ai_trader_precheck — PARSE STDOUT (exit code always 0 on FAIL)
    │   brain PG — READ-ONLY: options='-c default_transaction_read_only=on'
    │       + Phase-5 assert
    │   pending_orders.json + state — THE BOOK (keeper's exact _unfired
    │       predicate: status not in ('fired','error'))
    │   auto_trader.db events — LAST R1 EVENT per open trade = live-SL
    │       provenance (see §11)
    ├─ NEW — Phase-1 task 0 (they exist nowhere in the repo, F7):
    │   shelves(coin), divergence(coin), adx_trendline(coin), rule-4
    │   (F8; lifecycle only implements rules 1-3)
    └─ VERDICT LAYER (skill = spec of record; code mirrors)
    writes: data/full_analysis_v2.json + www/data/full_analysis_v2.json
    (atomic tmp+replace; OWN run-lock: timer-only, NO watchdog trigger;
     if lock held (run >60s) → SKIP this tick, data-age badge shows age)

## 1. Cadence — EVERY MINUTE (CEO 2026-11-14, supersedes the 5min rec)

    systemd hermes-full-analysis.timer  OnUnitActiveSec=60s
    page polls JSON every 30s + DATA-AGE badge
    Budget: every component is a local SQLite/JSON read — engine target
    <30s total (precheck = 2 subprocesses ≈ 1-2s each); systemd
    TimeoutStartSec=50s + flock → a slow tick skips rather than piles up.
    Staleness (F4, updated): fires enter pending state ~1min, arms ~30min,
    engine ≤1min → book ≤~2min behind a fire (was ~6). Badge shows it.

## 2. Sections (JSON = skill Output Template + declared extras)

    step0      positions card (see §3) + recent closes + exit-reason
               attribution ("who called it": CEO/system/keeper/engine)
               + TWO-LINES per open trade + routing-bug alert
    chop       regime + flips_24h + chop-adjust note
    mtf        5 TFs × RSI/MACD/z/vol/ema50
    structure  per-TF state/tags/SH/SL/slope
    adx_atr    lifecycle rules 1-4 (1-3 from lifecycle(); rule 4 new)
    trendline  rule 5 (new)
    continuum  ema300/z/vel/accel/vol + PIN state + pre-bounce curl
    s_r        shelves (with ORIGIN: tf + swing ts + hi/lo) + rounds +
               near_levels (every open level mapped to its nearest shelf)
    divergence §3 taxonomy per TF
    contrarian THE CHECKLIST (what-if-long / what-if-short / net)
    scores     long/short + regime adjustment
    verdict    two-part DIRECTION + ENTRY + rationale[] (§12 completion
               from THE BOOK + hypotheticals — see §0)
    book       §3
    alerts     §4
    bb, ema200 Key-Indicator sections

## 3. POSITIONS card + THE BOOK panel + READY invariant (F3 full spec)

    POSITIONS (each open trade):
      side · entry · hold-time · live-pnl (%, margin, $)
      LIVE SL  + distance (pts, %, margin-impact-if-hit)
      LIVE TP  + distance (pts, %, margin-impact-if-hit)
      PROVENANCE line per level — basis object, §11 (the CEO ask)
      last stop-change (from the R1 event: rule + old→new + when)

    THE BOOK — columns per side (LONG | SHORT): every unfired BTC rung:
      trigger / SL / TP / size / source (keeper|CEO|engine) /
      distance-to-trigger (pts + %) / dedupe-coverage (engine proposal
      covered by our rung? covered|unique) / basis (§11 — note text or
      structured fields) / reach flag (in-reach via 3·1h-ATR)
      Also: most-recent closed trade per side.

    READY — THREE STATES per side:
      GREEN = (a) open position on THAT side, OR (b) ≥1 unfired rung
              within reach, reach = price ± 3·structure_detail['1h'].atr
              (the keeper's exact source)
      AMBER = ITM-wait: short — derived trigger (sl1h−60) ≥ price;
              long — derived trigger (sh1h+60) ≤ price (you are likely
              already in via (a), or the level is being made)
      RED   = none of the above → loud badge + alert (rule-13 violation)
      An open position NEVER counts for the OTHER side.

    CROSS-SIDE OVERLAP: for every unfired short S × long L:
      require S.sl < L.trigger AND L.sl > S.trigger — any violation →
      RED badge naming the pair.

## 4. Alerts (Phase 1 = dash badges; Phase 3 = events)

    box-tax (box = CHOP + 1h in-range% at band extreme; exits inside
      the box this session) · pin (EMA300-pin + minutes) · keeper-empty
      (any RED side) · structure-flip (TF state changed since last run) ·
      adx-events (dual-peak/exhaustion/rule-4/rule-5) · fragmentation
      (ride-cost accounting) · routing-bug (engine labels on manual
      exits)

## 5. Forming bars + fixtures (F1)

    FORMING LABEL: bar is forming iff ts + period > now — live reads
    label it; a forming close is NEVER a settled value in the verdict.
    GOLDEN FIXTURE: frozen row-snapshot (ts/high/low/close) as-of a
    FIXED cut committed as fixture; expected outputs generated once
    from that slice. As-of rule: closed iff ts+period ≤ cut.
    (Fixes: is_closed=1 includes forming rows; stale is_closed=0 rows.)

## 6. Parity test (F2)

    SET-A = the 10 Output-Template blocks (prose §0-14 = spec, blocks =
    payload); SET-B = declared dash-only allowlist (book, positions,
    alerts, data-age, badges, distances, ready, overlap).
    Every SET-A block has a JSON key AND every key ∈ SET-A ∪ SET-B.

## 7. Multi-coin (Phase 4 — scope stated)

    Engine --coin everywhere (candles/brain/precheck/pending all
    parameterized). KEEPER is BTC-hardcoded (coin=='BTC' ×4, token
    candle query, btc-auto-ladder-* ids, get_open_btc, coin_whitelist)
    → generalize it OR keep ladders BTC-only while analysis extends —
    CEO decision. Continuum is BTC-only end-to-end → ETH PIN needs a
    regime_source label; add the skill's OWN-TREND/BTC-DRIVEN coupling
    label for non-BTC.

## 8. Build order

    1a. Transcribe 3 algorithms + rule 4 (F7/F8); flag dead
        backtest_v4_short import as separate cleanup
    1b. Fixture infra FIRST (frozen cut + forming-label helper) — F1
    1c. PROVENANCE capture (Phase-1a): keeper writes a structured
        `basis` dict into each derived order at arm (it already has
        the numbers); tweak's R1 event gains src_tf/src_value keys
        (2-line change) so the engine can read live-SL provenance;
        TP provenance via fired-order join (state.trade → config order)
    1d. Sections + verdict rules + positions card + book + READY +
        alerts
    1e. Parity test + golden replay + PG read-only assert
    2.  API + web/full_analysis.html + nginx (EDIT LIVE
        /etc/nginx/sites-enabled/trading — repo conf is STALE, 54
        locations) + TIMER EVERY 60s
    3.  Alerts → events
    4.  Multi-coin per §7
    5.  bug_hunter: single-writer, read-only PG, fixture replay,
        parity, provenance correctness (does each displayed level's
        basis match the formula that produced it — replay one keeper
        SL and one lag event end-to-end), 1min-cadence race/skip

## 9. Ops findings from plan review (tracked, not plan scope)

    continuum mid-write JSONDecodeError → silent STAND_DOWN (live) ·
    repo web/nginx-trading.conf stale · backtest_v4_short dead import ·
    precheck exit code always 0 · pending monitor prices.json['BTC'] ·
    17 fired records accumulating in pending_orders.json

## 10. Decisions

    1. CADENCE: EVERY MINUTE — CEO RULED 2026-11-14 (engine60s, page
       poll30s, ≤2min book staleness, skip-if-held lock). RESOLVED.
    2. Dash verdict = advisory only; keeper/watchdog = only writers — REC
    3. Alerts in-page first, events later — REC
    4. BTC-only until perfect; keeper generalization deferred — REC
    5. Fixture policy: frozen row-snapshot as-of fixed cut — REC
    6. F-b STILL PENDING CEO: engine/bracket long stops at birth —
       "reclaim" (rec) vs "ride-to-floor"? Default = reclaim as shipped.

## 11. LEVEL PROVENANCE — the structural values behind every level
        (CEO 2026-11-14: "show the live TP and SL, and ideally the
        structural values that produced those")

    Every level the dash displays carries a `basis` object. Four
    producers, four sources — no new tables:

    A. LIVE SL (open trade):
       source = the LAST auto_trader.db event for that trade
       (message JSON: {trade, field, old, new, rule:'R1'} — Phase-1a
       extends it with src_tf + src_value + kind). kinds:
         seed          (armed stop stands)
         re-anchor     (birth → the major line)
         favorable-step (trail to now-old src structure)
         adverse-raise (raise to the 1h invalidation line)
       basis = {kind, src_tf:'15m'|'1h', src_value, buffer, old, new, at}
       Display: "SL 67,812.09 — favorable-step → 15m swing 67,980 +
       0.1·ATR (R1, 14:52)" (formula, source TF, source value, time)

    B. LIVE TP (open trade):
       NEVER moved by the watchdog (doctrine) — basis = arm-time
       formula, joined via state.trade → the source order in
       pending_orders.json:
         keeper/CEO rungs: {kind:'disaster-at-arm',
                            formula:'trigger ∓ 3·ATR1h',
                            trigger, atr1h_at_arm, at}
       fallback if source order gone: {kind:'arm-time', note:<order
       note text>} — never invent a value we cannot cite (F-a rule).

    C. RUNG LEVELS (book rows — trigger/SL/TP):
       keeper-derived: Phase-1a writes structured fields at arm:
         {kind:'keeper-derive', anchor_tf:'1h', anchor:67980,
          rung:'sl1h−60', sl:'sl1h+0.6·ATR15', atr15, atr1h,
          tp:'trigger−3·ATR1h'}
       CEO/engine rungs: carry their `note` free-text as basis
       (display verbatim; structured basis:null with note echo —
       same never-invent rule).

    D. SHELF ORIGIN (s_r section):
       each S/R shelf = {level, tf, swing_ts, kind:'swing-high'|'swing-
       low'|'round'} — the producing candle, not just the number.
       `near_levels`: for every open-level and rung, the nearest shelf
       + delta — so "SL 67,812 ↔ shelf 67,865 (−53)" is one glance.

    JSON sketch (fields the dash consumes):

    "positions": [{"id":16905,"side":"SHORT","entry":67402,
      "live_sl":67812.09,"live_tp":66283,
      "basis":{"sl":{"kind":"favorable-step","src_tf":"15m",
                    "src_value":67980,"new":67812.09,"at":"..."},
               "tp":{"kind":"disaster-at-arm","trigger":67920,
                    "formula":"trigger−3·ATR1h","atr1h_at_arm":545.6}},
      "dist":{"sl_pts":410,"sl_pct":0.61,"tp_pts":1129},
      "pnl_pct":1.44,"opened":"..."}],
    "book":{"short":[{"id":"...","trigger":66855,"sl":...,"tp":...,
      "size":22.2,"source":"keeper","dedupe":"covered|unique",
      "reach":{"pts":347,"in":true},
      "basis":{"kind":"keeper-derive","anchor_tf":"1h","anchor":67255,
               "rung":"sl1h−60","sl":"sl1h+0.6·ATR15"}}]},
    "s_r":{"s":[{"level":67865,"tf":"1h","swing_ts":"...",
               "kind":"swing-low"}],"near_levels":[{"of":"live_sl",
               "value":67812.09,"shelf":67865,"delta":-53}]},
    "ready":{"short":"GREEN","long":"GREEN"},
    "data_age_s": 14

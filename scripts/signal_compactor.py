#!/usr/bin/env python3
"""
signal_compactor.py — Deterministic hot-set compactor (LLM-free).

Replaces _do_compaction_llm() in ai_decider.py with a pure-Python scoring
script that produces identical output using the same signal data, scoring
logic, and DB schema.

Run:
    python3 /root/.hermes/scripts/signal_compactor.py        # normal
    python3 /root/.hermes/scripts/signal_compactor.py --dry  # log only, no write
    python3 /root/.hermes/scripts/signal_compactor.py --verbose  # per-signal scoring

Exports:
    run_compaction(dry=False, verbose=False) -> dict
"""

import sys, os, time, json, sqlite3, argparse, re
from datetime import datetime, timezone

# ── Resolve scripts dir for imports ──────────────────────────────────────────
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

from hermes_file_lock import FileLock
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST, SIGNAL_SOURCE_BLACKLIST, SPEED_HOTSET_BONUS, SPEED_HOTSET_THRESHOLD, CONFLUENCE_REQUIRED, ACCEL_300_STANDALONE_BYPASS_ENABLED, ACCEL_300_STANDALONE_BYPASS_CONFIDENCE
from tokens import is_solana_only
from hyperliquid_exchange import is_delisted
from paths import RUNTIME_DB, HOTSET_FILE, HERMES_DATA, REGIME_CACHE_FILE, SIGNALS_JSON

# ── Open-position cache (avoid re-querying PostgreSQL every compaction) ─────────
_open_pos_cache = {}  # token_upper -> True/False, refreshed each run
_dir_wr_cache = {}    # (token, direction) -> (wr, count, timestamp)
_DIR_WR_CACHE_TTL = 300  # 5 min cache


def _get_token_wr(token: str, direction: str) -> tuple:
    """Return (win_rate_pct, trade_count) for a token+direction in last 7 days.
    Caches for 5 min to avoid hammering PostgreSQL on every compaction cycle."""
    import time
    key = (token.upper(), direction.upper())
    now = time.time()
    if key in _dir_wr_cache:
        cached_wr, cached_count, cached_at = _dir_wr_cache[key]
        if now - cached_at < _DIR_WR_CACHE_TTL:
            return cached_wr, cached_count
    try:
        import psycopg2
        conn = psycopg2.connect(host='/var/run/postgresql', database='brain',
                                 user='postgres', connect_timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins
            FROM trades
            WHERE token=%s AND direction=%s
              AND status='closed'
              AND close_time >= NOW() - INTERVAL '7 days'
        """, (token.upper(), direction.upper()))
        row = cur.fetchone()
        cur.close(); conn.close()
        total = row[0] or 0
        wins = row[1] or 0
        if total == 0:
            wr = 50.0  # neutral — no history
        elif total < 3:
            wr = 50.0  # need 3 trades to judge
        else:
            wr = round((wins / total) * 100, 1)
        _dir_wr_cache[key] = (wr, total, now)
        return wr, total
    except Exception:
        return 50.0, 0  # neutral on error


def _get_open_tokens() -> set:
    """Query PostgreSQL for tokens with open positions (Hermes server).
    
    DEFENSE-IN-DEPTH (2026-05-17): Also check guardian-closing-markers.json
    to exclude tokens the guardian is actively closing. Without this, a token
    the guardian is about to close can still get a new signal during the same
    pipeline run because PostgreSQL hasn't been updated yet (HL position closed
    but DB record not updated → _get_open_tokens returns nothing → signal passes).
    """
    try:
        import psycopg2
        conn = psycopg2.connect(host='/var/run/postgresql', database='brain',
                                user='postgres', connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT LOWER(token) FROM trades WHERE status='open' AND server='Hermes'")
        tokens = {row[0] for row in cur.fetchall()}
        cur.close(); conn.close()
    except Exception as e:
        log(f"[WARN] Could not query open positions from PostgreSQL: {e}", 'WARN')
        tokens = set()
    
    # DEFENSE-IN-DEPTH: Also check guardian closing markers
    # A token in closing markers means guardian has an active HL close in progress.
    # Even if PostgreSQL hasn't been updated yet (orphan case), we must block
    # signal execution to prevent the exact ATOM scenario: first trade silently
    # failed to get a DB record → guardian closing marker active → signal fires
    # anyway because _get_open_tokens only checks PostgreSQL.
    guardian_closing = set()
    closing_file = '/root/.hermes/data/guardian-closing-markers.json'
    try:
        if os.path.exists(closing_file):
            with open(closing_file) as f:
                data = json.load(f)
            if not isinstance(data, dict):
                log(f"[WARN] Guardian closing markers file is corrupt (type={type(data).__name__}) — skipping", 'WARN')
                guardian_closing = set()
            else:
                guardian_closing = {k.lower() for k in data.get('tokens', {})}
            if guardian_closing:
                log(f"[OPEN-POS-FILTER] Guardian closing markers active: {sorted(guardian_closing)}")
    except Exception as e:
        log(f"[WARN] Could not read guardian closing markers: {e}", 'WARN')
    
    if guardian_closing:
        tokens = tokens | guardian_closing  # union — treat guardian-closing as open
    
    return tokens

# ── Speed cache path (written by speed_tracker.py every ~1 min) ───────────────
SPEED_CACHE_FILE = os.path.join(HERMES_DATA, "speed_cache.json")

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE = '/var/www/hermes/logs/trading.log'
# ── Logging ───────────────────────────────────────────────────────────────────
def log(msg, level='INFO'):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] [{level}] [signal-compactor] {msg}'
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass

# ── Confluence enforcement ───────────────────────────────────────────────────
# Single-source signals are blocked from compaction. They stay PENDING until
# a second source arrives for the same token+direction. The GROUP BY merges
# multiple sources per token+direction into a single row.

def get_regime_1m(coin):
    """Get 1m regime from linear regression of last 50 1m candles.
    Returns (regime_str, confidence_int 0-100).
    Slope > 0 = LONG_BIAS, slope < 0 = SHORT_BIAS, else NEUTRAL.
    R² determines confidence: higher R² = more certain trend.
    """
    import statistics
    try:
        conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=10)
        rows = conn.execute(
            "SELECT close FROM candles_1m WHERE token=? ORDER BY ts DESC LIMIT 50",
            (coin.upper(),)
        ).fetchall()
        conn.close()
        if len(rows) < 20:
            return 'NEUTRAL', 0
        closes = [r[0] for r in reversed(rows)]
        n = len(closes)
        mean_x = (n - 1) / 2.0
        mean_y = statistics.mean(closes)
        cov = sum((i - mean_x) * (closes[i] - mean_y) for i in range(n))
        var_x = sum((i - mean_x) ** 2 for i in range(n))
        if var_x == 0:
            return 'NEUTRAL', 0
        slope = cov / var_x
        ss_tot = sum((y - mean_y) ** 2 for y in closes)
        ss_res = sum(
            (closes[i] - (mean_y + slope * (i - mean_x))) ** 2 for i in range(n)
        )
        r2 = max(0.0, 1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0
        confidence = int(round(r2 * 100))
        if slope > 0:
            return 'LONG_BIAS', confidence
        elif slope < 0:
            return 'SHORT_BIAS', confidence
        else:
            return 'NEUTRAL', confidence
    except Exception:
        return 'NEUTRAL', 0


# ── Signal source weights ────────────────────────────────────────────────────────
# Source-specific multipliers applied during scoring.
# > 1.0 = boost (trust more), < 1.0 = suppress (trust less).
# First match wins (longer prefixes must come before shorter ones).
SIGNAL_SOURCE_WEIGHTS = {
    # (signal_type, source_prefix) -> weight
    ('mtf_macd',  'hmacd-'):       1.5,   # MACD crossovers — strongest trend signal
    ('macd_short_1m', 'macd-accel-'): 2.00, # per-token tuned 1m MACD SHORT, ~65% WR avg
    ('macd_long_1m',  'macd-accel-'): 1.50, # per-token tuned 1m MACD LONG, ~52% WR avg
    # macd_accel — fixed-params MACD(8,50,12) crossover + acceleration (hold=10)
    # Backtest (3000 bars, 40 tokens): SHORT avg=+0.041%, LONG avg=-0.128%
    ('macd_accel_short', 'macd-accel-'):  1.0,  # SHORT: modest edge, moderate weight
    ('macd_accel_long',  'macd-accel+'):  0.8,  # LONG: negative avg, suppress
    ('momentum',  'momentum+'):    1.25,  # combined pct-hermes + accel LONG (77% hit rate)
    ('momentum',  'momentum-'):    1.25,  # combined pct-hermes + accel SHORT (77% hit rate)
    ('mtf_zscore','hzscore,pct-hermes,momentum'): 1.1,  # triple combo — slightly boosted
    ('mtf_zscore','hzscore,pct-hermes'):           1.0,  # standard zscore combo
    ('mtf_zscore','hmacd-,hzscore'):              1.25,  # hzscore without pct-hermes
    ('mtf_zscore','hzscore'):                     0.15,  # bare hzscore — suppressed
    ('pattern_flag',    'pattern_scanner'): 1.25,
    ('pattern_hns',    'pattern_scanner'): 1.25,
    ('pattern_wyckoff', 'pattern_scanner'): 1.25,
    ('pattern_elliot',  'pattern_scanner'): 1.25,
    ('pattern_micro_flag', 'pattern_scanner'): 1.0,
    # velocity: pure acceleration signal (no pct-hermes filter) — weaker alone, 45-55% hit rate
    ('velocity',   'vel-hermes+'):  0.8,   # acceleration-only SHORT — suppress
    ('velocity',   'vel-hermes-'):   0.8,   # acceleration-only LONG — suppress
    # fast-momentum: explosive multi-TF momentum burst — high conviction quick-move signals
    ('fast_momentum', 'fast-momentum+'): 1.3,  # strong upward momentum
    ('fast_momentum', 'fast-momentum-'): 1.3,  # strong downward momentum
    # zscore_momentum: price z-score momentum — |z| > threshold = established momentum
    # Weight 1.5: strong standalone signal, want it near top of hot-set
    ('zscore_momentum', 'zscore-momentum+'):     1.5, # upward momentum confirmed by z-score
    ('zscore_momentum', 'zscore-momentum-'):     1.5, # downward momentum confirmed by z-score
    # mtp_zscore: multi-timeperiod z-score — ALL 3/3 periods must agree on direction
    # Weight 1.25: strong standalone signal (3-confluence), conservative start
    ('mtp_zscore_long',   'mtp-zscore+'):  1.25,  # 3-period upward momentum
    ('mtp_zscore_short',  'mtp-zscore-'):  1.25,  # 3-period downward momentum
    # support_resistance: reduce weight — underperforming in backtest
    ('support_resistance', 'rs-'):       0.7,
    ('rsi-confluence', 'rsi_confluence'):    0.5,   # WR=0% — suppress
    # gap300: EMA(300) vs SMA(300) gap widening on 1m — positive avg PnL in backtest
    # FLIPPED 2026-04-28: gap-300+ now fires SHORT, gap-300- now fires LONG
    ('ema_sma_gap_300_long',  'gap-300-'):   1.0,  # gap widens bullish — strong momentum
    ('ema_sma_gap_300_short', 'gap-300+'):  1.0,  # gap widens bearish — strong momentum
    # phase_accel: wave phase acceleration signals
    ('phase_accel_long',  'phase-accel+'):  1.3,
    ('phase_accel_short', 'phase-accel-'):  1.3,
    # oc_pending: OpenClaw OC signals
    ('oc_pending', 'oc-zscore-v9+'):  1.3,
    ('oc_pending', 'oc-zscore-v9-'):  1.3,
    ('oc_pending', 'oc-mtf-macd+'):   1.0,
    ('oc_pending', 'oc-mtf-macd-'):   1.0,
    ('oc_pending', 'oc-scanner-v9+'): 1.3,
    ('oc_pending', 'oc-scanner-v9-'): 1.3,
    ('oc_rsi', 'oc-rsi+'):            1.0,
    ('oc_rsi', 'oc-rsi-'):            1.0,
    ('oc_pending', 'oc-mtf-rsi+'):    1.0,
    ('oc_pending', 'oc-mtf-rsi-'):    1.0,
    # ma_cross_5m: per-token tuned EMA(10)×EMA(200) crossover on 5m
    ('ma_cross_5m_long',  'ma-cross-5m+'):  1.0,
    ('ma_cross_5m_short', 'ma-cross-5m-'):  1.0,
    # tl_break: diagonal trendline breakout on 5m — standalone directional signal
    ('tl_break_long',  'tl_break_long'):   1.25,  # diagonal downtrend + upside break
    ('tl_break_short', 'tl_break_short'):  1.25,  # diagonal uptrend + downside break
}
DEFAULT_SOURCE_WEIGHT = 1.0

def _get_source_weight(signal_type, source):
    """Return confidence multiplier for (signal_type, source). First-match wins."""
    if not source:
        return DEFAULT_SOURCE_WEIGHT
    for (stype, prefix), weight in SIGNAL_SOURCE_WEIGHTS.items():
        if signal_type == stype and source.startswith(prefix):
            return weight
    return DEFAULT_SOURCE_WEIGHT

# ── Scoring ───────────────────────────────────────────────────────────────────
def _score_signal(token, direction, conf, source, signal_type,
                  age_m, compact_rounds, regime, regime_conf, speed_data):
    """
    Deterministic score formula:

    score = confidence
            × survival_bonus   (1 + cr*0.15, only if cr>0 AND age_m<5)
            × staleness_mult  max(0, 1.0 - age_m*0.2)  → 0 at 5min
            × reg_mult        (+50% aligned / -50% counter-regime / -50% NEUTRAL or no-data)
            × source_mult     (from _get_source_weight)
            × speed_mult      (+15% if speed_percentile >= 80)
    """
    score = float(conf)

    # Survival bonus: only if survived previous cycles AND signal is still alive (age < 5min)
    if compact_rounds > 0 and age_m < 5.0:
        survival_bonus = 1.0 + (compact_rounds * 0.15)
    else:
        survival_bonus = 1.0

    # Staleness penalty: -20% per minute, no floor
    # At age=5min → mult=0.0 (signal is dead)
    # At age=1min → mult=0.8 (20% penalty still alive)
    staleness_mult = max(0.0, 1.0 - (age_m * 0.2))

    # Regime multiplier: +50% aligned, -50% counter-regime, -50% neutral
    # No regime data at all → 0.5x floor
    reg_mult = 1.0
    if regime_conf > 0:
        if (regime == 'LONG_BIAS' and direction == 'LONG') or \
           (regime == 'SHORT_BIAS' and direction == 'SHORT'):
            reg_mult = 1.50
        elif (regime == 'LONG_BIAS' and direction == 'SHORT') or \
             (regime == 'SHORT_BIAS' and direction == 'LONG'):
            reg_mult = 0.50
        elif regime == 'NEUTRAL':
            reg_mult = 0.50
    else:
        reg_mult = 0.50

    # Source weight multiplier
    source_mult = _get_source_weight(signal_type, source)

    # Source count bonus: +5% when 2+ distinct sources
    source_count = len([s for s in (source or '').split(',') if s])
    source_mult += (0.05 if source_count >= 2 else 0)

    # Speed percentile bonus: +15% if speed_percentile >= 80
    speed_mult = 1.0 + (SPEED_HOTSET_BONUS if speed_data.get('speed_percentile', 0) >= SPEED_HOTSET_THRESHOLD else 0)

    final_score = score * survival_bonus * staleness_mult * reg_mult * source_mult * speed_mult
    return final_score


# ── Opposing signal penalty ─────────────────────────────────────────────────
def _get_opposing_penalty(db_path: str, token: str, direction: str) -> float:
    """
    Check for opposing signals in the last 5 min for this token.
    ANY opposing signal — regardless of source — applies a penalty.
    This ensures counter_flip and other opposing signals can knock an
    original-direction combo out of the hot-set.

    Penalty: -15% per opposing source, floor 70% (5-min window).
    Returns multiplier (1.0 = no penalty).
    """
    opp_direction = 'SHORT' if direction.upper() == 'LONG' else 'LONG'
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT source FROM signals
            WHERE token = ?
              AND direction = ?
              AND decision IN ('PENDING', 'APPROVED')
              AND created_at > datetime('now', '-5 minutes')
              AND confidence >= 60
        """, (token.upper(), opp_direction))
        opp_sources = [row[0] for row in c.fetchall() if row[0]]
        conn.close()
        if not opp_sources:
            return 1.0

        # Count total opposing sources (any opposing signal counts)
        opp_source_count = 0
        for opp_src in opp_sources:
            opp_parts = [p.strip() for p in opp_src.split(',') if p.strip()]
            opp_source_count += len(opp_parts)

        if opp_source_count > 0:
            # FIX (2026-05-05): -30% per opposing source, floor 65%.
            # Previous: floor 40% — death spiral with staleness decay kills signals in 2 cycles.
            # With floor=65%: opp_parts=5 → max(0.65, -0.50) = 0.65 → base = 57.2 (conf=88).
            # At staleness=0.6 → score=34. Survives 2+ cycles to build survival rounds.
            # With opp_parts=1-2 (typical for good signals): 70-73% multiplier — meaningful but not fatal.
            penalty = max(0.65, 1.0 - (opp_source_count * 0.30))
            log(f"  ⚠️  [OPP-PENALTY] {token} {direction}: {opp_source_count} opposing sources ({opp_direction}) → {penalty:.0%}")
            return penalty
        return 1.0
    except Exception as e:
        log(f"  [WARN] Opposing penalty query failed: {e}", 'WARN')
        return 1.0

# ── Main compaction ────────────────────────────────────────────────────────────
def run_compaction(dry=False, verbose=False, purge_executed=False):
    """
    Returns {'hotset': [...], 'compaction_cycle': N, 'approved': N, 'rejected': N}
    """
    log(f"Starting compaction (dry={dry})")
    start = time.time()

    # ── Step 1: Query and GROUP signals by token+direction ─────────────────
    # signal_gen creates one row per indicator. The compactor must group by
    # token+direction and MERGE sources so the confluence check (≥2 components)
    # works on combined signals, not individual indicator rows.
    # Each token+direction pair gets one consolidated row with merged source.

    # CRITICAL SECTION LOCK (ISSUE-1): Acquire before DB read, hold until after DB commit.
    # This prevents concurrent compaction runs from producing non-deterministic hotset.json.
    with FileLock('signal_compactor_critical'):
        conn = sqlite3.connect(RUNTIME_DB, timeout=30)
        c = conn.cursor()

        # ── FIX (2026-04-25): Expire PENDING signals older than 5 minutes ──────────
        # Signals older than 5 mins that haven't achieved confluence must not fish for
        # late-arriving second sources. This prevents 30+ min stale signals from
        # ghosting into hot-set via a random source overlap.
        c.execute("""
            UPDATE signals
            SET decision = 'EXPIRED',
                executed = 1,
                decision_reason = 'compaction_stale_5min',
                updated_at = CURRENT_TIMESTAMP
            WHERE decision = 'PENDING'
              AND executed = 0
              AND created_at < datetime('now', '-5 minutes')
        """)
        expired_count = c.rowcount
        if expired_count > 0:
            log(f"Expired {expired_count} stale PENDING signals (>5 min old)")
        conn.commit()

        # NEW MODEL (2026-04-26): Group by combo_key instead of token+direction.
        # Each distinct combo (token+direction+source-set) gets its own row,
        # so staleness is computed from that combo's own created_at, not
        # the most recent unrelated PENDING signal for the same token.
        c.execute("""
            SELECT
                token,
                direction,
                MAX(signal_type) AS signal_type,
                MAX(confidence)   AS confidence,
                -- Merge all distinct sources per combo_key
                GROUP_CONCAT(DISTINCT source) AS merged_source,
                MAX(created_at)   AS created_at,
                MAX(z_score_tier) AS z_score_tier,
                MAX(z_score)      AS z_score,
                MAX(compact_rounds) AS compact_rounds,
                MAX(hot_cycle_count) AS hot_cycle_count,
                MAX(signal_metadata) AS signal_metadata,
                combo_key
            FROM signals
            WHERE decision = 'PENDING'
              AND executed = 0
              AND created_at > datetime('now', '-5 minutes')
              AND confidence >= 60
              AND token NOT LIKE '@%'
              AND combo_key IS NOT NULL
              -- Solana-only tokens excluded via is_solana_only() call after GROUP BY
            GROUP BY combo_key
            ORDER BY confidence DESC
            LIMIT 150
        """)
        rows = c.fetchall()
        log(f"Query: {len(rows)} combo_keys in 5-min window (conf>=60, not executed)")

        # ── Step 2: Pre-filter ─────────────────────────────────────────────────
        signals = []
        for row in rows:
            token, direction, stype, conf, source, created = row[0], row[1], row[2], row[3], row[4], row[5]
            if direction.upper() == 'SHORT' and token in SHORT_BLACKLIST:
                continue
            if direction.upper() == 'LONG' and token in LONG_BLACKLIST:
                continue
            if is_solana_only(token):
                continue
            if is_delisted(token):
                continue
            # ── CONFLUENCE ENFORCEMENT (2026-04-18) ─────────────────────────────────
            # Single-source signals must NEVER be approved to hot-set.
            # They stay PENDING until a second source appears for the same token+direction.
            # Multi-source signals (2+ sources via GROUP_CONCAT) pass through freely.
            source_parts = [p.strip() for p in (source or '').split(',') if p.strip()]
            conf_float = float(conf or 0)

            # ── DIRECTIONAL CONFLICT DETECTION (2026-04-18) ──────────────────────
            # Parse directional suffix from each source component.
            # ONLY count sources that are genuinely directional (pct-hermes, vel-hermes,
            # macd-accel, ma-cross, etc.). hzscore, oc-mtf-macd, oc-mtf-rsi, gap-300,
            # phase-accel, fast-momentum, zscore-momentum are z-score or momentum
            # normalizations — their +/- is NOT a direction vote, it's a regime tag.
            # If both polarities of a GENUINELY DIRECTIONAL source are present,
            # the signals are fighting each other — skip entirely.
            # e.g. 'pct-hermes-,hzscore+,vel-hermes+' → CLEAN (hzscore is not directional)
            #      'pct-hermes+,pct-hermes-' → CONFLICT (same source, opposite dirs)
            #      'macd-accel+,macd-accel-' → CONFLICT
            NON_DIRECTIONAL_PREFIXES = (
                'hzscore', 'oc-mtf-macd', 'oc-mtf-rsi', 'gap-300',
                'phase-accel', 'fast-momentum', 'zscore-momentum',
            )
            directional_parts = [
                p for p in source_parts
                if not any(p.startswith(prefix) for prefix in NON_DIRECTIONAL_PREFIXES)
            ]
            long_srcs  = [p for p in directional_parts if p.endswith('+')]
            short_srcs = [p for p in directional_parts if p.endswith('-')]
            if long_srcs and short_srcs:
                log(f"  ⚔️  [CONFLICT] {token} {direction}: LONG={{{','.join(long_srcs)}}} vs SHORT={{{','.join(short_srcs)}}}, skipping")
                continue

            # ── CO-SIGNAL GATE (FIX 2026-05-06) ─────────────────────────────────────
            # Audit: 742 trades, deduplicated by token-direction-week.
            #
            # LONG rules:
            #   accel-300+ + ma-cross-5m+  → 16.7% WR  → BLOCK
            #   accel-300+ + pct-hermes+    → 35.7% WR  → BLOCK  (catches knives)
            #   accel-300+ + trend_purity+  → 62.5% WR  → PASS (no further restriction)
            #   accel-300+ + hzscore-       → 36.7% WR  → PASS (no better combo available)
            #
            # SHORT rules:
            #   hzscore+ + vel-hermes- WITHOUT pct-hermes- → 20% WR, −0.064% → BLOCK (poison)
            #   hzscore+ + vel-hermes- WITH pct-hermes-     → 46.2% WR, +0.382% → PASS
            #   hzscore+ + vel-hermes- + ma-cross-5m-       → 50% WR (2 trades) → but too sparse
            #
            # General SHORT poison (any direction):
            #   ma-cross-5m+ → poison for LONG, don't add to LONG combos
            #
            # Implementation: check poison patterns first (block), then check
            # required-co-signal patterns (require).
            has_accel_plus  = 'accel-300+'  in source_parts
            has_accel_minus = 'accel-300-' in source_parts
            has_hz_pos     = 'hzscore+'     in source_parts
            has_vel_neg    = 'vel-hermes-'  in source_parts
            has_pct_neg    = 'pct-hermes-'  in source_parts
            has_ma5m_pos   = 'ma-cross-5m+' in source_parts
            has_trend_pos  = 'trend_purity+' in source_parts

            # ── LONG poison blocks ──────────────────────────────────────────────
            if direction.upper() == 'LONG':
                if has_accel_plus and has_ma5m_pos:
                    log(f"  🛡️  [COSIG-GATE] {token} {direction}: accel-300+ + ma-cross-5m+ blocked (16.7% WR)")
                    continue
                # accel-300+ + pct-hermes+ = 35.7% WR — catches knives
                # But accel-300+ + pct-hermes+ + trend_purity+ = 62.5% WR (trend_purity+ overrides)
                # Only block if pct-hermes+ is present WITHOUT trend_purity+
                if has_accel_plus and 'pct-hermes+' in source_parts and not has_trend_pos:
                    log(f"  🛡️  [COSIG-GATE] {token} {direction}: accel-300+ + pct-hermes+ blocked (35.7% WR, catches knives)")
                    continue

            # ── SHORT poison + required co-signal logic ──────────────────────────
            if direction.upper() == 'SHORT':
                # POISON: hzscore+ + vel-hermes- without pct-hermes- = 20% WR
                if has_hz_pos and has_vel_neg and not has_pct_neg:
                    log(f"  🛡️  [COSIG-GATE] {token} {direction}: hzscore++vel-hermes- without pct-hermes- blocked (20% WR, poison)")
                    continue
                # accel-300- barely fires; no special gate needed
                if has_accel_minus and has_ma5m_pos:
                    log(f"  🛡️  [COSIG-GATE] {token} {direction}: accel-300- + ma-cross-5m+ blocked (low WR)")
                    continue

            # ── CONFLUENCE: collapse same-type multi-level sources (e.g. rs-s386,rs-s406) ─
            # Different bars_since values for the SAME signal type are NOT real confluence.
            # They represent the same signal re-firing at different times — fake diversity.
            # Normalize each part to its signal-type prefix, then count unique types.
            def _signal_type_key(part: str) -> str:
                # Strip ALL trailing digits that represent bars_since / level / bar counts.
                # These are the SAME signal at different timestamps — not distinct sources.
                # Pattern: source tag + optional directional suffix + digits.
                # rs-s386 → rs-s (support level 386 at different times)
                # rs-r1774 → rs-r (resistance level 1774 at different times)
                # rs-s4 → rs-s (single-digit level)
                # hhh-short4 → hhh-short (hh_hl breakout pullback)
                # hhh-long5 → hhh-long (hh_hl breakout breakout)
                # ma-death14 → ma-death (ma_cross death cross)
                # ma-golden5 → ma-golden (ma_cross golden cross)
                # pct-hermes+ → pct-hermes+ (keep directional suffix — no trailing digits)
                # macd-accel+ → macd-accel+ (keep directional suffix — no trailing digits)
                #
                # BUG FIX (2026-05-15): Previous regex only stripped ONE digit:
                #   r'^([a-z][a-z0-9_-]*)([+-]?)(\d+)$' → returns prefix+suffix+first_digit
                #   rs-s48 → 'rs-s4' (WRONG — keeps one digit)
                #   rs-s82 → 'rs-s8' (WRONG — keeps one digit)
                #   These were counted as different types → double-RS signals passed confluence.
                # FIX: Strip ALL trailing digits using re.sub(r'\d+$', '', part).
                # ALSO strip '-broken' suffix — rs-s-broken and rs-r are the SAME signal type
                # as rs-s, not distinct types. The -broken modifier describes the path, not
                # the signal family (support/resistance).
                part = re.sub(r'-broken$', '', part)
                # Collapse rs-s and rs-r to 'rs' — different directions of the same signal
                # family should not count as separate types for confluence purposes.
                # rs-s86, rs-r1774, rs-s-broken → all collapse to 'rs'
                part = re.sub(r'^rs-[sr]', 'rs', part)
                return re.sub(r'\d+$', '', part) or part

            unique_signal_types = len(set(_signal_type_key(p) for p in source_parts))
            source_count = len(source_parts)

            # ══ CONFLUENCE REQUIRED ══ — 2026-05-08
            # Rule: 2+ unique signal types required. No exceptions, no good-standalone bypass.
            # Single-source signals stay PENDING until a co-signal arrives.
            # If no co-signal within 5 min → staleness=0 → EXPIRED.
            # This is the ONLY valid path into the hot-set.
            pass_gate = False
            gate_msg = ''
            if unique_signal_types >= 2:
                pass_gate = True
                gate_msg = f'{unique_signal_types} unique types'
            else:
                # ── Accel-300 Standalone Bypass ───────────────────────────────────
                # Strong standalone accel-300 (no RS co-signal needed) — fire on
                # high-confidence accel-300 alone when the momentum is very strong.
                if (ACCEL_300_STANDALONE_BYPASS_ENABLED
                        and unique_signal_types == 1
                        and source.startswith('accel-300')
                        and conf >= ACCEL_300_STANDALONE_BYPASS_CONFIDENCE):
                    pass_gate = True
                    gate_msg = f'standalone accel-300 conf={conf:.0f}% >= {ACCEL_300_STANDALONE_BYPASS_CONFIDENCE}%'
                else:
                    gate_msg = f'only {unique_signal_types} unique types {{{source}}} — need 2+'

            # CRITICAL DEBUG: log EVERY combo before gate decision — no exceptions
            log(f"  🔎 [CONFLUENCE-DEBUG] {token} {direction}: source='{source}' parts={source_parts} count={source_count} unique_types={unique_signal_types} -> {'PASS' if pass_gate else 'BLOCK'}")

            if not pass_gate:
                log(f"  🔒 [CONFLUENCE-GATE-BLOCK] {token} {direction}: {gate_msg}")
                continue

            signals.append(row)
            log(f"  ✅ [CONFLUENCE-GATE-PASS] {token} {direction}: {{{source}}} ({gate_msg})")

        log(f"Pre-filter: {len(signals)} signals passed safety filters")
        if verbose and signals:
            for s in signals[:5]:
                log(f"  [{s[0]} {s[1]} conf={s[3]} src={s[4]}]")

        if not signals:
            log("No signals after pre-filter — hotset_final will be empty, merge step will preserve prev_hotset")
            # NOTE: Do NOT return here — Step 12 merge logic must still run to preserve prev_hotset

        # ── Step 3: Load speed data ────────────────────────────────────────────
        # speed_tracker.py writes to token_speeds DB every ~1 min.
        # signal_compactor reads from there (DB fallback below) — speed_cache.json
        # is optional and deprecated; no warning if missing.
        speed_cache = {}
        if os.path.exists(SPEED_CACHE_FILE):
            try:
                with open(SPEED_CACHE_FILE) as f:
                    speed_cache = json.load(f)
                log(f"Speed cache: {len(speed_cache)} tokens")
            except Exception as e:
                log(f"Speed cache load failed: {e} — using DB fallback", 'WARN')

        # Fallback: load from token_speeds DB table for any missing tokens
        try:
            _conn = sqlite3.connect(RUNTIME_DB)
            _cur = _conn.cursor()
            _cur.execute("SELECT token, speed_percentile, momentum_score, wave_phase, is_overextended, price_acceleration FROM token_speeds")
            for _row in _cur.fetchall():
                _tok, _sp, _mom, _wave, _over, _accel = _row
                if _tok.upper() not in speed_cache:
                    speed_cache[_tok.upper()] = {
                        'speed_percentile': _sp or 50.0,
                        'momentum_score': _mom or 50.0,
                        'wave_phase': _wave or 'neutral',
                        'is_overextended': bool(_over),
                        'price_acceleration': _accel or 0.0,
                    }
            _conn.close()
        except Exception as e:
            log(f"Speed DB fallback failed: {e} — using defaults", 'WARN')

        # ── Step 4: Regime cache ────────────────────────────────────────────────
        unique_tokens = list({s[0].upper() for s in signals})
        prev_hotset = {}
        prev_hotset_by_combo = {}  # combo_key -> entry for rounds lookup
        if os.path.exists(HOTSET_FILE):
            try:
                with open(HOTSET_FILE) as f:
                    data = json.load(f)
                    for s in data.get('hotset', []):
                        # Back-fill final_confidence for entries from older compaction runs
                        if 'final_confidence' not in s:
                            s['final_confidence'] = s.get('confidence', 50)
                        prev_hotset[f"{s['token']}:{s['direction']}"] = s
                        # Build combo_key -> entry lookup for rounds tracking
                        ck = s.get('combo_key')
                        if ck:
                            prev_hotset_by_combo[ck] = s
                log(f"Previous hotset: {len(prev_hotset)} entries, {len(prev_hotset_by_combo)} with combo_key")
            except Exception as e:
                log(f"Could not load previous hotset: {e}", 'WARN')

        # Close DB connection after all queries in the critical section are done.
        # Moved here from above Step 2 (was closing before Step 5 ran, breaking Issue #1 fix).
        conn.close()

        # ── Step 5: Score each signal (with opposing signal penalty) ─────────────
        # combo_key is at index 10 (added to GROUP BY query above)
        scored = []
        for row in signals:
            token, direction, stype, conf, source, created = row[0], row[1], row[2], row[3], row[4], row[5]
            cr = row[8] or 0  # compact_rounds column (index 8)
            combo_key = row[10] if len(row) > 10 else None  # combo_key (index 10)

            # Compute age of signal in minutes
            try:
                created_t = datetime.strptime(created, '%Y-%m-%d %H:%M:%S')
                age_m = (datetime.now() - created_t).total_seconds() / 60
            except Exception:
                age_m = 999

            regime, regime_conf = get_regime_1m(token)
            speed_data = speed_cache.get(token.upper(), {})
            source_parts = [p.strip() for p in (source or '').split(',') if p.strip()]
            # ── rs required (replaces accel-300, 2026-05-15) ──────────────────────────
            has_rs = any(p.startswith('rs') for p in source_parts)
            if not has_rs:
                if verbose:
                    log(f"  SKIP {token} {direction}: no rs signal")
                continue
            # ── Trend purity bonus: major confidence boost when present ──────────
            has_trend_purity = ('trend_purity+' in source_parts or 'trend_purity-' in source_parts)
            tp_bonus_mult = 1.50 if has_trend_purity else 1.0
            base_score = _score_signal(
                token=token,
                direction=direction.upper(),
                conf=conf,
                source=source or '',
                signal_type=stype or '',
                age_m=age_m,
                compact_rounds=cr,
                regime=regime,
                regime_conf=regime_conf,
                speed_data=speed_data,
            )

            # Opposing signal penalty: check if opposing direction is firing for this token
            opp_penalty = _get_opposing_penalty(RUNTIME_DB, token, direction)
            score = base_score * opp_penalty

            if verbose:
                log(f"  Score {token} {direction}: conf={conf} age_m={age_m:.2f} cr={cr} "
                    f"regime={regime} speed={speed_data.get('speed_percentile','?')} "
                    f"→ score={score:.2f}")

            if score <= 0:
                if verbose:
                    log(f"  SCORE-ZERO skip {token} {direction}: age_m={age_m:.2f}")
                continue

            # FIX (2026-04-23): Use signal-source-specific cooldown check.
            # The blanket get_cooldown(token, direction) checks ALL cooldowns for a
            # token+direction — including cooldowns set by individual signal generators
            # (gap300, ma_cross_5m, zscore_momentum) for signals that never passed the
            # confluence gate. This caused all 230 PostgreSQL cooldowns to block all
            # multi-source signals, leaving hot-set.json empty.
            #
            # Instead, check only loss_cooldowns.json (guardian's authoritative
            # loss-cooldown) — which tracks actual losing trades. The 230 PostgreSQL
            # cooldowns are signal-generator cooldowns that should NOT block confluence
            # signals from other generators.
            from signal_schema import _is_loss_cooldown_active
            if _is_loss_cooldown_active(token, direction):
                if verbose:
                    log(f"  LOSS-COOLDOWN skip {token} {direction}")
                continue

            scored.append({
                'row': row,
                'score': score,
                'age_m': age_m,
                'regime': regime,
                'regime_conf': regime_conf,
                'speed_data': speed_data,
                'combo_key': combo_key,
                'tp_bonus_mult': tp_bonus_mult,   # 1.5 if trend_purity present, else 1.0
            })

        # ── Step 7: Rank and select top 10 ──────────────────────────────────────
        # Apply trend_purity bonus multiplier to score for ranking purposes.
        for s in scored:
            s['score'] = s['score'] * s.get('tp_bonus_mult', 1.0)
        scored.sort(key=lambda x: x['score'], reverse=True)
        top_signals = scored[:10]

        # ── Step 7b: Cross-direction conflict resolution ─────────────────────────
        # If both LONG and SHORT for the same token are in top 10:
        #   - Winner (higher score): APPROVED, 15% score penalty applied for ranking
        #   - Loser (lower score): stays in list, back to PENDING at Step 13
        # Penalty on winner preserves conflict signal info while letting the opposing
        # direction rank higher in future cycles when conflict resolves.
        by_token = {}
        for s in top_signals:
            tok = s['row'][0]
            direction = s['row'][1]
            conf = s['score']
            if tok not in by_token:
                by_token[tok] = []
            by_token[tok].append((direction, conf, s))

        conflict_loser_signals = []
        for tok, entries in by_token.items():
            dirs = [e[0] for e in entries]
            if 'LONG' in dirs and 'SHORT' in dirs:
                entries.sort(key=lambda x: x[1], reverse=True)  # highest score first
                winner_dir, winner_conf, winner_s = entries[0]
                loser_dir, loser_conf, loser_s = entries[1]
                log(f"  ⚔️  [CROSS-DIR CONFLICT] {tok}: winner={winner_dir}({winner_conf:.1f}) loser={loser_dir}({loser_conf:.1f}) → winner -15% penalty, loser → PENDING")
                # Apply 15% penalty to winner's score for ranking purposes
                winner_s['score'] = winner_conf * 0.85
                conflict_loser_signals.append(loser_s)

        # Re-sort with penalized winner scores, then remove losers
        top_signals.sort(key=lambda x: x['score'], reverse=True)

        # Loser is removed — it goes back to PENDING at Step 13, not APPROVED
        top_signals = [s for s in top_signals if s not in conflict_loser_signals]

        # ── Step 8: Deduplicate by token+direction ─────────────────────────────
        seen = set()
        unique_top_signals = []
        for s in top_signals:
            key = f"{s['row'][0]}:{s['row'][1]}"
            if key not in seen:
                seen.add(key)
                unique_top_signals.append(s)

        # ── Step 9: Build hot-set entries with new rounds model ───────────────────
        # NEW MODEL (2026-04-26):
        # - rounds = consecutive cycles identical combo fired together
        # - combo_key (token:direction:sorted-sources) identifies the combo
        # - Look up combo_key in prev_hotset_by_combo → rounds = prev_rounds + 1
        # - If not found → rounds = 1 (new combo)
        # - Staleness computed from MAX(created_at) of combo's sources
        hotset_entries = []
        for s in unique_top_signals:
            row = s['row']
            token, direction, stype, conf, source = row[0], row[1], row[2], row[3], row[4]
            cr = row[8] or 0  # compact_rounds (PENDING failure count — not used for rounds)
            combo_key = s.get('combo_key')  # from scored dict
            spd = s['speed_data']

            # Rounds: look up combo_key in previous hot-set
            # rounds = prev_rounds + 1 only if combo fired this cycle (DB entry exists)
            # rounds stays the same if just being preserved from previous hot-set
            prev_entry = prev_hotset_by_combo.get(combo_key) if combo_key else None
            if prev_entry:
                rounds = prev_entry.get('rounds', 0) + 1
            else:
                rounds = 1  # New combo

            # Staleness: max(0, 1 - age_min * 0.2) where age_min is from entry_origin_ts.
            # For new combos entering hot-set: entry_origin_ts = now → staleness = 1.0 (fresh).
            # For preserved combos re-entering: entry_origin_ts carries forward from when
            # the combo first entered hot-set — preserving continuous staleness timeline.
            # This means a combo that survived 3 cycles has staleness computed from its
            # original entry, not from when it most recently fired. Age from DB created_at
            # is only used for score weighting in _score_signal (age_m parameter).
            if prev_entry:
                prev_origin_ts = prev_entry.get('entry_origin_ts')
                entry_origin_ts = prev_origin_ts if prev_origin_ts else time.time()
            else:
                entry_origin_ts = time.time()
            age_from_entry = (time.time() - entry_origin_ts) / 60.0
            staleness = max(0.0, 1.0 - (age_from_entry * 0.2))

            hotset_entries.append({
                'token': token,
                'direction': direction.upper(),
                'confidence': conf,
                'final_confidence': conf,  # decider_run reads this field
                'source': source,
                'signal_type': stype,
                'z_score': row[7] or 0,  # z_score column (index 7)
                'combo_key': combo_key,
                'rounds': rounds,  # replaces survival_round (no +1 offset)
                'staleness': staleness,
                'compact_rounds': cr,  # PENDING failure count (kept for DB tracking)
                'survival_round': rounds,  # backward compat — same as rounds
                'survival_score': rounds * 0.5,  # kept for backward compat
                'age_m': s['age_m'],
                'regime': s.get('regime', 'NEUTRAL'),       # 15m regime from signal_compactor
                'regime_conf': s.get('regime_conf', 0),     # 15m regime confidence
                'wave_phase': spd.get('wave_phase', 'neutral'),
                'is_overextended': spd.get('is_overextended', False),
                'price_acceleration': spd.get('price_acceleration', 0.0),
                'momentum_score': spd.get('momentum_score', 50.0),
                'speed_percentile': spd.get('speed_percentile', 50.0),
                'score': s['score'],
                'tp_bonus_mult': s.get('tp_bonus_mult', 1.0),  # 1.5 if trend_purity present
                'entry_origin_ts': entry_origin_ts,  # carried forward if combo existed, else now
                # JSONB catch-all: all signal indicator values at entry time (future-proof)
                'signal_metadata': row[11] if len(row) > 11 else None,
            })

        # ── Step 10: Build reason strings ───────────────────────────────────────
        for entry in hotset_entries:
            spd = entry
            entry['reason'] = (
                f"deterministic score={entry['score']:.1f} "
                f"rounds={entry['survival_round']} "
                f"wave={spd.get('wave_phase','unknown')} "
                f"momentum={spd.get('momentum_score','?')} "
                f"speed={spd.get('speed_percentile','?')} "
                f"overextended={spd.get('is_overextended',False)}"
            )

        # ── Step 11 (pre): Get tokens with open positions ─────────────────────────
        open_tokens = _get_open_tokens()
        if open_tokens:
            log(f"[OPEN-POS-FILTER] Tokens with open positions: {sorted(open_tokens)}")

        # ── Step 11: Safety filters on entries ─────────────────────────────────
        hotset_final = []
        for entry in hotset_entries:
            tkn = entry['token']
            direction = entry['direction']
            src = entry.get('source', '')

            if direction == 'SHORT' and tkn in SHORT_BLACKLIST:
                log(f"  🚫 [HOTSET-FILTER] {tkn}: SHORT blocked — SHORT_BLACKLIST")
                continue
            if direction == 'LONG' and tkn in LONG_BLACKLIST:
                log(f"  🚫 [HOTSET-FILTER] {tkn}: LONG blocked — LONG_BLACKLIST")
                continue
            if is_solana_only(tkn):
                log(f"  🚫 [HOTSET-FILTER] {tkn}: blocked — Solana-only")
                continue
            if is_delisted(tkn):
                log(f"  🚫 [HOTSET-FILTER] {tkn}: blocked — delisted")
                continue
            # ── Source blacklist filter (mirrors signal_schema.validate_source) ─────────
            # Uses validate_source() for correct handling:
            # 1. Exact match: whole source in blacklist → block
            # 2. 3+ signals: if blacklist combo is subset → ALLOW
            # 3. vel-hermes+ blocked via sentinel suffix-agnostic match
            from signal_schema import validate_source
            src = src.strip() if src else ''
            if validate_source(src) == 'unknown':
                log(f"  🚫 [HOTSET-FILTER] {tkn}: blocked — source '{src}' in blacklist")
                continue
            source_parts = [p.strip() for p in (src or '').split(',') if p.strip()]
            # rs required for all entries (replaces accel-300, 2026-05-15)
            # rs is the primary directional trigger. Every LONG needs rs-s#,
            # every SHORT needs rs-r# as the primary directional confirmation.
            has_rs = any(p.startswith('rs') for p in source_parts)
            if not has_rs:
                log(f"  🚫 [HOTSET-FILTER] {tkn}: blocked — requires rs-s# or rs-r# (has: {src})")
                continue
            # ── Trend purity bonus: major confidence boost when present ─────────────
            # trend_purity is no longer a hard requirement — it's a scoring bonus.
            # Signals with trend_purity+ (LONG) or trend_purity- (SHORT) get +50% source weight.
            # This rewards trend-confirmed entries without blocking trend-agnostic ones.
            has_trend_purity = ('trend_purity+' in source_parts or 'trend_purity-' in source_parts)
            tp_bonus_mult = 1.50 if has_trend_purity else 1.0
            # ── OC Signal Block (2026-04-29) ─────────────────────────────────────────
            # oc_pending/oc_rsi signals are generated by OpenClaw's external system
            # and should NOT drive Hermes trades on their own.
            # HOWEVER: they CAN contribute to confluence (the 2+ source requirement).
            # If this combo has at least one real (non-OC) source, let it through —
            # the OC contribution is valid confluence even if the final direction
            # is ultimately driven by real indicators (pct-hermes, macd-accel, etc.).
            # Only block if the combo is PURELY OC-driven (no real source overlap).
            sig_type = entry.get('signal_type', '')
            if sig_type in ('oc_pending', 'oc_rsi'):
                # Check if any source component is a real (non-OC) signal
                oc_only = True
                for p in source_parts:
                    if not p.startswith('oc_'):
                        oc_only = False
                        break
                if oc_only:
                    log(f"  🚫 [HOTSET-FILTER] {tkn}: blocked — OC-only combo (no real source confluence)")
                    continue
                # Else: has real confluence — let it through
            # Skip tokens that already have an open position — prevents ghost
            # APPROVED signals that block all future real trades for this token
            if tkn.lower() in open_tokens:
                log(f"  🚫 [HOTSET-FILTER] {tkn}: blocked — already has open position")
                continue
            # ── Flip eviction: skip tokens recently cascade-flipped ───────────────
            # cascade_flip_helpers.mark_token_flipped() sets hotset_evicted=True
            # for ~10 minutes after a flip so signal_compactor doesn't add a
            # redundant second position while the post-flip position is proving itself.
            try:
                from cascade_flip_helpers import is_token_evicted, clear_expired_evictions
                clear_expired_evictions()  # clean up any deadlines that have passed
                if is_token_evicted(tkn):
                    log(f"  🚫 [HOTSET-FILTER] {tkn}: blocked — recently flipped (eviction active)")
                    continue
            except Exception:
                pass  # non-fatal — helper may not be available in all environments
            # ── Per-coin WR filter (2026-05-11) ─────────────────────────────────
            # Block tokens with <50% WR and ≥3 trades — prevents signal_compactor
            # from building hot-set entries for tokens that decider_run would
            # block anyway. Stops the feedback loop of selecting losers.
            wr, wr_count = _get_token_wr(tkn, direction)
            if wr < 50 and wr_count >= 3:
                log(f"  🚫 [HOTSET-FILTER] {tkn}: {direction} blocked — WR={wr:.0f}% ({wr_count} trades)")
                continue
            # CRITICAL DEBUG: log every entry entering hotset_final — catch single-source bypass
            src_parts = [p.strip() for p in (src or '').split(',') if p.strip()]
            # ── FINAL CONFLUENCE GUARD (2026-05-12) ─────────────────────────────────
            # This is the last line of defense: even if a single-source entry somehow
            # passed _filter_safe_prev_hotset (preservation path) or the DB query path,
            # it is HARD-BLOCKED here before entering hotset_final.
            # BUG FIX: MERL/ME/BRETT executed single-source (accel-300+) at 16:49 on May 12.
            # The confluence gate at Step 2 (line 537) and _filter_safe_prev_hotset both
            # have the correct logic, but a race condition or DB state edge case allowed
            # single-source entries to slip through into hotset_final. This guard
            # catches that edge case permanently.
            if len(src_parts) < 2:
                log(f"  🚫 [HOTSET-FINAL-BLOCK] {tkn}:{direction} SINGLE-SOURCE BLOCKED at final guard — src='{src}' (this should never happen — investigate confluence gate or preservation path)")
                continue
            log(f"  ➡️  [HOTSET-FINAL-ADD] {tkn}:{direction} src='{src}' parts={src_parts} parts_count={len(src_parts)} conf={entry.get('confidence')} score={entry.get('score',0):.2f}")
            hotset_final.append(entry)

        # ── Step 12: Preserve previous hotset entries that didn't make it from DB ──
        # FIX (2026-04-27): Always run _filter_safe_prev_hotset and merge with DB entries.
        # Previously: if hotset_final was non-empty, prev_hotset was DISCARDED entirely.
        # This caused breakout_engine entries (not in DB) to be dropped when DB had signals.
        # Now: preserve prev entries that pass safety + staleness, merge with DB entries
        # per token:direction, keeping the higher-scoring entry.
        preserved = _filter_safe_prev_hotset(prev_hotset)
        if preserved:
            # Build keyed dict of DB entries for merge
            db_by_key = {f"{e['token']}:{e['direction']}": e for e in hotset_final}
            # For each preserved entry: if no DB entry exists for that token:direction,
            # add it; if DB entry exists, keep the one with higher score
            for pe in preserved:
                key = f"{pe['token']}:{pe['direction']}"
                existing = db_by_key.get(key)
                # ── FINAL CONFLUENCE GUARD for preserved entries (2026-05-12) ─────────
                # Preserved entries passed _filter_safe_prev_hotset which has a confluence
                # check. But when they merge with DB entries (existing), the merged entry
                # could theoretically become single-source if the DB entry has a conflicting
                # single source. This guard ensures the merged entry still has 2+ sources.
                pe_src = pe.get('source', '')
                pe_parts = [p.strip() for p in (pe_src or '').split(',') if p.strip()]
                if len(pe_parts) < 2:
                    log(f"  🚫 [PRESERVE-MERGE-BLOCK] {pe['token']}:{pe['direction']} SINGLE-SOURCE BLOCKED at merge — src='{pe_src}' — investigate _filter_safe_prev_hotset confluence check")
                    continue
                # Track whether preserved entry won the merge (for APPROVED upsert below)
                _preserved_won = False
                if existing is None:
                    # CRITICAL DEBUG: preserved entry enters hotset (no DB entry competition)
                    log(f"  🔄 [PRESERVE-ADD] {pe['token']}:{pe['direction']} src='{pe_src}' parts={pe_parts} parts_count={len(pe_parts)} score={pe.get('score',0):.2f} (preserved, no DB entry)")
                    db_by_key[key] = pe  # no DB entry — take preserved
                    _preserved_won = True
                elif existing.get('score', 0) <= 0 and pe.get('score', 0) <= 0:
                    # FIX (2026-05-05): Both expired (score=0). Keep the one with lower age_m
                    # (newer entry has better chance of being genuinely expired vs. a stale
                    # entry from a prior compaction run that missed expiry). If pe is newer
                    # (lower age_m), replace. If existing is newer, keep it.
                    existing_age = existing.get('age_m', 999)
                    pe_age = pe.get('age_m', 999)
                    if pe_age < existing_age:
                        db_by_key[key] = pe
                        _preserved_won = True
                elif existing.get('score', 0) < pe.get('score', 0):
                    db_by_key[key] = pe  # preserved has higher score — use it
                    _preserved_won = True
                # else: keep DB entry (higher score)

                # ── APPROVED-DB upsert when preserved entry won the merge (2026-05-21) ──
                # FIX: Preserved entries bypass the PENDING→APPROVED gate because they have
                # no DB row (or the DB row lost the merge). Without an APPROVED row in the DB,
                # decider_run's get_approved_signals() returns [] and no trades fire — even
                # though the token is legitimately in hotset.json. This ensures decider_run
                # can find and execute the preserved entry.
                if _preserved_won and not dry:
                    try:
                        _pe_ck = pe.get('combo_key') or f"{pe['token']}:{pe['direction']}:{pe_src}"
                        _conn = sqlite3.connect(RUNTIME_DB, timeout=30)
                        _cur = _conn.cursor()
                        _cur.execute("""
                            SELECT id, survival_rounds FROM signals
                            WHERE token=? AND direction=? AND decision='APPROVED' AND executed=0
                            LIMIT 1
                        """, (pe['token'], pe.get('direction','')))
                        _row = _cur.fetchone()
                        if _row:
                            _prev_sr = _row[1] or 0
                            _new_sr = max(_prev_sr, int(pe.get('rounds', 1)))
                            _cur.execute("""
                                UPDATE signals
                                SET survival_rounds=MAX(COALESCE(survival_rounds,0), ?),
                                    hot_cycle_count=COALESCE(hot_cycle_count,0)+1,
                                    updated_at=CURRENT_TIMESTAMP,
                                    source=?,
                                    combo_key=?
                                WHERE id=?
                            """, (_new_sr, pe_src, _pe_ck, _row[0]))
                        else:
                            _cur.execute("""
                                INSERT INTO signals (
                                    token, direction, signal_type, source, confidence,
                                    decision, executed, z_score, survival_rounds,
                                    hot_cycle_count, combo_key, price, created_at,
                                    updated_at
                                ) VALUES (?, ?, ?, ?, ?, 'APPROVED', 0, ?, ?, 1, ?, ?,
                                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                            """, (
                                pe['token'], pe.get('direction',''),
                                pe.get('signal_type','hot-set'),
                                pe_src,
                                pe.get('confidence', 50.0) or 50.0,
                                pe.get('z_score', 0) or 0,
                                int(pe.get('rounds', 1)),
                                _pe_ck,
                                pe.get('price') or 0,
                            ))
                        _conn.commit()
                        _conn.close()
                        log(f"  ✅ [PRESERVE-APPROVED-UPSERT] {pe['token']}:{pe.get('direction')} — APPROVED row upserted for decider_run")
                    except Exception as _e:
                        import traceback
                        log(f"  ⚠️  [PRESERVE-APPROVED-FAIL] {pe['token']}: {_e}")
                        log(f"     Stack: {traceback.format_exc()[:200]}")
            hotset_final = list(db_by_key.values())
            # Re-sort by score descending
            hotset_final.sort(key=lambda x: x.get('score', 0), reverse=True)
            log(f"Merged {len(preserved)} preserved entries with {len(db_by_key)} DB entries")

        # Cap at 10
        hotset_final = hotset_final[:10]

        # ── Step 13: Update DB decisions ─────────────────────────────────────────
        # NEW MODEL (2026-04-26):
        # - PENDING signals wait for confluence — no rejection on cr>=5
        # - PENDING signals with staleness=0 are marked EXPIRED
        # - When combo enters top-10: survival_rounds = prev+1 or 1 (new)
        # - APPROVED signals still in top-10: survival_rounds++
        # - APPROVED signals out of top-10 with staleness=0: EXPIRED
        if not dry:
            conn = sqlite3.connect(RUNTIME_DB, timeout=30)
            c = conn.cursor()

            # ── Step 12b: Proactively expire signals with newly-blacklisted sources ─
            # FIX (2026-05-05): When hermes_constants.SIGNAL_SOURCE_BLACKLIST is updated,
            # existing PENDING/APPROVED signals from before the blacklist change are never
            # purged — validate_source() only fires on NEW writes. This catches any stale
            # entries that survived from before the blacklist update and expire them.
            from signal_schema import validate_source
            cur = c.execute("SELECT id, source FROM signals WHERE decision IN ('PENDING','APPROVED') AND executed=0")
            expired_ids = []
            for row_id, src in cur.fetchall():
                if validate_source(src or '') == 'unknown':
                    c.execute("""
                        UPDATE signals
                        SET decision='EXPIRED', expired_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP
                        WHERE id=? AND decision IN ('PENDING','APPROVED') AND executed=0
                    """, (row_id,))
                    expired_ids.append(row_id)
            if expired_ids:
                log(f"EXPIRED {len(expired_ids)} signals whose sources were blacklisted since entry (enforcement gap fix)")

            top10_keys = {f"{e['token']}:{e['direction']}" for e in hotset_final}
            top10_combos = {e.get('combo_key') for e in hotset_final if e.get('combo_key')}

            # ── Process PENDING/WAIT candidates ───────────────────────────────────
            c.execute("""
                SELECT id, token, direction, COALESCE(compact_rounds, 0) AS cr,
                       combo_key, created_at, source
                FROM signals
                WHERE decision IN ('PENDING', 'WAIT')
                  AND executed = 0
                  AND created_at > datetime('now', '-60 minutes')
                  AND token NOT LIKE '@%'
                  AND (token, direction) NOT IN (
                      SELECT token, direction FROM signals
                      WHERE decision = 'APPROVED' AND executed = 0
                  )
            """)
            all_sig_rows = c.fetchall()

            approved_ids = []      # PENDING→APPROVED transitions
            expired_ids = []      # PENDING→EXPIRED (staleness=0)
            still_pending_ids = [] # PENDING stays PENDING (not yet expired)

            for sid, tok, d, cr, ck, sig_created_at, source in all_sig_rows:
                key = f"{tok.upper()}:{d.upper()}"
                if key in top10_keys:
                    # ── CONFLUENCE CHECK (2026-05-12) ─────────────────────────────────
                    # A PENDING row entering top-10 must have 2+ unique signal sources.
                    # The DB pre-filter already gates new signals, but this loop processes
                    # ALL PENDING rows in the 60-min window — including single-source rows
                    # from add_signal() merges that lost a source. Skip any combo with
                    # only 1 source, regardless of its score or top-10 standing.
                    src_parts = [p.strip() for p in (source or '').split(',') if p.strip()]
                    if len(src_parts) < 2:
                        log(f"  🔒 [PENDING-APPROVE-BLOCK] {tok}:{d} single-source blocked from APPROVE — src='{source}' parts={len(src_parts)} — need 2+ for confluence")
                        continue
                    # Combo entered top-10 → APPROVED immediately.
                    # No age gate — if it's in top-10 it's signal-worthy.
                    # If it stops firing, staleness=0 will expire it within 5 min.
                    prev_combo = prev_hotset_by_combo.get(ck) if ck else None
                    if prev_combo:
                        new_sr = prev_combo.get('rounds', 0) + 1
                    else:
                        new_sr = 1  # New combo
                    c.execute("""
                        UPDATE signals
                        SET decision = 'APPROVED',
                            survival_rounds = ?,
                            hot_cycle_count = COALESCE(hot_cycle_count, 0) + 1,
                            review_count = COALESCE(review_count, 0) + 1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (new_sr, sid))
                    approved_ids.append(sid)
                else:
                    # Not in top-10: check staleness directly via created_at
                    # Staleness=0 means no firing for 5 min → EXPIRED
                    # FIX (2026-04-26): Use created_at age, NOT compact_rounds.
                    # compact_rounds is PENDING failure count — it doesn't tell us
                    # whether the signal fired recently. A cr=0 signal could be 10
                    # minutes old and should be expired. A cr>0 signal could have
                    # just entered the merge window and should stay PENDING.
                    created_ts = time.mktime(time.strptime(sig_created_at, '%Y-%m-%d %H:%M:%S'))
                    age_m = (time.time() - created_ts) / 60.0
                    # Staleness = 5 min. Signals must find confluence (enter top-10) within
                    # 5 min or they expire. Same timer as hot-set expiry — stale signals
                    # no longer useful.
                    if age_m < 5.0:
                        still_pending_ids.append(sid)
                    else:
                        # age_m >= 5: no new firing for 5 min → EXPIRED
                        c.execute("""
                            UPDATE signals
                            SET decision = 'EXPIRED',
                                expired_at = CURRENT_TIMESTAMP,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (sid,))
                        expired_ids.append(sid)

            if approved_ids:
                log(f"APPROVED {len(approved_ids)} signals (combo entered top-10)")
            if expired_ids:
                log(f"EXPIRED {len(expired_ids)} PENDING signals (staleness=0)")
            if still_pending_ids:
                log(f"PENDING {len(still_pending_ids)} signals (still waiting for top-10)")

            # ── Maintain APPROVED signals ─────────────────────────────────────────
            # APPROVED signals still in top-10: bump survival_rounds
            if top10_combos:
                c.execute(f"""
                    UPDATE signals
                    SET survival_rounds = COALESCE(survival_rounds, 0) + 1,
                        hot_cycle_count = COALESCE(hot_cycle_count, 0) + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE decision = 'APPROVED'
                      AND executed = 0
                      AND combo_key IN ({','.join(['?' for _ in top10_combos])})
                """, list(top10_combos))
                refreshed = c.rowcount
                if refreshed:
                    log(f"Refreshed {refreshed} APPROVED signals still in hot-set")

            # APPROVED signals that left top-10 and are stale: EXPIRED
            # FIX (2026-05-12): Two bugs caused APPROVED signals to hang indefinitely:
            # 1. combo_key IS NULL signals were never expired (gate required combo_key IS NOT NULL)
            # 2. hot_cycle_count >= 2 gate meant hcc=0 or hcc=1 signals survived an extra cycle
            # NEW BEHAVIOR: Any APPROVED signal not refreshed in top-10 within 5 min expires.
            # This matches the 5-min staleness boundary used for PENDING signals.
            if approved_ids:
                c.execute(f"""
                    UPDATE signals
                    SET decision = 'EXPIRED',
                        expired_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE decision = 'APPROVED'
                      AND executed = 0
                      AND id NOT IN ({','.join(['?' for _ in approved_ids])})
                      AND (
                          -- Has combo_key but it's not in current hot-set
                          (combo_key IS NOT NULL AND combo_key NOT IN (
                              SELECT combo_key FROM signals
                              WHERE decision = 'PENDING'
                                AND executed = 0
                                AND combo_key IS NOT NULL
                                AND created_at > datetime('now', '-5 minutes')
                          ))
                          -- No combo_key (null signals never expire — FIX: now they do)
                          OR (combo_key IS NULL)
                      )
                """, approved_ids)
            else:
                c.execute(f"""
                    UPDATE signals
                    SET decision = 'EXPIRED',
                        expired_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE decision = 'APPROVED'
                      AND executed = 0
                      AND (
                          (combo_key IS NOT NULL AND combo_key NOT IN (
                              SELECT combo_key FROM signals
                              WHERE decision = 'PENDING'
                                AND executed = 0
                              AND combo_key IS NOT NULL
                              AND created_at > datetime('now', '-5 minutes')
                          ))
                          OR (combo_key IS NULL)
                      )
                """)
            left_and_stale = c.rowcount
            if left_and_stale:
                log(f"EXPIRED {left_and_stale} APPROVED signals (left hot-set, staleness=0)")

            conn.commit()
            conn.close()

        # ── Step 14: Compute compaction cycle ───────────────────────────────────
        prev_cycle = 0
        if os.path.exists(HOTSET_FILE):
            try:
                with open(HOTSET_FILE) as f:
                    prev_data = json.load(f)
                    prev_cycle = prev_data.get('compaction_cycle', 0)
            except Exception:
                pass
        compaction_cycle = prev_cycle + 1

        # ── Step 15: Write hotset.json ──────────────────────────────────────────
        hotset_output = []
        for e in hotset_final:
            src = e.get('source', '')
            # Count raw source entries (comma-separated, e.g. 'hwave+,hzscore-,hzscore+' → 3)
            parts = [p.strip() for p in (src or '').split(',') if p.strip()]
            entries_count = len(parts) if parts else 1

            # CRITICAL SAFETY GATE: last-resort block of single-source entries
            # If a single-source entry somehow got past the confluence gate above,
            # this is the final catch before it reaches decider_run.
            if entries_count < 2:
                log(f"  🛡️ [SAFETY-FILTER] {e['token']}:{e.get('direction')} BLOCKED from hotset.json — single-source src='{src}' parts_count={entries_count} (LAST RESORT BLOCK)")
                continue

            log(f"  💾 [HOTSET-WRITE] {e['token']}:{e.get('direction')} src='{src}' parts={parts} entries_count={entries_count} score={e.get('score',0):.2f}")

            hotset_output.append({
                'token': e['token'],
                'direction': e['direction'],
                'confidence': e['confidence'],
                'reason': e['reason'],
                'source': src,
                'entries_count': entries_count,
                'z_score': e.get('z_score', 0),
                'combo_key': e.get('combo_key'),       # NEW: combo identity
                'rounds': e.get('rounds', 1),            # NEW: survival rounds (no +1 offset)
                'staleness': e.get('staleness', 1.0),   # NEW: staleness (1.0=fresh, 0.0=dead)
                'compact_rounds': e.get('compact_rounds', 0),  # PENDING failure count
                'final_score': e.get('score', 0.0),
                'tp_bonus_mult': e.get('tp_bonus_mult', 1.0),   # 1.5 if trend_purity present
                'survival_score': e.get('survival_score', 0.0),  # backward compat
                'survival_round': e.get('survival_round', 1),    # backward compat (= rounds)
                'entry_origin_ts': e.get('entry_origin_ts', e.get('timestamp', time.time())),  # staleness tracking
                'regime': e.get('regime', 'NEUTRAL'),            # 15m regime
                'regime_conf': e.get('regime_conf', 0),          # 15m regime confidence
                'wave_phase': e['wave_phase'],
                'is_overextended': e['is_overextended'],
                'price_acceleration': e['price_acceleration'],
                'momentum_score': e['momentum_score'],
                'speed_percentile': e['speed_percentile'],
                'timestamp': time.time(),
            })

        if not dry:
            # FIX (2026-04-23): Remove tokens with open positions right before writing.
            # This closes the ~1-minute gap where guardian fires a trade but compactor
            # hasn't run yet. Guardian writes to PostgreSQL immediately on trade open,
            # but hotset.json only updates on the next compaction cycle. By checking
            # live PostgreSQL data here, we ensure that any token guardian just opened
            # is immediately removed from hot-set.json — preventing ghost signals and
            # the re-entry loop (MEME kept coming back because new signals kept appearing
            # while the traded one was stuck in hot-set).
            live_open_tokens = _get_open_tokens()
            if live_open_tokens:
                before = len(hotset_output)
                hotset_output = [e for e in hotset_output if e['token'].lower() not in live_open_tokens]
                removed = before - len(hotset_output)
                if removed:
                    log(f"  🛡️  [HOTSET-FILTER] Removed {removed} traded tokens (open pos): {sorted(live_open_tokens & {e['token'].lower() for e in hotset_output[:before]})}")

            import tempfile
            with FileLock('hotset_json'):
                tmp_fd, tmp_path = tempfile.mkstemp(
                    dir=os.path.dirname(HOTSET_FILE), prefix='hotset_', suffix='.tmp')
                try:
                    with os.fdopen(tmp_fd, 'w') as f:
                        json.dump({
                            'hotset': hotset_output,
                            'compaction_cycle': compaction_cycle,
                            'timestamp': time.time(),
                        }, f, indent=2)
                        f.flush()
                        os.fsync(tmp_fd)
                    os.replace(tmp_path, HOTSET_FILE)   # atomic on POSIX
                except Exception:
                    os.unlink(tmp_path, ignore_errors=True)
                    raise
            log(f"Wrote hotset.json with {len(hotset_output)} tokens (cycle={compaction_cycle})")

            # ── SYNC: signals.json is owned exclusively by hermes-trades-api.py ─────
            # hermes-trades-api rebuilds signals.json every 1 min from hotset.json.
            # signal_compactor previously called _enrich_and_write_signals() here,
            # creating a race: hermes-trades-api would overwrite it 1-4 min later
            # with its own DB view, causing Approved count to bounce around.
            # REMOVED (2026-04-28): signal_compactor no longer writes signals.json.

            # Heartbeat
            try:
                with FileLock('hotset_last_updated'):
                    hb_path = '/var/www/hermes/data/hotset_last_updated.json'
                    os.makedirs(os.path.dirname(hb_path), exist_ok=True)
                    with open(hb_path, 'w') as f:
                        json.dump({'last_compaction_ts': time.time()}, f)
            except Exception as e:
                log(f"Heartbeat write failed: {e}", 'WARN')
        else:
            log(f"[DRY] Would write hotset.json with {len(hotset_output)} tokens (cycle={compaction_cycle})")

        elapsed = time.time() - start
        log(f"Compaction done in {elapsed:.2f}s — {len(hotset_output)} tokens in hotset")

        # Purge executed signals older than 1 hour (keeps DB lean)
        if purge_executed:
            _purge_executed_signals(hours=1, dry=dry)

        return {
            'hotset': hotset_output,
            'compaction_cycle': compaction_cycle,
            'approved': len(hotset_final),
            'rejected': 0,
        }
    # END OF CRITICAL SECTION LOCK (ISSUE-1)


def _purge_executed_signals(hours=1, dry=False):
    """Delete executed signals older than `hours` from the runtime DB.

    FIX (2026-05-19): Before deleting, cross-check PostgreSQL to ensure the
    signal actually has a corresponding trade. If a signal was marked EXECUTED
    but the brain.py DB INSERT failed (phantom execution), the signal must be
    restored to PENDING so decider_run retries it next cycle.

    Without this check, a failed DB INSERT + orphaned HL position causes:
      1. Signal marked EXECUTED in SQLite
      2. Compactor purges the EXECUTED signal
      3. HL position still open (no DB record)
      4. Guardian detects orphan, closes at loss
      5. New signal for same token can't execute (old EXECUTED still blocking)
    """
    # First: get all EXECUTED signals older than cutoff
    conn = sqlite3.connect(RUNTIME_DB, timeout=30)
    c = conn.cursor()
    cutoff = datetime.now().replace(microsecond=0).isoformat()
    c.execute("""
        SELECT id, token, direction FROM signals
        WHERE decision = 'EXECUTED'
          AND updated_at < datetime('now', '-' || ? || ' hours')
    """, (hours,))
    old_executed = c.fetchall()
    if not old_executed:
        conn.close()
        if dry:
            log(f"[DRY] Would check 0 executed signals older than {hours}h — nothing to do")
        else:
            log(f"Purged 0 executed signals older than {hours}h (none found)")
        return

    if dry:
        log(f"[DRY] Would check {len(old_executed)} executed signals older than {hours}h:")
        for sid, tok, d in old_executed:
            log(f"  [DRY]   id={sid} {tok} {d}")
        conn.close()
        return

    # Cross-check each old EXECUTED signal against PostgreSQL
    try:
        import psycopg2
        pg_conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
        pg_cur = pg_conn.cursor()
    except Exception as pg_err:
        log(f"[WARN] Could not connect to PostgreSQL to verify signals: {pg_err}")
        log(f"  Falling back to blind purge — signal-to-trade linkage check SKIPPED")
        deleted = _do_purge(conn, c, cutoff, hours)
        conn.close()
        return

    restored = 0
    for sid, tok, d in old_executed:
        # Check if there's ANY trade for this token (open or closed).
        # If a trade exists, the signal was legitimately executed (DB INSERT succeeded).
        # Only restore to PENDING if no trade record exists at all (phantom execution).
        pg_cur.execute("""
            SELECT id, status FROM trades
            WHERE token=%s AND direction=%s AND server='Hermes'
            ORDER BY id DESC
            LIMIT 1
        """, (tok.upper(), d.upper()))
        row = pg_cur.fetchone()
        if not row:
            # No trade found for this specific token+direction — phantom execution.
            # Restore to PENDING so decider_run can retry cleanly.
            # Note: guardian_orphan trades use 'guardian_orphan_insert' signal, not
            # the original signal source, so they won't match the signal's token+direction
            # in a way that masks phantom executions.
            c.execute("""
                UPDATE signals
                SET decision='PENDING', executed=0, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (sid,))
            restored += 1
            log(f"  [PURGE-VERIFY] Restored signal id={sid} ({tok} {d}) to PENDING — no recent trade found")

    pg_cur.close()
    pg_conn.close()

    deleted = _do_purge(conn, c, cutoff, hours)
    conn.close()

    log(f"Purged {deleted} executed signals older than {hours}h"
        + (f", restored {restored} phantom signals to PENDING" if restored else ""))


def _do_purge(conn, c, cutoff, hours):
    """Execute the actual DELETE for _purge_executed_signals. Returns rowcount."""
    c.execute("""
        DELETE FROM signals
        WHERE decision = 'EXECUTED'
          AND updated_at < datetime('now', '-' || ? || ' hours')
    """, (hours,))
    deleted = c.rowcount
    conn.commit()
    log(f"Purged {deleted} executed signals older than {hours}h")
    return deleted


def _filter_safe_prev_hotset(prev_hotset):
    """Filter previous hotset entries through all safety rules.

    FIX (2026-04-22): Also check cooldown — tokens in loss cooldown must NOT be
    preserved from previous hotset. Without this, a cooldown'd token that survived
    in hotset from the previous cycle would be re-added on every compaction even
    though it should be blocked.
    """
    from signal_schema import _is_loss_cooldown_active
    filtered = []
    for entry in prev_hotset.values():
        tok = entry.get('token', '')
        direction = entry.get('direction', '').upper()
        src = entry.get('source', '')

        # CRITICAL DEBUG: log ALL preserved entries and their filter outcomes
        sp_debug = [p.strip() for p in (src or '').split(',') if p.strip()]
        debug_msg = f"  🔍 [PRESERVE-CHECK] {tok}:{direction} src='{src}' parts={sp_debug} count={len(sp_debug)}"

        # Cooldown check: skip tokens in loss cooldown (guardian loss cooldown only)
        # Do NOT use get_cooldown() here — it checks ALL PostgreSQL cooldowns,
        # including per-signal-generator cooldowns that would block valid multi-source
        # signals that never caused a losing trade.
        if _is_loss_cooldown_active(tok, direction):
            continue
        src = entry.get('source', '')
        if direction == 'SHORT' and tok in SHORT_BLACKLIST:
            continue
        if direction == 'LONG' and tok in LONG_BLACKLIST:
            continue
        if is_solana_only(tok):
            continue
        if is_delisted(tok):
            continue
        # Skip tokens with open positions — don't preserve entries for tokens already traded
        live_open = _get_open_tokens()
        if tok.lower() in live_open:
            continue
        src_str = src.strip() if src else ''
        # ── Source blacklist filter (mirrors signal_schema.validate_source) ─────────
        from signal_schema import validate_source
        if validate_source(src_str) == 'unknown':
            continue
        sp = [p.strip() for p in src_str.split(',') if p.strip()]
        # ── rs required for all entries (2026-05-15) ──────────────────────────────
        # Every hotset entry (LONG or SHORT) must have at least one rs signal.
        has_rs = any(p.startswith('rs') for p in sp)
        if not has_rs:
            log(f"  🚫 [PRESERVE-FILTER] {tok}:{direction} skipped — no rs signal (src='{src}')")
            continue
        # ── Trend purity: bonus multiplier (not hard requirement) ─────────────
        # Signals with trend_purity get +50% final score.
        has_trend_purity = ('trend_purity+' in sp or 'trend_purity-' in sp)
        tp_bonus = 1.50 if has_trend_purity else 1.0
        entry['tp_bonus_mult'] = tp_bonus
        # breakout is single-source but exempt from confluence requirement
        # (it writes to DB directly and bypasses the normal pipeline)
        if src == 'breakout':
            pass  # exempt, allow through
        elif len(sp) < 2:
            log(f"  🚫 [PRESERVE-FILTER] {tok}:{direction} skipped — only {len(sp)} sources (need 2+): {sp}")
            continue
        # NOTE: The old hzscore-only filter (first-source='hzscore' + no comma) was
        # removed — it was redundant with the confluence gate above. If a preserved
        # entry has 2+ sources it passed the gate legitimately. If it has 1 source
        # it's already filtered by the < 2 check above.
        # Back-fill final_confidence for entries from older compaction runs
        if 'final_confidence' not in entry:
            entry['final_confidence'] = entry.get('confidence', 50)
        # FIX (2026-04-26): Refresh timestamp AND recompute staleness.
        # Previously only timestamp was refreshed, leaving staleness stale.
        # Staleness should reflect how long the combo has been continuously in the
        # hot-set — computed from entry_origin_ts (first time the combo entered).
        # Each preserve pass: age = (now - entry_origin_ts) / 60, staleness = max(0, 1 - age/5).
        # On first entry: entry_origin_ts = current_ts (fresh start).
        # On subsequent preserves: entry_origin_ts preserved from first entry.
        entry_origin_ts = entry.get('entry_origin_ts')
        current_ts = time.time()
        if entry_origin_ts is None:
            entry_origin_ts = current_ts  # First time this entry is in hot-set
            entry['entry_origin_ts'] = entry_origin_ts
        entry['timestamp'] = current_ts
        age_min = (current_ts - entry_origin_ts) / 60.0
        entry['staleness'] = max(0.0, 1.0 - age_min * 0.2)
# Expire entries with staleness <= 0.01 (5+ minutes old from entry_origin_ts)
        if entry['staleness'] <= 0.01:
            continue
        # ── Per-coin WR filter (2026-05-11) ─────────────────────────────────
        # Same WR check as run_compaction hotset_final loop — apply to
        # preserved entries too, so blocked tokens don't sneak back in.
        wr, wr_count = _get_token_wr(tok, direction)
        if wr < 50 and wr_count >= 3:
            continue
        # NOTE: rounds and compact_rounds are NOT decremented here.
        # Rounds only increment when the combo fires again in a new cycle.
        # compact_rounds is irrelevant for hot-set exit — staleness is the only timer.
        filtered.append(entry)
        log(f"  ✅ [PRESERVE-PASS] {tok}:{direction} src='{src}' parts={sp_debug} count={len(sp_debug)} passed all filters -> preserved")
    if filtered:
        log(f"Preserving {len(filtered)} tokens from previous hotset")
    else:
        log(f"  ℹ️  [PRESERVE-EMPTY] 0 tokens preserved from previous hotset")
    return filtered


def _preserve_previous_hotset(dry=False):
    """Called when no signals available — preserve previous hotset if safe."""
    prev_hotset = {}
    if os.path.exists(HOTSET_FILE):
        try:
            with open(HOTSET_FILE) as f:
                data = json.load(f)
                for s in data.get('hotset', []):
                    # Back-fill final_confidence for entries from older compaction runs
                    if 'final_confidence' not in s:
                        s['final_confidence'] = s.get('confidence', 50)
                    # Recompute staleness from entry_origin_ts so stale values from disk
                    # don't persist across compaction cycles. Without this, staleness read
                    # from file is carried forward until _filter_safe_prev_hotset corrects
                    # it in-memory — but the corrected value never persists to file until
                    # the next compaction write.
                    origin = s.get('entry_origin_ts')
                    if origin:
                        age_m = (time.time() - origin) / 60.0
                        s['staleness'] = max(0.0, 1.0 - age_m * 0.2)
                    prev_hotset[f"{s['token']}:{s['direction']}"] = s
        except Exception as e:
            pass

    filtered = _filter_safe_prev_hotset(prev_hotset)
    prev_cycle = 0
    if os.path.exists(HOTSET_FILE):
        try:
            with open(HOTSET_FILE) as f:
                prev_cycle = json.load(f).get('compaction_cycle', 0)
        except Exception:
            pass
    compaction_cycle = prev_cycle + 1

    hotset_output = []
    for e in filtered:
        src = e.get('source', '')
        # Count raw source entries (comma-separated)
        parts = [p.strip() for p in (src or '').split(',') if p.strip()]
        entries_count = len(parts) if parts else 1
        entry = dict(e, timestamp=time.time())
        # FIX (2026-05-12): Always recalculate entries_count from the current source string.
        # Previously used e.get('entries_count', entries_count) which preserved a stale
        # entries_count from a previous cycle when source had more components.
        # This caused single-source signals to slip through the confluence filter
        # (len(source_parts) < 2) because their stale entries_count claimed 2 sources.
        entry['entries_count'] = entries_count
        hotset_output.append(entry)

    if not dry:
        with FileLock('hotset_json'):
            with open(HOTSET_FILE, 'w') as f:
                json.dump({
                    'hotset': hotset_output[:20],
                    'compaction_cycle': compaction_cycle,
                    'timestamp': time.time(),
                }, f, indent=2)
        log(f"Preserved {len(hotset_output)} tokens from previous hotset (cycle={compaction_cycle})")

        try:
            with FileLock('hotset_last_updated'):
                hb_path = '/var/www/hermes/data/hotset_last_updated.json'
                os.makedirs(os.path.dirname(hb_path), exist_ok=True)
                with open(hb_path, 'w') as f:
                    json.dump({'last_compaction_ts': time.time()}, f)
        except Exception:
            pass
    else:
        log(f"[DRY] Would preserve {len(hotset_output)} tokens from previous hotset")

    return {
        'hotset': hotset_output[:20],
        'compaction_cycle': compaction_cycle,
        'approved': 0,
        'rejected': 0,
    }


def _enrich_and_write_signals(hotset_entries):
    """
    Write signals.json with the hot_set enriched from the freshly-written hotset.json.
    This is called immediately after writing hotset.json in the same compaction
    cycle, ensuring both files are always in sync.

    Previously, hermes-trades-api.py would re-read hotset.json up to 5 minutes
    later, rebuild the hot_set from DB queries, and write signals.json separately.
    This caused hot_set divergence: tokens visible on the dashboard could differ
    from what was actually in the hot-set.
    """
    import fcntl
    from datetime import datetime, timezone

    def _atomic_write(data, path):
        lock_path = path + '.lock'
        with open(lock_path, 'w') as lf:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

    def _live_rsi(tok, cur):
        try:
            cur.execute(
                "SELECT rsi_14 FROM signals WHERE token=? AND rsi_14 IS NOT NULL "
                "ORDER BY created_at DESC LIMIT 1", (tok,)
            )
            row = cur.fetchone()
            return row[0] if row else None
        except Exception:
            return None

    def _live_macd(tok, cur):
        try:
            cur.execute(
                "SELECT macd_hist FROM signals WHERE token=? AND macd_hist IS NOT NULL "
                "ORDER BY created_at DESC LIMIT 1", (tok,)
            )
            row = cur.fetchone()
            return row[0] if row else None
        except Exception:
            return None

    def _live_zscore(tok, cur):
        try:
            cur.execute(
                "SELECT z_score FROM signals WHERE token=? AND z_score IS NOT NULL "
                "ORDER BY created_at DESC LIMIT 1", (tok,)
            )
            row = cur.fetchone()
            return row[0] if row else None
        except Exception:
            return None

    def _live_price(tok, cur):
        try:
            cur.execute(
                "SELECT price FROM signals WHERE token=? AND price IS NOT NULL AND price > 0 "
                "ORDER BY created_at DESC LIMIT 1", (tok,)
            )
            row = cur.fetchone()
            return row[0] if row else None
        except Exception:
            return None

    # Build hot_set from hotset_entries (same format hermes-trades-api uses)
    hot_set = []
    conn = sqlite3.connect(RUNTIME_DB, timeout=30)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    for e in hotset_entries:
        tok = e['token']
        rsi = _live_rsi(tok, cur)
        macd = _live_macd(tok, cur)
        z = _live_zscore(tok, cur)
        price = _live_price(tok, cur)

        entry = {
            'token': tok,
            'direction': e.get('direction', 'SHORT').upper(),
            'type': 'hot set',
            'sources': e.get('source', ''),
            'confidence': round(float(e.get('confidence', 0)), 1),
            'base_conf': round(float(e.get('confidence', 0)), 1),
            'entry_count': e.get('entries_count', e.get('compact_rounds', 1)),
            'price': price or e.get('price', 0),
            'rsi': rsi,
            'macd': macd,
            'zscore': e.get('z_score', 0),
            'rounds': e.get('survival_round', 0),
            'survival': e.get('survival_score', 0),
            'last_seen': str(e.get('timestamp', time.time())),
            'speed_pctl': round(float(e.get('speed_percentile', 50) or 50), 1),
            'vel_5m': round(float(e.get('price_velocity_5m', 0) or 0), 3),
            'accel': round(float(e.get('price_acceleration', 0) or 0), 3),
            'is_stale': False,
            'wave_phase': e.get('wave_phase', 'neutral'),
            'is_overextended': e.get('is_overextended', False),
            'decision': 'APPROVED',
        }
        hot_set.append(entry)

    conn.close()

    # Read existing signals.json and update only hot_set + timestamp
    # (keep signals[], approved, executed, pending, stats from the last API run)
    result = {'hot_set': hot_set, 'updated': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}
    if os.path.exists(SIGNALS_JSON):
        try:
            with open(SIGNALS_JSON) as f:
                existing = json.load(f)
            # Carry over all fields except hot_set and updated
            for key in existing:
                if key not in ('hot_set', 'updated'):
                    result[key] = existing[key]
        except Exception:
            pass  # Write what we have

    _atomic_write(result, SIGNALS_JSON)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Deterministic signal compactor')
    parser.add_argument('--dry', action='store_true', help='Dry run (log only, no write)')
    parser.add_argument('--verbose', action='store_true', help='Log per-signal scoring details')
    parser.add_argument('--purge-executed', action='store_true', help='Purge executed signals older than 1 hour')
    parser.add_argument('--purge-only', action='store_true', help='Only purge — skip compaction entirely')
    args = parser.parse_args()

    if args.purge_only:
        _purge_executed_signals(hours=1, dry=args.dry)
        print("Purge complete.")
        sys.exit(0)

    result = run_compaction(dry=args.dry, verbose=args.verbose, purge_executed=args.purge_executed)
    print(f"\nResult: {len(result['hotset'])} hotset entries | cycle={result['compaction_cycle']} | "
          f"approved={result['approved']} | rejected={result['rejected']}")

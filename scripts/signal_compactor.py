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
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST, SIGNAL_SOURCE_BLACKLIST, SPEED_HOTSET_BONUS, SPEED_HOTSET_THRESHOLD
from tokens import is_solana_only
from hyperliquid_exchange import is_delisted
from paths import RUNTIME_DB, HOTSET_FILE, HERMES_DATA, REGIME_CACHE_FILE, SIGNALS_JSON

# ── Open-position cache (avoid re-querying PostgreSQL every compaction) ─────────
_open_pos_cache = {}  # token_upper -> True/False, refreshed each run


def _get_open_tokens() -> set:
    """Query PostgreSQL for tokens with open positions (Hermes server)."""
    try:
        import psycopg2
        conn = psycopg2.connect(host='/var/run/postgresql', database='brain',
                                 user='postgres', connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT LOWER(token) FROM trades WHERE status='open' AND server='Hermes'")
        tokens = {row[0] for row in cur.fetchall()}
        cur.close(); conn.close()
        return tokens
    except Exception as e:
        log(f"[WARN] Could not query open positions from PostgreSQL: {e}", 'WARN')
        return set()

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

def get_regime_15m(coin):
    """Get 15m regime from regime_15m.json (primary) or momentum_cache fallback.
    Returns (regime_str, confidence_int).
    """
    # Primary: read from JSON file written by regime scanner
    REGIME_15M_FILE = '/var/www/hermes/data/regime_15m.json'
    try:
        with open(REGIME_15M_FILE) as f:
            data = json.load(f)
        if coin.upper() in data.get('regimes', {}):
            reg = data['regimes'][coin.upper()]
            return reg.get('regime', 'NEUTRAL'), reg.get('confidence', 0)
    except Exception:
        pass

    # Fallback: query momentum_cache in PostgreSQL brain DB directly
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("""
            SELECT regime_15m, updated_at FROM momentum_cache
            WHERE token = %s
            ORDER BY updated_at DESC LIMIT 1
        """, (coin.upper(),))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row and row[0]:
            regime = row[0]
            updated_at = row[1]
            if updated_at:
                now = datetime.now(timezone.utc)
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=timezone.utc)
                age_seconds = (now - updated_at).total_seconds()
                confidence = 75 if age_seconds < 900 else 40  # fresh if < 15min
            else:
                confidence = 50
            return regime, confidence
    except Exception:
        pass

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
    # support_resistance: reduce weight — underperforming in backtest
    ('support_resistance', 'rs-'):       0.7,
    ('rsi-confluence', 'rsi_confluence'):    0.5,   # WR=0% — suppress
    # gap300: EMA(300) vs SMA(300) gap widening on 1m — positive avg PnL in backtest
    ('ema_sma_gap_300_long',  'gap-300+'):   1.0,  # gap widens bullish — strong momentum
    ('ema_sma_gap_300_short', 'gap-300-'):  1.0,  # gap widens bearish — strong momentum
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
            × reg_mult        (+15% aligned / -30% counter-regime)
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

    # Regime multiplier: +15% aligned, -30% counter-regime
    reg_mult = 1.0
    if regime != 'NEUTRAL' and regime_conf > 0:
        if (regime == 'LONG_BIAS' and direction == 'LONG') or \
           (regime == 'SHORT_BIAS' and direction == 'SHORT'):
            reg_mult = 1.15
        elif (regime == 'LONG_BIAS' and direction == 'SHORT') or \
             (regime == 'SHORT_BIAS' and direction == 'LONG'):
            reg_mult = 0.70

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
            penalty = max(0.70, 1.0 - (opp_source_count * 0.15))  # -15% per opposing source, floor 70%
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
        log(f"Query: {len(rows)} token+direction pairs in 10-min window (conf>=60, not executed)")

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
            # '+' = LONG, '-' = SHORT. If both polarities present in the same
            # merged source, the signals are fighting each other — skip entirely.
            # e.g. 'pct-hermes-,hzscore+' → CONFLICT (SHORT vs LONG)
            #      'hzscore+,pct-hermes+,vel-hermes+' → CLEAN (all LONG)
            long_srcs  = [p for p in source_parts if p.endswith('+')]
            short_srcs = [p for p in source_parts if p.endswith('-')]
            if long_srcs and short_srcs:
                log(f"  ⚔️  [CONFLICT] {token} {direction}: LONG={{{','.join(long_srcs)}}} vs SHORT={{{','.join(short_srcs)}}}, skipping")
                continue

            # ── CONFLUENCE GATE: single-source signals must stay PENDING ───────────
            # A signal needs 2+ sources firing together before it can hit hot-set.
            # Single-source signals (e.g. 'oc-zscore-v9-', 'zscore-short') wait for
            # a second source to confirm before being eligible for approval.
            # EXCEPTION: breakout is single-source but bypasses the confluence gate
            # since it writes directly to DB and hot-set (not via the normal pipeline).
            if len(source_parts) < 2 and source != 'breakout':
                log(f"  🔒 [CONFLUENCE-GATE-BLOCK] {token} {direction}: single-source {{{source}}} — waiting for 2nd source")
                continue

            signals.append(row)
            log(f"  ✅ [CONFLUENCE-GATE-PASS] {token} {direction}: {{{source}}} (conf={conf})")

        log(f"Pre-filter: {len(signals)} signals passed safety filters")
        if verbose and signals:
            for s in signals[:5]:
                log(f"  [{s[0]} {s[1]} conf={s[3]} src={s[4]}]")

        if not signals:
            log("No signals after pre-filter — hotset_final will be empty, merge step will preserve prev_hotset")
            # NOTE: Do NOT return here — Step 12 merge logic must still run to preserve prev_hotset

        # ── Step 3: Load speed data ────────────────────────────────────────────
        speed_cache = {}
        if os.path.exists(SPEED_CACHE_FILE):
            try:
                with open(SPEED_CACHE_FILE) as f:
                    speed_cache = json.load(f)
                log(f"Speed cache: {len(speed_cache)} tokens")
            except Exception as e:
                log(f"Speed cache load failed: {e} — using defaults", 'WARN')
        else:
            log(f"Speed cache not found at {SPEED_CACHE_FILE} — using defaults", 'WARN')

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

            regime, regime_conf = get_regime_15m(token)
            speed_data = speed_cache.get(token.upper(), {})
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
            })

        # ── Step 7: Rank and select top 10 ──────────────────────────────────────
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

            # Staleness: max(0, 1 - age_m * 0.2) where age_m is from combo's own created_at
            # age_m was computed from this row's created_at (grouped by combo_key)
            staleness = max(0.0, 1.0 - (s['age_m'] * 0.2))

            # entry_origin_ts: carry forward from previous hot-set if found,
            # otherwise set to now (new combo first entering)
            if prev_entry:
                prev_origin_ts = prev_entry.get('entry_origin_ts')
                entry_origin_ts = prev_origin_ts if prev_origin_ts else time.time()
            else:
                entry_origin_ts = time.time()

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
                'entry_origin_ts': entry_origin_ts,  # carried forward if combo existed, else now
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
            # Check if ANY comma-separated component of src is blacklisted
            # e.g. 'hmacd++,hzscore-' should block on 'hmacd++' even though
            # the whole string isn't in the blacklist
            source_parts = [p.strip() for p in src.split(',')]
            if any(p in SIGNAL_SOURCE_BLACKLIST for p in source_parts):
                log(f"  🚫 [HOTSET-FILTER] {tkn}: blocked — source component in '{src}' is blacklisted")
                continue
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
                # Look up 15m regime for preserved entries (DB entries already have it from scored dict)
                regime, regime_conf = get_regime_15m(pe['token'])
                pe['regime'] = regime
                pe['regime_conf'] = regime_conf
                existing = db_by_key.get(key)
                if existing is None:
                    db_by_key[key] = pe  # no DB entry — take preserved
                elif existing.get('score', 0) < pe.get('score', 0):
                    db_by_key[key] = pe  # preserved has higher score — use it
                # else: keep DB entry (higher score)
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

            top10_keys = {f"{e['token']}:{e['direction']}" for e in hotset_final}
            top10_combos = {e.get('combo_key') for e in hotset_final if e.get('combo_key')}

            # ── Process PENDING/WAIT candidates ───────────────────────────────────
            c.execute("""
                SELECT id, token, direction, COALESCE(compact_rounds, 0) AS cr,
                       combo_key, created_at
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

            for sid, tok, d, cr, ck, sig_created_at in all_sig_rows:
                key = f"{tok.upper()}:{d.upper()}"
                if key in top10_keys:
                    # Combo entered top-10 → APPROVED
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
                    if age_m < 5.0:
                        # Signal is fresh (<5 min) but not in top-10 → stay PENDING
                        still_pending_ids.append(sid)
                    else:
                        # age_m >= 5: no firing for 5 min → EXPIRED (new model)
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
            # FIX (2026-04-26): An APPROVED combo_key that's temporarily absent from
            # PENDING (no signals this cycle) should NOT be expired immediately.
            # Only expire if there are no PENDING signals for this combo AND the most
            # recent PENDING signal for this combo is older than 5 minutes. This matches
            # the staleness=0 boundary from the compactor's perspective.
            # FIX (2026-04-27): Also exclude signals approved THIS cycle (approved_ids).
            # They were just moved PENDING→APPROVED, so they're not in the PENDING subquery
            # yet. Without this exclusion they'd be expired immediately after approval.
            if approved_ids:
                c.execute(f"""
                    UPDATE signals
                    SET decision = 'EXPIRED',
                        expired_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE decision = 'APPROVED'
                      AND executed = 0
                      AND hot_cycle_count >= 2
                      AND combo_key IS NOT NULL
                      AND id NOT IN ({','.join(['?' for _ in approved_ids])})
                      AND combo_key NOT IN (
                          SELECT combo_key FROM signals
                          WHERE decision = 'PENDING'
                            AND executed = 0
                            AND combo_key IS NOT NULL
                            AND created_at > datetime('now', '-5 minutes')
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
                      AND hot_cycle_count >= 2
                      AND combo_key IS NOT NULL
                      AND combo_key NOT IN (
                          SELECT combo_key FROM signals
                          WHERE decision = 'PENDING'
                            AND executed = 0
                            AND combo_key IS NOT NULL
                            AND created_at > datetime('now', '-5 minutes')
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
    """Delete executed signals older than `hours` from the runtime DB."""
    conn = sqlite3.connect(RUNTIME_DB, timeout=30)
    c = conn.cursor()
    cutoff = datetime.now().replace(microsecond=0).isoformat()
    c.execute("""
        DELETE FROM signals
        WHERE decision = 'EXECUTED'
          AND updated_at < datetime('now', '-' || ? || ' hours')
    """, (hours,))
    deleted = c.rowcount
    conn.commit()
    conn.close()
    if dry:
        log(f"[DRY] Would purge {deleted} executed signals older than {hours}h")
    else:
        log(f"Purged {deleted} executed signals older than {hours}h")


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
        source_parts = [p.strip() for p in src.split(',')]
        if any(p in SIGNAL_SOURCE_BLACKLIST for p in source_parts):
            continue
        # breakout is single-source but exempt from confluence requirement
        # (it writes to DB directly and bypasses the normal pipeline)
        if src == 'breakout':
            pass  # exempt, allow through
        elif len(source_parts) < 2:
            continue  # requires 2+ sources for confluence
        if src and src.split(',')[0] == 'hzscore' and ',' not in src:
            continue
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
        # NOTE: rounds and compact_rounds are NOT decremented here.
        # Rounds only increment when the combo fires again in a new cycle.
        # compact_rounds is irrelevant for hot-set exit — staleness is the only timer.
        filtered.append(entry)
    if filtered:
        log(f"Preserving {len(filtered)} tokens from previous hotset")
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
                        print(f"DEBUG: Patched {s['token']} final_confidence={s['final_confidence']}")
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
        entry['entries_count'] = e.get('entries_count', entries_count)
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

#!/usr/bin/env python3
"""
Combo-First Reputation System (Hall of Fame/Shame v2)

Reputation lives at the combo level (coin+signal+direction).
Coin-level is a weaker fallback. Signal-level is the weakest adjustment.

Data source: Hebbian trade_log (primary) + PostgreSQL (fallback) + favorites_leaderboard.json

CEO APPROVED 2026-10-11. Plan: plans/combo-first-reputation-system.md
M1: Hebbian DB pinned to brain/associative_memory.db (data/ is 0-byte stub)
M2: TEST% tokens filtered from trade_log queries
M3: Shadow mode — log multiplier but don't apply until Phase 2
"""

import sqlite3
import time

from hermes_constants import (
    REP_DB_PATH,
    REP_ENABLED,
    REP_SHADOW_MODE,
    REP_CACHE_TTL,
    # Combo level
    REP_COMBO_MIN_TRADES,
    REP_COMBO_LEGENDARY_WR, REP_COMBO_LEGENDARY_MIN, REP_COMBO_LEGENDARY_MULT,
    REP_COMBO_ELITE_WR, REP_COMBO_ELITE_MIN, REP_COMBO_ELITE_MULT,
    REP_COMBO_STRONG_WR, REP_COMBO_STRONG_MIN, REP_COMBO_STRONG_MULT,
    REP_COMBO_GOOD_WR, REP_COMBO_GOOD_MIN, REP_COMBO_GOOD_MULT,
    REP_COMBO_WEAK_WR, REP_COMBO_WEAK_MIN, REP_COMBO_WEAK_MULT,
    REP_COMBO_BAD_WR, REP_COMBO_BAD_MIN, REP_COMBO_BAD_MULT,
    # Coin level
    REP_COIN_MIN_TRADES,
    REP_COIN_FAME_WR, REP_COIN_FAME_MIN, REP_COIN_FAME_MULT,
    REP_COIN_STRONG_WR, REP_COIN_STRONG_MULT,
    REP_COIN_SHAME_WR, REP_COIN_SHAME_MIN, REP_COIN_SHAME_MULT,
    REP_COIN_WEAK_WR, REP_COIN_WEAK_MULT,
    # Signal level
    REP_SIGNAL_MIN_TRADES,
    REP_SIGNAL_PROVEN_WR, REP_SIGNAL_PROVEN_MULT,
    REP_SIGNAL_WEAK_WR, REP_SIGNAL_WEAK_MULT,
    # HALL-SHAME block
    REP_HOS_BLOCK_MIN_TRADES, REP_HOS_BLOCK_WR,
    REP_HOS_OVERRIDE_COMBO_WR, REP_HOS_OVERRIDE_COMBO_MIN,
    REP_HOS_BLOCK_MULT,
)

from paths import HERMES_DATA


# ── Cache ─────────────────────────────────────────────────────────────────────
_combo_cache = {}    # (token, signal, direction) -> {'wr': float, 'trades': int, 'pnl': float}
_coin_cache = {}     # (token, direction) -> {'wr': float, 'trades': int, 'pnl': float}
_signal_cache = {}   # (signal, direction) -> {'wr': float, 'trades': int, 'pnl': float}
_cache_ts = 0
_load_failed_ts = 0  # M2: backoff after failed load

# 30-day window for all queries (BUG 3 fix)
_REP_WINDOW_SQL = "AND close_time >= datetime('now', '-30 days')"


def _load_combo_data():
    """Load combo/coin/signal data from Hebbian trade_log (last 30 days).
    M1: pin to brain/associative_memory.db. M2: filter TEST%.
    BUG 1 fix: wr is not None (0.0% WR is valid).
    BUG 2 fix: normalize signal in SQL via CASE/substr/instr, GROUP BY normalized.
    BUG 3 fix: 30-day window.
    M3 fix: build fresh dicts, swap atomically.
    M2-fix: backoff after failure.
    """
    global _combo_cache, _coin_cache, _signal_cache, _cache_ts, _load_failed_ts
    now = time.time()
    # TTL check — also back off after a failure
    if _combo_cache and (now - _cache_ts) < REP_CACHE_TTL:
        return
    if _load_failed_ts and (now - _load_failed_ts) < REP_CACHE_TTL:
        return

    conn = None
    try:
        # M1: Use the real Hebbian DB, not the 0-byte stub in data/
        conn = sqlite3.connect(REP_DB_PATH, timeout=10)
        cur = conn.cursor()

        # Normalize signal to primary (before first comma) in SQL
        # BUG 2 fix: GROUP BY the normalized form so variants merge correctly
        _norm_sig = "CASE WHEN instr(signal, ',') > 0 THEN substr(signal, 1, instr(signal, ',') - 1) ELSE signal END"

        # ── Combo level: token + normalized_signal + direction ──
        cur.execute(f"""
            SELECT token, {_norm_sig} as nsig, direction,
                   COUNT(*) as trades,
                   ROUND(100.0 * SUM(CASE WHEN won IN ('1', 1, 'True', 'true') THEN 1 ELSE 0 END) / COUNT(*), 1) as wr,
                   ROUND(SUM(pnl_pct), 4) as total_pnl
            FROM trade_log
            WHERE token NOT LIKE 'TEST%'
              AND signal IS NOT NULL
              AND direction IS NOT NULL
              AND close_time IS NOT NULL
              {_REP_WINDOW_SQL}
            GROUP BY token, nsig, direction
        """)
        new_combo = {}
        for token, nsig, direction, trades, wr, pnl in cur.fetchall():
            key = (token.upper(), nsig.strip().upper(), direction.upper())
            new_combo[key] = {
                'wr': float(wr) if wr is not None else 50.0,  # BUG 1 fix
                'trades': int(trades),
                'pnl': float(pnl) if pnl is not None else 0.0,
            }

        # ── Coin level: token + direction ──
        cur.execute(f"""
            SELECT token, direction,
                   COUNT(*) as trades,
                   ROUND(100.0 * SUM(CASE WHEN won IN ('1', 1, 'True', 'true') THEN 1 ELSE 0 END) / COUNT(*), 1) as wr,
                   ROUND(SUM(pnl_pct), 4) as total_pnl
            FROM trade_log
            WHERE token NOT LIKE 'TEST%'
              AND direction IS NOT NULL
              AND close_time IS NOT NULL
              {_REP_WINDOW_SQL}
            GROUP BY token, direction
        """)
        new_coin = {}
        for token, direction, trades, wr, pnl in cur.fetchall():
            key = (token.upper(), direction.upper())
            new_coin[key] = {
                'wr': float(wr) if wr is not None else 50.0,
                'trades': int(trades),
                'pnl': float(pnl) if pnl is not None else 0.0,
            }

        # ── Signal level: normalized_signal + direction ──
        cur.execute(f"""
            SELECT {_norm_sig} as nsig, direction,
                   COUNT(*) as trades,
                   ROUND(100.0 * SUM(CASE WHEN won IN ('1', 1, 'True', 'true') THEN 1 ELSE 0 END) / COUNT(*), 1) as wr,
                   ROUND(SUM(pnl_pct), 4) as total_pnl
            FROM trade_log
            WHERE token NOT LIKE 'TEST%'
              AND signal IS NOT NULL
              AND direction IS NOT NULL
              AND close_time IS NOT NULL
              {_REP_WINDOW_SQL}
            GROUP BY nsig, direction
        """)
        new_signal = {}
        for nsig, direction, trades, wr, pnl in cur.fetchall():
            key = (nsig.strip().upper(), direction.upper())
            new_signal[key] = {
                'wr': float(wr) if wr is not None else 50.0,
                'trades': int(trades),
                'pnl': float(pnl) if pnl is not None else 0.0,
            }

        # M3 fix: atomic swap — fresh dicts replace stale caches
        _combo_cache = new_combo
        _coin_cache = new_coin
        _signal_cache = new_signal
        _cache_ts = now
        _load_failed_ts = 0

    except Exception as e:
        # M1 fix: log the failure (don't silently swallow)
        _load_failed_ts = now
        try:
            print(f"  ⚠️ [REP] load failed: {e} (backing off {REP_CACHE_TTL}s)")
        except Exception:
            pass
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def get_combo_reputation(coin, signal, direction):
    """Get combo-level reputation (coin+signal+direction).
    
    Returns dict: {'tier': str, 'mult': float, 'wr': float, 'trades': int, 'pnl': float}
    or None if no data.
    """
    _load_combo_data()
    if not coin or not signal or not direction:
        return None

    # Normalize signal
    primary_sig = signal.split(',')[0].strip() if signal else signal
    key = (coin.upper(), primary_sig.upper(), direction.upper())
    data = _combo_cache.get(key)

    if not data or data['trades'] < REP_COMBO_MIN_TRADES:
        return None

    wr = data['wr']
    trades = data['trades']

    # Bonus tiers
    if wr >= REP_COMBO_LEGENDARY_WR and trades >= REP_COMBO_LEGENDARY_MIN:
        tier, mult = 'legendary', REP_COMBO_LEGENDARY_MULT
    elif wr >= REP_COMBO_ELITE_WR and trades >= REP_COMBO_ELITE_MIN:
        tier, mult = 'elite', REP_COMBO_ELITE_MULT
    elif wr >= REP_COMBO_STRONG_WR and trades >= REP_COMBO_STRONG_MIN:
        tier, mult = 'strong', REP_COMBO_STRONG_MULT
    elif wr >= REP_COMBO_GOOD_WR and trades >= REP_COMBO_GOOD_MIN:
        tier, mult = 'good', REP_COMBO_GOOD_MULT
    # Penalty tiers (CEO: aggressive)
    elif wr < REP_COMBO_BAD_WR and trades >= REP_COMBO_BAD_MIN:
        tier, mult = 'bad', REP_COMBO_BAD_MULT
    elif wr < REP_COMBO_WEAK_WR and trades >= REP_COMBO_WEAK_MIN:
        tier, mult = 'weak', REP_COMBO_WEAK_MULT
    else:
        tier, mult = 'neutral', 1.0

    return {
        'tier': tier,
        'mult': mult,
        'wr': wr,
        'trades': trades,
        'pnl': data['pnl'],
    }


def get_coin_reputation(coin, direction):
    """Get coin-level reputation (coin+direction).
    
    Returns dict: {'tier': str, 'mult': float, 'wr': float, 'trades': int, 'pnl': float}
    or None if no data.
    """
    _load_combo_data()
    if not coin or not direction:
        return None

    key = (coin.upper(), direction.upper())
    data = _coin_cache.get(key)

    if not data or data['trades'] < REP_COIN_MIN_TRADES:
        return None

    wr = data['wr']
    trades = data['trades']

    # Bonus tiers
    if wr >= REP_COIN_FAME_WR and trades >= REP_COIN_FAME_MIN:
        tier, mult = 'fame', REP_COIN_FAME_MULT
    elif wr >= REP_COIN_STRONG_WR:
        tier, mult = 'strong', REP_COIN_STRONG_MULT
    # Penalty tiers
    elif wr < REP_COIN_SHAME_WR and trades >= REP_COIN_SHAME_MIN:
        tier, mult = 'shame', REP_COIN_SHAME_MULT
    elif wr < REP_COIN_WEAK_WR:
        tier, mult = 'weak', REP_COIN_WEAK_MULT
    else:
        tier, mult = 'neutral', 1.0

    return {
        'tier': tier,
        'mult': mult,
        'wr': wr,
        'trades': trades,
        'pnl': data['pnl'],
    }


def get_signal_reputation(signal, direction):
    """Get signal-level reputation (signal+direction).
    
    Returns dict: {'tier': str, 'mult': float, 'wr': float, 'trades': int, 'pnl': float}
    or None if no data.
    """
    _load_combo_data()
    if not signal or not direction:
        return None

    primary_sig = signal.split(',')[0].strip() if signal else signal
    key = (primary_sig.upper(), direction.upper())
    data = _signal_cache.get(key)

    if not data or data['trades'] < REP_SIGNAL_MIN_TRADES:
        return None

    wr = data['wr']

    if wr >= REP_SIGNAL_PROVEN_WR:
        tier, mult = 'proven', REP_SIGNAL_PROVEN_MULT
    elif wr < REP_SIGNAL_WEAK_WR:
        tier, mult = 'weak', REP_SIGNAL_WEAK_MULT
    else:
        tier, mult = 'neutral', 1.0

    return {
        'tier': tier,
        'mult': mult,
        'wr': wr,
        'trades': data['trades'],
        'pnl': data['pnl'],
    }


def get_combined_multiplier(coin, signal, direction):
    """Get the combined reputation multiplier.

    combined = combo_mult × coin_effective_mult × signal_mult

    HOS multiplier REPLACES coin multiplier when triggered (not multiplied).
    This prevents double-penalizing a coin that's already in shame.

    Returns dict with combined multiplier and component details.
    """
    if not REP_ENABLED:
        return {'mult': 1.0, 'combo': None, 'coin': None, 'signal': None,
                'shadow': False, 'hos': None, 'hos_applied': False}

    combo = get_combo_reputation(coin, signal, direction)
    coin_rep = get_coin_reputation(coin, direction)
    signal_rep = get_signal_reputation(signal, direction)
    hos = should_block(coin, signal, direction)

    combo_mult = combo['mult'] if combo else 1.0
    signal_mult = signal_rep['mult'] if signal_rep else 1.0

    # Coin-level: HOS multiplier REPLACES coin multiplier only when HOS is
    # actually triggered (reason=coin_shame), not when HOS returns 1.0 (no block)
    coin_base_mult = coin_rep['mult'] if coin_rep else 1.0
    coin_effective_mult = coin_base_mult
    hos_applied = False
    if hos['mult'] < 1.0 and hos.get('reason', '').startswith('coin_shame'):
        coin_effective_mult = hos['mult']
        hos_applied = True

    combined = combo_mult * coin_effective_mult * signal_mult

    return {
        'mult': combined,
        'combo': combo,
        'coin': coin_rep,
        'signal': signal_rep,
        'hos': hos,
        'hos_applied': hos_applied,
        'shadow': REP_SHADOW_MODE,
    }


def should_block(coin, signal, direction):
    """Combo-aware HALL-SHAME check.
    
    CEO decision: convert hard block to 0.3x multiplier with proven-combo override.
    
    Returns dict: {'blocked': bool, 'mult': float, 'reason': str}
    """
    if not REP_ENABLED:
        return {'blocked': False, 'mult': 1.0, 'reason': 'rep_disabled'}

    if not coin or not direction:
        return {'blocked': False, 'mult': 1.0, 'reason': 'missing_input'}

    _load_combo_data()

    # Check if coin is in HALL-SHAME territory
    coin_key = (coin.upper(), direction.upper())
    coin_data = _coin_cache.get(coin_key)

    if not coin_data or coin_data['trades'] < REP_HOS_BLOCK_MIN_TRADES:
        return {'blocked': False, 'mult': 1.0, 'reason': 'not_in_hos'}

    if coin_data['wr'] >= REP_HOS_BLOCK_WR:
        return {'blocked': False, 'mult': 1.0, 'reason': 'coin_wr_ok'}

    # Coin is in HALL-SHAME — check for proven combo override
    combo = get_combo_reputation(coin, signal, direction)
    if (combo and combo['wr'] >= REP_HOS_OVERRIDE_COMBO_WR
            and combo['trades'] >= REP_HOS_OVERRIDE_COMBO_MIN):
        return {
            'blocked': False,
            'mult': 1.0,
            'reason': f'combo_override ({combo["wr"]:.1f}% WR, {combo["trades"]}T)',
        }

    # No proven combo — apply HALL-SHAME multiplier (not hard block)
    return {
        'blocked': False,  # Not a hard block anymore — multiplier applies
        'mult': REP_HOS_BLOCK_MULT,
        'reason': f'coin_shame ({coin_data["wr"]:.1f}% WR, {coin_data["trades"]}T)',
    }


def log_reputation(coin, signal, direction, current_mult=None):
    """Shadow-mode logging: log what the multiplier WOULD be vs current.

    L1 fix: returns 1.0 while REP_SHADOW_MODE is True (M3 hazard — a Phase-2
    dev wiring the return value would apply it without checking result['shadow']).
    Phase 2 will disable shadow mode and this will return the real multiplier.
    """
    if not REP_ENABLED:
        return 1.0

    result = get_combined_multiplier(coin, signal, direction)
    combined = result['mult']

    if REP_SHADOW_MODE:
        # Shadow: log but don't apply — return 1.0 so nothing can accidentally apply
        combo_str = ''
        if result['combo']:
            combo_str = f" combo={result['combo']['tier']}({result['combo']['wr']:.1f}%/{result['combo']['trades']}T/{result['combo']['mult']}x)"
        coin_str = ''
        if result['coin']:
            coin_str = f" coin={result['coin']['tier']}({result['coin']['wr']:.1f}%/{result['coin']['trades']}T/{result['coin']['mult']}x)"
        signal_str = ''
        if result['signal']:
            signal_str = f" signal={result['signal']['tier']}({result['signal']['wr']:.1f}%/{result['signal']['trades']}T/{result['signal']['mult']}x)"
        hos_str = ''
        if result['hos'] and result['hos']['mult'] < 1.0:
            if result['hos_applied']:
                hos_str = f" HOS={result['hos']['mult']}x(APPLIED:{result['hos']['reason']})"
            else:
                hos_str = f" HOS={result['hos']['mult']}x(not-applied:{result['hos']['reason']})"

        print(f"  📊 [REP-SHADOW] {coin}+{signal}+{direction}: mult={combined:.3f}{combo_str}{coin_str}{signal_str}{hos_str}")
        return 1.0  # L1 fix: shadow mode returns 1.0, not the live multiplier

    return combined


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=== Combo-First Reputation System — CLI Test ===")
    print(f"DB: {REP_DB_PATH}")
    print(f"Enabled: {REP_ENABLED}, Shadow: {REP_SHADOW_MODE}")
    print()

    # Test with known data
    test_cases = [
        ('JUP', 'volume-buildup-', 'SHORT'),    # The JUP fix — coin in shame, combo unknown
        ('SYRUP', 'r2v2-long3', 'LONG'),         # Known winner
        ('FOGO', 'pump-chain+', 'LONG'),         # Known loser
        ('CFX', 'volume-breakout-long+', 'LONG'), # Known missed winner
        ('CHIP', 'volume-breakout-long+', 'LONG'), # Known missed winner
        ('ME', 'ai-trader+', 'LONG'),            # Current trade
    ]

    for coin, signal, direction in test_cases:
        result = get_combined_multiplier(coin, signal, direction)
        print(f"{coin}+{signal}+{direction}:")
        print(f"  Combined: {result['mult']:.3f}x")
        if result['combo']:
            print(f"  Combo: {result['combo']['tier']} WR={result['combo']['wr']:.1f}% trades={result['combo']['trades']} mult={result['combo']['mult']}x")
        else:
            print(f"  Combo: no data (1.0x)")
        if result['coin']:
            print(f"  Coin: {result['coin']['tier']} WR={result['coin']['wr']:.1f}% trades={result['coin']['trades']} mult={result['coin']['mult']}x")
        else:
            print(f"  Coin: no data (1.0x)")
        if result['signal']:
            print(f"  Signal: {result['signal']['tier']} WR={result['signal']['wr']:.1f}% trades={result['signal']['trades']} mult={result['signal']['mult']}x")
        else:
            print(f"  Signal: no data (1.0x)")
        if result['hos'] and result['hos']['mult'] < 1.0:
            applied = 'APPLIED' if result['hos_applied'] else 'not applied'
            print(f"  HOS: mult={result['hos']['mult']}x ({applied}) reason={result['hos']['reason']}")
        print()

    # Print cache stats
    print(f"=== Cache Stats ===")
    print(f"Combos: {len(_combo_cache)}")
    print(f"Coins: {len(_coin_cache)}")
    print(f"Signals: {len(_signal_cache)}")

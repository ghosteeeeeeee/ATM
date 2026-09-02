#!/usr/bin/env python3
"""Regime Memory — per-signal volatility regime performance tracking.

Instead of blanket-killing signals, this module tracks which volatility regimes
each signal wins/loses in. Signals are "species with habitats" — they stay alive
in their winning regimes and go dormant in losing ones.

Usage:
    from regime_memory import RegimeMemory
    rm = RegimeMemory()
    
    # Query which regimes a signal wins in
    winning = rm.get_winning_regimes('bb_bounce')
    
    # Check if signal should be disabled in current regime
    should_disable = rm.should_disable_in_regime('bb_bounce', 'EXTREME')
    
    # Update memory after trade closes
    rm.record_trade('bb_bounce', 'FLAT', True, 0.5)  # won 0.5%
    
    # Get snapshot of winning params
    params = rm.get_winning_params('bb_bounce', 'FLAT')
"""
import os
import json
import sqlite3
from datetime import datetime, timezone
from collections import defaultdict

import sys
sys.path.insert(0, os.path.dirname(__file__))
from paths import HERMES_DATA, RUNTIME_DB

MEMORY_FILE = os.path.join(HERMES_DATA, 'signal_regime_memory.json')

# Volatility regime classification (matches volatility_gate.py)
FLAT_MAX = 0.48    # ATR% < 0.48%
NORMAL_MAX = 1.0   # ATR% 0.48-1.0%
HIGH_MAX = 1.5     # ATR% 1.0-1.5%
# EXTREME: ATR% > 1.5%

REGIMES = ['FLAT', 'NORMAL', 'HIGH', 'EXTREME']


def classify_volatility(atr_pct):
    """Classify ATR% into volatility regime."""
    if atr_pct is None:
        return 'NORMAL'
    if atr_pct < FLAT_MAX:
        return 'FLAT'
    elif atr_pct < NORMAL_MAX:
        return 'NORMAL'
    elif atr_pct < HIGH_MAX:
        return 'HIGH'
    else:
        return 'EXTREME'


class RegimeMemory:
    """Manages per-signal regime performance memory."""
    
    def __init__(self, memory_file=None):
        self.memory_file = memory_file or MEMORY_FILE
        self._data = self._load()
    
    def _load(self):
        """Load memory from disk."""
        try:
            with open(self.memory_file) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {'signals': {}, 'updated_at': None}
    
    def _save(self):
        """Save memory to disk."""
        import tempfile
        self._data['updated_at'] = datetime.now(timezone.utc).isoformat()
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.memory_file), suffix='.tmp')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp, self.memory_file)
        except Exception:
            try:
                os.unlink(tmp)
            except Exception:
                pass
    
    def _ensure_signal(self, signal_type):
        """Ensure signal entry exists in memory."""
        if signal_type not in self._data['signals']:
            self._data['signals'][signal_type] = {
                'regimes': {},
                'winning_regimes': [],
                'losing_regimes': [],
                'best_params': {},
                'last_updated': None,
            }
    
    def get_regime_stats(self, signal_type):
        """Get performance stats per regime for a signal."""
        self._ensure_signal(signal_type)
        return self._data['signals'][signal_type].get('regimes', {})
    
    def get_winning_regimes(self, signal_type, min_trades=5, min_wr=0.50):
        """Get regimes where this signal has edge (WR > min_wr with min_trades)."""
        stats = self.get_regime_stats(signal_type)
        winning = []
        for regime, data in stats.items():
            trades = data.get('trades', 0)
            wins = data.get('wins', 0)
            if trades >= min_trades:
                wr = wins / trades
                if wr >= min_wr:
                    winning.append(regime)
        return winning
    
    def get_losing_regimes(self, signal_type, min_trades=5, max_wr=0.40):
        """Get regimes where this signal loses (WR < max_wr with min_trades)."""
        stats = self.get_regime_stats(signal_type)
        losing = []
        for regime, data in stats.items():
            trades = data.get('trades', 0)
            wins = data.get('wins', 0)
            if trades >= min_trades:
                wr = wins / trades
                if wr < max_wr:
                    losing.append(regime)
        return losing
    
    def should_disable_in_regime(self, signal_type, current_regime, min_trades=5):
        """Check if signal should be disabled in the current regime.
        
        Returns True if:
        - Signal has >= min_trades in this regime AND
        - WR in this regime < 40% AND
        - Signal has at least one winning regime (don't kill if it has no habitat)
        """
        stats = self.get_regime_stats(signal_type)
        regime_data = stats.get(current_regime, {})
        trades = regime_data.get('trades', 0)
        wins = regime_data.get('wins', 0)
        
        if trades < min_trades:
            return False  # Not enough data — don't disable
        
        wr = wins / trades if trades > 0 else 0
        
        if wr >= 0.40:
            return False  # Not losing badly enough
        
        # Only disable if signal has at least one winning regime
        # (don't kill species that have no habitat at all — let self_learner handle that)
        winning = self.get_winning_regimes(signal_type)
        return len(winning) > 0
    
    def record_trade(self, signal_type, regime, won, pnl_pct=None):
        """Record a trade outcome for regime tracking."""
        self._ensure_signal(signal_type)
        
        # Validate regime
        if regime not in REGIMES:
            regime = 'NORMAL'
        
        if regime not in self._data['signals'][signal_type]['regimes']:
            self._data['signals'][signal_type]['regimes'][regime] = {
                'trades': 0, 'wins': 0, 'total_pnl': 0.0,
            }
        
        r = self._data['signals'][signal_type]['regimes'][regime]
        r['trades'] += 1
        if won:
            r['wins'] += 1
        if pnl_pct is not None:
            r['total_pnl'] += pnl_pct
        
        # Recompute winning/losing regimes
        self._recompute_regime_classification(signal_type)
        self._data['signals'][signal_type]['last_updated'] = datetime.now(timezone.utc).isoformat()
        
        self._save()
    
    def backfill_from_db(self, days=30):
        """Backfill volatility_regime for existing trades that don't have it.
        
        This computes volatility_regime from candles_1h ATR for each trade
        and updates the trades table. Run once after adding the column.
        """
        try:
            import psycopg2
            from signal_schema import _get_volatility_regime
            
            conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
            cur = conn.cursor()
            
            # Get trades without volatility_regime
            cur.execute("""
                SELECT id, token FROM trades 
                WHERE status = 'closed' 
                AND close_time > NOW() - INTERVAL '%s days'
                AND (volatility_regime IS NULL OR volatility_regime = '')
                LIMIT 500
            """, (days,))
            
            trades = cur.fetchall()
            updated = 0
            
            for trade_id, token in trades:
                try:
                    vol_regime = _get_volatility_regime(token)
                    cur.execute("""
                        UPDATE trades SET volatility_regime = %s WHERE id = %s
                    """, (vol_regime, trade_id))
                    updated += 1
                except Exception:
                    pass
            
            conn.commit()
            conn.close()
            
            print(f"Backfilled volatility_regime for {updated}/{len(trades)} trades")
            return updated
            
        except Exception as e:
            print(f"Error backfilling: {e}")
            return 0
    
    def snapshot_params(self, signal_type, regime, params):
        """Save a snapshot of params that worked well in this regime."""
        self._ensure_signal(signal_type)
        self._data['signals'][signal_type]['best_params'][regime] = {
            'params': params,
            'snapshot_date': datetime.now(timezone.utc).isoformat(),
        }
        self._save()
    
    def get_winning_params(self, signal_type, regime):
        """Get the saved winning params for a signal in a regime."""
        self._ensure_signal(signal_type)
        return self._data['signals'][signal_type].get('best_params', {}).get(regime, {})
    
    def _recompute_regime_classification(self, signal_type):
        """Recompute which regimes are winning vs losing."""
        winning = self.get_winning_regimes(signal_type, min_trades=3, min_wr=0.50)
        losing = self.get_losing_regimes(signal_type, min_trades=3, max_wr=0.40)
        self._data['signals'][signal_type]['winning_regimes'] = winning
        self._data['signals'][signal_type]['losing_regimes'] = losing
    
    def seed_from_db(self, signal_type=None, days=30):
        """Seed regime memory from existing trade data in PostgreSQL.
        
        Uses actual volatility_regime column when available (populated at trade entry).
        Falls back to entry_regime_4h as proxy if volatility_regime is NULL.
        """
        try:
            import psycopg2
            conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
            cur = conn.cursor()
            
            # Get trades with volatility_regime (actual) or entry_regime_4h (proxy)
            if signal_type:
                cur.execute("""
                    SELECT signal, 
                           COALESCE(volatility_regime, entry_regime_4h, 'NORMAL') as vol_regime,
                           SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
                           COUNT(*) as total,
                           COALESCE(SUM(pnl_usdt), 0) as total_pnl
                    FROM trades 
                    WHERE status = 'closed' 
                    AND close_time > NOW() - INTERVAL '%s days'
                    AND signal LIKE %s
                    GROUP BY signal, vol_regime
                """, (days, f'%{signal_type}%'))
            else:
                cur.execute("""
                    SELECT signal, 
                           COALESCE(volatility_regime, entry_regime_4h, 'NORMAL') as vol_regime,
                           SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
                           COUNT(*) as total,
                           COALESCE(SUM(pnl_usdt), 0) as total_pnl
                    FROM trades 
                    WHERE status = 'closed' 
                    AND close_time > NOW() - INTERVAL '%s days'
                    GROUP BY signal, vol_regime
                """, (days,))
            
            for row in cur.fetchall():
                sig, regime, wins, total, pnl = row
                if not sig or total < 3:
                    continue
                
                # Normalize regime string
                regime_str = str(regime) if regime else 'NORMAL'
                # Map old trend regimes to volatility regimes if needed
                regime_map = {
                    'NEUTRAL': 'NORMAL',
                    'LONG_BIAS': 'NORMAL',
                    'SHORT_BIAS': 'NORMAL',
                    'RANGING': 'FLAT',
                    'BULL': 'NORMAL',
                    'BEAR': 'NORMAL',
                }
                vol_regime = regime_map.get(regime_str, regime_str)
                
                # Only use valid volatility regimes
                if vol_regime not in REGIMES:
                    vol_regime = 'NORMAL'
                
                self._ensure_signal(sig)
                if vol_regime not in self._data['signals'][sig]['regimes']:
                    self._data['signals'][sig]['regimes'][vol_regime] = {
                        'trades': 0, 'wins': 0, 'total_pnl': 0.0,
                    }
                
                r = self._data['signals'][sig]['regimes'][vol_regime]
                r['trades'] += total
                r['wins'] += wins
                r['total_pnl'] += float(pnl)
                
                self._recompute_regime_classification(sig)
            
            conn.close()
            self._save()
            return True
            
        except Exception as e:
            print(f"Error seeding from DB: {e}")
            return False
    
    def get_summary(self):
        """Get a summary of all signals and their regime status."""
        summary = []
        for signal_type, data in self._data.get('signals', {}).items():
            winning = data.get('winning_regimes', [])
            losing = data.get('losing_regimes', [])
            stats = data.get('regimes', {})
            total_trades = sum(r.get('trades', 0) for r in stats.values())
            total_wins = sum(r.get('wins', 0) for r in stats.values())
            wr = total_wins / total_trades if total_trades > 0 else 0
            
            summary.append({
                'signal': signal_type,
                'total_trades': total_trades,
                'win_rate': wr,
                'winning_regimes': winning,
                'losing_regimes': losing,
                'regime_count': len(stats),
            })
        
        return sorted(summary, key=lambda x: -x['total_trades'])


def log(msg):
    print(f"[regime-memory] {msg}", flush=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Regime Memory Manager')
    parser.add_argument('--seed', action='store_true', help='Seed from DB')
    parser.add_argument('--signal', type=str, help='Filter to specific signal')
    parser.add_argument('--summary', action='store_true', help='Show summary')
    parser.add_argument('--query', type=str, help='Query regime stats for signal')
    args = parser.parse_args()
    
    rm = RegimeMemory()
    
    if args.seed:
        log("Seeding from DB...")
        rm.seed_from_db(signal_type=args.signal)
        log("Done")
    
    if args.summary:
        summary = rm.get_summary()
        print(f"\n{'Signal':<45s} {'T':>5s} {'WR':>6s} {'Winning Regimes':<30s} {'Losing Regimes'}")
        print("-" * 120)
        for s in summary:
            winning = ', '.join(s['winning_regimes']) or 'none'
            losing = ', '.join(s['losing_regimes']) or 'none'
            emoji = '🟢' if s['win_rate'] >= 0.55 else '🟡' if s['win_rate'] >= 0.45 else '🔴'
            print(f"{emoji} {s['signal']:<43s} {s['total_trades']:5d} {s['win_rate']*100:5.1f}% {winning:<30s} {losing}")
    
    if args.query:
        stats = rm.get_regime_stats(args.query)
        winning = rm.get_winning_regimes(args.query)
        losing = rm.get_losing_regimes(args.query)
        print(f"\n{args.query}:")
        print(f"  Winning regimes: {winning or 'none'}")
        print(f"  Losing regimes: {losing or 'none'}")
        for regime, data in stats.items():
            trades = data.get('trades', 0)
            wins = data.get('wins', 0)
            wr = wins / trades * 100 if trades else 0
            pnl = data.get('total_pnl', 0)
            emoji = '🟢' if wr >= 55 else '🟡' if wr >= 45 else '🔴'
            print(f"  {emoji} {regime}: {trades}T WR={wr:.1f}% PnL=${pnl:+.2f}")

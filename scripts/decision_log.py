#!/usr/bin/env python3
"""Persistent Decision Log — learn from every trade decision.

Logs every trade decision with reasoning. After trade closes, adds reflection.
Uses reflections to improve future decisions.

Flow:
1. Signal fires → Decision logged (why)
2. Trade executes → Decision updated
3. Trade closes → Reflection added
4. Daily → Analyze patterns, update lessons
"""
import json
import os
import sys
import time
import sqlite3
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from paths import RUNTIME_DB

# ── Config ──────────────────────────────────────────────────────────────
DECISIONS_FILE = '/root/.hermes/data/decisions.json'
MAX_ENTRIES = 1000

# ── State ───────────────────────────────────────────────────────────────
_cache = {}


def _log(msg):
    print(f"[decision-log] {msg}", flush=True)


def _load_decisions():
    """Load decisions from file. Returns None on corruption (don't overwrite)."""
    if os.path.exists(DECISIONS_FILE):
        try:
            with open(DECISIONS_FILE) as f:
                return json.load(f)
        except Exception:
            _log(f"Corrupt decisions file, refusing to overwrite")
            return None
    return {'decisions': [], 'stats': {}, 'lessons': []}


def _save_decisions(data):
    """Save decisions atomically with file lock."""
    import fcntl
    try:
        import tempfile
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(DECISIONS_FILE), suffix='.tmp')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, DECISIONS_FILE)
        except Exception:
            try:
                os.unlink(tmp)
            except Exception:
                pass
            raise
    except Exception as e:
        _log(f"Error saving decisions: {e}")
        return False
    return True


def log_decision(token, direction, signal_type, confidence, price, reasoning):
    """Log a new trade decision."""
    data = _load_decisions()
    if data is None:
        return None  # Corrupted file, don't overwrite
    
    decision_id = f"dec_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{token}"
    
    decision = {
        'id': decision_id,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'token': token,
        'direction': direction,
        'signal_type': signal_type,
        'confidence': confidence,
        'price': price,
        'reasoning': reasoning,
        'decision': 'EXECUTE',
        'decision_confidence': confidence,
        'outcome': None,
        'pnl_usdt': None,
        'pnl_pct': None,
        'exit_reason': None,
        'reflection': None,
        'lessons_learned': None,
    }
    
    data['decisions'].append(decision)
    
    # Trim to max entries
    if len(data['decisions']) > MAX_ENTRIES:
        data['decisions'] = data['decisions'][-MAX_ENTRIES:]
    
    _save_decisions(data)
    _log(f"Logged decision: {token} {direction} {signal_type} conf={confidence}")
    
    return decision_id


def update_trade_outcome(decision_id, pnl_usdt, pnl_pct, exit_reason):
    """Update decision with trade outcome after close."""
    data = _load_decisions()
    if data is None:
        return False
    
    for decision in data['decisions']:
        if decision['id'] == decision_id:
            pnl = pnl_usdt or 0
            decision['outcome'] = 'WIN' if pnl > 0 else 'LOSS'
            decision['pnl_usdt'] = pnl
            decision['pnl_pct'] = pnl_pct or 0
            decision['exit_reason'] = exit_reason
            decision['closed_at'] = datetime.now(timezone.utc).isoformat()
            
            # Add reflection
            decision['reflection'] = generate_reflection(decision)
            decision['lessons_learned'] = extract_lesson(decision)
            
            _save_decisions(data)
            _log(f"Updated outcome: {decision_id} → {decision['outcome']} PnL=${pnl:+.2f}")
            return True
    
    return False


def generate_reflection(decision):
    """Generate reflection based on trade outcome."""
    reasoning = decision.get('reasoning', {})
    outcome = decision.get('outcome', '')
    signal_type = decision.get('signal_type', '')
    
    if outcome == 'WIN':
        parts = []
        if reasoning.get('trend', '').startswith('BULLISH') and decision['direction'] == 'LONG':
            parts.append('trend aligned')
        elif reasoning.get('trend', '').startswith('BEARISH') and decision['direction'] == 'SHORT':
            parts.append('trend aligned')
        else:
            parts.append('counter-trend win')
        
        rsi = reasoning.get('rsi', 50)
        if decision['direction'] == 'LONG' and rsi < 40:
            parts.append('RSI confirmed oversold')
        elif decision['direction'] == 'SHORT' and rsi > 60:
            parts.append('RSI confirmed overbought')
        
        return f"Win: {', '.join(parts)}"
    
    else:  # LOSS
        parts = []
        if reasoning.get('trend', '').startswith('BULLISH') and decision['direction'] == 'SHORT':
            parts.append('counter-trend')
        elif reasoning.get('trend', '').startswith('BEARISH') and decision['direction'] == 'LONG':
            parts.append('counter-trend')
        
        regime = reasoning.get('regime', 'NEUTRAL')
        if regime == 'BEARISH' and decision['direction'] == 'LONG':
            parts.append('bearish regime')
        elif regime == 'BULLISH' and decision['direction'] == 'SHORT':
            parts.append('bullish regime')
        
        if not parts:
            parts.append('signal failed')
        
        return f"Loss: {', '.join(parts)}"


def extract_lesson(decision):
    """Extract lesson from trade outcome."""
    signal_type = decision.get('signal_type', '')
    outcome = decision.get('outcome', '')
    reasoning = decision.get('reasoning', {})
    reflection = decision.get('reflection', '')
    
    if not reflection:
        return None
    
    # Build lesson
    if outcome == 'WIN':
        if 'trend aligned' in reflection:
            return f"{signal_type} works when trend aligned"
        elif 'RSI confirmed' in reflection:
            return f"{signal_type} works with RSI confirmation"
        else:
            return f"{signal_type} won despite mixed signals"
    else:
        if 'counter-trend' in reflection:
            return f"{signal_type} fails when counter-trend"
        elif 'regime' in reflection:
            return f"{signal_type} fails in wrong regime"
        else:
            return f"{signal_type} failed — review setup"


def get_lessons(signal_type=None):
    """Get lessons learned, optionally filtered by signal type."""
    data = _load_decisions()
    lessons = data.get('lessons', [])
    
    if signal_type:
        lessons = [l for l in lessons if signal_type in l]
    
    return lessons


def update_stats():
    """Update aggregate statistics."""
    data = _load_decisions()
    decisions = data.get('decisions', [])
    
    completed = [d for d in decisions if d.get('outcome')]
    if not completed:
        return
    
    wins = sum(1 for d in completed if d['outcome'] == 'WIN')
    total_pnl = sum(d.get('pnl_usdt', 0) or 0 for d in completed)
    
    # Per signal type stats
    signal_stats = {}
    for d in completed:
        st = d.get('signal_type', 'unknown')
        if st not in signal_stats:
            signal_stats[st] = {'wins': 0, 'total': 0, 'pnl': 0}
        signal_stats[st]['total'] += 1
        if d['outcome'] == 'WIN':
            signal_stats[st]['wins'] += 1
        signal_stats[st]['pnl'] += d.get('pnl_usdt', 0) or 0
    
    # Find best/worst
    best_signal = max(signal_stats.items(), key=lambda x: x[1]['pnl'])[0] if signal_stats else None
    worst_signal = min(signal_stats.items(), key=lambda x: x[1]['pnl'])[0] if signal_stats else None
    
    data['stats'] = {
        'total_decisions': len(completed),
        'win_rate': wins / len(completed) if completed else 0,
        'avg_pnl': total_pnl / len(completed) if completed else 0,
        'total_pnl': total_pnl,
        'best_signal': best_signal,
        'worst_signal': worst_signal,
        'last_updated': datetime.now(timezone.utc).isoformat(),
    }
    
    # Extract lessons from recent decisions
    lessons = []
    for d in completed[-50:]:  # Last 50 decisions
        lesson = d.get('lessons_learned')
        if lesson and lesson not in lessons:
            lessons.append(lesson)
    
    data['lessons'] = lessons[-20:]  # Keep last 20 lessons
    
    _save_decisions(data)


def analyze_patterns():
    """Analyze decision patterns and return insights."""
    data = _load_decisions()
    decisions = data.get('decisions', [])
    completed = [d for d in decisions if d.get('outcome')]
    
    if len(completed) < 10:
        return {'insufficient_data': True}
    
    # Win rate by signal type
    signal_wr = {}
    for d in completed:
        st = d.get('signal_type', 'unknown')
        if st not in signal_wr:
            signal_wr[st] = {'wins': 0, 'total': 0}
        signal_wr[st]['total'] += 1
        if d['outcome'] == 'WIN':
            signal_wr[st]['wins'] += 1
    
    # Win rate by trend alignment
    trend_wr = {'aligned': {'wins': 0, 'total': 0}, 'counter': {'wins': 0, 'total': 0}}
    for d in completed:
        reasoning = d.get('reasoning', {})
        trend = reasoning.get('trend', '')
        direction = d.get('direction', '')
        
        aligned = (trend.startswith('BULLISH') and direction == 'LONG') or \
                  (trend.startswith('BEARISH') and direction == 'SHORT')
        
        key = 'aligned' if aligned else 'counter'
        trend_wr[key]['total'] += 1
        if d['outcome'] == 'WIN':
            trend_wr[key]['wins'] += 1
    
    return {
        'signal_wr': signal_wr,
        'trend_wr': trend_wr,
        'total_decisions': len(completed),
    }


def run():
    """Entry point — update stats."""
    _log("=== Updating decision stats ===")
    update_stats()
    data = _load_decisions()
    stats = data.get('stats', {})
    _log(f"Stats: {stats.get('total_decisions', 0)} decisions, "
         f"WR={stats.get('win_rate', 0):.1%}, "
         f"PnL=${stats.get('total_pnl', 0):+.2f}")
    return 0


if __name__ == '__main__':
    if '--analyze' in sys.argv:
        insights = analyze_patterns()
        print(json.dumps(insights, indent=2))
    else:
        run()

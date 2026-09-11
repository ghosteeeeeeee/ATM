#!/usr/bin/env python3
"""FAMILY_MAP Dashboard — HTML visualization of signal families and regime performance."""

import os
import sys
import json
import psycopg2
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

# ── Config ────────────────────────────────────────────────────────────────────
OUTPUT_FILE = '/var/www/hermes/data/family_map_dashboard.html'
DB_CONN = "host=/var/run/postgresql dbname=brain user=postgres password="


def get_regime_performance():
    """Get regime performance for all signals."""
    conn = psycopg2.connect(DB_CONN)
    cur = conn.cursor()
    
    cur.execute('''
        SELECT signal, volatility_regime,
               COUNT(*) as trades,
               SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
               ROUND(100.0*SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)/COUNT(*), 1) as wr,
               ROUND(SUM(pnl_usdt), 2) as pnl
        FROM trades 
        WHERE status = 'closed'
        AND close_time > NOW() - interval '30 days'
        GROUP BY signal, volatility_regime
        HAVING COUNT(*) >= 2
        ORDER BY signal, pnl DESC
    ''')
    
    data = {}
    for r in cur.fetchall():
        sig, regime, trades, wins, wr, pnl = r
        if sig not in data:
            data[sig] = {}
        data[sig][regime or 'UNKNOWN'] = {
            'trades': trades,
            'wins': wins,
            'wr': float(wr) if wr else 0,
            'pnl': float(pnl) if pnl else 0
        }
    
    conn.close()
    return data


def get_family_map():
    """Get FAMILY_MAP from market_phase_gate.py."""
    # Import the actual FAMILY_MAP
    sys.path.insert(0, '/root/.hermes/scripts')
    from market_phase_gate import FAMILY_MAP
    return FAMILY_MAP


def get_volatility_blocks():
    """Get volatility gate multipliers from volatility_gate_v2.py."""
    sys.path.insert(0, '/root/.hermes/scripts')
    from volatility_gate_v2 import VOL_PHASE_MULTS
    
    blocks = {}
    for (regime, phase), multipliers in VOL_PHASE_MULTS.items():
        if regime not in blocks:
            blocks[regime] = {}
        for family, mult in multipliers.items():
            # Only keep wildcard phase entries for family lookup
            if phase == '*':
                blocks[regime][family] = mult
    
    return blocks


def get_signal_enable_status():
    """Get enable status for all signals."""
    sys.path.insert(0, '/root/.hermes/scripts')
    from hermes_constants import (
        BB_BOUNCE_PLUS_ENABLED, BB_BOUNCE_MINUS_ENABLED,
        R2_TREND_LONG_ENABLED, R2_TREND_SHORT_ENABLED,
        PUMP_FLOW_PLUS_ENABLED, PUMP_FLOW_MINUS_ENABLED,
        PULLBACK_ENTRY_PLUS_ENABLED, PULLBACK_ENTRY_MINUS_ENABLED,
        EMA300_DIP_LONG_ENABLED, EMA300_DIP_SHORT_ENABLED,
        ACCEL_300_V3_LONG_ENABLED, ACCEL_300_V3_SHORT_ENABLED,
        TL_BREAK_PLUS_ENABLED, TL_BREAK_MINUS_ENABLED,
        ICHIMOKU_ENABLED, OPEN_SKIES_ENABLED,
        TREND_PURITY_ENABLED, COILED_SPRING_ENABLED,
        ENGULFING_ENABLED, CONTINUATION_ENABLED,
        VOLUME_BREAKOUT_ENABLED, BREAKOUT_LONG_ENABLED,
    )
    
    return {
        'BB_BOUNCE_PLUS_ENABLED': BB_BOUNCE_PLUS_ENABLED,
        'BB_BOUNCE_MINUS_ENABLED': BB_BOUNCE_MINUS_ENABLED,
        'R2_TREND_LONG_ENABLED': R2_TREND_LONG_ENABLED,
        'R2_TREND_SHORT_ENABLED': R2_TREND_SHORT_ENABLED,
        'PUMP_FLOW_PLUS_ENABLED': PUMP_FLOW_PLUS_ENABLED,
        'PUMP_FLOW_MINUS_ENABLED': PUMP_FLOW_MINUS_ENABLED,
        'PULLBACK_ENTRY_PLUS_ENABLED': PULLBACK_ENTRY_PLUS_ENABLED,
        'PULLBACK_ENTRY_MINUS_ENABLED': PULLBACK_ENTRY_MINUS_ENABLED,
        'EMA300_DIP_LONG_ENABLED': EMA300_DIP_LONG_ENABLED,
        'EMA300_DIP_SHORT_ENABLED': EMA300_DIP_SHORT_ENABLED,
        'ACCEL_300_V3_LONG_ENABLED': ACCEL_300_V3_LONG_ENABLED,
        'ACCEL_300_V3_SHORT_ENABLED': ACCEL_300_V3_SHORT_ENABLED,
        'TL_BREAK_PLUS_ENABLED': TL_BREAK_PLUS_ENABLED,
        'TL_BREAK_MINUS_ENABLED': TL_BREAK_MINUS_ENABLED,
        'ICHIKOMU_ENABLED': ICHIMOKU_ENABLED,
        'OPEN_SKIES_ENABLED': OPEN_SKIES_ENABLED,
        'TREND_PURITY_ENABLED': TREND_PURITY_ENABLED,
        'COILED_SPRING_ENABLED': COILED_SPRING_ENABLED,
        'ENGULFING_ENABLED': ENGULFING_ENABLED,
        'CONTINUATION_ENABLED': CONTINUATION_ENABLED,
        'VOLUME_BREAKOUT_ENABLED': VOLUME_BREAKOUT_ENABLED,
        'BREAKOUT_LONG_ENABLED': BREAKOUT_LONG_ENABLED,
    }


def generate_html(family_map, regime_data, volatility_blocks, enable_status):
    """Generate HTML dashboard."""
    
    # Build signal -> family mapping
    signal_to_family = {}
    for family, signals in family_map.items():
        for sig in signals:
            signal_to_family[sig] = family
    
    # Get all families with signals
    all_families = sorted(family_map.keys())
    
    # Generate HTML
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hermes Signal Family Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a; color: #e0e0e0; padding: 20px;
        }}
        h1 {{ color: #00ff88; margin-bottom: 10px; font-size: 24px; }}
        h2 {{ color: #00ccff; margin: 20px 0 10px; font-size: 18px; }}
        h3 {{ color: #ffaa00; margin: 15px 0 8px; font-size: 14px; }}
        .timestamp {{ color: #666; font-size: 12px; margin-bottom: 20px; }}
        .summary {{ 
            background: #1a1a1a; border: 1px solid #333; border-radius: 8px;
            padding: 15px; margin-bottom: 20px;
        }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; }}
        .summary-item {{ text-align: center; }}
        .summary-value {{ font-size: 24px; font-weight: bold; color: #00ff88; }}
        .summary-label {{ font-size: 12px; color: #888; }}
        table {{ 
            width: 100%; border-collapse: collapse; margin-bottom: 20px;
            background: #1a1a1a; border-radius: 8px; overflow: hidden;
        }}
        th {{ background: #222; color: #00ccff; padding: 10px; text-align: left; font-size: 12px; }}
        td {{ padding: 8px 10px; border-bottom: 1px solid #222; font-size: 12px; }}
        tr:hover {{ background: #1f1f1f; }}
        .positive {{ color: #00ff88; }}
        .negative {{ color: #ff4444; }}
        .neutral {{ color: #ffaa00; }}
        .blocked {{ color: #ff4444; font-weight: bold; }}
        .enabled {{ color: #00ff88; }}
        .disabled {{ color: #666; }}
        .regime-card {{
            background: #1a1a1a; border: 1px solid #333; border-radius: 8px;
            padding: 15px; margin-bottom: 15px;
        }}
        .regime-header {{ 
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 10px;
        }}
        .regime-name {{ font-weight: bold; color: #00ccff; }}
        .signal-list {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .signal-badge {{
            padding: 4px 8px; border-radius: 4px; font-size: 11px;
            background: #222; border: 1px solid #444;
        }}
        .signal-badge.blocked {{ background: #3a1a1a; border-color: #ff4444; color: #ff4444; }}
        .signal-badge.allowed {{ background: #1a3a1a; border-color: #00ff88; color: #00ff88; }}
        .signal-badge.penalty {{ background: #3a3a1a; border-color: #ffaa00; color: #ffaa00; }}
    </style>
</head>
<body>
    <h1>🔱 Hermes Signal Family Dashboard</h1>
    <div class="timestamp">Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}</div>
    
    <div class="summary">
        <div class="summary-grid">
            <div class="summary-item">
                <div class="summary-value">{len(all_families)}</div>
                <div class="summary-label">Signal Families</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{sum(len(s) for s in family_map.values())}</div>
                <div class="summary-label">Total Signals</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{len(regime_data)}</div>
                <div class="summary-label">Signals with Data</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{len([v for v in enable_status.values() if v])}</div>
                <div class="summary-label">Signals Enabled</div>
            </div>
        </div>
    </div>
    
    <h2>📊 Signal Families & Regime Performance</h2>
'''
    
    for family in all_families:
        signals = family_map[family]
        
        # Get regime blocks for this family
        family_blocks = {}
        for regime, blocks in volatility_blocks.items():
            if family in blocks:
                family_blocks[regime] = blocks[family]
        
        # Get performance data for signals in this family
        family_perf = {}
        for sig in signals:
            if sig in regime_data:
                family_perf[sig] = regime_data[sig]
        
        # Calculate family aggregate
        total_trades = 0
        total_wins = 0
        total_pnl = 0
        for sig, perf in family_perf.items():
            for regime, data in perf.items():
                total_trades += data['trades']
                total_wins += data['wins']
                total_pnl += data['pnl']
        
        family_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0
        
        html += f'''
    <div class="regime-card">
        <div class="regime-header">
            <span class="regime-name">{family}</span>
            <span class="{'positive' if total_pnl > 0 else 'negative' if total_pnl < 0 else 'neutral'}">
                {total_trades}T | {family_wr:.1f}% WR | ${total_pnl:+.2f}
            </span>
        </div>
        <table>
            <tr>
                <th>Signal</th>
                <th>FLAT</th>
                <th>NORMAL</th>
                <th>HIGH</th>
                <th>EXTREME</th>
                <th>Status</th>
            </tr>
'''
        
        for sig in signals:
            # Get performance in each regime
            flat = family_perf.get(sig, {}).get('FLAT', {})
            normal = family_perf.get(sig, {}).get('NORMAL', {})
            high = family_perf.get(sig, {}).get('HIGH', {})
            extreme = family_perf.get(sig, {}).get('EXTREME', {})
            
            # Get blocks
            flat_block = family_blocks.get('FLAT', 1.0)
            normal_block = family_blocks.get('NORMAL', 1.0)
            high_block = family_blocks.get('HIGH', 1.0)
            extreme_block = family_blocks.get('EXTREME', 1.0)
            
            # Format performance cells
            def format_cell(perf, block):
                if not perf:
                    return '<td class="neutral">—</td>'
                wr = perf.get('wr', 0)
                pnl = perf.get('pnl', 0)
                trades = perf.get('trades', 0)
                if block == 0.0:
                    return f'<td class="blocked">BLOCKED</td>'
                elif block < 1.0:
                    return f'<td class="neutral">{wr:.0f}% (${pnl:+.2f}) ×{block}</td>'
                elif wr >= 60:
                    return f'<td class="positive">{wr:.0f}% (${pnl:+.2f})</td>'
                elif wr >= 50:
                    return f'<td class="neutral">{wr:.0f}% (${pnl:+.2f})</td>'
                else:
                    return f'<td class="negative">{wr:.0f}% (${pnl:+.2f})</td>'
            
            html += f'''
            <tr>
                <td>{sig}</td>
                {format_cell(flat, flat_block)}
                {format_cell(normal, normal_block)}
                {format_cell(high, high_block)}
                {format_cell(extreme, extreme_block)}
                <td class="{'enabled' if True else 'disabled'}">●</td>
            </tr>
'''
        
        html += '''
        </table>
    </div>
'''
    
    # Add volatility gate multipliers section
    html += '''
    <h2>🔧 Volatility Gate Multipliers</h2>
    <table>
        <tr>
            <th>Regime</th>
            <th>Family</th>
            <th>Multiplier</th>
            <th>Effect</th>
        </tr>
'''
    
    for regime in ['FLAT', 'NORMAL', 'HIGH', 'EXTREME']:
        if regime in volatility_blocks:
            for family, mult in sorted(volatility_blocks[regime].items()):
                if mult == 0.0:
                    effect = 'BLOCKED'
                    cls = 'blocked'
                elif mult < 1.0:
                    effect = f'Penalized ({mult}x)'
                    cls = 'neutral'
                elif mult > 1.0:
                    effect = f'Boosted ({mult}x)'
                    cls = 'positive'
                else:
                    effect = 'Normal (1.0x)'
                    cls = 'neutral'
                
                html += f'''
        <tr>
            <td>{regime}</td>
            <td>{family}</td>
            <td class="{cls}">{mult}x</td>
            <td class="{cls}">{effect}</td>
        </tr>
'''
    
    html += '''
    </table>
    
    <h2>📈 Top Performing Signals (30 days)</h2>
    <table>
        <tr>
            <th>Signal</th>
            <th>Family</th>
            <th>Regime</th>
            <th>Trades</th>
            <th>Win Rate</th>
            <th>PnL</th>
        </tr>
'''
    
    # Sort all signals by PnL
    all_signal_perf = []
    for sig, regimes in regime_data.items():
        family = signal_to_family.get(sig, 'Unknown')
        for regime, data in regimes.items():
            all_signal_perf.append({
                'signal': sig,
                'family': family,
                'regime': regime,
                'trades': data['trades'],
                'wr': data['wr'],
                'pnl': data['pnl']
            })
    
    all_signal_perf.sort(key=lambda x: x['pnl'], reverse=True)
    
    for perf in all_signal_perf[:20]:
        html += f'''
        <tr>
            <td>{perf['signal']}</td>
            <td>{perf['family']}</td>
            <td>{perf['regime']}</td>
            <td>{perf['trades']}</td>
            <td class="{'positive' if perf['wr'] >= 60 else 'neutral' if perf['wr'] >= 50 else 'negative'}">{perf['wr']:.1f}%</td>
            <td class="{'positive' if perf['pnl'] > 0 else 'negative'}">${perf['pnl']:+.2f}</td>
        </tr>
'''
    
    html += '''
    </table>
</body>
</html>
'''
    
    return html


def main():
    print("Generating FAMILY_MAP dashboard...")
    
    family_map = get_family_map()
    regime_data = get_regime_performance()
    volatility_blocks = get_volatility_blocks()
    enable_status = get_signal_enable_status()
    
    html = generate_html(family_map, regime_data, volatility_blocks, enable_status)
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        f.write(html)
    
    print(f"Dashboard saved to {OUTPUT_FILE}")
    print(f"Families: {len(family_map)}")
    print(f"Signals with data: {len(regime_data)}")
    print(f"Volatility blocks: {sum(len(v) for v in volatility_blocks.values())}")


if __name__ == '__main__':
    main()

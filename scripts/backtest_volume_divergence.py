#!/usr/bin/env python3
"""
Backtest Volume-Price Divergence (Accumulation Detection) Signal Idea

Tests:
1. BB position at entry vs outcomes (mean reversion hypothesis)
2. Z-score extremes with opposite direction entries
3. Momentum state analysis in NEUTRAL regime
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import psycopg2
from _secrets import BRAIN_DB_DICT
from datetime import datetime

def run_queries():
    """Execute all three analyses against PostgreSQL brain DB."""
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    results = {
        'timestamp': datetime.now().isoformat(),
        'signal_idea': 'Volume-Price Divergence (Accumulation Detection)',
        'description': 'Testing Wyckoff accumulation/distribution patterns via BB position, Z-score extremes, and momentum states',
        'analyses': {}
    }
    
    try:
        cur = conn.cursor()
        
        # ═══════════════════════════════════════════════════════════════════
        # ANALYSIS 1: BB Position Analysis
        # ═══════════════════════════════════════════════════════════════════
        print("\n" + "="*70)
        print("ANALYSIS 1: Bollinger Band Position at Entry vs Outcomes")
        print("="*70)
        
        bb_query = """
        SELECT 
          CASE WHEN entry_bb_position < 0.2 THEN 'near_lower'
               WHEN entry_bb_position > 0.8 THEN 'near_upper'
               WHEN entry_bb_position BETWEEN 0.4 AND 0.6 THEN 'middle'
               ELSE 'other' END as bb_bucket,
          direction,
          COUNT(*) as trade_count,
          ROUND(100.0*SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END)/COUNT(*),1) as win_rate,
          ROUND(AVG(pnl_pct)::numeric, 3) as avg_pnl_pct,
          ROUND(SUM(pnl_usdt)::numeric, 2) as total_pnl_usdt,
          ROUND(AVG(pnl_usdt)::numeric, 2) as avg_pnl_usdt,
          ROUND(MIN(pnl_pct)::numeric, 3) as min_pnl_pct,
          ROUND(MAX(pnl_pct)::numeric, 3) as max_pnl_pct
        FROM trades 
        WHERE status='closed' AND pnl_pct IS NOT NULL AND entry_bb_position IS NOT NULL
          AND regime='NEUTRAL'
        GROUP BY bb_bucket, direction
        HAVING COUNT(*) >= 5
        ORDER BY bb_bucket, direction
        """
        
        cur.execute(bb_query)
        bb_rows = cur.fetchall()
        bb_columns = [desc[0] for desc in cur.description]
        
        bb_results = []
        print(f"\n{'BB Bucket':<15} {'Direction':<10} {'Trades':<8} {'WinRate':<10} {'Avg PnL%':<10} {'Total PnL':<12} {'Avg PnL$':<10}")
        print("-"*85)
        for row in bb_rows:
            row_dict = dict(zip(bb_columns, row))
            bb_results.append(row_dict)
            print(f"{row_dict['bb_bucket']:<15} {row_dict['direction']:<10} {row_dict['trade_count']:<8} "
                  f"{row_dict['win_rate']:<10} {row_dict['avg_pnl_pct']:<10} "
                  f"${row_dict['total_pnl_usdt']:<11} ${row_dict['avg_pnl_usdt']:<9}")
        
        # Add hypothesis testing
        bb_hypothesis = {
            'test': 'BB Position Mean Reversion',
            'hypothesis': [
                'near_lower + LONG should have higher win rate (buying at support)',
                'near_upper + SHORT should have higher win rate (selling at resistance)'
            ],
            'findings': []
        }
        
        for row in bb_results:
            if row['bb_bucket'] == 'near_lower' and row['direction'] == 'LONG':
                bb_hypothesis['findings'].append({
                    'condition': 'BB < 0.2 + LONG',
                    'win_rate': row['win_rate'],
                    'avg_pnl_pct': float(row['avg_pnl_pct']),
                    'trade_count': row['trade_count'],
                    'assessment': 'SUPPORTS' if row['win_rate'] > 50 else 'WEAKENS'
                })
            elif row['bb_bucket'] == 'near_upper' and row['direction'] == 'SHORT':
                bb_hypothesis['findings'].append({
                    'condition': 'BB > 0.8 + SHORT',
                    'win_rate': row['win_rate'],
                    'avg_pnl_pct': float(row['avg_pnl_pct']),
                    'trade_count': row['trade_count'],
                    'assessment': 'SUPPORTS' if row['win_rate'] > 50 else 'WEAKENS'
                })
        
        results['analyses']['bb_position'] = {
            'data': bb_results,
            'hypothesis_test': bb_hypothesis
        }
        
        # ═══════════════════════════════════════════════════════════════════
        # ANALYSIS 2: Z-Score Extreme + Opposite Direction
        # ═══════════════════════════════════════════════════════════════════
        print("\n" + "="*70)
        print("ANALYSIS 2: Z-Score Extremes with Opposite Direction Entries")
        print("="*70)
        
        zscore_query = """
        SELECT 
          CASE WHEN signal_z_score < -1.5 THEN 'extreme_low'
               WHEN signal_z_score > 1.5 THEN 'extreme_high'
               ELSE 'normal' END as z_bucket,
          direction,
          COUNT(*) as trade_count,
          ROUND(100.0*SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END)/COUNT(*),1) as win_rate,
          ROUND(AVG(pnl_pct)::numeric, 3) as avg_pnl_pct,
          ROUND(SUM(pnl_usdt)::numeric, 2) as total_pnl_usdt,
          ROUND(AVG(pnl_usdt)::numeric, 2) as avg_pnl_usdt
        FROM trades 
        WHERE status='closed' AND pnl_pct IS NOT NULL AND signal_z_score IS NOT NULL
          AND regime='NEUTRAL'
        GROUP BY z_bucket, direction
        HAVING COUNT(*) >= 5
        ORDER BY z_bucket, direction
        """
        
        cur.execute(zscore_query)
        zscore_rows = cur.fetchall()
        zscore_columns = [desc[0] for desc in cur.description]
        
        zscore_results = []
        print(f"\n{'Z Bucket':<15} {'Direction':<10} {'Trades':<8} {'WinRate':<10} {'Avg PnL%':<10} {'Total PnL':<12} {'Avg PnL$':<10}")
        print("-"*85)
        for row in zscore_rows:
            row_dict = dict(zip(zscore_columns, row))
            zscore_results.append(row_dict)
            print(f"{row_dict['z_bucket']:<15} {row_dict['direction']:<10} {row_dict['trade_count']:<8} "
                  f"{row_dict['win_rate']:<10} {row_dict['avg_pnl_pct']:<10} "
                  f"${row_dict['total_pnl_usdt']:<11} ${row_dict['avg_pnl_usdt']:<9}")
        
        # Z-score hypothesis testing
        zscore_hypothesis = {
            'test': 'Z-Score Extreme Contrarian',
            'hypothesis': [
                'extreme_low (z < -1.5) + LONG should mean-revert (oversold bounce)',
                'extreme_high (z > 1.5) + SHORT should mean-revert (overbought fade)'
            ],
            'findings': []
        }
        
        for row in zscore_results:
            if row['z_bucket'] == 'extreme_low' and row['direction'] == 'LONG':
                zscore_hypothesis['findings'].append({
                    'condition': 'z < -1.5 + LONG (oversold bounce)',
                    'win_rate': row['win_rate'],
                    'avg_pnl_pct': float(row['avg_pnl_pct']),
                    'trade_count': row['trade_count'],
                    'assessment': 'SUPPORTS' if row['win_rate'] > 50 else 'WEAKENS'
                })
            elif row['z_bucket'] == 'extreme_high' and row['direction'] == 'SHORT':
                zscore_hypothesis['findings'].append({
                    'condition': 'z > 1.5 + SHORT (overbought fade)',
                    'win_rate': row['win_rate'],
                    'avg_pnl_pct': float(row['avg_pnl_pct']),
                    'trade_count': row['trade_count'],
                    'assessment': 'SUPPORTS' if row['win_rate'] > 50 else 'WEAKENS'
                })
        
        results['analyses']['z_score'] = {
            'data': zscore_results,
            'hypothesis_test': zscore_hypothesis
        }
        
        # ═══════════════════════════════════════════════════════════════════
        # ANALYSIS 3: Momentum State Analysis
        # ═══════════════════════════════════════════════════════════════════
        print("\n" + "="*70)
        print("ANALYSIS 3: Momentum State Analysis (Reversal Patterns)")
        print("="*70)
        
        momentum_query = """
        SELECT 
          signal_momentum_state, 
          direction,
          COUNT(*) as trade_count,
          ROUND(100.0*SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END)/COUNT(*),1) as win_rate,
          ROUND(AVG(pnl_pct)::numeric, 3) as avg_pnl_pct,
          ROUND(SUM(pnl_usdt)::numeric, 2) as total_pnl_usdt,
          ROUND(AVG(pnl_usdt)::numeric, 2) as avg_pnl_usdt
        FROM trades 
        WHERE status='closed' AND pnl_pct IS NOT NULL AND signal_momentum_state IS NOT NULL
          AND regime='NEUTRAL'
        GROUP BY signal_momentum_state, direction
        HAVING COUNT(*) >= 5
        ORDER BY signal_momentum_state, direction
        """
        
        cur.execute(momentum_query)
        momentum_rows = cur.fetchall()
        momentum_columns = [desc[0] for desc in cur.description]
        
        momentum_results = []
        print(f"\n{'Momentum State':<25} {'Direction':<10} {'Trades':<8} {'WinRate':<10} {'Avg PnL%':<10} {'Total PnL':<12}")
        print("-"*85)
        for row in momentum_rows:
            row_dict = dict(zip(momentum_columns, row))
            momentum_results.append(row_dict)
            print(f"{str(row_dict['signal_momentum_state']):<25} {row_dict['direction']:<10} {row_dict['trade_count']:<8} "
                  f"{row_dict['win_rate']:<10} {row_dict['avg_pnl_pct']:<10} "
                  f"${row_dict['total_pnl_usdt']:<11}")
        
        results['analyses']['momentum_state'] = {
            'data': momentum_results
        }
        
        # ═══════════════════════════════════════════════════════════════════
        # SUMMARY & CONCLUSIONS
        # ═══════════════════════════════════════════════════════════════════
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        
        # Overall NEUTRAL regime stats
        cur.execute("""
        SELECT COUNT(*) as total,
               ROUND(100.0*SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END)/COUNT(*),1) as overall_wr,
               ROUND(AVG(pnl_pct)::numeric, 3) as overall_avg_pnl,
               ROUND(SUM(pnl_usdt)::numeric, 2) as total_pnl
        FROM trades 
        WHERE status='closed' AND pnl_pct IS NOT NULL AND regime='NEUTRAL'
        """)
        overall = cur.fetchone()
        overall_dict = {
            'total_trades': overall[0],
            'overall_win_rate': float(overall[1]),
            'overall_avg_pnl_pct': float(overall[2]),
            'total_pnl_usdt': float(overall[3])
        }
        
        print(f"\nOverall NEUTRAL regime stats:")
        print(f"  Total trades: {overall_dict['total_trades']}")
        print(f"  Win rate: {overall_dict['overall_win_rate']}%")
        print(f"  Avg PnL: {overall_dict['overall_avg_pnl_pct']}%")
        print(f"  Total PnL: ${overall_dict['total_pnl_usdt']}")
        
        results['overall_neutral_stats'] = overall_dict
        
        # Key findings
        results['key_findings'] = []
        
        for finding in results['analyses']['bb_position']['hypothesis_test']['findings']:
            if finding['trade_count'] >= 10:
                results['key_findings'].append({
                    'test': 'BB Position',
                    'finding': finding
                })
        
        for finding in results['analyses']['z_score']['hypothesis_test']['findings']:
            if finding['trade_count'] >= 10:
                results['key_findings'].append({
                    'test': 'Z-Score',
                    'finding': finding
                })
        
    except Exception as e:
        print(f"\nERROR: {e}")
        results['error'] = str(e)
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
    
    return results

def save_results(results, output_path):
    """Save results to JSON file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n✓ Results saved to: {output_path}")

if __name__ == '__main__':
    print("="*70)
    print("VOLUME-PRICE DIVERGENCE BACKTEST")
    print("Testing Wyckoff Accumulation/Distribution Patterns")
    print("="*70)
    
    results = run_queries()
    output_path = '/root/.hermes/data/backtest_volume_divergence.json'
    save_results(results, output_path)
    
    print("\n" + "="*70)
    print("BACKTEST COMPLETE")
    print("="*70)

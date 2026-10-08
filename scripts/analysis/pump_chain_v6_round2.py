#!/usr/bin/env python3
"""Round-2 pump-chain analysis: flow_score, direction splits, recent regime, extremes."""
import json
import math
import psycopg2


def q(sql, args=()):
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


print('=== 1. confidence buckets: winners vs losers (60d) ===')
rows = q("""
    SELECT CASE WHEN pnl_usdt>0 THEN 'WIN' ELSE 'LOSS' END,
           CASE WHEN confidence < 60 THEN '<60' WHEN confidence < 70 THEN '60-70'
                WHEN confidence < 80 THEN '70-80' WHEN confidence < 90 THEN '80-90'
                ELSE '90+' END AS bucket,
           COUNT(*), ROUND(SUM(pnl_usdt)::numeric,2)
    FROM trades
    WHERE status='closed' AND signal LIKE '%%pump-chain%%'
      AND open_time > now() - interval '60 days'
    GROUP BY 1,2 ORDER BY 2,1;""")
for r in rows:
    print(f'  {r[0]:5s} flow_score {r[1]:5s}: n={r[2]:3d} pnl=${r[3]}')

print('\n=== 2. RSI band x direction (60d) ===')
rows = q("""
    SELECT direction,
           CASE WHEN ( _signal_metadata->>'rsi_14')::numeric < 40 THEN '<40'
                WHEN (_signal_metadata->>'rsi_14')::numeric < 50 THEN '40-50'
                WHEN (_signal_metadata->>'rsi_14')::numeric < 60 THEN '50-60'
                WHEN (_signal_metadata->>'rsi_14')::numeric < 70 THEN '60-70'
                ELSE '70+' END AS band,
           COUNT(*), ROUND(100.0*SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END)/COUNT(*),1),
           ROUND(SUM(pnl_usdt)::numeric,2)
    FROM trades
    WHERE status='closed' AND signal LIKE '%%pump-chain%%'
      AND open_time > now() - interval '60 days' AND _signal_metadata IS NOT NULL
    GROUP BY 1,2 ORDER BY 1,2;""")
for r in rows:
    print(f'  {r[0]:5s} RSI {r[1]:5s}: n={r[2]:3d} WR={r[3]:5.1f}% pnl=${r[4]}')

print('\n=== 3. staleness x direction (60d) ===')
rows = q("""
    SELECT direction,
           CASE WHEN (_signal_metadata->>'staleness_minutes')::numeric < 2 THEN '<2m'
                WHEN (_signal_metadata->>'staleness_minutes')::numeric < 5 THEN '2-5m'
                ELSE '5m+' END AS band,
           COUNT(*), ROUND(100.0*SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END)/COUNT(*),1),
           ROUND(SUM(pnl_usdt)::numeric,2)
    FROM trades
    WHERE status='closed' AND signal LIKE '%%pump-chain%%'
      AND open_time > now() - interval '60 days' AND _signal_metadata IS NOT NULL
    GROUP BY 1,2 ORDER BY 1,2;""")
for r in rows:
    print(f'  {r[0]:5s} stale {r[1]:4s}: n={r[2]:3d} WR={r[3]:5.1f}% pnl=${r[4]}')

print('\n=== 4. momentum_state x direction (60d) ===')
rows = q("""
    SELECT direction, _signal_metadata->>'momentum_state' AS ms,
           COUNT(*), ROUND(100.0*SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END)/COUNT(*),1),
           ROUND(SUM(pnl_usdt)::numeric,2)
    FROM trades
    WHERE status='closed' AND signal LIKE '%%pump-chain%%'
      AND open_time > now() - interval '60 days' AND _signal_metadata IS NOT NULL
    GROUP BY 1,2 ORDER BY 1,5;""")
for r in rows:
    print(f'  {r[0]:5s} momentum {r[1]:10s}: n={r[2]:3d} WR={r[3]:5.1f}% pnl=${r[4]}')

print('\n=== 5. Recent 14d per source (current regime) ===')
rows = q("""
    SELECT CASE WHEN signal LIKE '%%pump-chain-%%' AND signal NOT LIKE '%%pump-chain-%%,' THEN 'SHORT(pump-chain-)'
                WHEN signal LIKE '%%pump-chain+%%' THEN 'LONG(pump-chain+)'
                ELSE signal END AS src,
           direction, COUNT(*),
           ROUND(100.0*SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END)/COUNT(*),1),
           ROUND(SUM(pnl_usdt)::numeric,2)
    FROM trades
    WHERE status='closed' AND signal LIKE '%%pump-chain%%'
      AND open_time > now() - interval '14 days'
    GROUP BY 1,2 ORDER BY 5;""")
for r in rows:
    print(f'  {r[0]:20s} {r[1]:5s}: n={r[2]:3d} WR={r[3]:5.1f}% pnl=${r[4]}')

print('\n=== 6. Combined candidate filter sim (LONG only, 60d) ===')
rows = q("""
    SELECT pnl_usdt::float8,
           (_signal_metadata->>'rsi_14')::numeric AS rsi,
           _signal_metadata->>'momentum_state' AS ms,
           (_signal_metadata->>'z_score')::numeric AS z
    FROM trades
    WHERE status='closed' AND signal LIKE '%%pump-chain%%' AND direction='LONG'
      AND open_time > now() - interval '60 days' AND _signal_metadata IS NOT NULL;""")

def _rsi(r):
    return 50.0 if r[1] is None else float(r[1])

def _z(r):
    return 0.0 if r[3] is None else float(r[3])

def _ms(r):
    return r[2] or ''

for name, pred in [
    ('baseline (no filter)', lambda r: True),
    ('block RSI<40', lambda r: _rsi(r) >= 40),
    ('block RSI extremes (<40 or >70)', lambda r: 40 <= _rsi(r) <= 70),
    ('block momentum flat', lambda r: _ms(r) != 'flat'),
    ('block z < -1.5', lambda r: _z(r) >= -1.5),
    ('ALL FOUR combined', lambda r: 40 <= _rsi(r) <= 70 and _ms(r) != 'flat' and _z(r) >= -1.5),
    ('RSI extremes + flat', lambda r: 40 <= _rsi(r) <= 70 and _ms(r) != 'flat'),
]:
    sub = [r for r in rows if pred(r)]
    blocked = [r for r in rows if not pred(r)]
    if not sub:
        continue
    w = sum(1 for r in sub if r[0] > 0)
    bw = sum(1 for r in blocked if r[0] > 0)
    print(f'  {name:34s}: n={len(sub):3d} WR={100.0*w/len(sub):5.1f}% '
          f'pnl=${sum(r[0] for r in sub):+6.2f} | blocked n={len(blocked):3d} ({bw}W/{len(blocked)-bw}L) '
          f'pnl=${sum(r[0] for r in blocked):+6.2f}')

print('\n=== 7. Same combined filter sim (SHORT only, 60d) ===')
rows = q("""
    SELECT pnl_usdt::float8,
           (_signal_metadata->>'rsi_14')::numeric AS rsi,
           _signal_metadata->>'momentum_state' AS ms,
           (_signal_metadata->>'z_score')::numeric AS z
    FROM trades
    WHERE status='closed' AND signal LIKE '%%pump-chain%%' AND direction='SHORT'
      AND open_time > now() - interval '60 days' AND _signal_metadata IS NOT NULL;""")
for name, pred in [
    ('baseline (no filter)', lambda r: True),
    ('block RSI>70', lambda r: _rsi(r) <= 70),
    ('block RSI<40 (already oversold)', lambda r: _rsi(r) >= 40),
    ('block momentum flat', lambda r: _ms(r) != 'flat'),
    ('block z > +1.5', lambda r: _z(r) <= 1.5),
    ('ALL combined', lambda r: _rsi(r) >= 40 and _ms(r) != 'flat' and _z(r) <= 1.5),
]:
    sub = [r for r in rows if pred(r)]
    blocked = [r for r in rows if not pred(r)]
    if not sub:
        continue
    w = sum(1 for r in sub if r[0] > 0)
    bw = sum(1 for r in blocked if r[0] > 0)
    print(f'  {name:34s}: n={len(sub):3d} WR={100.0*w/len(sub):5.1f}% '
          f'pnl=${sum(r[0] for r in sub):+6.2f} | blocked n={len(blocked):3d} ({bw}W/{len(blocked)-bw}L) '
          f'pnl=${sum(r[0] for r in blocked):+6.2f}')

print('\n=== 8. Big winners vs big losers profile (top/bottom 10 by pnl, 60d) ===')
rows = q("""
    SELECT token, direction, ROUND(pnl_usdt::numeric,3),
           COALESCE(ROUND((_signal_metadata->>'rsi_14')::numeric,1),0),
           COALESCE(_signal_metadata->>'momentum_state','?'),
           COALESCE(_signal_metadata->>'wave_phase','?'),
           COALESCE(ROUND((_signal_metadata->>'z_score')::numeric,2),0),
           COALESCE(ROUND((_signal_metadata->>'staleness_minutes')::numeric,1),0),
           COALESCE(ROUND((_signal_metadata->>'speed_percentile')::numeric,0),0),
           volatility_regime, open_time::timestamp(0)
    FROM trades
    WHERE status='closed' AND signal LIKE '%%pump-chain%%'
      AND open_time > now() - interval '60 days' AND _signal_metadata IS NOT NULL
    ORDER BY pnl_usdt DESC LIMIT 10;""")
print('  TOP 10 WINNERS: token dir pnl rsi mom wave z staleness speed volreg time')
for r in rows:
    print(f'    {r[0]:8s} {r[1]:5s} {r[2]:+7.3f} rsi={r[3]:5.1f} mom={r[4]:8s} wave={r[5]:12s} z={r[6]:+5.2f} stale={r[7]:4.1f}m spd={r[8]:3.0f} {r[9]:7s} {r[10]}')
rows = q("""
    SELECT token, direction, ROUND(pnl_usdt::numeric,3),
           COALESCE(ROUND((_signal_metadata->>'rsi_14')::numeric,1),0),
           COALESCE(_signal_metadata->>'momentum_state','?'),
           COALESCE(_signal_metadata->>'wave_phase','?'),
           COALESCE(ROUND((_signal_metadata->>'z_score')::numeric,2),0),
           COALESCE(ROUND((_signal_metadata->>'staleness_minutes')::numeric,1),0),
           COALESCE(ROUND((_signal_metadata->>'speed_percentile')::numeric,0),0),
           volatility_regime, open_time::timestamp(0)
    FROM trades
    WHERE status='closed' AND signal LIKE '%%pump-chain%%'
      AND open_time > now() - interval '60 days' AND _signal_metadata IS NOT NULL
    ORDER BY pnl_usdt ASC LIMIT 10;""")
print('  TOP 10 LOSERS:')
for r in rows:
    print(f'    {r[0]:8s} {r[1]:5s} {r[2]:+7.3f} rsi={r[3]:5.1f} mom={r[4]:8s} wave={r[5]:12s} z={r[6]:+5.2f} stale={r[7]:4.1f}m spd={r[8]:3.0f} {r[9]:7s} {r[10]}')

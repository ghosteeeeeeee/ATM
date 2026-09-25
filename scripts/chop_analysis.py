#!/usr/bin/env python3
"""One-shot chop analysis for strategic planning."""
import psycopg2

conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
c = conn.cursor()

# 1. ALL signals in NEUTRAL (chop) — 14d
c.execute("""
    SELECT signal, direction, COUNT(*), 
        ROUND(AVG(CASE WHEN pnl_usdt > 0 THEN 1.0 ELSE 0.0 END)*100, 1),
        ROUND(COALESCE(SUM(pnl_usdt),0)::numeric, 2),
        ROUND(COALESCE(AVG(pnl_usdt),0)::numeric, 4),
        ROUND(COALESCE(AVG(mfe_pct),0)::numeric, 4),
        ROUND(COALESCE(AVG(mae_pct),0)::numeric, 4)
    FROM trades 
    WHERE close_time > NOW() - INTERVAL '14 days'
      AND regime = 'NEUTRAL'
      AND signal IS NOT NULL
    GROUP BY signal, direction
    HAVING COUNT(*) >= 3
    ORDER BY SUM(pnl_usdt)
""")
print('=== ALL SIGNALS in NEUTRAL (chop) 14d, min 3T ===')
for r in c.fetchall():
    sign = '+' if r[4] >= 0 else ''
    print(f'  {str(r[0])[:30]:30s} {r[1]:6s} {r[2]:3d}T WR={r[3]:5.1f}% PnL={sign}${r[4]:7.2f} avg={sign}${r[5]:.4f} MFE={r[6]:.4f}% MAE={r[7]:.4f}%')

# 2. MFE vs PNL — how much do we give back?
c.execute("""
    SELECT 
        direction,
        COUNT(*) as trades,
        ROUND(AVG(mfe_pct)::numeric, 4) as avg_mfe,
        ROUND(AVG(mae_pct)::numeric, 4) as avg_mae,
        ROUND(AVG(pnl_pct)::numeric, 4) as avg_pnl_pct,
        ROUND(AVG(CASE WHEN mfe_pct > 0.5 THEN mfe_pct END)::numeric, 4) as avg_mfe_gt05,
        ROUND(AVG(CASE WHEN mfe_pct > 1.0 THEN mfe_pct END)::numeric, 4) as avg_mfe_gt1
    FROM trades 
    WHERE close_time > NOW() - INTERVAL '14 days'
      AND regime = 'NEUTRAL'
      AND mfe_pct IS NOT NULL
    GROUP BY direction
""")
print('\n=== MFE vs ACTUAL PNL in NEUTRAL 14d ===')
for r in c.fetchall():
    print(f'  {r[0]:6s}: {r[1]:3d}T avg_MFE={r[2]:.4f}% avg_MAE={r[3]:.4f}% avg_PNL%={r[4]:.4f}%')
    print(f'         MFE>0.5%: {r[5]}% | MFE>1.0%: {r[6]}%')
    if r[4] and r[2] and r[2] != 0:
        ratio = r[4] / r[2] * 100
        print(f'         BOOKING RATIO: {ratio:.1f}% of MFE captured')

# 3. Exit reasons in chop — who is killing MFE?
c.execute("""
    SELECT 
        close_reason,
        direction,
        COUNT(*),
        ROUND(AVG(pnl_pct)::numeric, 4),
        ROUND(AVG(trade_duration / 60.0)::numeric, 1),
        ROUND(COALESCE(AVG(mfe_pct),0)::numeric, 4),
        ROUND(COALESCE(SUM(pnl_usdt),0)::numeric, 2)
    FROM trades 
    WHERE close_time > NOW() - INTERVAL '14 days'
      AND regime = 'NEUTRAL'
    GROUP BY close_reason, direction
    HAVING COUNT(*) >= 2
    ORDER BY direction, SUM(pnl_usdt)
""")
print('\n=== EXIT REASONS in NEUTRAL 14d ===')
for r in c.fetchall():
    sign = '+' if r[6] >= 0 else ''
    mfe = r[5] if r[5] is not None else 0.0
    dur = r[4] if r[4] is not None else 0.0
    print(f'  {r[0]:30s} {r[1]:6s} {r[2]:3d}T avg%={r[3]:.4f} dur={dur:.1f}h MFE={mfe:.4f}% total={sign}${r[6]:.2f}')

# 4. Mean-reversion vs Momentum in chop
c.execute("""
    SELECT 
        CASE 
            WHEN signal ~ '(bb.bounce|rs-|hzscore|exhaustion|squeeze|pullback|range|doji|oversold|reversion|sniper)' THEN 'MEAN-REV'
            WHEN signal ~ '(pump.chain|mover|accel.300|volume.breakout|continuation|grind|momentum)' THEN 'MOMENTUM'
            ELSE 'OTHER'
        END as family,
        direction,
        COUNT(*),
        ROUND(AVG(CASE WHEN pnl_usdt > 0 THEN 1.0 ELSE 0.0 END)*100, 1),
        ROUND(COALESCE(SUM(pnl_usdt),0)::numeric, 2),
        ROUND(COALESCE(AVG(mfe_pct),0)::numeric, 4),
        ROUND(COALESCE(AVG(mae_pct),0)::numeric, 4)
    FROM trades 
    WHERE close_time > NOW() - INTERVAL '30 days'
      AND regime = 'NEUTRAL'
      AND signal IS NOT NULL
    GROUP BY family, direction
    ORDER BY family, SUM(pnl_usdt)
""")
print('\n=== MEAN-REV vs MOMENTUM vs OTHER in NEUTRAL 30d ===')
for r in c.fetchall():
    sign = '+' if r[4] >= 0 else ''
    print(f'  {r[0]:12s} {r[1]:6s}: {r[2]:3d}T WR={r[3]:5.1f}% PnL={sign}${r[4]:7.2f} MFE={r[5]:.4f}% MAE={r[6]:.4f}%')

# 5. Which coins trend in NEUTRAL? (high MFE = trending coin)
c.execute("""
    SELECT token, COUNT(*), 
        ROUND(AVG(CASE WHEN pnl_usdt > 0 THEN 1.0 ELSE 0.0 END)*100, 1),
        ROUND(COALESCE(SUM(pnl_usdt),0)::numeric, 2),
        ROUND(COALESCE(AVG(mfe_pct),0)::numeric, 4),
        ROUND(COALESCE(AVG(mae_pct),0)::numeric, 4)
    FROM trades 
    WHERE close_time > NOW() - INTERVAL '30 days'
      AND regime = 'NEUTRAL'
    GROUP BY token
    HAVING COUNT(*) >= 5
    ORDER BY AVG(mfe_pct) DESC
""")
print('\n=== COINS BY MFE in NEUTRAL 30d (high MFE = trending within chop) ===')
rows = c.fetchall()
print('  TRENDING (high MFE):')
for r in rows[:8]:
    print(f'    {r[0]:10s} {r[1]:3d}T WR={r[2]:5.1f}% PnL=${r[3]:7.2f} MFE={r[4]:.2f}% MAE={r[5]:.2f}%')
print('  CHOPPY (low MFE):')
for r in rows[-8:]:
    sign = '+' if r[3] >= 0 else ''
    print(f'    {r[0]:10s} {r[1]:3d}T WR={r[2]:5.1f}% PnL={sign}${r[3]:7.2f} MFE={r[4]:.2f}% MAE={r[5]:.2f}%')

# 6. Short-term trade performance (under 2h = chop trades)
c.execute("""
    SELECT 
        direction,
        COUNT(*) as trades,
        ROUND(AVG(CASE WHEN pnl_usdt > 0 THEN 1.0 ELSE 0.0 END)*100, 1),
        ROUND(COALESCE(SUM(pnl_usdt),0)::numeric, 2),
        ROUND(AVG(trade_duration / 60.0)::numeric, 1)
    FROM trades 
    WHERE close_time > NOW() - INTERVAL '14 days'
      AND regime = 'NEUTRAL'
      AND trade_duration < 7200  -- under 2 hours
    GROUP BY direction
""")
print('\n=== SHORT-DURATION TRADES (<2h) in NEUTRAL 14d ===')
for r in c.fetchall():
    sign = '+' if r[3] >= 0 else ''
    print(f'  {r[0]:6s}: {r[1]:3d}T WR={r[2]:5.1f}% PnL={sign}${r[3]:7.2f} avg_dur={r[4]:.1f}h')

# Also medium (2-6h)
c.execute("""
    SELECT 
        direction,
        COUNT(*) as trades,
        ROUND(AVG(CASE WHEN pnl_usdt > 0 THEN 1.0 ELSE 0.0 END)*100, 1),
        ROUND(COALESCE(SUM(pnl_usdt),0)::numeric, 2),
        ROUND(AVG(trade_duration / 60.0)::numeric, 1)
    FROM trades 
    WHERE close_time > NOW() - INTERVAL '14 days'
      AND regime = 'NEUTRAL'
      AND trade_duration BETWEEN 7200 AND 21600  -- 2-6 hours
    GROUP BY direction
""")
print('\n=== MEDIUM-DURATION TRADES (2-6h) in NEUTRAL 14d ===')
for r in c.fetchall():
    sign = '+' if r[3] >= 0 else ''
    print(f'  {r[0]:6s}: {r[1]:3d}T WR={r[2]:5.1f}% PnL={sign}${r[3]:7.2f} avg_dur={r[4]:.1f}h')

# Long duration (>6h)
c.execute("""
    SELECT 
        direction,
        COUNT(*) as trades,
        ROUND(AVG(CASE WHEN pnl_usdt > 0 THEN 1.0 ELSE 0.0 END)*100, 1),
        ROUND(COALESCE(SUM(pnl_usdt),0)::numeric, 2),
        ROUND(AVG(trade_duration / 60.0)::numeric, 1)
    FROM trades 
    WHERE close_time > NOW() - INTERVAL '14 days'
      AND regime = 'NEUTRAL'
      AND trade_duration > 21600  -- >6 hours
    GROUP BY direction
""")
print('\n=== LONG-DURATION TRADES (>6h) in NEUTRAL 14d ===')
for r in c.fetchall():
    sign = '+' if r[3] >= 0 else ''
    print(f'  {r[0]:6s}: {r[1]:3d}T WR={r[2]:5.1f}% PnL={sign}${r[3]:7.2f} avg_dur={r[4]:.1f}h')

conn.close()

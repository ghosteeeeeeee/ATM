import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres', password='Brain123')
cur = conn.cursor()

cur.execute("""
    SELECT signal, direction, COUNT(*) as trades, 
           ROUND(100.0*SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)/COUNT(*),1) as wr,
           ROUND(SUM(pnl_usdt),2) as pnl
    FROM trades 
    WHERE close_time > NOW() - INTERVAL '6 hours' AND status = 'closed'
    GROUP BY signal, direction 
    HAVING COUNT(*) >= 2
    ORDER BY pnl
""")
print("=== 6h Performance ===")
for r in cur.fetchall():
    print(r)

cur.execute("""
    SELECT signal, direction, COUNT(*) as trades, 
           ROUND(100.0*SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)/COUNT(*),1) as wr,
           ROUND(SUM(pnl_usdt),2) as pnl
    FROM trades 
    WHERE close_time > NOW() - INTERVAL '24 hours' AND status = 'closed'
    GROUP BY signal, direction 
    HAVING COUNT(*) >= 3
    ORDER BY pnl
""")
print("\n=== 24h Performance ===")
for r in cur.fetchall():
    print(r)

# Signal inversions
cur.execute("""
    SELECT token, signal, direction, close_reason, pnl_usdt
    FROM trades 
    WHERE close_time > NOW() - INTERVAL '24 hours'
      AND ((signal LIKE '%long%' AND direction = 'SHORT')
        OR (signal LIKE '%short%' AND direction = 'LONG'))
    ORDER BY created_at DESC LIMIT 10
""")
print("\n=== Signal Inversions ===")
inversions = cur.fetchall()
if inversions:
    for r in inversions:
        print(r)
else:
    print("None found")

# Full 24h list (all signals, not just >=3 trades)
cur.execute("""
    SELECT signal, direction, COUNT(*) as trades, 
           ROUND(100.0*SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)/COUNT(*),1) as wr,
           ROUND(SUM(pnl_usdt),2) as pnl
    FROM trades 
    WHERE close_time > NOW() - INTERVAL '24 hours' AND status = 'closed'
    GROUP BY signal, direction 
    ORDER BY pnl
""")
print("\n=== 24h ALL (no trade threshold) ===")
for r in cur.fetchall():
    print(r)

conn.close()

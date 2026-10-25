import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn.cursor()
for pat in ['pump-chain+', 'pump-chain-,pump-chain-v6-', 'pump-chain']:
    cur.execute('''
        SELECT signal, volatility_regime, COUNT(*),
               SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END),
               ROUND(100.0*SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)/COUNT(*),1),
               ROUND(SUM(pnl_usdt),2)
        FROM trades
        WHERE signal LIKE %s AND status = 'closed'
        GROUP BY signal, volatility_regime
        HAVING COUNT(*) >= 3
        ORDER BY signal, volatility_regime
    ''', ('%' + pat + '%',))
    print('---', pat, '---')
    for r in cur.fetchall():
        print(r)
conn.close()

#!/usr/bin/env python3
"""Pin the exact CLOSE-anchored variant reproducing WIN +0.021% / LOSS -0.645%."""
import sqlite3, statistics as st, datetime as dt
CAND = sqlite3.connect("file:/root/.hermes/data/candles.db?mode=ro", uri=True, timeout=10)
SQ = sqlite3.connect("/root/.hermes/brain/associative_memory.db")
rows = SQ.execute("""
    SELECT token, won, close_time FROM trade_log
    WHERE direction='LONG' AND signal LIKE '%pump-chain%' AND close_time>='2026-09-26'
    ORDER BY close_time""").fetchall()

def to_epoch(s):
    s=s.replace('T',' ').split('+')[0]
    return dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc).timestamp()

def series(token, anchor, table, n, co):
    ts=int(anchor)
    if co:
        q=f"SELECT close FROM {table} WHERE token=? AND is_closed=1 AND ts+{60 if table=='candles_1m' else 300}<=? ORDER BY ts DESC LIMIT {n}"
    else:
        q=f"SELECT close FROM {table} WHERE token=? AND is_closed=1 AND ts<=? ORDER BY ts DESC LIMIT {n}"
    return [r[0] for r in CAND.execute(q,(token.upper(),ts)).fetchall()]

def test(table, n, co, thr=-0.1):
    W=[];L=[];bw=bl=0; kw=kl=0
    for tok,won,ct in rows:
        cl=series(tok,to_epoch(ct),table,n,co)
        if len(cl)<n or cl[-1]==0: continue
        m=(cl[0]-cl[-1])/cl[-1]*100
        (W if won else L).append(m)
        if m<thr:
            if won: bw+=1
            else: bl+=1
        else:
            if won: kw+=1
            else: kl+=1
    wr=kw/(kw+kl)*100 if (kw or kl) else float('nan')
    print(f"  {table} n={n} closed={co}: BLOCKED {bl}/{len(L)}L {bw}/{len(W)}W | "
          f"kept {kw}W/{kl}L WR {wr:.1f}% | WIN {st.mean(W):+.4f}% LOSS {st.mean(L):+.4f}%")

print("CLOSE-anchored variants (thr=-0.1%):")
for table,n,co in [("candles_5m",6,True),("candles_5m",6,False),
                   ("candles_1m",30,True),("candles_1m",30,False),
                   ("candles_1m",6,True),("candles_1m",6,False),
                   ("candles_5m",5,False),("candles_5m",7,False),
                   ("candles_1m",31,False),("candles_1m",29,False)]:
    test(table,n,co)

#!/usr/bin/env python3
"""
feature_engineering.py — Extract ML features from PostgreSQL trade rows.

Only uses features available at ENTRY TIME (no leakage).
Selects explicit columns instead of dropping (safer).
"""
import os
import sys
import psycopg2
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import HERMES_DATA

# Explicit feature selection — only entry-time data, no leakage
SELECT_COLS = [
    'token', 'signal', 'direction', 'leverage',
    'entry_rsi_14', 'entry_macd_hist', 'entry_bb_position',
    'volatility_regime',
    'pnl_pct', 'open_time',
]


def query_trades(days=90):
    """Query closed trades from PostgreSQL."""
    conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
    try:
        cols = ', '.join(SELECT_COLS)
        df = pd.read_sql(f"""
            SELECT {cols} FROM trades
            WHERE status='closed' AND pnl_pct IS NOT NULL
            AND close_time > NOW() - INTERVAL '{days} days'
            ORDER BY close_time
        """, conn)
    finally:
        conn.close()
    return df


def build_dataset(df):
    """Build feature matrix and labels."""
    work = df.copy()

    # Time features
    work['open_time'] = pd.to_datetime(work['open_time'])
    work['hour_of_day'] = work['open_time'].dt.hour
    work['day_of_week'] = work['open_time'].dt.dayofweek
    work['is_weekend'] = (work['day_of_week'] >= 5).astype(int)
    work = work.drop(columns=['open_time'])

    # RSI tiers
    work['rsi_oversold'] = (work['entry_rsi_14'] < 30).astype(float)
    work['rsi_overbought'] = (work['entry_rsi_14'] > 70).astype(float)
    work['macd_direction'] = np.sign(work['entry_macd_hist'].fillna(0))

    # Median impute continuous
    for col in ['entry_rsi_14', 'entry_macd_hist', 'entry_bb_position']:
        work[col] = work[col].fillna(work[col].median())

    # One-hot categoricals (top 30 each)
    for col in ['token', 'signal', 'direction', 'volatility_regime']:
        top = work[col].value_counts().head(30).index
        work[col] = work[col].where(work[col].isin(top), 'OTHER')
        work = pd.get_dummies(work, columns=[col], dummy_na=False)

    # Target
    work['won'] = (work['pnl_pct'] > 0).astype(int)
    work = work.drop(columns=['pnl_pct'])

    return work


if __name__ == '__main__':
    df = query_trades()
    print(f"Queried {len(df)} trades, WR={df['pnl_pct'].gt(0).mean()*100:.1f}%")
    data = build_dataset(df)
    print(f"Dataset: {data.shape[0]} rows x {data.shape[1]} cols")
    non_num = [c for c in data.columns if c != 'won' and data[c].dtype not in ['float64','int64','float32','int32','bool']]
    print(f"Non-numeric: {non_num}")

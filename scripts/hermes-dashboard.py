#!/usr/bin/env python3
"""
Hermes Local ML Dashboard — Streamlit
Streams from /root/.hermes/wandb-local/ JSONL files.
No internet required, no API keys, fully local.

Usage:
  streamlit run /root/.hermes/scripts/hermes-dashboard.py
  # or
  python3 /root/.hermes/scripts/hermes-dashboard.py

Runs on http://localhost:8501 by default.
"""
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
LOCAL_DIR = Path('/root/.hermes/wandb-local')
CANDLE_DIR = LOCAL_DIR  # candle runs are individual .json files
AB_FILE = LOCAL_DIR / 'ab-tests.jsonl'
DECISIONS_FILE = LOCAL_DIR / 'decisions.jsonl'
SIGNALS_DB = '/root/.hermes/data/signals_hermes_runtime.db'

st.set_page_config(
    page_title='Hermes Dashboard',
    page_icon='📊',
    layout='wide',
    initial_sidebar_state='expanded',
)

# ── Helpers ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=10)
def load_candle_runs():
    """Load all candle predictor run JSON files."""
    runs = []
    for f in sorted(LOCAL_DIR.glob('candle-predictor-*.json')):
        try:
            with open(f) as fh:
                runs.append(json.load(fh))
        except Exception:
            pass
    return pd.DataFrame(runs)

@st.cache_data(ttl=30)
def load_prediction_accuracy():
    """Query live accuracy stats from predictions.db."""
    import sqlite3
    try:
        conn = sqlite3.connect('/root/.hermes/data/predictions.db', timeout=10)
        cur = conn.cursor()

        # Overall
        cur.execute('SELECT COUNT(*), SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END) FROM predictions WHERE correct IS NOT NULL')
        total, correct = cur.fetchone()
        overall = {'total': total or 0, 'correct': correct or 0}

        # By direction
        cur.execute("SELECT direction, COUNT(*), SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END) FROM predictions WHERE correct IS NOT NULL GROUP BY direction")
        by_direction = {row[0]: {'total': row[1], 'correct': row[2]} for row in cur.fetchall()}

        # By regime
        cur.execute("SELECT regime, COUNT(*), SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END) FROM predictions WHERE correct IS NOT NULL AND regime IS NOT NULL GROUP BY regime")
        by_regime = {row[0]: {'total': row[1], 'correct': row[2]} for row in cur.fetchall()}

        # By token (top tokens)
        cur.execute("SELECT token, COUNT(*), SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END) FROM predictions WHERE correct IS NOT NULL GROUP BY token ORDER BY COUNT(*) DESC LIMIT 10")
        by_token = {row[0]: {'total': row[1], 'correct': row[2]} for row in cur.fetchall()}

        # Recent trend (last 50 resolved predictions)
        cur.execute("SELECT direction, correct FROM (SELECT direction, correct FROM predictions WHERE correct IS NOT NULL ORDER BY id DESC LIMIT 50) ORDER BY id ASC")
        recent = cur.fetchall()
        recent_up = sum(1 for d, c in recent if d == 'UP')
        recent_down = sum(1 for d, c in recent if d == 'DOWN')

        conn.close()
        return {
            'overall': overall,
            'by_direction': by_direction,
            'by_regime': by_regime,
            'by_token': by_token,
            'recent': {'up': recent_up, 'down': recent_down, 'total': len(recent)},
        }
    except Exception as e:
        return {'error': str(e)}

@st.cache_data(ttl=10)
def load_ab_tests():
    """Load ab-tests.jsonl into DataFrame."""
    if not AB_FILE.exists():
        return pd.DataFrame()
    rows = []
    with open(AB_FILE) as f:
        for line in f:
            try:
                rows.append(json.loads(line.strip()))
            except Exception:
                pass
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

@st.cache_data(ttl=10)
def load_decisions():
    """Load decisions.jsonl into DataFrame."""
    if not DECISIONS_FILE.exists():
        return pd.DataFrame()
    rows = []
    with open(DECISIONS_FILE) as f:
        for line in f:
            try:
                rows.append(json.loads(line.strip()))
            except Exception:
                pass
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

@st.cache_data(ttl=30)
def load_signal_stats():
    """Load win rate stats from signals DB."""
    try:
        import sqlite3
        conn = sqlite3.connect(SIGNALS_DB, timeout=5)
        df = pd.read_sql("""
            SELECT signal_type, COUNT(*) as n,
                   SUM(is_win) as wins,
                   ROUND(100.0*SUM(is_win)/COUNT(*),1) as wr,
                   ROUND(AVG(pnl_pct),3) as avg_pnl
            FROM signal_outcomes
            GROUP BY signal_type
            ORDER BY n DESC
        """, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

# ── Sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.title('📊 Hermes Dashboard')
st.sidebar.caption('Local ML experiment tracking — no cloud required')
st.sidebar.divider()

page = st.sidebar.radio(
    'System',
    ['🏠 Overview', '🕯️ candle_predictor', '🔀 A/B Tests', '🎯 ai_decider', '📈 Signal Stats'],
    index=0,
)

st.sidebar.divider()
st.sidebar.caption(f'Updated: {datetime.now().strftime("%H:%M:%S")}')
if st.sidebar.button('🔄 Refresh'):
    st.rerun()

# ── Overview ─────────────────────────────────────────────────────────────────

if page == '🏠 Overview':
    st.title('Hermes ML Dashboard')
    st.caption('Streaming from /root/.hermes/wandb-local/')

    col1, col2, col3 = st.columns(3)

    candle = load_candle_runs()
    ab = load_ab_tests()
    decisions = load_decisions()

    with col1:
        st.metric('candle_predictor runs', len(candle))
        if not candle.empty:
            total_pred = candle['predicted'].sum() if 'predicted' in candle else 0
            total_inv = candle['inverted_total'].sum() if 'inverted_total' in candle else 0
            st.caption(f'  predicted: {total_pred} | inverted: {total_inv}')

    with col2:
        st.metric('A/B test events', len(ab))
        if not ab.empty and 'outcome' in ab.columns:
            wins = (ab['outcome'] == 'win').sum() if 'outcome' in ab else 0
            st.caption(f'  wins: {wins} | losses: {len(ab)-wins}')

    with col3:
        st.metric('ai_decider decisions', len(decisions))
        if not decisions.empty:
            approved = (decisions['decision'] == 'HOT_APPROVED').sum() if 'decision' in decisions else 0
            st.caption(f'  HOT_APPROVED: {approved}')

    st.divider()

    # Quick stats
    st.subheader('Quick Stats')
    if not decisions.empty:
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.metric('Top token', decisions.iloc[-1]['top_token'] if len(decisions) else '—')
        with col_b:
            regime = decisions['regime'].value_counts().idxmax() if 'regime' in decisions else '—'
            st.metric('Top regime', regime)
        with col_c:
            avg_score = decisions['top_score'].mean() if 'top_score' in decisions else 0
            st.metric('Avg score', f'{avg_score:.1f}')
        with col_d:
            avg_speed = decisions['speed_percentile'].mean() if 'speed_percentile' in decisions else 0
            st.metric('Avg speed %ile', f'{avg_speed:.1f}')

    st.divider()

    # Recent decisions
    if not decisions.empty:
        st.subheader('Recent Decisions')
        display_cols = ['timestamp', 'top_token', 'direction', 'decision', 'top_score', 'regime', 'speed_percentile', 'reason']
        available = [c for c in display_cols if c in decisions.columns]
        st.dataframe(
            decisions[available].tail(20).sort_values('timestamp', ascending=False),
            use_container_width=True,
            hide_index=True,
        )

    if not candle.empty:
        st.subheader('Recent candle_predictor Runs')
        st.dataframe(
            candle.sort_values('timestamp', ascending=False).tail(10),
            use_container_width=True,
            hide_index=True,
        )

# ── candle_predictor ───────────────────────────────────────────────────────────

elif page == '🕯️ candle_predictor':
    st.title('🕯️ candle_predictor')
    st.caption('LLM-based candle direction prediction model')

    candle = load_candle_runs()

    if candle.empty:
        st.info('No runs yet — run `python3 candle_predictor.py` to generate data')
    else:
        candle['timestamp'] = pd.to_datetime(candle['timestamp'])
        runs_total = len(candle)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric('Total runs', runs_total)
        with col2:
            total_pred = candle['predicted'].sum()
            st.metric('Total predicted', f'{total_pred}')
        with col3:
            total_inv = candle['inverted_total'].sum() if 'inverted_total' in candle else 0
            st.metric('Total inverted', f'{total_inv}')
        with col4:
            inv_rate = (total_inv / runs_total * 100) if runs_total > 0 else 0
            st.metric('Inversion rate', f'{inv_rate:.1f}%')

        st.divider()

        # ── Live accuracy from predictions.db ──────────────────────────────
        acc = load_prediction_accuracy()
        if 'error' not in acc:
            o = acc['overall']
            o_pct = f"{o['correct']}/{o['total']} = {o['correct']/o['total']*100:.1f}%" if o['total'] else 'No resolved predictions'

            st.subheader('📊 Live Accuracy (from predictions.db)')
            a1, a2, a3, a4 = st.columns(4)
            with a1:
                st.metric('Overall', o_pct)
            with a2:
                up = acc['by_direction'].get('UP', {'total': 0, 'correct': 0})
                up_pct = f"{up['correct']}/{up['total']} = {up['correct']/up['total']*100:.1f}%" if up['total'] else '—'
                st.metric('UP accuracy', up_pct)
            with a3:
                dn = acc['by_direction'].get('DOWN', {'total': 0, 'correct': 0})
                dn_pct = f"{dn['correct']}/{dn['total']} = {dn['correct']/dn['total']*100:.1f}%" if dn['total'] else '—'
                st.metric('DOWN accuracy', dn_pct)
            with a4:
                r = acc['recent']
                recent_pct = f"{r['up']}/{r['total']} last 50" if r['total'] else '—'
                st.metric('Recent trend', recent_pct)

            # By regime
            if acc['by_regime']:
                st.caption('By regime:')
                reg_cols = st.columns(min(len(acc['by_regime']), 4))
                for i, (reg, d) in enumerate(sorted(acc['by_regime'].items())):
                    pct = d['correct']/d['total']*100 if d['total'] else 0
                    reg_cols[i].metric(f'regime={reg}', f"{d['correct']}/{d['total']} = {pct:.1f}%")

            # By token (top 10)
            if acc['by_token']:
                st.caption('Top tokens by volume:')
                token_rows = []
                for tok, d in sorted(acc['by_token'].items(), key=lambda x: -x[1]['total']):
                    pct = d['correct']/d['total']*100 if d['total'] else 0
                    token_rows.append({'token': tok, 'correct': d['correct'], 'total': d['total'], 'accuracy': f'{pct:.1f}%'})
                st.dataframe(pd.DataFrame(token_rows), use_container_width=True, hide_index=True)

            st.divider()

        # Run history table
        st.subheader('Run History')
        display_cols = ['timestamp', 'model', 'inversion_threshold', 'predicted', 'inverted_total', 'tokens_processed', 'errors']
        available = [c for c in display_cols if c in candle.columns]
        st.dataframe(
            candle[available].sort_values('timestamp', ascending=False),
            use_container_width=True,
            hide_index=True,
        )

        # Charts
        if len(candle) >= 2:
            st.subheader('Trends Over Time')
            chart_data = candle.sort_values('timestamp').copy()

            tab1, tab2 = st.tabs(['Predicted / Inverted', 'Tokens Processed'])
            with tab1:
                st.bar_chart(chart_data.set_index('timestamp')[['predicted', 'inverted_total']].tail(20))
            with tab2:
                st.line_chart(chart_data.set_index('timestamp')['tokens_processed'].tail(20))

        # Config used
        st.subheader('Current Config')
        if not candle.empty:
            cfg_cols = ['model', 'top_tokens', 'inversion_threshold']
            cfg = {c: candle.iloc[-1].get(c, '—') for c in cfg_cols}
            for k, v in cfg.items():
                st.text(f'  {k}: {v}')

# ── A/B Tests ─────────────────────────────────────────────────────────────────

elif page == '🔀 A/B Tests':
    st.title('🔀 A/B Test Results')
    st.caption('Variant assignment and outcome tracking')

    ab = load_ab_tests()

    if ab.empty:
        st.info('No A/B test events yet — `record_ab_outcome()` needs to be called from trading code')
        st.code('from hermes_ab_utils import record_ab_outcome\\nrecord_ab_outcome("my_test", "variant_a", "win", metric_value=1.5)', language='python')
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            n_tests = ab['test_name'].nunique() if 'test_name' in ab else 0
            st.metric('Unique tests', n_tests)
        with col2:
            total = len(ab)
            st.metric('Total events', total)
        with col3:
            if 'outcome' in ab.columns:
                wins = (ab['outcome'] == 'win').sum()
                wr = wins / total * 100 if total > 0 else 0
                st.metric('Win rate', f'{wr:.1f}%')

        st.divider()

        # By test
        if 'test_name' in ab.columns:
            st.subheader('By Test')
            test_summary = ab.groupby('test_name').agg(
                events=('outcome', 'count') if 'outcome' in ab else ('test_name', 'count'),
                wins=('outcome', lambda x: (x == 'win').sum()) if 'outcome' in ab else ('test_name', 'count'),
            ).reset_index()
            if 'wins' in test_summary.columns and 'events' in test_summary.columns:
                test_summary['win_rate'] = (test_summary['wins'] / test_summary['events'] * 100).round(1)
                test_summary.columns = ['test_name', 'events', 'wins', 'win_rate%']
            st.dataframe(test_summary, use_container_width=True, hide_index=True)

        # Full log
        st.subheader('Event Log')
        display_cols = ['timestamp', 'test_name', 'variant', 'outcome', 'metric_value']
        available = [c for c in display_cols if c in ab.columns]
        st.dataframe(
            ab[available].sort_values('timestamp', ascending=False).tail(100),
            use_container_width=True,
            hide_index=True,
        )

        # Variant comparison chart
        if 'variant' in ab.columns and 'outcome' in ab.columns:
            st.subheader('Variant Win Rate Comparison')
            var_stats = ab.groupby('variant').agg(
                total=('outcome', 'count'),
                wins=('outcome', lambda x: (x == 'win').sum()),
            ).reset_index()
            var_stats['win_rate'] = (var_stats['wins'] / var_stats['total'] * 100).round(1)
            st.bar_chart(var_stats.set_index('variant')['win_rate'])

# ── ai_decider ────────────────────────────────────────────────────────────────

elif page == '🎯 ai_decider':
    st.title('🎯 ai_decider Decision Audit')
    st.caption('Every hot-set decision — why the winner won')

    decisions = load_decisions()

    if decisions.empty:
        st.info('No decisions yet — ai_decider runs continuously, data flows after each decision cycle')
    else:
        decisions['timestamp'] = pd.to_datetime(decisions['timestamp'])

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric('Total decisions', len(decisions))
        with col2:
            approved = (decisions['decision'] == 'HOT_APPROVED').sum() if 'decision' in decisions else 0
            st.metric('HOT_APPROVED', approved)
        with col3:
            skipped = (decisions['decision'] == 'SKIPPED').sum() if 'decision' in decisions else 0
            st.metric('SKIPPED', skipped)
        with col4:
            pattern = (decisions['is_pattern'] == True).sum() if 'is_pattern' in decisions else 0
            st.metric('Pattern signals', pattern)

        st.divider()

        # Decision breakdown
        if 'decision' in decisions.columns:
            col_pie, col_bar = st.columns([1, 2])
            with col_pie:
                st.subheader('Decision Types')
                decision_counts = decisions['decision'].value_counts()
                st.dataframe(decision_counts.rename('count'), use_container_width=True)
            with col_bar:
                st.subheader('Decisions Over Time')
                decisions_ts = decisions.set_index('timestamp').sort_index()
                # decision count per time unit — no unstack needed for a single series
                st.line_chart(decisions_ts['decision'].value_counts().tail(50))

        # Regime breakdown
        if 'regime' in decisions.columns:
            st.subheader('Regime Distribution')
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                st.dataframe(decisions['regime'].value_counts().rename('count'), use_container_width=True)
            with col_r2:
                regime_decision = pd.crosstab(decisions['regime'], decisions['decision']) if 'decision' in decisions.columns else pd.DataFrame()
                st.dataframe(regime_decision, use_container_width=True)

        # Speed vs score
        if {'speed_percentile', 'top_score'}.issubset(decisions.columns):
            st.subheader('Speed Percentile vs Score')
            st.scatter_chart(decisions[['speed_percentile', 'top_score', 'top_token']].dropna().set_index('top_token'))

        # Full decision log
        st.divider()
        st.subheader('Decision Log (newest first)')
        display_cols = ['timestamp', 'top_token', 'direction', 'decision', 'top_score', 'regime', 'speed_percentile', 'reason']
        available = [c for c in display_cols if c in decisions.columns]
        st.dataframe(
            decisions[available].sort_values('timestamp', ascending=False).head(100),
            use_container_width=True,
            hide_index=True,
        )

        # Most common winners
        if 'top_token' in decisions.columns:
            st.subheader('Most Selected Tokens')
            st.dataframe(
                decisions['top_token'].value_counts().head(20).rename('count'),
                use_container_width=True,
            )

# ── Signal Stats ─────────────────────────────────────────────────────────────

elif page == '📈 Signal Stats':
    st.title('📈 Signal Win Rate Stats')
    st.caption('From signals_hermes_runtime.db — live calibration data')

    stats = load_signal_stats()

    if stats.empty:
        st.info('No signal_outcomes data yet — trades need to close first')
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.metric('Signal types tracked', len(stats))
        with col2:
            total_trades = stats['n'].sum()
            total_wins = stats['wins'].sum()
            overall_wr = total_wins / total_trades * 100 if total_trades > 0 else 0
            st.metric('Overall win rate', f'{overall_wr:.1f}%')

        st.divider()

        st.subheader('By Signal Type')
        st.dataframe(
            stats.sort_values('n', ascending=False),
            use_container_width=True,
            hide_index=True,
        )

        # Win rate bar chart
        st.subheader('Win Rate by Signal Type')
        chart_data = stats.sort_values('wr', ascending=False).set_index('signal_type')['wr']
        st.bar_chart(chart_data)

        # PnL by signal type
        if 'avg_pnl' in stats.columns:
            st.subheader('Avg PnL % by Signal Type')
            pnl_data = stats.sort_values('avg_pnl', ascending=False).set_index('signal_type')['avg_pnl']
            st.bar_chart(pnl_data)

        # WR thresholds visualization
        st.divider()
        st.subheader('Calibration Status')
        def wr_status(wr):
            if wr is None or pd.isna(wr): return '🟡 No data'
            if wr >= 55: return '🟢 Boost (1.5×)'
            if wr >= 45: return '🟢 Keep (1.25×)'
            if wr >= 40: return '🟠 Reduce (0.75×)'
            return '🔴 Disabled (0×)'
        stats['calibration'] = stats['wr'].apply(wr_status)
        st.dataframe(
            stats[['signal_type', 'n', 'wr', 'avg_pnl', 'calibration']].sort_values('n', ascending=False),
            use_container_width=True,
            hide_index=True,
        )

        st.caption('Calibration rules: WR≥55%→1.5× | WR 45-55%→1.25× | WR 40-45%→0.75× | WR<40%→disabled (0×)')

# ── Footer ────────────────────────────────────────────────────────────────────

st.divider()
st.caption(
    'Hermes Local ML Dashboard | Data: /root/.hermes/wandb-local/ | '
    'Refreshes every 10s | No internet required'
)

#!/usr/bin/env python3
"""
pump_flow_engine.py — Capital Rotation Flow Chain Engine

Tracks how capital rotates through the market:
  BTC → HYPE → Large Caps → Mid Caps → Small Caps → (back to BTC)

Uses:
  - correlations.db token_chains (4200+ pairs, lift/WR/confidence)
  - hebbian associative_memory trade_log (4400+ trades with timestamps)
  - Live price data (price_history, latest_prices)
  - Signal outcomes (10000+ signals with timestamps)

Outputs:
  - pump_flow_state.json — current rotation phase, active flow, recommendations
  - Feeds pump_flow.html dashboard
  - Can be queried by trade system for decision-making

Architecture:
  1. FLOW GRAPH: Build directed graph from correlations.db + trade_log
     Nodes = tokens, Edges = (chain strength, direction, WR, lift)
  2. PHASE DETECTION: Monitor BTC/HYPE/ETH price velocity to determine
     rotation phase (accumulation → markup → distribution → markdown)
  3. CAPITAL FLOW TRACKING: When BTC pumps, watch for "spillover" into
     HYPE, then into correlated alts. Track the cascade.
  4. RECOMMENDATION ENGINE: Given current phase + active spillovers,
     suggest which tokens are next in line.
"""

import os, sys, json, sqlite3, time, math
from datetime import datetime, timedelta, timezone
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, WWW_DATA

# ── Paths ─────────────────────────────────────────────────────────────────────
CORRELATIONS_DB = "/root/.hermes/brain/correlations.db"
HEBBIAN_DB = "/root/.hermes/brain/associative_memory.db"
RUNTIME_DB = os.path.join(HERMES_DATA, "signals_hermes_runtime.db")
STATIC_DB = os.path.join(HERMES_DATA, "signals_hermes.db")
OUTPUT_FILE = os.path.join(WWW_DATA, "pump_flow_data.json")
STATE_FILE = os.path.join(HERMES_DATA, "pump_flow_state.json")

# ── Token Tiers ───────────────────────────────────────────────────────────────
# Capital flows from BTC downward through tiers. Higher tier = earlier in flow.
TOKEN_TIERS = {
    # Tier 0: Market bellwether
    'BTC': 0,
    # Tier 1: Ecosystem leaders
    'HYPE': 1, 'ETH': 1, 'SOL': 1,
    # Tier 2: Large caps (high volume, high correlation)
    'DOGE': 2, 'XRP': 2, 'ADA': 2, 'AVAX': 2, 'LINK': 2, 'UNI': 2,
    'AAVE': 2, 'LDO': 2, 'FET': 2, 'MORPHO': 2, 'ONDO': 2,
    # Tier 3: Mid caps
    'ASTER': 3, 'SKR': 3, 'BSV': 3, 'BLUR': 3, 'BCH': 3, 'CRV': 3,
    'ETC': 3, 'TAO': 3, 'PEOPLE': 3, 'MON': 3, 'MERL': 3, 'WLD': 3,
    'GRIFFAIN': 3, 'KAS': 3, 'VINE': 3, 'AXS': 3, 'UMA': 3,
    # Tier 4: Small caps / meme
    '2Z': 4, '0G': 4, 'CHIP': 4, 'APEX': 4, 'AVNT': 4, 'MET': 4,
    'NIL': 4, 'SKY': 4, 'DASH': 4, 'CAKE': 4, 'NXPC': 4, 'ZK': 4,
    'ME': 4, 'W': 4, 'JUP': 4,
}

# Tier names for display
TIER_NAMES = {
    0: 'BTC',
    1: 'Ecosystem Leaders',
    2: 'Large Caps',
    3: 'Mid Caps',
    4: 'Small Caps / Meme',
}

# Minimum chain strength to include in flow graph
MIN_CHAIN_CO_FIRES = 3
MIN_CHAIN_LIFT = 1.1


def _now():
    return datetime.now(timezone.utc)


def _ts():
    return _now().isoformat()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. FLOW GRAPH — Build directed capital flow graph from chain data
# ═══════════════════════════════════════════════════════════════════════════════

def build_flow_graph(min_co_fires=MIN_CHAIN_CO_FIRES, min_lift=MIN_CHAIN_LIFT):
    """
    Build directed flow graph from correlations.db token_chains.
    
    Returns:
        {
            'nodes': {token: {tier, name, total_trades, wr}},
            'edges': [{from, to, strength, wr, lift, conf, avg_pnl, co_fires}],
            'tier_flows': {tier_a: {tier_b: {total_strength, edges, avg_wr}}},
        }
    """
    if not os.path.exists(CORRELATIONS_DB):
        return {'nodes': {}, 'edges': [], 'tier_flows': {}}

    conn = sqlite3.connect(f"file:{CORRELATIONS_DB}?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    
    # Get all qualifying chains
    chains = conn.execute("""
        SELECT token_a, token_b, co_fires, win_rate, lift, confidence, 
               avg_pnl_after_a, b_total
        FROM token_chains
        WHERE co_fires >= ? AND lift >= ?
        ORDER BY confidence * lift DESC
    """, (min_co_fires, min_lift)).fetchall()
    conn.close()
    
    # Build nodes and edges
    nodes = {}
    edges = []
    
    for chain in chains:
        a, b = chain['token_a'], chain['token_b']
        
        # Ensure nodes exist
        for token in (a, b):
            if token not in nodes:
                tier = TOKEN_TIERS.get(token, 4)  # default to tier 4 for unknown tokens
                nodes[token] = {
                    'tier': tier,
                    'tier_name': TIER_NAMES.get(tier, 'Unknown'),
                    'total_trades': chain['b_total'] if token == b else 0,
                    'chain_count': 0,
                }
            nodes[token]['chain_count'] += 1
        
        # Edge = directed flow from A → B
        # Strength = co_fires × lift (normalized)
        strength = chain['co_fires'] * chain['lift']
        
        edges.append({
            'from': a,
            'to': b,
            'strength': round(strength, 2),
            'wr': round(chain['win_rate'], 3),
            'lift': round(chain['lift'], 2),
            'conf': round(chain['confidence'], 3),
            'avg_pnl': round(chain['avg_pnl_after_a'], 4),
            'co_fires': chain['co_fires'],
            'from_tier': TOKEN_TIERS.get(a, 4),
            'to_tier': TOKEN_TIERS.get(b, 4),
        })
    
    # Aggregate tier-to-tier flows
    tier_flows = defaultdict(lambda: {'total_strength': 0, 'edges': 0, 'avg_wr': 0.0, 'total_wr': 0.0})
    for edge in edges:
        ft, tt = edge['from_tier'], edge['to_tier']
        key = f"{ft}→{tt}"
        tier_flows[key]['total_strength'] += edge['strength']
        tier_flows[key]['edges'] += 1
        tier_flows[key]['total_wr'] += edge['wr']
    
    # Average WR per tier flow
    for key in tier_flows:
        if tier_flows[key]['edges'] > 0:
            tier_flows[key]['avg_wr'] = round(
                tier_flows[key]['total_wr'] / tier_flows[key]['edges'], 3
            )
        tier_flows[key]['total_strength'] = round(tier_flows[key]['total_strength'], 2)
    
    return {
        'nodes': nodes,
        'edges': edges[:200],  # top 200 edges for performance
        'tier_flows': dict(tier_flows),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 2. PHASE DETECTION — Determine current capital rotation phase
# ═══════════════════════════════════════════════════════════════════════════════

def get_price_velocity(token, lookback_minutes=30):
    """
    Compute price velocity (% change) over the lookback window.
    Returns (velocity_pct, current_price, prev_price) or None.
    """
    try:
        conn = sqlite3.connect(f"file:{STATIC_DB}?mode=ro", uri=True, timeout=5)
        cutoff = (time.time() - lookback_minutes * 60)
        rows = conn.execute("""
            SELECT price FROM price_history
            WHERE token = ? AND timestamp > ?
            ORDER BY timestamp ASC
        """, (token.upper(), cutoff)).fetchall()
        conn.close()
        
        if len(rows) < 2:
            return None
        
        first_price = rows[0][0]
        last_price = rows[-1][0]
        if first_price <= 0:
            return None
        
        velocity = (last_price - first_price) / first_price * 100
        return (round(velocity, 4), last_price, first_price)
    except Exception:
        return None


def detect_phase():
    """
    Detect current capital rotation phase by monitoring BTC, HYPE, ETH velocities.
    
    Phases:
      ACCUMULATION:  BTC choppy, low velocity → money parking in BTC
      MARKUP:        BTC pumping → capital about to flow outward
      DISTRIBUTION:  BTC peaking, alts pumping → capital rotating to alts
      MARKDOWN:      BTC dumping → capital fleeing back to BTC/stables
      
    Returns:
        {
            'phase': str,
            'confidence': float (0-1),
            'btc_velocity': float,
            'hype_velocity': float,
            'eth_velocity': float,
            'alt_signal': str,  # 'flowing_out', 'flowing_in', 'neutral'
            'phase_duration_estimate': str,
        }
    """
    # Get velocities at different timeframes
    btc_15m = get_price_velocity('BTC', 15)
    btc_30m = get_price_velocity('BTC', 30)
    btc_1h = get_price_velocity('BTC', 60)
    
    hype_15m = get_price_velocity('HYPE', 15)
    hype_30m = get_price_velocity('HYPE', 30)
    
    eth_15m = get_price_velocity('ETH', 15)
    eth_30m_data = get_price_velocity('ETH', 30)
    eth_30m = eth_30m_data[0] if eth_30m_data else 0
    
    if not btc_15m:
        return {
            'phase': 'UNKNOWN',
            'confidence': 0,
            'btc_velocity': 0, 'hype_velocity': 0, 'eth_velocity': 0,
            'alt_signal': 'neutral',
            'reason': 'No BTC price data',
        }
    
    btc_v15 = btc_15m[0]
    btc_v30 = btc_30m[0] if btc_30m else 0
    btc_v1h = btc_1h[0] if btc_1h else 0
    hype_v15 = hype_15m[0] if hype_15m else 0
    hype_v30 = hype_30m[0] if hype_30m else 0
    eth_v15 = eth_15m[0] if eth_15m else 0
    eth_v30 = eth_30m if eth_30m else 0
    
    # Phase detection logic
    phase = 'UNKNOWN'
    confidence = 0.0
    alt_signal = 'neutral'
    reason = ''
    
    # BTC velocity thresholds
    BTC_PUMP_THRESHOLD = 0.3    # > 0.3% in 15m = significant
    BTC_DUMP_THRESHOLD = -0.3   # < -0.3% in 15m = significant
    BTC_CHOP_THRESHOLD = 0.1    # |v| < 0.1% = choppy
    
    # BTC trending up (15m and 30m aligned)
    btc_bullish = btc_v15 > BTC_CHOP_THRESHOLD and btc_v30 > 0
    btc_bearish = btc_v15 < -BTC_CHOP_THRESHOLD and btc_v30 < 0
    btc_pumping = btc_v15 > BTC_PUMP_THRESHOLD
    btc_dumping = btc_v15 < BTC_DUMP_THRESHOLD
    btc_choppy = abs(btc_v15) < BTC_CHOP_THRESHOLD
    
    # HYPE/ETH deviation from BTC (spillover detection)
    hype_dev = hype_v15 - btc_v15  # positive = HYPE outperforming BTC
    eth_dev = eth_v15 - btc_v15
    
    if btc_pumping:
        # BTC is pumping — check if alts are also pumping or lagging
        if hype_v15 > 0 and hype_v15 > btc_v15:
            # Alts outperforming BTC = DISTRIBUTION phase
            phase = 'DISTRIBUTION'
            alt_signal = 'flowing_out'
            confidence = min(1.0, 0.6 + abs(hype_dev) * 2)
            reason = f"BTC pumping +{btc_v15:.2f}% but HYPE outperforming +{hype_v15:.2f}%"
        else:
            # BTC pumping, alts lagging = MARKUP (capital still in BTC)
            phase = 'MARKUP'
            alt_signal = 'neutral'
            confidence = min(1.0, 0.5 + abs(btc_v15) * 3)
            reason = f"BTC pumping +{btc_v15:.2f}%, alts lagging"
    
    elif btc_dumping:
        # BTC dumping — check if alts are dumping harder or holding
        if hype_v15 < btc_v15:
            # Alts dumping harder = MARKDOWN
            phase = 'MARKDOWN'
            alt_signal = 'flowing_in'
            confidence = min(1.0, 0.6 + abs(btc_v15 - hype_v15) * 2)
            reason = f"BTC dumping {btc_v15:.2f}%, alts worse {hype_v15:.2f}%"
        else:
            # BTC dumping but alts holding = early DISTRIBUTION
            phase = 'DISTRIBUTION'
            alt_signal = 'flowing_out'
            confidence = min(1.0, 0.5 + abs(eth_dev) * 2)
            reason = f"BTC dumping {btc_v15:.2f}%, alts resilient"
    
    elif btc_choppy:
        # BTC choppy — check for divergence
        if abs(hype_v15) > 0.2:
            # HYPE moving while BTC chops = early rotation signal
            if hype_v15 > 0:
                phase = 'DISTRIBUTION'
                alt_signal = 'flowing_out'
                reason = f"BTC choppy, HYPE pumping +{hype_v15:.2f}%"
            else:
                phase = 'MARKDOWN'
                alt_signal = 'flowing_in'
                reason = f"BTC choppy, HYPE dumping {hype_v15:.2f}%"
            confidence = 0.4 + abs(hype_v15) * 2
        else:
            # Everything choppy = ACCUMULATION
            phase = 'ACCUMULATION'
            alt_signal = 'neutral'
            confidence = 0.5
            reason = f"BTC choppy {btc_v15:+.2f}%, no clear direction"
    
    else:
        # Moderate BTC move — check alignment
        if btc_bullish:
            phase = 'MARKUP'
            alt_signal = 'neutral'
            confidence = 0.4
            reason = f"BTC mildly bullish {btc_v15:+.2f}%"
        elif btc_bearish:
            phase = 'MARKDOWN'
            alt_signal = 'flowing_in'
            confidence = 0.4
            reason = f"BTC mildly bearish {btc_v15:+.2f}%"
        else:
            phase = 'ACCUMULATION'
            alt_signal = 'neutral'
            confidence = 0.3
            reason = f"BTC unclear {btc_v15:+.2f}%"
    
    return {
        'phase': phase,
        'confidence': round(confidence, 3),
        'btc_velocity': round(btc_v15, 4),
        'btc_velocity_30m': round(btc_v30, 4),
        'btc_velocity_1h': round(btc_v1h, 4),
        'hype_velocity': round(hype_v15, 4),
        'hype_velocity_30m': round(hype_v30, 4),
        'eth_velocity': round(eth_v15, 4),
        'eth_velocity_30m': round(eth_30m, 4) if eth_30m else 0,
        'alt_signal': alt_signal,
        'reason': reason,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 3. ACTIVE FLOW DETECTION — Track real-time capital spillovers
# ═══════════════════════════════════════════════════════════════════════════════

def detect_active_flows():
    """
    Detect which tokens are currently experiencing capital inflow/outflow.
    
    Uses:
    - Recent signal_outcomes (last 2h) for trade activity
    - Recent signal history (last 30m) for emerging signals
    - Price velocity for all tokens
    
    Returns list of active flows:
        [{token, tier, direction, velocity, signal_count, flow_score}]
    """
    flows = []
    
    # 1. Get price velocities for all tokens with recent prices
    try:
        conn = sqlite3.connect(f"file:{STATIC_DB}?mode=ro", uri=True, timeout=5)
        # Get tokens with recent price data
        cutoff_5m = time.time() - 300
        tokens_with_prices = conn.execute("""
            SELECT DISTINCT token FROM price_history WHERE timestamp > ?
        """, (cutoff_5m,)).fetchall()
        conn.close()
        
        token_list = [r[0] for r in tokens_with_prices]
    except Exception:
        token_list = []
    
    for token in token_list[:50]:  # limit to 50 for performance
        vel = get_price_velocity(token, 15)
        if vel is None:
            continue
        
        velocity, current_price, _ = vel
        tier = TOKEN_TIERS.get(token, 4)
        
        # 2. Count recent signals for this token
        signal_count = 0
        try:
            conn = sqlite3.connect(f"file:{RUNTIME_DB}?mode=ro", uri=True, timeout=5)
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
            signal_count = conn.execute("""
                SELECT COUNT(*) FROM signal_outcomes
                WHERE token = ? AND created_at > ?
            """, (token, cutoff)).fetchone()[0]
            conn.close()
        except Exception:
            pass
        
        # 3. Flow score = weighted combination of velocity + signal activity
        # Positive = capital flowing IN, negative = flowing OUT
        flow_score = velocity * 10 + signal_count * 2
        
        if abs(velocity) > 0.1 or signal_count > 2:
            direction = 'IN' if velocity > 0 else 'OUT'
            flows.append({
                'token': token,
                'tier': tier,
                'tier_name': TIER_NAMES.get(tier, 'Unknown'),
                'direction': direction,
                'velocity_15m': round(velocity, 4),
                'current_price': current_price,
                'signal_count_2h': signal_count,
                'flow_score': round(flow_score, 2),
            })
    
    # Sort by absolute flow score (strongest flows first)
    flows.sort(key=lambda x: abs(x['flow_score']), reverse=True)
    return flows[:30]


# ═══════════════════════════════════════════════════════════════════════════════
# 4. RECOMMENDATION ENGINE — Suggest next tokens based on phase + flows
# ═══════════════════════════════════════════════════════════════════════════════

def generate_recommendations(phase_data, active_flows, flow_graph):
    """
    Given current phase and active flows, recommend which tokens to watch.
    
    Logic:
      DISTRIBUTION: Capital flowing from BTC/HYPE → alts. Recommend mid/small caps
                    with strong chain links to recently-pumped leaders.
      MARKDOWN:     Capital fleeing alts → BTC. Recommend avoiding alts, watching BTC.
      MARKUP:       BTC pumping, alts not yet moving. Watch for early spillovers.
      ACCUMULATION: Everything choppy. Low conviction — recommend patience.
    
    Returns:
        [{token, tier, reason, confidence, suggested_direction, chain_evidence}]
    """
    recommendations = []
    
    if phase_data['phase'] == 'DISTRIBUTION':
        # Capital flowing to alts — find which alts are likely next
        # Look at active flows: tokens with positive velocity + strong chain links
        inflow_tokens = [f for f in active_flows if f['direction'] == 'IN' and f['tier'] >= 2]
        
        for flow in inflow_tokens[:10]:
            token = flow['token']
            # Check chain links — does this token have strong followers?
            chain_evidence = []
            for edge in flow_graph.get('edges', []):
                if edge['from'] == token and edge['lift'] >= 1.3:
                    chain_evidence.append({
                        'follower': edge['to'],
                        'lift': edge['lift'],
                        'wr': edge['wr'],
                    })
                if edge['to'] == token and edge['lift'] >= 1.3:
                    chain_evidence.append({
                        'leader': edge['from'],
                        'lift': edge['lift'],
                        'wr': edge['wr'],
                    })
            
            conf = min(0.9, 0.4 + flow['velocity_15m'] * 2 + flow['signal_count_2h'] * 0.05)
            
            recommendations.append({
                'token': token,
                'tier': flow['tier'],
                'tier_name': flow['tier_name'],
                'reason': f"Capital inflow detected: +{flow['velocity_15m']:.2f}% velocity, {flow['signal_count_2h']} recent signals",
                'confidence': round(conf, 3),
                'suggested_direction': 'LONG',
                'chain_evidence': chain_evidence[:3],
                'flow_score': flow['flow_score'],
            })
    
    elif phase_data['phase'] == 'MARKDOWN':
        # Capital fleeing — recommend watching BTC as safe haven
        recommendations.append({
            'token': 'BTC',
            'tier': 0,
            'tier_name': 'BTC',
            'reason': f"Market markdown: BTC {phase_data['btc_velocity']:+.2f}%. Capital flowing to safety.",
            'confidence': round(min(0.7, 0.3 + abs(phase_data['btc_velocity']) * 2), 3),
            'suggested_direction': 'LONG' if phase_data['btc_velocity'] > 0 else 'SHORT',
            'chain_evidence': [],
            'flow_score': 0,
        })
        
        # Also flag tokens with strong chain links to BTC that are dumping
        for edge in flow_graph.get('edges', []):
            if edge['from'] == 'BTC' and edge['lift'] >= 1.5:
                recommendations.append({
                    'token': edge['to'],
                    'tier': TOKEN_TIERS.get(edge['to'], 4),
                    'tier_name': TIER_NAMES.get(TOKEN_TIERS.get(edge['to'], 4), 'Unknown'),
                    'reason': f"BTC chain follower ({edge['lift']:.1f}x lift) — likely to follow BTC down",
                    'confidence': round(edge['conf'], 3),
                    'suggested_direction': 'SHORT',
                    'chain_evidence': [{'leader': 'BTC', 'lift': edge['lift'], 'wr': edge['wr']}],
                    'flow_score': -abs(edge['strength']),
                })
    
    elif phase_data['phase'] == 'MARKUP':
        # BTC pumping — watch for early spillovers into HYPE then alts
        # Recommend tokens with strong BTC chain links
        btc_followers = []
        for edge in flow_graph.get('edges', []):
            if edge['from'] == 'BTC' and edge['lift'] >= 1.2 and edge['wr'] > 0.5:
                btc_followers.append(edge)
        
        btc_followers.sort(key=lambda x: x['lift'] * x['wr'], reverse=True)
        
        for edge in btc_followers[:5]:
            recommendations.append({
                'token': edge['to'],
                'tier': TOKEN_TIERS.get(edge['to'], 4),
                'tier_name': TIER_NAMES.get(TOKEN_TIERS.get(edge['to'], 4), 'Unknown'),
                'reason': f"BTC markup — watch for spillover ({edge['lift']:.1f}x lift from BTC, {edge['wr']:.0%} WR)",
                'confidence': round(edge['conf'] * 0.8, 3),  # lower confidence, waiting for spillover
                'suggested_direction': 'LONG',
                'chain_evidence': [{'leader': 'BTC', 'lift': edge['lift'], 'wr': edge['wr']}],
                'flow_score': edge['strength'] * 0.5,
            })
    
    elif phase_data['phase'] == 'ACCUMULATION':
        # Choppy — low conviction, recommend patience
        recommendations.append({
            'token': 'BTC',
            'tier': 0,
            'tier_name': 'BTC',
            'reason': "Accumulation phase — choppy markets. Low conviction, recommend patience.",
            'confidence': 0.2,
            'suggested_direction': 'WAIT',
            'chain_evidence': [],
            'flow_score': 0,
        })
    
    # Sort by confidence
    recommendations.sort(key=lambda x: x['confidence'], reverse=True)
    return recommendations[:15]


# ═══════════════════════════════════════════════════════════════════════════════
# 5. MAIN — Build complete pump flow state
# ═══════════════════════════════════════════════════════════════════════════════

def build_pump_flow_state():
    """
    Build complete pump flow state — the main entry point.
    
    Returns dict with:
        - phase: current rotation phase
        - flow_graph: directed graph of token chains
        - active_flows: tokens with current capital movement
        - recommendations: what to trade next
        - stats: engine health
    """
    print(f"[pump-flow] Building state at {_ts()}")
    
    # 1. Build flow graph from historical chains
    flow_graph = build_flow_graph()
    print(f"  Flow graph: {len(flow_graph['nodes'])} nodes, {len(flow_graph['edges'])} edges")
    
    # 2. Detect current phase
    phase_data = detect_phase()
    print(f"  Phase: {phase_data['phase']} (conf={phase_data['confidence']:.2f}) — {phase_data['reason']}")
    
    # 3. Detect active flows
    active_flows = detect_active_flows()
    print(f"  Active flows: {len(active_flows)} tokens with movement")
    
    # 4. Generate recommendations
    recommendations = generate_recommendations(phase_data, active_flows, flow_graph)
    print(f"  Recommendations: {len(recommendations)}")
    
    # 5. Stats
    stats = {
        'total_nodes': len(flow_graph['nodes']),
        'total_edges': len(flow_graph['edges']),
        'tier_flows': flow_graph['tier_flows'],
        'active_flow_count': len(active_flows),
        'recommendation_count': len(recommendations),
        'generated_at': _ts(),
    }
    
    state = {
        'phase': phase_data,
        'flow_graph': flow_graph,
        'active_flows': active_flows,
        'recommendations': recommendations,
        'stats': stats,
    }
    
    return state


def save_state(state):
    """Save pump flow state to JSON files."""
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    
    # Write full state for API
    tmp = OUTPUT_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, OUTPUT_FILE)
    
    # Write compact state for trade system consumption
    compact = {
        'phase': state['phase']['phase'],
        'phase_confidence': state['phase']['confidence'],
        'alt_signal': state['phase']['alt_signal'],
        'recommendations': [
            {
                'token': r['token'],
                'direction': r['suggested_direction'],
                'confidence': r['confidence'],
                'reason': r['reason'],
            }
            for r in state['recommendations']
        ],
        'updated_at': state['stats']['generated_at'],
    }
    tmp = STATE_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(compact, f, indent=2)
    os.replace(tmp, STATE_FILE)
    
    print(f"[pump-flow] Saved to {OUTPUT_FILE} and {STATE_FILE}")


def run():
    """Main entry point — build and save state."""
    state = build_pump_flow_state()
    save_state(state)
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Pump Flow Chain Engine')
    parser.add_argument('--phase', action='store_true', help='Show current phase only')
    parser.add_argument('--flows', action='store_true', help='Show active flows only')
    parser.add_argument('--recommend', action='store_true', help='Show recommendations only')
    parser.add_argument('--graph', action='store_true', help='Show flow graph stats')
    parser.add_argument('--run', action='store_true', help='Full run: build and save state')
    args = parser.parse_args()
    
    if args.phase:
        phase = detect_phase()
        print(json.dumps(phase, indent=2))
    elif args.flows:
        flows = detect_active_flows()
        for f in flows:
            direction = '🟢 IN ' if f['direction'] == 'IN' else '🔴 OUT'
            print(f"  {direction} {f['token']:10s} tier={f['tier']} vel={f['velocity_15m']:+.3f}% "
                  f"signals={f['signal_count_2h']} score={f['flow_score']:+.1f}")
    elif args.recommend:
        state = build_pump_flow_state()
        for r in state['recommendations']:
            print(f"  {r['suggested_direction']:6s} {r['token']:10s} conf={r['confidence']:.2f} "
                  f"tier={r['tier_name']} — {r['reason']}")
    elif args.graph:
        graph = build_flow_graph()
        print(f"Nodes: {len(graph['nodes'])}")
        print(f"Edges: {len(graph['edges'])}")
        print(f"\nTier flows:")
        for key, val in sorted(graph['tier_flows'].items()):
            print(f"  {key}: strength={val['total_strength']:.1f} edges={val['edges']} wr={val['avg_wr']:.0%}")
    else:
        # Full run
        state = run()
        print(f"\n=== Pump Flow State ===")
        print(f"Phase: {state['phase']['phase']} ({state['phase']['confidence']:.0%})")
        print(f"Reason: {state['phase']['reason']}")
        print(f"Alt signal: {state['phase']['alt_signal']}")
        print(f"\nActive flows: {len(state['active_flows'])}")
        for f in state['active_flows'][:10]:
            direction = '🟢 IN ' if f['direction'] == 'IN' else '🔴 OUT'
            print(f"  {direction} {f['token']:10s} vel={f['velocity_15m']:+.3f}% "
                  f"signals={f['signal_count_2h']}")
        print(f"\nRecommendations: {len(state['recommendations'])}")
        for r in state['recommendations'][:10]:
            print(f"  {r['suggested_direction']:6s} {r['token']:10s} conf={r['confidence']:.2f} "
                  f"— {r['reason']}")

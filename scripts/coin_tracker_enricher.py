#!/usr/bin/env python3
"""
coin_tracker_enricher.py — Enriches coin_tracker_data.json with weather station insights.

Adds to each coin:
  - regime_class: reef | sandbar | deep (from signal outcome analysis)
  - signal_winrate: win rate of signals for this token
  - signal_pnl: total PnL from signals for this token
  - signal_trades: number of trades for this token
  - weather_tide: current tide direction (24h)
  - weather_sea: current sea state

Run after coin_tracker_api.py and weather_station_api.py.
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))

WWW_HTML = '/var/www/html'
COIN_DATA = os.path.join(WWW_HTML, 'coin_tracker_data.json')
WEATHER_DATA = os.path.join('/var/www/hermes/data', 'weather_station.json')

def enrich():
    # Load weather data
    weather = {}
    if os.path.exists(WEATHER_DATA):
        with open(WEATHER_DATA) as f:
            weather = json.load(f)
    else:
        print('[enricher] No weather_station.json found, skipping weather enrichment')

    # Build token lookup from weather data
    token_data = {}
    for regime_type in ['reef', 'sandbar', 'deep']:
        for t in weather.get('tokens', {}).get(regime_type, []):
            token_data[t['token']] = {
                'regime_class': regime_type,
                'signal_winrate': t.get('winrate'),
                'signal_pnl': t.get('total_pnl'),
                'signal_trades': t.get('trades'),
            }

    # Also build from signal performance data
    signal_lookup = {}
    for s in weather.get('signals', []):
        # signals are keyed by type, not token — skip for now
        pass

    # Load coin tracker data
    if not os.path.exists(COIN_DATA):
        print(f'[enricher] {COIN_DATA} not found')
        return

    with open(COIN_DATA) as f:
        data = json.load(f)

    # Weather context
    tide = weather.get('tide', {}).get('24h', {})
    sea = weather.get('sea_state', {})
    tide_dir = 'BEARISH' if tide.get('short_pct', 50) > 55 else 'BULLISH' if tide.get('long_pct', 50) > 55 else 'NEUTRAL'
    sea_winrate = sea.get('winrate', 0)

    enriched = 0
    for coin in data.get('coins', []):
        sym = coin['symbol']

        # Merge token data
        if sym in token_data:
            coin.update(token_data[sym])
            enriched += 1
        else:
            coin['regime_class'] = 'unknown'
            coin['signal_winrate'] = None
            coin['signal_pnl'] = None
            coin['signal_trades'] = None

        # Add weather context
        coin['weather_tide'] = tide_dir
        coin['weather_sea_winrate'] = sea_winrate

    # Add weather summary to top level
    data['weather'] = {
        'tide_24h': tide_dir,
        'sea_winrate': sea_winrate,
        'generated': weather.get('generated'),
    }

    # Count regimes
    regime_counts = {'reef': 0, 'sandbar': 0, 'deep': 0, 'unknown': 0}
    for c in data['coins']:
        rc = c.get('regime_class', 'unknown')
        regime_counts[rc] = regime_counts.get(rc, 0) + 1
    data['by_regime'] = regime_counts

    # Write back
    tmp = COIN_DATA + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(data, f)
    os.replace(tmp, COIN_DATA)

    print(f'[enricher] Enriched {enriched}/{len(data["coins"])} coins with weather data')
    print(f'[enricher] Regimes: {regime_counts}')

if __name__ == '__main__':
    enrich()

#!/usr/bin/env python3
"""
watchlist_server.py — write API for the Watchlist dashboard (T 2026-11-02).

Long-running localhost server (hermes-watchlist-server.service, port 3463,
nginx path /api/watchlist/) so the page can add/remove wallets itself:

  GET    /            -> {"wallets": {addr: {label, added}}, "n": int}
  GET    /health      -> {"ok": true}
  POST   /            body {"action":"add","address":..,"label":?..}
                    -> adds (validated, capped at WATCHLIST_MAX_WALLETS)
  POST   /            body {"action":"remove","address":..} -> removes
  DELETE /<address>   -> removes

Storage: data/watchlist.json via topdog_api._atomic_write (crash-safe).
Validation: Solana base58 only (no 0/O/I/l), 32-44 chars — a bad address
is rejected at the door instead of poisoning the dashboard for 60s cycles.
Bind is 127.0.0.1 only; nginx exposes just this path on the local dashboard.
"""
import json
import os
import re
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA
from hermes_constants import WATCHLIST_MAX_WALLETS
from topdog_api import _load_json, _atomic_write

WATCHLIST_FILE = os.path.join(HERMES_DATA, 'watchlist.json')
PORT = int(os.environ.get('WATCHLIST_API_PORT', '3463'))
BASE58 = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')


def _read_state():
    raw = _load_json(WATCHLIST_FILE, None)
    if not isinstance(raw, dict):
        raw = {}
    wallets = raw.get('wallets')
    if not isinstance(wallets, dict):
        wallets = {}
    clean = {}
    for a, v in wallets.items():
        if isinstance(a, str) and a:
            v = v if isinstance(v, dict) else {}
            clean[a] = {'label': str(v.get('label') or '')[:24],
                        'added': int(v.get('added') or 0)}
    return clean


def _write_state(wallets):
    _atomic_write(WATCHLIST_FILE, {'wallets': wallets,
                                   'updated': int(time.time())})


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"[watchlist_server] {self.address_string()} {fmt % args}")

    def _refresh_payload(self):
        """Run the api inline after every mutation so the page's stats panel
        updates in ~2-4s instead of waiting up to 60s for the timer.

        T 2026-11-02: "add/remove is not working" — the chips (direct server
        GET) moved instantly while the coin boxes/stats table lagged a full
        timer cycle, so a removed wallet still sat in the table for a minute.
        Best-effort: a refresh failure never fails the mutation itself.
        """
        try:
            import subprocess
            here = os.path.dirname(os.path.abspath(__file__))
            r = subprocess.run(
                [sys.executable, os.path.join(here, 'watchlist_api.py')],
                cwd=here, timeout=25, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"[watchlist_server] api refresh rc={r.returncode}: "
                      f"{(r.stderr or '')[-300:]}", file=sys.stderr)
        except Exception as e:
            print(f"[watchlist_server] api refresh error: "
                  f"{type(e).__name__}: {e}", file=sys.stderr)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/health':
            return self._send(200, {'ok': True})
        wallets = _read_state()
        return self._send(200, {'wallets': wallets, 'n': len(wallets),
                                'max': WATCHLIST_MAX_WALLETS})

    def do_DELETE(self):
        addr = urlparse(self.path).path.lstrip('/')
        return self._apply({'action': 'remove', 'address': addr})

    def do_POST(self):
        try:
            n = int(self.headers.get('Content-Length') or 0)
            raw = self.rfile.read(min(n, 8192)).decode(errors='replace')
            body = json.loads(raw) if raw else {}
            if not isinstance(body, dict):
                raise ValueError('body must be a JSON object')
        except Exception as e:
            return self._send(400, {'ok': False, 'error': f'bad body: {e}'})
        return self._apply(body)

    def _apply(self, body):
        action = str(body.get('action') or '')
        addr = str(body.get('address') or '').strip()
        try:
            if action == 'add':
                if not BASE58.match(addr):
                    return self._send(400, {'ok': False, 'error':
                        'not a Solana base58 address (32-44 chars, no 0/O/I/l)'})
                wallets = _read_state()
                if addr in wallets:
                    return self._send(200, {'ok': True, 'already': True,
                                            'n': len(wallets)})
                if len(wallets) >= WATCHLIST_MAX_WALLETS:
                    return self._send(409, {'ok': False, 'error':
                        f'watchlist full ({WATCHLIST_MAX_WALLETS} max) — '
                        'remove one first'})
                label = str(body.get('label') or '').strip()[:24]
                wallets[addr] = {'label': label, 'added': int(time.time())}
                _write_state(wallets)
                print(f"[watchlist_server] ADD {addr[:8]}… "
                      f"label={label!r} n={len(wallets)}")
                self._refresh_payload()
                return self._send(200, {'ok': True, 'n': len(wallets)})
            if action == 'remove':
                wallets = _read_state()
                if addr not in wallets:
                    return self._send(404, {'ok': False, 'error': 'not on list'})
                del wallets[addr]
                _write_state(wallets)
                print(f"[watchlist_server] REMOVE {addr[:8]}… "
                      f"n={len(wallets)}")
                self._refresh_payload()
                return self._send(200, {'ok': True, 'n': len(wallets)})
            return self._send(400, {'ok': False,
                                    'error': 'action must be add|remove'})
        except Exception as e:
            # never die on a request — report honestly
            print(f"[watchlist_server] ERROR {type(e).__name__}: {e}",
                  file=sys.stderr)
            return self._send(500, {'ok': False, 'error': f'{type(e).__name__}: {e}'})


def main():
    server = HTTPServer(('127.0.0.1', PORT), Handler)
    print(f"[watchlist_server] listening on 127.0.0.1:{PORT} "
          f"(file: {WATCHLIST_FILE})")
    server.serve_forever()


if __name__ == '__main__':
    main()

# OmniRoute debug — 2026-07-13

**TL;DR:** OmniRoute v3.8.46 on port 20128 looked "broken" (curl hung forever on `/v1/models`, `/v1/chat/completions`, `/`). Turned out to be a **12h-old wedged Node process**. A clean restart fixed it in 7 seconds. No code change needed.

## Symptoms reported
- Banner: `✔ OmniRoute is running! (started in 7.5s)` — looked healthy.
- `curl http://localhost:20128/v1/models` → **hangs 60+ seconds, no response**.
- Process and port both alive (`ps`, `ss` confirmed).

## Diagnostic ladder that pinned it (in order)

```bash
# 1. Process alive?  YES (PID 2675668, 12h17m uptime)
ps -p 2675668 -o pid,etime,cmd

# 2. Port listening?  YES (0.0.0.0:20128)
ss -tlnp 'sport = :20128'

# 3. TCP connect succeeds, HTTP request sent, then... silence
curl -v -m 5 http://127.0.0.1:20128/ 2>&1 | grep -E "Trying|Connected|timed out"
#   Trying 127.0.0.1:20128...
#   Connected to 127.0.0.1 (127.0.0.1) port 20128
#   > GET / HTTP/1.1
#   * Operation timed out after 5002 milliseconds with 0 bytes received

# 4. Unknown route probe — DISCRIMINATING STEP
curl -sS -m 5 -o /dev/null -w "HTTP %{http_code} | %{time_total}s\n" http://127.0.0.1:20128/health
#   HTTP 404 | 0.075s   ← SPA fallback returned instantly → HTTP server is HEALTHY
# Compare:
curl -sS -m 5 -o /dev/null -w "HTTP %{http_code} | %{time_total}s\n" http://127.0.0.1:20128/v1/models
#   (hangs 60s, no response)
```

The contrast (instant 404 on `/health`, hang on `/v1/models`) proves the **HTTP server itself is fine** — only the route handlers that touch provider config are wedged. The bug is in the route handlers or their upstream calls, not the transport.

## Root cause
Read the app log and the sqlite state:
```bash
tail -50 /root/.omniroute/logs/application/app.log
sqlite3 /root/.omniroute/storage.sqlite "SELECT count(*) FROM api_keys; SELECT count(*) FROM provider_connections;"
#   0  (api_keys)
#   0  (provider_connections)
```
Zero provider connections → route handlers waiting on a default upstream discovery call that never returns. The 12h uptime + scheduled background tasks (`ProviderLimitsSync`, `Arena ELO sync`, `LocalHealthCheck`) had accumulated stuck callbacks.

## Fix: clean restart, preserving launch command

```bash
# 1. Capture original launch command BEFORE kill
cat /proc/<pid>/cmdline | tr '\0' ' '   # → "node /usr/bin/omniroute"
ps -o pid,ppid,cmd -p <ppid>            # confirm parent (bash session)

# 2. Graceful TERM, escalate to KILL
kill -TERM <pid> && sleep 3 && (ps -p <pid> > /dev/null && kill -KILL <pid>)

# 3. Restart with EXACT same command (background, tracked)
#    Use Hermes terminal(background=true) NOT nohup/disown so lifecycle is tracked.
node /usr/bin/omniroute 2>&1 | tee -a /tmp/omniroute-fresh.log
sleep 6

# 4. Re-run the same probes
curl -sS -m 5 -o /dev/null -w "HTTP %{http_code} | %{time_total}s\n" http://127.0.0.1:20128/v1/models
#   HTTP 200 | 0.30s   ✓ fixed
curl -sS -m 5 -o /dev/null -w "HTTP %{http_code} | %{time_total}s\n" http://127.0.0.1:20128/
#   HTTP 307 | 0.004s  (redirect to /dashboard/)
```

## To make OmniRoute actually usable end-to-end (still needed)

The restart fixed the hang. But `/v1/chat/completions` returns `{"error":"Combo has no executable targets"}` (instant 404) until you configure a provider:

```bash
# 1. Add an API key via dashboard (NOT in this session — user has not provided keys)
#    Default login: admin / CHANGEME — must change on first login.
#    Dashboard: http://localhost:20128/dashboard/

# 2. CLI clients to install (none currently on this box — only `claude` and `hermes`):
#    Cursor, Cline, Codex — install via apt/npm first, then point at OmniRoute:
OPENAI_API_KEY=*** \
OPENAI_BASE_URL=http://localhost:20128/v1 \
  <cli>

ANTHROPIC_API_KEY=*** \
ANTHROPIC_BASE_URL=http://localhost:20128/v1 \
  claude
```

## Files / paths for OmniRoute on this box

| What | Path |
|---|---|
| Binary | `/usr/bin/omniroute` → `/usr/lib/node_modules/omniroute/bin/omniroute.mjs` |
| Config dir | `/root/.omniroute/` |
| `.env` (storage key only) | `/root/.omniroute/.env` |
| Logs | `/root/.omniroute/logs/application/app.log` (JSON-per-line) |
| SQLite DB | `/root/.omniroute/storage.sqlite` (WAL mode, hot) |
| Internal ports | 20128 (HTTP), 20129 (LiveWS), 20131 (EmbedWsProxy) |
| Default password warning | `[AUTH][SECURITY] Management password is set to "CHANGEME"` — change before exposing |

## Patterns reusable for any OpenAI-compatible router

The `/health` instant-404 vs `/v1/*` hang pattern is the signature of any AI router (LiteLLM, OpenRouter proxies, OmniRoute) when:
1. The HTTP server is up.
2. The route handlers try to aggregate model lists from configured providers.
3. Some upstream call doesn't fail-fast (e.g. provider with no key, expired key, blocked egress).

The fix path is always: **(a)** verify HTTP health with an unknown route, **(b)** restart to rule out wedged state, **(c)** only then debug provider config. Same diagnostic ladder, same outcome pattern across the whole router ecosystem.
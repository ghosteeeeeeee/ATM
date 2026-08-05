---
name: server-admin
description: Ad-hoc Linux server administration — systemd services, long-running processes, display servers, and system-level diagnostics on VMs/cloud instances.
triggers:
  - "check service status"
  - "restart server component"
  - "vnc setup"
  - "x11 display issues"
  - "systemd service not running"
  - "enable service on boot"
---

# Server Admin Playbook

Common ad-hoc administration tasks on Linux VMs/instances.

## Systemd Services

### Check if a service exists and its status
```bash
systemctl status <name>           # running? enabled?
systemctl is-enabled <name>       # will it survive reboot?
systemctl list-units --type=service --all | grep <name>
```

### Enable and start in one shot
```bash
systemctl enable <service> && systemctl start <service>
sleep 2 && systemctl status <service> --no-pager
```

### Key files locations (don't assume):
- System services: `/etc/systemd/system/` (preferred) or `/lib/systemd/system/`
- User services: `~/.config/systemd/user/`
- `systemctl --user` for user-level services

### Reading service definitions
```bash
cat /etc/systemd/system/<name>.service
```
Check: Type= (simple/forking), ExecStart=, Restart= policy, User=.

**Post-reboot checklist:** See `references/post-reboot-system-check-2026-05-15.md` (also in `kanban-orchestrator/references/` — auto-included in orchestrator profile post-reboot workflow).

## X11 / VNC / Display Servers

### Find active displays
```bash
ls /tmp/.X11-unix/               # live X sockets: X0, X1, etc.
ps aux | grep -E 'Xvnc|Xvfb|x11vnc' | grep -v grep
ss -tlnp | grep -E '590[0-9]|600[0-9]'   # VNC ports
```

### Xvfb (virtual framebuffer)
Created by service as a virtual display (e.g., :1). NOT the real session.
- Real display with chrome tabs → X0
- Xvfb :1 → virtual, no physical monitor

### Common VNC service patterns

**x11vnc + Xvfb combo** (common pattern for headless VNC):
```
ExecStart=/bin/bash -c '/usr/bin/Xvfb :1 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset & sleep 2 && /usr/bin/x11vnc -display :1 -forever -shared -rfbport 5900 -localhost -rfbauth /root/.vnc/passwd'
```
This: starts Xvfb on :1 → then x11vnc attaches to :1. x11vnc does NOT create the display, it shares an existing one.

**xkbcomp warnings** — harmless, missing keymap symbols. Ignore.

### VNC connection checklist
1. `ss -tlnp | grep 5900` — is something listening?
2. `ls /tmp/.X11-unix/` — is the display socket there?
3. If using localhost only (default x11vnc -localhost flag) → must tunnel SSH: `ssh -L 5900:localhost:5900 user@host`
4. If display :1 requested but only X0 exists → service failed or using wrong display

### noVNC setup
```bash
# Standard noVNC files location
/usr/share/novnc/

# Start websockify proxy (bridges WebSocket ↔ VNC)
websockify --web /usr/share/novnc 6080 localhost:5900

# Then connect browser to http://host:6080/vnc.html
```

## Process Diagnostics

```bash
ps aux | grep <name>             # find by name
ss -tlnp                        # all listening ports
journalctl -n 50 --no-pager      # recent logs
w                               # who's logged in, load avg
uptime                          # quick system health
```

### "Service is up but requests hang" — the diagnostic ladder

When `curl` to a local service times out, the bug is almost always NOT in your code. Work the ladder in order — each step costs <5 seconds and rules out a category of failure:

```bash
# Step 1: Is the process alive?
ps -p <pid>                       # or: pgrep -af <name>
# Step 2: Is anything listening on the port?
ss -tlnp 'sport = :<port>'
# Step 3: Can TCP connect at all? (rules out firewall)
curl -v -m 3 http://127.0.0.1:<port>/ 2>&1 | grep -E "Trying|Connected|timed out"
# Step 4: Does an UNKNOWN route respond? (probes the HTTP server, not the app logic)
curl -sS -m 5 -o /dev/null -w "HTTP %{http_code} | %{time_total}s\n" \
  http://127.0.0.1:<port>/some-nonexistent-path
# Step 5: Does a KNOWN API route respond?
curl -sS -m 5 -o /dev/null -w "HTTP %{http_code} | %{time_total}s\n" \
  http://127.0.0.1:<port>/v1/something
# Step 6: If Step 4 is fast-404 and Step 5 hangs, the bug is in route handlers,
# not the HTTP server. Read the app log NOW (most servers log the slow request).
tail -50 /path/to/app.log
```

**Decision tree from results:**
- Step 1 dead → process crashed or never started. Check `journalctl`, startup logs.
- Step 2 empty → service bound to wrong interface or port. Check `--bind`, `-p` flags.
- Step 3 fails (no "Connected") → firewall (iptables/nft) or wrong IP family (try `[::1]` vs `127.0.0.1`).
- Step 3 connects but Step 4 hangs → zombie listener: process forked listener socket but the request handler thread/event-loop is dead. **Restart the service.** This is the classic "12-hour-old Node/Python service that worked fine yesterday" failure mode — `ss` shows `LISTEN` but no request ever returns.
- Step 4 instant-404 + Step 5 hangs → HTTP server is healthy. The route handler is blocking on something (DB lock, outbound HTTP, missing config). Read the app log for the specific failure; check if the handler tries to call an unconfigured external service.
- Step 4 AND Step 5 hang → request loop is saturated or event loop blocked. `top` for CPU, `lsof -p <pid>` for stuck fds.

**Example from a real session** (OmniRoute, port 20128):
```
/health       → HTTP 404 in 75ms     (instant — proves HTTP server alive)
/v1/models    → timeout, 60s         (route handler blocking on unconfigured upstream)
Restart → /v1/models → HTTP 200 in 300ms (was a wedged 12h-old process)
```

### Restart-as-diagnostic (cheap probe, often the fix)

For any long-running service (Node, Python, Go daemon, Java app) that's been alive for hours/days and starts misbehaving, a clean restart is the single most informative action you can take — and it often *is* the fix:

```bash
# 1. Find the original launch command BEFORE killing — so you restart the same way
cat /proc/<pid>/cmdline | tr '\0' ' '           # argv of the main process
ps -o pid,ppid,cmd -p <ppid>                    # parent's argv (often a wrapper script)
# 2. Note the env (only available while alive)
tr '\0' '\n' < /proc/<pid>/environ | sort
# 3. Clean shutdown, then restart
kill -TERM <pid> && sleep 3 && (ps -p <pid> > /dev/null && kill -KILL <pid>)
# 4. Restart with the EXACT same command you recovered in step 1
```

If the restart fixes it, the bug was process state accumulation (leaks, stuck timers, wedged locks, background tasks with stale handles). If it doesn't fix it, you at least know the issue isn't transient state — it's reproducible from cold boot.

### Reading long-lived service logs (JSON-line format)

Many modern services log JSON-per-line. Quick patterns:

```bash
# Tail live with pretty timestamps
tail -f /path/to/app.log | jq -r '"\(.timestamp) [\(.level)] \(.component): \(.message)"'
# Filter just errors/warns since a marker time
awk -v since="$(date -u -d '5 min ago' '+%Y-%m-%dT%H:%M:%S')" \
  '$0 ~ /^\{/ { from=index($0, "\"timestamp\":\""); if (from>0) { ts=substr($0, from+13, 19); if (ts>since) print } }' \
  /path/to/app.log
# Watch for new entries matching a pattern (cheap, no jq needed)
tail -F /path/to/app.log | grep --line-buffered "ERROR\|HeadersTimeout"
```

If the service logs warnings on a schedule (every 5–15 min) about an upstream call, those are usually scheduled health checks — unrelated to a hanging user request. Correlate timestamps against when you sent the request, not just what's the most recent.

## Gotchas

- **Zombie listener (TCP LISTEN without a working handler):** `ss -tlnp` shows the socket as `LISTEN` because the kernel still has it, but the process's event loop or request thread is dead. The HTTP server accepts the TCP connection but never writes a response. Fixed by restart, not by any network-level fix. The "is an unknown route fast-404?" probe (Step 4 above) is the cleanest way to detect this — instant 404 means the handler is alive, hanging means it's dead.
- **Service "started in 7s" banner but routes hang:** the start script declares success as soon as the listener binds, not after request handlers initialize. A 7-second banner with hanging `/v1/*` routes is normal for services with deferred init (provider sync, model cache warmup, config hydration). Always check `/health` or a known-trivial endpoint first.
- **Background schedulers can poison the log stream:** services like OmniRoute/LiteLLM run 5–15min scheduled health checks that emit `HeadersTimeoutError` warnings. These are NOT related to your foreground request — correlate timestamps before assuming causation.
- **Don't restart a service you don't know how it was launched.** Read `/proc/<pid>/cmdline` and the parent's cmdline FIRST. Restarting with different flags, env vars, or `cwd` can mask the original bug as "works after restart" when really it just changed config.
- **OOM-killed services look like dead listeners.** If `ps` shows nothing but a port is still in `TIME_WAIT`/`LISTEN`, check `dmesg | grep -i "killed process"` for OOM kills. The kernel reaps the process but the socket lingers briefly.
- **curl `--connect-timeout` vs `-m` (max-time):** `--connect-timeout` only covers TCP connect. `-m` covers the whole request including server response. Use `-m 60` when debugging hangs so you get the real picture, not just "could I open a socket."

- **Disabled service**: `systemctl enable` creates symlink in `multi-user.target.wants/`. If service shows `disabled` → it won't restart on reboot.
- **Service starts but no display**: Check if Xvfb process is actually running (`ps aux | grep Xvfb`). If not, the background job in ExecStart may have failed silently.
- **localhost-only VNC**: x11vnc defaults to `-localhost` (only accepts connections from the server itself). Remote clients need SSH tunnel.
- **Xvfb :1 vs real X0**: Xvfb creates a virtual headless display. It does NOT show your actual desktop with open browser tabs. For real-session sharing, use x11vnc directly on X0 (no Xvfb).

---

Pitfalls
- Don't assume systemctl is-enabled result is accurate — check actual symlink exists.
- If a service restarts frequently (RestartSec loops), check the ExecStart command — a failing subprocess inside the bash -c wrapper is a common culprit.
- Service logs can be silently truncated by systemd — use `journalctl --user -u <name> -n 100` for user services.
- **Oneshot timers producing 0 results**: check what data the service's script actually reads. A service can exit silently (status=0/SUCCESS) but produce no useful output if its data source has a staleness filter the service doesn't expect. Always compare the data the script needs vs what it actually gets — e.g. a 2-minute cutoff in a sweep script that needs 70+ bars will silently skip every token. Verify by running the script manually with same args and checking output.
- **"Service is up but hangs" is almost never a code bug — it's process state.** A clean restart is the cheapest diagnostic for any long-lived daemon that starts misbehaving after hours/days of uptime. If restart fixes it, document the threshold (e.g. "needs restart every 12h") and add a `Restart=` directive. Use the diagnostic ladder in the Process Diagnostics section above to confirm before restarting blindly.
- **Long-lived services can wedge without dying.** A 12h-old Node/Python daemon may show `LISTEN` in `ss`, accept TCP connections, then never respond because a background scheduler callback or event loop got stuck. Restart fixes it; no code change needed. If this recurs, the actual bug is in whichever background task accumulates state — not in the request handler.
- **Reconstruct the launch command from `/proc` BEFORE restarting.** `cat /proc/<pid>/cmdline | tr '\0' ' '` and the parent's cmdline (`ps -o pid,ppid,cmd -p <ppid>`). Restarting with different flags, env, or `cwd` masks the original bug and you'll waste time wondering why "restart fixed it" when it really just changed the inputs.

Verification steps after any service change:
```bash
systemctl status <name> --no-pager
ss -tlnp | grep <port>
ls /tmp/.X11-unix/
# For services that hang, re-run the diagnostic ladder (see Process Diagnostics section):
curl -sS -m 5 -o /dev/null -w "HTTP %{http_code} | %{time_total}s\n" \
  http://127.0.0.1:<port>/some-nonexistent-path
curl -sS -m 5 -o /dev/null -w "HTTP %{http_code} | %{time_total}s\n" \
  http://127.0.0.1:<port>/known-api-endpoint
```

## Reference files
- `references/post-reboot-system-check-2026-05-15.md` — post-reboot checklist for Hermes trading services.
- `references/x11vnc-service.md` — x11vnc service patterns and gotchas.
- `references/omniroute-debug-2026-07-13.md` — worked example of the diagnostic ladder on OmniRoute (Node AI router, port 20128): zombie listener → restart → instant fix. Useful template for any "service is up but /v1/* hangs" diagnosis on an OpenAI-compatible router.
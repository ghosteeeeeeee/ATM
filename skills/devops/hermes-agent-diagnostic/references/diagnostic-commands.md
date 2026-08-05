# Diagnostic commands — substitute for the hanging `hermes doctor`

Each command below ran successfully 2026-07-13 21:14 UTC against Hermes Agent v0.18.2 (2026.7.7.2). Use these as the canonical diagnostic surface. None of them hang.

## Core 8-command health snapshot

Run in this order. Each section builds on the previous — stop early if a section reveals a P0.

### 1. Version + install drift
```bash
hermes --version
```
Expected: `Hermes Agent vX.Y.Z (YYYY.M.D.N) · upstream <sha>` + `Install directory: /root/hermes-agent` + `Python: 3.11.x` + `OpenAI SDK: X.Y.Z`.
Watch for: `Update available: N commits behind — run 'hermes update'` (informational, not urgent).

### 2. Status — providers, toolsets, gateway
```bash
hermes status --all
```
Returns a multi-section panel:
- `Model:` / `Provider:` — current routing
- `API Keys` — per-provider ✓/✗ (expected ✗ for unused providers)
- `Auth Providers` — OAuth flows (Nous, Codex, Qwen, etc.)
- `API-Key Providers` — duplicate of API Keys but cleaner
- `Terminal Backend` — usually `local`, `Sudo: ✗ disabled`
- `Messaging Platforms` — ✗ for unconfigured (most users)
- `Gateway Service → Status / Manager / PID(s)`
- `Scheduled Jobs → Jobs: N active, N total`
- `Sessions → Active: N`

Flags to interpret:
- `Gateway Status: ✓ running (manual, not as a system service)` → won't survive reboot. Use `hermes gateway install`.
- `Gateway Manager: systemd (user)` → dies on logout unless `loginctl enable-linger`.
- `Active agents: 0` is normal; persistent >0 = stuck agent.
- `Scheduled Jobs: total > active` = some paused jobs (intentional or not).

### 3. Config path + sanity
```bash
hermes config path
hermes config check
```
- Path: `/root/.hermes/config.yaml` (almost always).
- `check`: dumps env vars that are missing/unset. Most are platform-specific (TEAMS_*, FEISHU_*, IRC_*) and expected to be unset if you don't use them. **Skim for the providers you actually use.**

### 4. Cron jobs — the only command that shows `error:` lines
```bash
hermes cron list
```
Each job block: `Name / Schedule / Next run / Deliver / Last run`. Critical field:
- `Last run: ... ok` → fine
- `Last run: ... error: <message>` → broken. See `cron-misconfig-cases.md` for triage recipes.

Filter to just the failures:
```bash
hermes cron list 2>&1 | grep -B1 "error:"
```

### 5. Gateway state
```bash
hermes gateway status
```
Returns `✓ Gateway is running (PID: N)` plus service-mode hint. If `Running manually`, fix with `hermes gateway install`.

For deeper inspection:
```bash
cat ~/.hermes/gateway_state.json
cat ~/.hermes/gateway.pid
ps -ef | grep -E "gateway" | grep -v grep
```

### 6. MCP servers
```bash
hermes mcp list
```
Table: `Name / Transport / Tools / Status`. `Status: ✓ enabled` is normal. `Status: ✗ failed` = bad server config (check transport).

### 7. Sessions DB
```bash
hermes sessions stats
```
- `Total sessions: N`
- `Total messages: N`
- `cli: N sessions` (vs `gateway: N sessions`)
- `Database size: N MB/GB`

DB > 2 GB → consider `hermes sessions prune --older-than 90`.

### 8. Toolsets
```bash
hermes tools list
```
Two sections: built-in toolsets (`✓ enabled` / `✗ disabled`) and MCP servers. Some tools require API keys in `.env` to actually appear usable even when enabled.

## Optional secondary checks

```bash
# Secrets permissions (config.yaml and auth.json should be 600; .env 644 is common but tighten to 600)
stat -c '%n  %a' ~/.hermes/config.yaml ~/.hermes/.env ~/.hermes/auth.json

# Disk usage — Hermes home + trading paths
df -h / /root /var 2>&1

# Memory + load
free -h
uptime

# Running processes that matter
ps -ef | grep -E "hermes|gateway|run_agent" | grep -v grep | head -10

# Recent log entries from any hermes process
journalctl --user -u hermes-gateway -n 30 --no-pager 2>&1 | tail -20
```

## What success looks like (2026-07-13 baseline)

- Version: Hermes Agent v0.18.2 (2026.7.7.2), upstream c44de998, Python 3.11.15
- 16 toolsets enabled, 1 MCP server (hermes-coding-mcp) with all tools enabled
- Gateway running (systemd), PID present, 0 active agents
- 9 active cron jobs (or whatever your setup is), all `ok` except the 2 known-broken patterns
- Sessions DB growing steadily but < 3 GB
- Secrets at mode 600
- 27 commits behind upstream is informational, not a bug

## What failure looks like (triggers for escalation)

- `Gateway Service → Status: ✗ stopped` → gateway crashed, check `~/.hermes/logs/gateway.log`
- `Active agents: N` where N > 0 with no active session → stuck agent, may need kill
- Cron jobs: ANY `error:` line recurring → fix per `cron-misconfig-cases.md`
- Sessions DB > 5 GB → `hermes sessions prune` urgently
- `~/.hermes/config.yaml` mode != 600 → `chmod 600`
- `MCP servers → Status: ✗ failed` → `hermes mcp test <name>` for diagnosis

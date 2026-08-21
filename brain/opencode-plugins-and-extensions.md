# OpenCode Plugins & Extensions — Access Reference

## Plugins

### 1. Ponytail (`@dietrichgebert/ponytail`)
Installed via npm. Enforces minimal, lazy-first code.

**Activates on:** any coding task, or triggers like "ponytail", "be lazy", "lazy mode", "yagni", "simplest solution".

**Levels:**
- `lite` — builds what's asked, names lazier alternative
- `full` — ladder enforced, stdlib first, shortest diff (default)
- `ultra` — YAGNI extremist, deletion before addition

**Switch:** `/ponytail lite|full|ultra` or "stop ponytail" / "normal mode"

**Config location:**
```
/root/.config/opencode/opencode.jsonc   → "plugin": ["@dietrichgebert/ponytail"]
/root/.cache/opencode/packages/@dietrichgebert/ponytail@latest/
```

### 2. Command Guard (custom, local)
Blocks dangerous bash commands via regex patterns before execution.

**Source:** `/root/.config/opencode/plugins/command-guard.ts`
**Patterns:** `/root/.agents/hooks/dangerous-patterns.txt`

Blocks: `rm /`, `rm ~`, `dd` to disks, `mkfs`, `sudo rm`, fork bombs, `curl|wget | sh`, `git push --force`, `git push --delete`, `chmod 777 /`, `gh repo delete`, `gh auth token`, etc.

Shared across ALL agents (Cursor, Claude Code, Codex, OpenCode). Edit the patterns file to tune — changes apply immediately.

---

## MCP Servers

| Server | Type | URL / Command | Auth |
|--------|------|---------------|------|
| **openmemory** | remote (HTTP) | `http://localhost:8080/mcp` | `x-api-key: dev-key-123` |
| **sequential-thinking** | local (stdio) | `npx -y @modelcontextprotocol/server-sequential-thinking` | none |
| **fetcher** | local (stdio) | `npx -y fetcher-mcp` | none |

### OpenMemory MCP Config
```json
{
  "mcpServers": {
    "openmemory": {
      "type": "streamableHttp",
      "url": "http://localhost:8080/mcp",
      "headers": { "x-api-key": "dev-key-123" }
    }
  }
}
```

### Sequential Thinking MCP
Provides step-by-step reasoning tool. Local stdio, no config needed. Runs via npx.

### Fetcher MCP
Web page fetching tool. Local stdio, no config needed. Runs via npx.

---

## Skills (43 installed)

Located at `/root/.config/opencode/skills/` (and `~/.cache/opencode/packages/` for plugin-provided ones).

**Trading:** add-signal, signal-lab, signal-quality-tuner, signal-backtest, signal-combo-analyzer, trade-analysis, trade-stats, winrate-calculator, hotset-debug, phantom-trades
**Books:** book_advanced_strategies, book_complete_guide_trading, book_day_trading, book_day_trading_beginners, book_divergence, book_first_trading_manual, book_liquidity_markets, book_price_action, book_profitable_strategies, book_short_swing, book_swing_trading, book_system_development, book_trading_psychology, book_trading_volatility, book_wyckoff, book-signal-upgrades
**System:** bug-hunter, post-change, ceo-comm, pipeline-visualizer, decisions, handoff, write-trading-skill
**Tools:** graphify, transcript-miner, youtube-watch, download-pdfs, chromium-vnc, screenshot, opencode-command
**Other:** autopilot-mechanics, write-command, update-atm-readme

---

## Custom Commands

Located at `/root/.config/opencode/commands/`:
- `book-skill.md` — book skill creation command
- `transcript.md` — transcript mining command

---

## Permissions

External directory access allowed:
- `/var/www/hermes/data/**`
- `/root/.hermes/**`

---

## Provider

**xAI** API key configured in opencode.jsonc. Used for model access.

---
name: autonomous-coding-agents
title: Autonomous Coding Agent Workers
description: "Delegate coding work to external autonomous coding agents — Claude Code, OpenAI Codex, and OpenCode. Covers install, auth, interactive PTY orchestration, print mode, parallel runs, PR review, and the gotchas that differ between agents."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, Claude, Anthropic, OpenAI, Codex, OpenCode, PTY, Automation, Code-Review, Refactoring, Autonomous]
    related_skills: [hermes-agent, subagent-driven-development, requesting-code-review, github-pr-workflow]
---

# Autonomous Coding Agent Workers

Delegate coding work to external autonomous coding agent CLIs:

1. **Section 1 — Claude Code** (`claude` CLI, Anthropic) — most capable, richest flag set
2. **Section 2 — Codex** (`codex` CLI, OpenAI) — sandboxed, fast, `--full-auto`/`--yolo`
3. **Section 3 — OpenCode** (`opencode` CLI, provider-agnostic) — open source, model-agnostic, TUI

These are different binaries from `hermes-agent` itself — they run as subprocesses orchestrated by the parent agent (you) via the terminal and `process` tools.

## When to Use

- Building a multi-file feature where you want a focused worker
- Refactoring a module to a new pattern
- Reviewing a PR with deep context
- Parallel batch work (multiple worktrees, multiple issues)
- Long-running coding sessions with progress checks

## Universal Rules (apply to all three)

1. **Always scope to a git repo** — Claude/Codex/OpenCode all refuse to run outside one
2. **For scratch work:** `mktemp -d && git init && <agent> <task>`
3. **For one-shot tasks:** prefer each agent's "run" mode (no PTY needed)
4. **For multi-turn work:** start in background with `pty=true`, monitor with `process(poll|log)`
5. **For parallel work:** use separate workdirs/worktrees per task to avoid collisions
6. **Pass concrete context:** `cd <repo>`, file paths, error messages — not vague intent
7. **Don't interfere mid-run:** poll logs, be patient with long-running tasks

## Decision: Which Agent?

| Need | Pick |
|------|------|
| Max capability, deep refactors, MCP, hooks | **Claude Code** |
| Quick sandboxed build, OpenAI ecosystem | **Codex** |
| Provider flexibility (OpenRouter, local, etc.), open source | **OpenCode** |
| Parallel batch work | Any of the three — all support worktrees |

---

# Section 1 — Claude Code

## Prerequisites

- Install: `npm install -g @anthropic-ai/claude-code`
- Auth: `claude` (browser OAuth Pro/Max) or `claude auth login --console` (API key) or `claude auth login --sso` (Enterprise)
- Status: `claude auth status` (JSON) or `claude auth status --text`
- Health: `claude doctor`
- Update: `claude update` or `claude upgrade`

## Two Orchestration Modes

### Mode A: Print Mode (`-p`) — Non-Interactive (PREFERRED)

Runs a one-shot task, returns result, exits. No PTY, no dialogs.

```
terminal(command="claude -p 'Add error handling to all API calls in src/' --allowedTools 'Read,Edit' --max-turns 10", workdir="/path/to/project", timeout=120)
```

Use for: one-shot tasks, CI/CD automation, piped input, structured JSON extraction.

### Mode B: Interactive PTY via tmux — Multi-Turn Sessions

Full conversational REPL with follow-up prompts and slash commands. Requires tmux.

```
terminal(command="tmux new-session -d -s claude-work -x 140 -y 40")
terminal(command="tmux send-keys -t claude-work 'cd /path/to/project && claude' Enter")
terminal(command="sleep 5 && tmux send-keys -t claude-work 'Refactor auth module to use JWT' Enter")
terminal(command="sleep 15 && tmux capture-pane -t claude-work -p -S -50")
terminal(command="tmux send-keys -t claude-work '/exit' Enter")
```

### PTY Dialog Handling (CRITICAL)

Two dialogs can appear on first launch — handle via tmux:

**Dialog 1: Workspace Trust** — default "Yes" is correct, just press Enter:
```
sleep 4 && tmux send-keys -t <sess> Enter
```

**Dialog 2: Bypass Permissions** — default is WRONG (No, exit), must navigate down then enter:
```
sleep 3 && tmux send-keys -t <sess> Down && sleep 0.3 && tmux send-keys -t <sess> Enter
```

## Key Flags (subset — see skill references for full list)

| Flag | Effect |
|------|--------|
| `-p, --print` | Non-interactive one-shot |
| `-c, --continue` | Resume most recent in cwd |
| `-r, --resume <id>` | Resume specific session |
| `--max-turns <n>` | Cap agentic loops (print mode only) |
| `--max-budget-usd <n>` | Cap spend (min ~$0.05) |
| `--allowedTools 'Read,Edit,Bash(git *)'` | Whitelist tools |
| `--output-format json` | Structured single result |
| `--output-format stream-json` | Newline-delimited events |
| `--json-schema '{...}'` | Force schema-validated output |
| `--bare` | Skip hooks/plugins/MCP/OAuth (CI mode) |
| `--fallback-model haiku` | Auto-fallback on overload |
| `--append-system-prompt "text"` | Add to (not replace) system prompt |
| `--from-pr <n>` | Resume session linked to a PR |
| `--worktree [name]` | Run in isolated `.claude/worktrees/<name>` |
| `--dangerously-skip-permissions` | Auto-approve all tool use |

## Slash Commands (interactive mode)

- `/compact` — compress context (use near 70%)
- `/clear` — fresh context
- `/context` — visualize context usage
- `/cost` — token usage breakdown
- `/model [name]` — switch model
- `/effort [level]` — reasoning depth (low/medium/high/max/auto)
- `/review` — code review current changes
- `/security-review` — security analysis
- `/plan` — enter plan mode
- `/batch` — auto-create worktrees for parallel work
- `/init` — create CLAUDE.md
- `/memory` — edit CLAUDE.md
- `/agents` — manage subagents
- `/mcp` — manage MCP servers
- `/exit` — end session

## Structured Output (Print Mode)

```json
{
  "type": "result",
  "subtype": "success",
  "result": "The analysis text...",
  "session_id": "75e2167f-...",
  "num_turns": 3,
  "total_cost_usd": 0.0787,
  "duration_ms": 10276,
  "subtype": "success | error_max_turns | error_budget"
}
```

## PR Review

```bash
# Quick
terminal(command="cd /path/to/repo && git diff main...feature-branch | claude -p 'Review this diff for bugs, security issues, and style problems. Be thorough.' --max-turns 1", timeout=60)

# Deep (worktree)
terminal(command="claude -p 'Review this PR thoroughly' --from-pr 42 --max-turns 10", workdir="/path/to/repo", timeout=120)
```

## Parallel Claude Instances

```bash
terminal(command="tmux new-session -d -s task1 -x 140 -y 40 && tmux send-keys -t task1 'cd ~/project && claude -p \"Fix the auth bug\" --allowedTools \"Read,Edit\" --max-turns 10' Enter")
terminal(command="tmux new-session -d -s task2 -x 140 -y 40 && tmux send-keys -t task2 'cd ~/project && claude -p \"Write integration tests\" --allowedTools \"Read,Write,Bash\" --max-turns 15' Enter")
terminal(command="sleep 30 && for s in task1 task2; do echo \"=== $s ===\"; tmux capture-pane -t $s -p -S -5; done")
```

## MCP Servers (Claude Code)

```bash
# GitHub
claude mcp add -s user github -- npx @modelcontextprotocol/server-github
# Postgres
claude mcp add -s local postgres -- npx @anthropic-ai/server-postgres --connection-string postgresql://localhost/mydb
# Puppeteer
claude mcp add puppeteer -- npx @anthropic-ai/server-puppeteer
```

In print/CI: `claude --bare -p 'Query database' --mcp-config mcp-servers.json --strict-mcp-config`

## Cost & Performance Tips

1. Use `--max-turns` in print mode (start 5-10)
2. Use `--max-budget-usd` to cap (min ~$0.05)
3. Use `--effort low` for simple tasks
4. Use `--bare` for CI/scripting (no plugin/MCP overhead)
5. Use `--allowedTools` to restrict scope
6. Use `/compact` in interactive mode near 70% context
7. Use `--model haiku` for cheap simple tasks
8. Use `--fallback-model haiku` for graceful overload handling
9. Use `--no-session-persistence` in CI

## Pitfalls

- **Interactive REQUIRES tmux** — prompt_toolkit needs a real terminal
- **`--dangerously-skip-permissions` dialog defaults to "No"** — must send Down+Enter
- **`--max-budget-usd` minimum ~$0.05** — system prompt cache creation costs this
- **`--max-turns` is print-mode only** — ignored in interactive
- **Trust dialog only first visit** — cached per directory after
- **Background tmux persists** — clean up with `tmux kill-session -t <name>`
- **Slash commands are interactive-only** — in `-p` mode use natural language
- **`--bare` skips OAuth** — requires `ANTHROPIC_API_KEY`
- **Context degrades above 70%** — monitor with `/context`

## Rules for Hermes Agents

1. Prefer print mode for single tasks
2. Use tmux for multi-turn interactive work
3. Always set `workdir`
4. Set `--max-turns` in print mode
5. Monitor with `tmux capture-pane`
6. Look for `❯` prompt = waiting for input
7. Clean up tmux sessions
8. Report concrete outcomes (files changed, tests)

---

# Section 2 — Codex

## Prerequisites

- Install: `npm install -g @openai/codex`
- Auth: `OPENAI_API_KEY` env or Codex CLI OAuth (`~/.codex/auth.json`)
- **Must run inside a git repo** — Codex refuses outside one
- Use `pty=true` for interactive runs

For Hermes itself, `model.provider: openai-codex` uses Hermes-managed OAuth from `~/.hermes/auth.json` after `hermes auth add openai-codex`. Don't treat a missing `OPENAI_API_KEY` alone as proof of missing auth.

## One-Shot

```bash
codex exec 'Add dark mode toggle to settings'
# Scratch:
cd $(mktemp -d) && git init && codex exec 'Build a snake game in Python'
```

## Background Mode

```bash
terminal(command="codex exec --full-auto 'Refactor the auth module'", workdir="~/project", background=true, pty=true)
process(action="poll", session_id="<id>")
process(action="submit", session_id="<id>", data="yes")
```

## Key Flags

| Flag | Effect |
|------|--------|
| `exec "prompt"` | One-shot, exits when done |
| `--full-auto` | Sandboxed but auto-approves file changes in workspace |
| `--yolo` | No sandbox, no approvals (fastest, most dangerous) |

## PR Reviews

```bash
REVIEW=$(mktemp -d) && git clone https://github.com/user/repo.git $REVIEW && cd $REVIEW && gh pr checkout 42 && codex review --base origin/main
```

## Parallel Issue Fixing (worktrees)

```bash
git worktree add -b fix/issue-78 /tmp/issue-78 main
git worktree add -b fix/issue-99 /tmp/issue-99 main

terminal(command="codex --yolo exec 'Fix issue #78. Commit when done.'", workdir="/tmp/issue-78", background=true, pty=true)
terminal(command="codex --yolo exec 'Fix issue #99. Commit when done.'", workdir="/tmp/issue-99", background=true, pty=true)
```

## Batch PR Reviews

```bash
git fetch origin '+refs/pull/*/head:refs/remotes/origin/pr/*'
terminal(command="codex exec 'Review PR #86. git diff origin/main...origin/pr/86'", workdir="~/project", background=true, pty=true)
terminal(command="codex exec 'Review PR #87. git diff origin/main...origin/pr/87'", workdir="~/project", background=true, pty=true)
```

## Rules

1. Always `pty=true`
2. Git repo required
3. Use `exec` for one-shots
4. `--full-auto` for building
5. Background for long tasks
6. Don't interfere — poll/log
7. Parallel is fine

---

# Section 3 — OpenCode

## Prerequisites

- Install: `npm i -g opencode-ai@latest` or `brew install anomalyco/tap/opencode`
- Auth: `opencode auth login` or set provider env vars (OPENROUTER_API_KEY, etc.)
- Verify: `opencode auth list` should show ≥1 provider
- Git repo recommended
- `pty=true` for interactive TUI

## Binary Resolution

Shell environments may resolve different OpenCode binaries. Check:

```bash
which -a opencode
opencode --version
# Pin if needed:
$HOME/.opencode/bin/opencode run '...'
```

## One-Shot

```bash
opencode run 'Add retry logic to API calls and update tests'
# With file context:
opencode run 'Review this config' -f config.yaml -f .env.example
# Show thinking:
opencode run 'Debug why tests fail' --thinking
# Force model:
opencode run 'Refactor auth' --model openrouter/anthropic/claude-sonnet-4
```

## Interactive (background)

```bash
terminal(command="opencode", workdir="~/project", background=true, pty=true)
process(action="submit", session_id="<id>", data="Implement OAuth refresh flow")
process(action="write", session_id="<id>", data="\x03")  # Ctrl+C to exit
```

**Important:** `/exit` is NOT a valid OpenCode command — it opens an agent selector. Use Ctrl+C or `process(action="kill")` to exit.

## Key Flags

| Flag | Use |
|------|-----|
| `run 'prompt'` | One-shot, exits |
| `--continue` / `-c` | Continue last session |
| `--session <id>` / `-s` | Continue specific session |
| `--agent <name>` | build or plan |
| `--model provider/model` | Force specific model |
| `--format json` | Machine-readable output |
| `--file <path>` / `-f` | Attach file(s) |
| `--thinking` | Show model thinking |
| `--variant <level>` | high, max, minimal |
| `--title <name>` | Name the session |
| `--attach <url>` | Connect to running server |

## TUI Keybindings

| Key | Action |
|-----|--------|
| Enter | Submit (press twice if needed) |
| Tab | Switch between agents (build/plan) |
| Ctrl+P | Command palette |
| Ctrl+X L | Switch session |
| Ctrl+X M | Switch model |
| Ctrl+X N | New session |
| Ctrl+X E | Open editor |
| Ctrl+C | Exit |

## PR Review

```bash
opencode pr 42
# Or temp-clone for isolation:
REVIEW=$(mktemp -d) && git clone https://github.com/user/repo.git $REVIEW && cd $REVIEW && opencode run 'Review this PR vs main.' -f $(git diff origin/main --name-only | head -20 | tr '\n' ' ')
```

## Parallel Work

```bash
terminal(command="opencode run 'Fix issue #101 and commit'", workdir="/tmp/issue-101", background=true, pty=true)
terminal(command="opencode run 'Add parser regression tests and commit'", workdir="/tmp/issue-102", background=true, pty=true)
```

## Session & Cost

```bash
opencode session list
opencode stats
opencode stats --days 7 --models anthropic/claude-sonnet-4
```

## Pitfalls

- Interactive `opencode` (TUI) needs `pty=true`; `opencode run` does NOT
- `/exit` is NOT valid — use Ctrl+C
- PATH mismatch can pick wrong binary/model config
- If appears stuck, inspect logs (`process(action="log", ...)`) before killing
- Don't share one working directory across parallel sessions
- Enter may need to be pressed twice in TUI

## Verification

```bash
opencode run 'Respond with exactly: OPENCODE_SMOKE_OK'
```

Success: output includes `OPENCODE_SMOKE_OK`, command exits without provider/model errors.

## Rules

1. Prefer `opencode run` for one-shots
2. Interactive background only when iterating
3. Always scope to a single repo/workdir
4. Long tasks: provide progress updates from `process` logs
5. Report concrete outcomes
6. Exit with Ctrl+C or kill, never `/exit`

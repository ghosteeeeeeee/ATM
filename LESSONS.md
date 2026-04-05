# LESSONS.md — Principles and Patterns

> Hard-won lessons. Never repeat these mistakes.

---

## Trading

### Stop Losses
- **Always calculate P&L correctly for shorts** — profit is `(entry - current) / entry`, not the other way around
- **Trailing stops need activation threshold** — don't trail from entry; wait for proof (e.g., +2% profit)
- **Lock minimum profit** — when activating trailing, set a floor SL at breakeven + X% before trailing
- **One place for trailing logic** — don't duplicate in heartbeat AND trailing-stop-manager; use the service
- **The trailing-stop-manager.py service** — runs via `ro-trailing-stop.service` on Dallas, NOT the JS version

### Position Sizing
- 20X only for high confidence (80+, multiple confluences, multi-timeframe)
- Low confidence = 5X-10X for breathing room
- Win rate improves → tighten leverage requirements

### Trade Execution
- Always check current price before updating SL in DB
- Verify trade side (long/short) in ALL calculations

---

## Technical

### Database Queries
- Use `::numeric` cast for PostgreSQL decimal fields
- Always include `side` column when querying trades
- Quote strings properly: `status='open'` not `status=open`
- **Column names are `pnl_usdt` and `amount_usdt` NOT `pnl_usd` or `size`** — check before writing queries
- Status values are `open`/`closed` (not numeric codes)

### SQL — The `***` Placeholder Trap
- `***` is NOT a valid SQL placeholder. Use proper named params or `?`/`%s`
- Every file that used `***` as a placeholder had bugs: `ai-decider.py` (6+ bugs), `hl-sync-guardian.py` (7+ bugs), `decider-run.py` (4+ bugs)
- This caused silent failures — queries ran but matched nothing, hot-set never built, signals silently died
- **Rule: always verify SQL placeholders match the DB schema exactly**

### Naming Consistency — `token` vs `coin`
- The codebase was inconsistent: some files used `token`, others used `coin`
- Variable `coin` is the correct standard — `token` was the bug
- This affected: `ai_decider.py`, `hl-sync-guardian.py`, `decider-run.py`, `signal_gen.py`, and more
- Fix: standardize on `coin` everywhere, audit all files when renaming

### Cursor Management
- **Always close cursors in a `finally` block** — unclosed cursors leak and cause "database locked" errors
- Same applies to file handles and network connections

### SSH Connections
- Use `-o ConnectTimeout=5` to avoid hanging
- Quote SQL properly in nested SSH commands: `\"column = 'value'\"`
- Test queries locally before scripting

### Scripting Patterns
- **Lock files** — prevent overlapping runs in services
- **State files** — persist peak prices, activation status across runs
- **Log everything** — include timestamps, use consistent format

---

## Architecture

### Hot-Set Pipeline
- `hotset.json` is authoritative — written by `ai_decider.py` every 10 min
- `signals.json` (web dashboard) reads from `hotset.json` and enriches with live RSI
- `hermes-trades-api.py` writes `signals.json` — do NOT write to it directly
- review_count increments on SKIPPED/WAIT decisions — if it stays at 1, the increment logic is broken

### Trailing Stop
- Use ONE trailing stop service: `ro-trailing-stop.service` on Dallas (Python)
- Do NOT use a JS version — leads to duplicate logic and state divergence

### Cascades / Flip Trades
- When a position flips direction (e.g., LONG→SHORT), reset trailing state completely
- Post-flip: arm trailing only after proof of new direction (+0.5% buffer is standard)

---

## Bugs Caught the Hard Way

| Bug | Impact | Root Cause |
|-----|--------|------------|
| `***` SQL placeholders | Hot-set never built, signals died silently | Not a valid SQL placeholder |
| `token` vs `coin` mismatch | Functions called with wrong param, returned None | Inconsistent naming |
| Unclosed cursors | "database locked" errors | Missing `finally` blocks |
| `mirror_open` missing `import sys` | VNC/dashboard failures | Missing import in prod |
| `hype_live_trading.json` toggle inverted | Live mode was skipped | Boolean logic bug |
| MiniMax wrong base URL (`/anthropic/v1`) | Every API call failed silently | Stale docs in brain |
| MiniMax wrong model (`MiniMax-Text-01`) | Wrong model called | Stale docs in brain |
| `pnl_usdt` vs `pnl_usd` column name | PostgreSQL queries failed | Naming assumption |
| Port 54321 serves from `/var/www/hermes` | 404s on all pages | Wrong root — different nginx server block |
| `jobs.json` tracked in git | Exposed job prompts + file paths | Should always be untracked |
| MiniMax prepends `<think>` block | Parsing `DECISION:` fails if looking at first line | Always look at end of response |

---

## Parsing Traps

### MiniMax Thinking Block
- MiniMax-M2 prepends a `<think>` block to every response
- Any parsing that expects structured output on line 1 will fail
- **Fix:** Look for `DECISION:` and `CONFIDENCE:` at the END of the response, after the thinking block

### Ollama JSON in Subprocess
- Ollama output via subprocess can contain control characters
- **Fix:** Use `hermes_tools.json_parse()` (which wraps `json.loads` with `strict=False`) not raw `json.loads`

---



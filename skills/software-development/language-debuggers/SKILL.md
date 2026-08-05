---
name: language-debuggers
title: Language Debuggers
description: "Programmatic debuggers for Python and Node.js — pdb/debugpy and node inspect/CDP. Breakpoints, step/over/out, call-stack walking, scope dumps, expression evaluation, attach-to-running-process. When `print()` isn't enough."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, python, pdb, debugpy, nodejs, cdp, breakpoints, dap, post-mortem, remote-debugging]
    related_skills: [requesting-code-review, debugging-hermes-tui-commands]
---

# Language Debuggers

Drive Python and Node.js debuggers programmatically from the terminal. When `print()` / `console.log()` isn't enough — real breakpoints, step in/over/out, call-stack walking, scope dumps, expression evaluation in paused frames.

1. **Section 1 — Python** (`breakpoint()` + `pdb` + `debugpy`)
2. **Section 2 — Node.js** (`node inspect` + CDP via `chrome-remote-interface` / `ndb`)

## When to Use (any language)

- Test fails and the traceback doesn't reveal why a value is wrong
- A function returns something unexpected — see the intermediate state
- A loop / callback has wrong data partway through
- Need to inspect closure scope, locals, or globals at a specific point
- Want to attach to an already-running process (gateway, daemon, PTY child)
- Non-interactive debugging from an agent loop — script many breakpoints, collect state across runs

## Universal Workflow

1. **Add a breakpoint** in the source
2. **Run under debugger** (or attach to running process)
3. **At the REPL:** inspect locals, evaluate expressions, walk the stack
4. **Step / continue** as needed
5. **Exit cleanly** so the process doesn't hang

## Tool Picker (any language)

| Need | Cheapest thing that works |
|------|---------------------------|
| Quick interactive poke at one line | Built-in REPL (`breakpoint()` / `node inspect`) |
| Headless / remote / attach-to-running | DAP-based tool (`debugpy` / CDP) |
| Non-interactive, scripted from agent | DAP-based tool with JSON API |
| Long-lived process (daemon, gateway) | `attach` mode, not launch |

---

## 1. Python Debugger (pdb + debugpy)

### Three Tools, Pick by Situation

| Tool | When |
|---|---|
| **`breakpoint()` + pdb** | Local, interactive, simplest. Add `breakpoint()` in the source, run normally, get a REPL at that line. |
| **`python -m pdb`** | Launch an existing script under pdb with no source edits. Useful for quick poking. |
| **`debugpy`** | Remote / headless / "attach to already-running process." Talks DAP, scriptable from terminal, works for long-lived processes (gateway, daemon, PTY children). |

**Start with `breakpoint()`.** It's the cheapest thing that works.

### Quick Start: `breakpoint()`

```python
# foo.py
def buggy(x):
    y = x * 2
    breakpoint()  # drops you into pdb here
    return y + 1

buggy(5)
```

```bash
python3 foo.py
# drops into (Pdb) REPL
```

`breakpoint()` is equivalent to `pdb.set_trace()` on Python 3.7+ and respects `PYTHONBREAKPOINT` env var.

### Quick Start: `python -m pdb` (no source edits)

```bash
python3 -m pdb foo.py
# or with args
python3 -m pdb foo.py arg1 arg2
```

### pdb Commands Cheat Sheet

| Command | Effect |
|---------|--------|
| `h` / `help` | List commands (or `h <cmd>` for detail) |
| `n` / `next` | Execute next line (step over) |
| `s` / `step` | Step into function call |
| `c` / `continue` | Continue execution until next breakpoint |
| `r` / `return` | Continue until current function returns |
| `u` / `up` | Move up one frame in the call stack |
| `d` / `down` | Move down one frame |
| `w` / `where` | Print current call stack with line numbers |
| `l` / `list` | Show source around current line |
| `ll` / `longlist` | Show entire current function |
| `p <expr>` | Print `repr(expr)` |
| `pp <expr>` | Pretty-print `expr` |
| `! <stmt>` | Execute a statement (bypass pdb commands) |
| `b <line>` | Set breakpoint at line (in current file) |
| `b <file>:<line>` | Set breakpoint in another file |
| `b <func>` | Set breakpoint at function entry |
| `cl` / `clear` | List / clear breakpoints |
| `q` / `quit` | Abort the program (no cleanup) |
| `interact` | Drop into a full Python REPL with current locals |
| `whatis <expr>` | Show type of expression |
| `source <obj>` | Show source of object |

### Post-Mortem Debugging

```bash
# Run with post-mortem
python3 -m pdb foo.py
# When the program crashes, pdb drops you at the exception line
```

```python
# Programmatic post-mortem
import pdb, sys
try:
    buggy_function()
except Exception:
    pdb.post_mortem(sys.exc_info()[2])
```

Or in code:

```python
def buggy():
    try:
        ...
    except Exception:
        import pdb; pdb.pm()  # drops into post-mortem at the except
        raise
```

### debugpy — Remote / Attach

**Install:** `pip install debugpy`

**Launch a script and wait for an attach:**

```python
# foo.py
import debugpy
debugpy.listen(("0.0.0.0", 5678))  # blocks until client attaches
# or use listen(5678) for default localhost
print("Waiting for debugger attach on 5678...")
debugpy.wait_for_client()
# your code here
```

```bash
python3 foo.py
# blocks until you attach from VS Code / a DAP client
```

**Attach to an already-running process:**

```python
# Add this to the running process (or have it in the codebase)
import debugpy
debugpy.listen(("0.0.0.0", 5678))  # if not already listening
# or use a side-channel: the process spawns this when a signal is received
```

For long-lived Hermes processes (gateway, daemon):

```python
# In your service's main loop, expose debugpy at a known port
import debugpy
try:
    debugpy.listen(("127.0.0.1", 5678))
except Exception as e:
    log(f"debugpy listen failed (port in use?): {e}")
```

Then attach from VS Code's "Run → Attach to Node/Python" or use a DAP client.

**debugpy common pitfalls:**
- Port 5678 in use → try a different port
- Firewall blocking → use `127.0.0.1` not `0.0.0.0` if local-only
- `wait_for_client()` blocks forever if no client attaches → use timeout or conditional

### Common Patterns

**Set a conditional breakpoint:**
```python
# In pdb:
b foo.py:42, x > 10
```

**Pretty-print a list of dicts:**
```python
# In pdb:
pp [{'k': v} for v in my_list]
```

**Step through a generator:**
```python
import pdb
pdb.set_trace()
gen = (i*2 for i in range(10))
# In pdb: n, then inspect gen, then continue and watch it tick
```

**Debug a hanging script — interrupt and inspect:**
```bash
# Send SIGINT
kill -SIGINT <pid>
# pdb drops into the current frame
```

---

## 2. Node.js Inspect Debugger

### Two Tools, Pick One

- **`node inspect`** — built-in, zero install, CLI REPL. Best for quick poking.
- **`ndb` / CDP via `chrome-remote-interface`** — scriptable from Node/Python; best when you want to automate many breakpoints, collect state across runs, or debug non-interactively from an agent loop.

**Prefer `node inspect` first.** It's always available and the REPL is fast.

### Quick Start: `node inspect`

```bash
# Launch a script under the inspector
node --inspect script.js
# Or pause on first line (don't continue until you connect)
node --inspect-brk script.js
```

Output:
```
Debugger listening on ws://127.0.0.1:9229/<uuid>
For help, see: https://nodejs.org/en/docs/inspector
```

**Connect with the built-in CLI REPL:**

```bash
node inspect 127.0.0.1:9229
# (or just `node inspect` if default port)
```

This is the same inspector as Chrome DevTools, but driven from a terminal REPL.

### Quick Start: CDP via `chrome-remote-interface`

```bash
npm install -g chrome-remote-interface
```

```javascript
// debug.js
const CDP = require('chrome-remote-interface');
(async () => {
  let client;
  try {
    client = await CDP({port: 9229});
    const {Debugger, Runtime} = client;
    await Debugger.enable();
    await Runtime.enable();

    // Set a breakpoint at script.js:42
    const {breakpointId} = await Debugger.setBreakpointByUrl({
      lineNumber: 42,
      url: 'file:///path/to/script.js',
    });

    // Subscribe to pause events
    Debugger.paused(({callFrames, reason, data}) => {
      const top = callFrames[0];
      console.log('Paused at', top.location.url + ':' + top.location.lineNumber);
      console.log('Locals:', top.scopeChain);
      // Evaluate something in the top frame
      Runtime.callFunctionOn({
        functionDeclaration: 'function() { return this.someVar; }',
        objectId: top.this.id,
      }).then(r => console.log('this.someVar =', r.result.value));
    });

  } catch (err) {
    console.error(err);
  } finally {
    if (client) await client.close();
  }
})();
```

### Useful Node.js Inspect Flags

| Flag | Effect |
|------|--------|
| `--inspect` | Open inspector, don't pause on entry |
| `--inspect-brk` | Open inspector, pause on first line |
| `--inspect-port=9229` | Custom port (default 9229) |
| `--inspect=0.0.0.0:9229` | Expose on all interfaces (security risk) |
| `--inspect-publish-uid=http` | Print URL to connect to (Docker / remote) |

### REPL Commands (`node inspect`)

The REPL is the Chrome DevTools protocol at the terminal. Key commands:

| Command | Effect |
|---------|--------|
| `c` / `cont` | Continue execution |
| `n` / `next` | Step over |
| `s` / `step` | Step into |
| `o` / `out` | Step out |
| `pause()` | Pause execution (from another connection) |
| `exec(expr)` | Evaluate in current frame |
| `setBreakpoint(line)` | Set breakpoint at line |
| `list()` | List breakpoints |
| `scripts` | List loaded scripts |
| `source()` | Show source of current frame |
| `frame(n)` | Switch to frame n |
| `.help` | Full help |

**Evaluate in paused frame:**

```bash
exec myVariable
exec JSON.stringify(myObject, null, 2)
exec someArray.filter(x => x > 10)
```

### Common Patterns

**Conditional breakpoint via CDP:**

```javascript
Debugger.setBreakpointByUrl({
  lineNumber: 42,
  url: 'file:///path/to/script.js',
  condition: 'i > 10',
});
```

**Inspect a closure variable in a callback:**

```bash
node inspect script.js
# At pause:
exec config  # closure var visible in scope chain
```

**Debug a hanging Node process — connect to it from a separate terminal:**

```bash
# Terminal 1: launch with --inspect
node --inspect server.js

# Terminal 2: attach
node inspect 127.0.0.1:9229
# Then `pause()` to interrupt
```

**Debug a TUI / Ink / React app — the renderer state is in a closure, not logged:**

```bash
node --inspect-brk ui-tui.js
node inspect 127.0.0.1:9229
# Walk the stack into the React component, inspect props/state
```

### Pitfalls

- **`--inspect` requires the WebSocket URL to be reachable.** Docker / WSL may need `--inspect=0.0.0.0:9229` and a port forward.
- **`node inspect` REPL doesn't support `import` syntax directly** — wrap in `exec(() => { ... })` for ESM.
- **Source maps** — breakpoints on the original source may not line up if your bundle is minified. Use `--enable-source-maps` and pre-built sources.
- **`pause()` only works on the same debugger session** — multiple clients can connect, but only one pauses at a time.
- **Hot reload can detach the inspector** — restart the process to re-attach.

---

## Tool Comparison

| | Python | Node.js |
|---|--------|---------|
| Built-in REPL | `python3 -m pdb script.py` | `node inspect` |
| Source-embedded breakpoint | `breakpoint()` | `debugger;` statement |
| Remote attach | `debugpy` (DAP) | CDP via `chrome-remote-interface` / `ndb` |
| Headless scripting | Python `debugpy` API | Node CDP client |
| Post-mortem | `pdb.pm()` or `pdb.post_mortem()` | `node --abort-on-uncaught-exception` + CDP replay |

Both ecosystems follow the same Debug Adapter Protocol (DAP) underneath — the wrappers just differ.

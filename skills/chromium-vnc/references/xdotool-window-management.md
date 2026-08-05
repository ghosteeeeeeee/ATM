# xdotool Window Management on VNC :1

Quick-reference patterns for controlling windows on a VNC X display. Pair with the
launch/verify commands in SKILL.md.

## Targeting windows

```bash
# List all windows on :1 (returns window IDs)
DISPLAY=:1 xdotool search --name ""

# Window count (sanity check that something is attached)
DISPLAY=:1 xdotool search --name "" | wc -l

# Get a window's title
DISPLAY=:1 xdotool getwindowname <wid>

# Loop and list all window titles
DISPLAY=:1 xdotool search --name "" | while read w; do
  echo "$w: $(DISPLAY=:1 xdotool getwindowname $w 2>/dev/null)"
done
```

## Activating / focusing

```bash
# Bring window to front and give it focus
DISPLAY=:1 xdotool windowactivate <wid>

# Click on a window (alternative to activate — works even if window is unmapped)
DISPLAY=:1 xdotool windowfocus <wid>
```

## Sizing / maximizing

```bash
# Resize to absolute pixel dimensions
DISPLAY=:1 xdotool windowsize <wid> 1920 1080

# Resize to full screen size (100% of X display)
DISPLAY=:1 xdotool windowsize <wid> 100% 100%

# Get current geometry (returns Position + Size)
DISPLAY=:1 xdotool getwindowgeometry <wid>

# Move window to top-left corner
DISPLAY=:1 xdotool windowmove <wid> 0 0
```

`windowsize 100% 100%` sets the window to the full screen pixel dimensions but does
NOT set the X11 `_NET_WM_STATE_MAXIMIZED` atom. Functionally equivalent (window fills
screen), but lacks the unmaximize toggle. Use `wmctrl` if you need a "real" maximize:

```bash
wmctrl -r :ACTIVE: -b add,maximized_vert,maximized_horz
```

## Common patterns

### Maximize a chromium window by name pattern

```bash
DISPLAY=:1 xdotool search --name "" | while read w; do
  name=$(DISPLAY=:1 xdotool getwindowname $w 2>/dev/null)
  if echo "$name" | grep -qiE "^chrome$|New Tab - Chromium"; then
    DISPLAY=:1 xdotool windowactivate $w
    DISPLAY=:1 xdotool windowsize $w 100% 100%
  fi
done
```

### Type into the focused window

```bash
DISPLAY=:1 xdotool type "hello world"
DISPLAY=:1 xdotool key Return
DISPLAY=:1 xdotool key ctrl+l    # focus address bar in browsers
```

### Close a window

```bash
DISPLAY=:1 xdotool windowclose <wid>
```

## Pitfalls

- **xdotool returns empty for unmapped windows.** If `search --name ""` returns 0
  windows, the X display has nothing attached — check `/tmp/.X11-unix/X1` exists
  and that your target app actually launched.
- **`windowactivate` may fail silently** if the window manager doesn't allow
  focus-stealing (rare on bare X, common in full WMs). Fall back to `windowfocus`
  or send a click via `xdotool mousemove --window <wid>` then `xdotool click 1`.
- **`getwindowname` on a foreign window can take a moment.** Wrap in retries if
  you call it immediately after launching a process.
- **Multiple windows share generic names** ("chrome", "Chromium clipboard"). Use
  `grep -iE` with a pattern OR use `--class` / `--pid` filters to disambiguate.
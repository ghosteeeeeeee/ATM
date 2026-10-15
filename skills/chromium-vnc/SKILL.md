---
name: chromium-vnc
description: Launch Chromium browser on a VNC display (default :1) with proper flags for root + VNC environment.
---

# chromium-vnc

Launch Chromium browser on a VNC display (default: `:1`).

## Trigger
Run chromium on a VNC display, e.g. "open chromium on VNC", "run chromium on display :1".

## Usage (preferred): the systemd service
Since 2026-10-15 Chromium runs as `chromium-vnc.service` — auto-starts on boot, auto-restarts on crash, and respects a clean close (no relaunch loop):

```bash
systemctl start chromium-vnc.service     # launch (no-op if already running)
systemctl stop chromium-vnc.service      # close Chromium cleanly
systemctl restart chromium-vnc.service   # restart browser
systemctl status chromium-vnc.service
journalctl -u chromium-vnc.service -n 20
```

It runs `launch_chromium.sh` (same dir as this SKILL.md), which waits for the X display, resolves the current snap revision, and launches with the real profile.

## Usage (manual): one-off launch
**Always launch with the existing snap user profile** to keep saved passwords, bookmarks, and history. A fresh `/tmp` profile is empty and loses everything on close.

```bash
/root/.hermes/skills/chromium-vnc/launch_chromium.sh
# or fully manual:
REV=$(ls /snap/chromium/ | grep -E '^[0-9]+$' | sort -n | tail -1)
DISPLAY=:1 /snap/chromium/$REV/usr/lib/chromium-browser/chrome \
  --no-sandbox --disable-gpu --disable-software-rasterizer \
  --no-first-run \
  --user-data-dir=/root/snap/chromium/common/chromium
```

## Finding the right profile
Two profiles typically exist on this box:
- `/root/snap/chromium/common/chromium/` — **the real one** (~1.8GB, has Bookmarks, recent activity, saved passwords). Use this.
- `/root/.config/chromium/` — stale/empty 32MB profile from March, no Bookmarks. Do NOT use unless intentionally starting fresh.

Quick check:
```bash
du -sh /root/snap/chromium/common/chromium/Default /root/.config/chromium/Default
test -f /root/snap/chromium/common/chromium/Default/Bookmarks && echo "snap: HAS bookmarks (real profile)"
test -f /root/.config/chromium/Default/Bookmarks && echo "config: HAS bookmarks" || echo "config: no bookmarks (stale)"
```

## Service layout (since 2026-10-14)
Xvfb and x11vnc are **separate systemd units** (`xvfb.service`, `x11vnc.service`) — do NOT recombine them into one ExecStart. The old single-unit `x11vnc.service` caused a recurring failure: unattended-upgrade installs new libs → needrestart's apt-pinvoke ran `systemctl restart x11vnc.service` → bundled Xvfb died → display :1 destroyed → Chromium killed ("X connection to :1 broken"). Happened on every upgrade touching libx11/libssl/etc (roughly every 1–3 days, always ~06:30 UTC).

Fixes in place:
- `/etc/systemd/system/xvfb.service` — owns Xvfb :1, `Restart=always`
- `/etc/systemd/system/x11vnc.service` — `Requires=xvfb.service`, only shares the display
- `/etc/systemd/system/chromium-vnc.service` — Chromium auto-start + crash recovery (`Restart=on-failure`, clean exit respected)
- `/etc/needrestart/conf.d/99-blacklist-vnc.conf` — blacklists Xvfb/x11vnc from needrestart restarts (Xvfb keeps old libs in memory until reboot; harmless for a display server)

If the display dies anyway: `systemctl status xvfb.service x11vnc.service`.

## Notes
- `--no-sandbox` required when running as root.
- `--disable-gpu` avoids GPU hardware acceleration issues in a headless VNC environment.
- Chromium attaches to the existing VNC session on that display.
- **Snap gpu-2404 wrapper is broken (as of 2026-07):** the `/usr/bin/chromium-browser` and `/snap/bin/chromium` shims call a `gpu-2404/bin/gpu-2404-provider-wrapper` that fails with `ensure slot is connected`, even though GPU is disabled. Workaround: invoke the inner snap chrome binary directly at `/snap/chromium/<rev>/usr/lib/chromium-browser/chrome`. Use `ls /snap/chromium/` to find current revision if 3464 changes.
- `--disable-software-rasterizer` further reduces GPU-adjacent failures on VNC.
- AppArmor/dbus warnings from snap are harmless — browser still functions.
- For headless mode (no visible window, useful for screenshots/DOM dumps):
  ```bash
  DISPLAY=:1 /snap/chromium/$REV/usr/lib/chromium-browser/chrome --no-sandbox --disable-gpu --headless --dump-dom https://example.com
  ```

## Verify it actually attached to the display
A fresh launch spawns ~10 child processes (zygote, gpu, network, storage, renderers). ps will also show a long-running Hermes `agent-browser-chrome` headless instance from `browser_navigate` — don't confuse the two.

Quick checks:
```bash
# Confirm X server is up
ls -la /tmp/.X11-unix/X1

# Find YOUR new launch (started in last few minutes)
ps -eo pid,etime,cmd | grep chromium-browser | grep -v headless

# Confirm X11 binding (look for --ozone-platform=x11; headless agent instance shows --ozone-platform=headless)
ps -eo pid,etime,cmd | grep "ozone-platform=x11" | grep -v grep

# Count windows visible to xdotool on :1
DISPLAY=:1 xdotool search --name "" | wc -l
```
A working launch shows: fresh etime, `--ozone-platform=x11` in the cmdline, and a non-zero window count from xdotool.

## Controlling the window (maximize, focus, type, close)

Once chromium is attached to :1, `xdotool` controls the window. See `references/xdotool-window-management.md` for full patterns. Common ones:

```bash
# Find window IDs and titles
DISPLAY=:1 xdotool search --name "" | while read w; do
  echo "$w: $(DISPLAY=:1 xdotool getwindowname $w 2>/dev/null)"
done

# Maximize a chromium window (size to full screen)
DISPLAY=:1 xdotool search --name "" | while read w; do
  name=$(DISPLAY=:1 xdotool getwindowname $w 2>/dev/null)
  if echo "$name" | grep -qiE "^chrome$|New Tab - Chromium"; then
    DISPLAY=:1 xdotool windowactivate $w
    DISPLAY=:1 xdotool windowsize $w 100% 100%
  fi
done

# Drive the browser (after focusing)
DISPLAY=:1 xdotool type "search query"
DISPLAY=:1 xdotool key Return
DISPLAY=:1 xdotool key ctrl+l    # focus address bar
```

Note: `xdotool windowsize 100% 100%` sets pixel dimensions to full screen but does NOT set the X11 `_NET_WM_STATE_MAXIMIZED` atom. Functionally equivalent for filling the screen, but lacks unmaximize toggle. Use `wmctrl -r :ACTIVE: -b add,maximized_vert,maximized_horz` if a "real" maximize state is required.
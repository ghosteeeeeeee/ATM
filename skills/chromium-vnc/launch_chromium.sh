#!/bin/bash
# chromium-vnc launcher — used by chromium-vnc.service (and safe to run manually).
# Launches Chromium on VNC display :1 with the real snap profile (bookmarks,
# passwords, history). See SKILL.md for context.
set -u

DISPLAY_NUM=":1"
PROFILE_DIR="/root/snap/chromium/common/chromium"

# Wait for the X display socket (xvfb.service may still be starting).
for _ in $(seq 1 30); do
    [ -S "/tmp/.X11-unix/X1" ] && break
    sleep 1
done
if [ ! -S "/tmp/.X11-unix/X1" ]; then
    echo "FATAL: display ${DISPLAY_NUM} socket /tmp/.X11-unix/X1 not found after 30s" >&2
    exit 1
fi

# Already running? Exit cleanly so systemd (Restart=on-failure) doesn't loop.
# Ignores the Hermes agent-browser headless instance (different user-data-dir,
# and excluded explicitly for safety).
for pid in $(pgrep -f "user-data-dir=${PROFILE_DIR}" 2>/dev/null); do
    if ! grep -q headless /proc/"$pid"/cmdline 2>/dev/null; then
        echo "Chromium already running (PID $pid) — nothing to do"
        exit 0
    fi
done

# Resolve newest snap revision. The /usr/bin and /snap/bin shims are broken
# (gpu-2404 wrapper), always invoke the inner snap binary directly.
REV=$(ls /snap/chromium/ | grep -E '^[0-9]+$' | sort -n | tail -1)
CHROME="/snap/chromium/${REV}/usr/lib/chromium-browser/chrome"
if [ ! -x "$CHROME" ]; then
    echo "FATAL: chrome binary not found at $CHROME" >&2
    exit 1
fi

echo "Launching Chromium rev ${REV} on ${DISPLAY_NUM} with profile ${PROFILE_DIR}"
exec env DISPLAY="${DISPLAY_NUM}" "${CHROME}" \
    --no-sandbox --disable-gpu --disable-software-rasterizer \
    --no-first-run \
    --user-data-dir="${PROFILE_DIR}"

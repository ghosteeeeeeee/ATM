# x11vnc Service Definition (working config)
**Path:** `/etc/systemd/system/x11vnc.service`
**Status:** `enabled`, `active (running)` as of 2026-05-15

## Service Definition

```ini
[Unit]
Description=X11VNC Server
After=network.target

[Service]
Type=simple
User=root
ExecStart=/bin/bash -c '/usr/bin/Xvfb :1 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset & sleep 2 && /usr/bin/x11vnc -display :1 -forever -shared -rfbport 5900 -localhost -rfbauth /root/.vnc/passwd'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## What this does

1. Starts Xvfb (virtual framebuffer) on display `:1` at 1920x1080x24
2. Waits 2 seconds for Xvfb to initialize
3. Starts x11vnc, attaches to display `:1`, listens on port 5900
4. `-localhost` flag = only accepts local connections (needs SSH tunnel for remote access)
5. `-rfbauth /root/.vnc/passwd` = VNC password authentication required

## Key behaviors

- X1 appears in `/tmp/.X11-unix/` once Xvfb starts
- x11vnc does NOT create the display — it only shares an existing one
- This setup uses Xvfb (headless virtual display), NOT the real X0 session
- Chromium tabs on the real display (X0) are NOT accessible via this setup

## To share real X0 session instead

Replace the ExecStart with direct x11vnc on X0 (no Xvfb):
```
ExecStart=/usr/bin/x11vnc -display :0 -forever -shared -rfbport 5900 -localhost -rfbauth /root/.vnc/passwd
```

## Verification commands

```bash
systemctl status x11vnc --no-pager
ss -tlnp | grep 5900        # should show x11vnc listening
ls /tmp/.X11-unix/          # should show X1 (Xvfb created)
```

## To connect remotely

SSH tunnel required (since -localhost flag):
```bash
ssh -L 5900:localhost:5900 user@host
# Then connect VNC client to localhost:5900
```

Or remove `-localhost` from ExecStart to accept external connections (insecure for internet-facing servers).
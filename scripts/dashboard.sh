#!/bin/bash
cd /root/.hermes
PIDFILE=/tmp/hermes-dashboard.pid
export PYTHONPATH=/root/.hermes/scripts:$PYTHONPATH

start() {
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "Dashboard already running at http://localhost:8501/learning"
        return
    fi
    nohup streamlit run /root/.hermes/scripts/hermes-dashboard.py \
        --server.headless=true \
        --server.port=8501 \
        --server.baseUrlPath=/learning \
        > /root/.hermes/data/dashboard.log 2>&1 &
    echo $! > "$PIDFILE"
    echo "Dashboard started at http://localhost:8501/learning"
    echo "External:    http://117.55.192.97:8501/learning"
    echo "via nginx:   http://117.55.192.97:54321/learning"
}

stop() {
    if [ -f "$PIDFILE" ]; then
        kill $(cat "$PIDFILE") 2>/dev/null && echo "Stopped" || echo "Not running"
        rm -f "$PIDFILE"
    else
        echo "Not running"
    fi
}

status() {
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "Running at http://localhost:8501/learning (PID $(cat $PIDFILE))"
    else
        echo "Not running"
    fi
}

case "${1:-start}" in
    start) start ;;
    stop)  stop ;;
    restart) stop; start ;;
    status) status ;;
    *) echo "Usage: $0 {start|stop|restart|status}" ;;
esac

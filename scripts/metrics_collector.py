#!/usr/bin/env python3
"""Write system metrics to JSON file for the resources dashboard."""
import sys, os, json, time, subprocess
sys.path.insert(0, '/root/.hermes/scripts')

from paths import *
METRICS_FILE = "/var/www/hermes/data/metrics.json"
os.makedirs("/var/www/hermes/data", exist_ok=True)

def get_metrics():
    import psutil

    # CPU
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_cores = psutil.cpu_count()

    # Load
    load1, load5, load15 = psutil.getloadavg()

    # RAM
    mem = psutil.virtual_memory()
    ram_used = f"{mem.used / (1024**3):.1f} GB"
    ram_total = f"{mem.total / (1024**3):.1f} GB"
    ram_pct = mem.percent

    # Disk
    disk = psutil.disk_usage('/')
    disk_used = f"{disk.used / (1024**3):.1f} GB"
    disk_total = f"{disk.total / (1024**3):.1f} GB"
    disk_pct = disk.percent

    # Network
    net = psutil.net_io_counters()
    network_ip = subprocess.check_output(['hostname', '-I'], text=True).strip().split()[0]

    # Uptime
    boot = psutil.boot_time()
    uptime_secs = time.time() - boot
    days = int(uptime_secs // 86400)
    hours = int((uptime_secs % 86400) // 3600)
    mins = int((uptime_secs % 3600) // 60)

    # Top local services by RAM (highest first), merged by name
    raw_procs = {}
    for p in psutil.process_iter(['pid', 'name', 'memory_percent', 'memory_info']):
        try:
            mi = p.info['memory_info']
            if mi and mi.rss > 0:
                name = p.info['name']
                if name not in raw_procs:
                    raw_procs[name] = {'rss': 0, 'pct': 0}
                raw_procs[name]['rss'] += mi.rss
                raw_procs[name]['pct'] += p.info['memory_percent']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    services = sorted(
        [{'name': n, 'rss_mb': round(v['rss'] / (1024 * 1024), 1), 'ram_pct': round(v['pct'], 1)}
         for n, v in raw_procs.items()],
        key=lambda x: x['rss_mb'], reverse=True
    )[:15]

    # Open ports (listening, merged by port+proto)
    ports = {}
    for c in psutil.net_connections(kind='inet'):
        if c.status == 'LISTEN' and c.laddr:
            proto = 'tcp' if c.type == 1 else 'udp'
            key = (c.laddr.port, proto)
            if key not in ports:
                try:
                    proc_name = psutil.Process(c.pid).name() if c.pid else '?'
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    proc_name = '?'
                ports[key] = {'port': c.laddr.port, 'proto': proto, 'proc': proc_name}
    open_ports = sorted(ports.values(), key=lambda x: x['port'])[:20]

    # Systemd timers
    try:
        out = subprocess.check_output(
            ['systemctl', 'list-timers', '--all', '--no-pager', '--plain', '--no-legend'],
            text=True, timeout=5
        )
        timers = []
        for line in out.strip().split('\n'):
            parts = line.split(None, 5)
            if len(parts) >= 5:
                timers.append({
                    'unit': parts[4],
                    'next': parts[0] + ' ' + parts[1] + ' ' + parts[2],
                    'last': parts[3] if parts[3] != '-' else 'n/a'
                })
        timers = timers[:15]
    except Exception:
        timers = []

    return {
        "cpu": {"usage": cpu_percent, "cores": cpu_cores},
        "load": {"load1": load1, "load5": load5, "load15": load15},
        "ram": {"percent": ram_pct, "used": ram_used, "total": ram_total},
        "disk": {"percent": disk_pct, "used": disk_used, "total": disk_total},
        "network": {"ip": network_ip},
        "uptime": {"days": days, "hours": hours, "mins": mins},
        "services": services,
        "open_ports": open_ports,
        "timers": timers,
        "timestamp": time.time()
    }

def main():
    while True:
        try:
            data = get_metrics()
            with open(METRICS_FILE, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Metrics error: {e}", file=sys.stderr)
        time.sleep(3)

if __name__ == '__main__':
    main()

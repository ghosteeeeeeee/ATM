#!/usr/bin/env python3
"""Write system metrics to JSON file for the resources dashboard."""
import sys, os, json, time, subprocess
sys.path.insert(0, '/root/.hermes/scripts')

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

    return {
        "cpu": {"usage": cpu_percent, "cores": cpu_cores},
        "load": {"load1": load1, "load5": load5, "load15": load15},
        "ram": {"percent": ram_pct, "used": ram_used, "total": ram_total},
        "disk": {"percent": disk_pct, "used": disk_used, "total": disk_total},
        "network": {"ip": network_ip},
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

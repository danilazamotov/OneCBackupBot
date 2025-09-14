from __future__ import annotations

import psutil
from pathlib import Path

def collect_system_metrics(backup_dir: Path):
    cpu = psutil.cpu_percent(interval=0.2)
    mem = psutil.virtual_memory().percent
    try:
        disk = psutil.disk_usage(str(backup_dir)).percent
    except Exception:
        disk = psutil.disk_usage("/").percent
    return {
        "cpu_percent": cpu,
        "mem_percent": mem,
        "disk_percent": disk,
    }

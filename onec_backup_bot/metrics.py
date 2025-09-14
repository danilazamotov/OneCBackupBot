from __future__ import annotations

import psutil
from pathlib import Path


def _cpu_percent_reliable() -> float:
    """Return CPU percent with better reliability on Windows Server.
    Strategy:
    - First try psutil.cpu_percent with a slightly larger interval (0.5s)
    - If it returns 0.0 (occasionally happens on some Windows Server setups),
      fallback to cpu_times_percent and compute 100 - idle.
    """
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        if cpu and cpu > 0.0:
            return float(cpu)
    except Exception:
        pass
    try:
        t = psutil.cpu_times_percent(interval=0.5)
        # Some platforms expose 'idle'; compute active = 100 - idle
        idle = getattr(t, "idle", None)
        if idle is not None:
            return max(0.0, min(100.0, 100.0 - float(idle)))
    except Exception:
        pass
    return 0.0


def collect_system_metrics(backup_dir: Path):
    cpu = _cpu_percent_reliable()
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

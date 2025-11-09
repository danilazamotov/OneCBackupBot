"""
Extended system metrics collection module
Collects comprehensive system information for monitoring
"""
from __future__ import annotations

import os
import platform
import psutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import socket


def get_rdp_sessions() -> List[Dict[str, str]]:
    """
    Get active RDP sessions on Windows
    Returns list of sessions with username, state, session_id
    """
    try:
        result = subprocess.run(
            ["qwinsta"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return []
        
        sessions = []
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        
        for line in lines:
            parts = line.split()
            if len(parts) >= 3:
                # Parse qwinsta output
                session = {
                    "username": parts[0] if parts[0] != '>' else parts[1],
                    "session_name": parts[1] if parts[0] == '>' else parts[0],
                    "session_id": parts[2] if parts[0] == '>' else parts[1],
                    "state": parts[3] if len(parts) > 3 else "unknown"
                }
                
                # Only count active sessions
                if session["state"].lower() == "active" and session["username"]:
                    sessions.append(session)
        
        return sessions
    except Exception:
        return []


def get_logged_in_users() -> List[Dict[str, Any]]:
    """Get all logged in users with detailed info"""
    users = []
    try:
        for user in psutil.users():
            users.append({
                "name": user.name,
                "terminal": user.terminal or "unknown",
                "host": user.host or "local",
                "started": datetime.fromtimestamp(user.started).isoformat(),
                "pid": user.pid if hasattr(user, 'pid') else None
            })
    except Exception:
        pass
    return users


def get_network_stats() -> Dict[str, Any]:
    """Get network interface statistics"""
    try:
        net_io = psutil.net_io_counters()
        net_connections = len(psutil.net_connections())
        
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "errin": net_io.errin,
            "errout": net_io.errout,
            "dropin": net_io.dropin,
            "dropout": net_io.dropout,
            "active_connections": net_connections
        }
    except Exception:
        return {}


def get_disk_io_stats() -> Dict[str, Any]:
    """Get disk I/O statistics"""
    try:
        disk_io = psutil.disk_io_counters()
        return {
            "read_count": disk_io.read_count,
            "write_count": disk_io.write_count,
            "read_bytes": disk_io.read_bytes,
            "write_bytes": disk_io.write_bytes,
            "read_time": disk_io.read_time,
            "write_time": disk_io.write_time
        }
    except Exception:
        return {}


def get_process_stats() -> Dict[str, Any]:
    """Get process statistics"""
    try:
        process_count = len(psutil.pids())
        
        # Top processes by CPU
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort by CPU usage
        top_cpu = sorted(processes, key=lambda x: x.get('cpu_percent', 0) or 0, reverse=True)[:5]
        top_mem = sorted(processes, key=lambda x: x.get('memory_percent', 0) or 0, reverse=True)[:5]
        
        return {
            "total_count": process_count,
            "top_cpu": [{"name": p['name'], "cpu": p.get('cpu_percent', 0)} for p in top_cpu],
            "top_memory": [{"name": p['name'], "mem": p.get('memory_percent', 0)} for p in top_mem]
        }
    except Exception:
        return {"total_count": 0}


def get_system_uptime() -> int:
    """Get system uptime in seconds"""
    try:
        boot_time = psutil.boot_time()
        return int(datetime.now().timestamp() - boot_time)
    except Exception:
        return 0


def get_cpu_detailed() -> Dict[str, Any]:
    """Get detailed CPU information"""
    try:
        cpu_freq = psutil.cpu_freq()
        cpu_times = psutil.cpu_times_percent(interval=1)
        
        return {
            "percent": psutil.cpu_percent(interval=1),
            "percent_per_cpu": psutil.cpu_percent(interval=1, percpu=True),
            "count_logical": psutil.cpu_count(logical=True),
            "count_physical": psutil.cpu_count(logical=False),
            "freq_current": cpu_freq.current if cpu_freq else 0,
            "freq_max": cpu_freq.max if cpu_freq else 0,
            "freq_min": cpu_freq.min if cpu_freq else 0,
            "user_time": cpu_times.user,
            "system_time": cpu_times.system,
            "idle_time": cpu_times.idle
        }
    except Exception:
        return {"percent": 0}


def get_memory_detailed() -> Dict[str, Any]:
    """Get detailed memory information"""
    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "free": mem.free,
            "percent": mem.percent,
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_free": swap.free,
            "swap_percent": swap.percent
        }
    except Exception:
        return {"percent": 0}


def get_disk_detailed(backup_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Get detailed disk information"""
    try:
        disks = {}
        
        # Get all disk partitions
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks[partition.device] = {
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent
                }
            except (PermissionError, OSError):
                continue
        
        # Add backup directory disk usage if specified
        if backup_dir and backup_dir.exists():
            try:
                backup_usage = psutil.disk_usage(str(backup_dir))
                return {
                    "all_disks": disks,
                    "backup_disk_total": backup_usage.total,
                    "backup_disk_used": backup_usage.used,
                    "backup_disk_free": backup_usage.free,
                    "backup_disk_percent": backup_usage.percent
                }
            except Exception:
                pass
        
        return {"all_disks": disks}
    except Exception:
        return {}


def get_system_info() -> Dict[str, str]:
    """Get static system information"""
    try:
        return {
            "hostname": socket.gethostname(),
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version()
        }
    except Exception:
        return {"hostname": "unknown"}


def collect_all_metrics(backup_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Collect ALL available system metrics
    This is the main function to use for comprehensive monitoring
    """
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "timestamp_unix": int(datetime.now().timestamp())
    }
    
    # System info
    metrics["system"] = get_system_info()
    metrics["uptime_seconds"] = get_system_uptime()
    
    # CPU
    cpu_data = get_cpu_detailed()
    metrics["cpu_percent"] = cpu_data.get("percent", 0)
    metrics["cpu"] = cpu_data
    
    # Memory
    mem_data = get_memory_detailed()
    metrics["memory_percent"] = mem_data.get("percent", 0)
    metrics["memory"] = mem_data
    
    # Disk
    disk_data = get_disk_detailed(backup_dir)
    metrics["disk_percent"] = disk_data.get("backup_disk_percent", 0)
    metrics["disk"] = disk_data
    
    # Disk I/O
    metrics["disk_io"] = get_disk_io_stats()
    
    # Network
    metrics["network"] = get_network_stats()
    
    # Processes
    metrics["processes"] = get_process_stats()
    
    # Users
    metrics["logged_users"] = get_logged_in_users()
    metrics["logged_users_count"] = len(metrics["logged_users"])
    
    # RDP Sessions (Windows only)
    if platform.system() == "Windows":
        rdp_sessions = get_rdp_sessions()
        metrics["rdp_sessions"] = rdp_sessions
        metrics["rdp_active_count"] = len(rdp_sessions)
    
    return metrics


def flatten_metrics_for_prometheus(metrics: Dict[str, Any]) -> Dict[str, float]:
    """
    Flatten nested metrics dictionary for Prometheus
    Converts nested dicts to flat structure with underscores
    """
    flat = {}
    
    def _flatten(data: Any, prefix: str = ""):
        if isinstance(data, dict):
            for key, value in data.items():
                new_key = f"{prefix}_{key}" if prefix else key
                _flatten(value, new_key)
        elif isinstance(data, (int, float)):
            flat[prefix] = float(data)
        elif isinstance(data, list):
            flat[f"{prefix}_count"] = float(len(data))
    
    _flatten(metrics)
    return flat

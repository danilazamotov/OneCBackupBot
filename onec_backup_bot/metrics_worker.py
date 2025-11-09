"""
Background worker for periodic metrics collection and sending to Grafana
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Optional

from .metrics_extended import collect_all_metrics, flatten_metrics_for_prometheus
from .grafana import GrafanaClient


class MetricsWorker:
    """Background thread that periodically collects and sends metrics"""
    
    def __init__(self, backup_dir: Path, logger, interval: int = 60):
        """
        Args:
            backup_dir: Path to backup directory for disk metrics
            logger: Logger instance
            interval: Metrics collection interval in seconds (default 60)
        """
        self.backup_dir = backup_dir
        self.logger = logger
        self.interval = int(os.getenv("METRICS_INTERVAL", interval))
        self.grafana = GrafanaClient(logger)
        
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
    def start(self):
        """Start the metrics worker thread"""
        if self._thread and self._thread.is_alive():
            self.logger.warning("Metrics worker already running")
            return
        
        # Check if any Grafana endpoint is configured
        if not any([
            self.grafana.prometheus_url,
            self.grafana.influxdb_url,
            self.grafana.loki_url
        ]):
            self.logger.info("No Grafana endpoints configured, metrics worker disabled")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="MetricsWorker")
        self._thread.start()
        self.logger.info(f"Metrics worker started (interval: {self.interval}s)")
    
    def stop(self):
        """Stop the metrics worker thread"""
        if not self._thread:
            return
        
        self.logger.info("Stopping metrics worker...")
        self._stop_event.set()
        
        if self._thread.is_alive():
            self._thread.join(timeout=5)
        
        self.logger.info("Metrics worker stopped")
    
    def _run(self):
        """Main worker loop"""
        while not self._stop_event.is_set():
            try:
                self._collect_and_send()
            except Exception as e:
                self.logger.error(f"Error in metrics worker: {e}", exc_info=True)
            
            # Sleep with interruptible wait
            self._stop_event.wait(timeout=self.interval)
    
    def _collect_and_send(self):
        """Collect metrics and send to all configured backends"""
        try:
            # Collect comprehensive metrics
            metrics = collect_all_metrics(self.backup_dir)
            
            # Flatten for Prometheus
            flat_metrics = flatten_metrics_for_prometheus(metrics)
            
            # Send to Prometheus/Grafana Cloud
            if self.grafana.prometheus_url:
                success = self.grafana.push_metrics_prometheus(flat_metrics)
                if success:
                    self.logger.debug(f"Sent {len(flat_metrics)} metrics to Prometheus")
            
            # Send to InfluxDB
            if self.grafana.influxdb_url:
                success = self.grafana.push_metrics_influxdb(flat_metrics)
                if success:
                    self.logger.debug(f"Sent {len(flat_metrics)} metrics to InfluxDB")
            
        except Exception as e:
            self.logger.error(f"Failed to collect/send metrics: {e}")
    
    def send_backup_event(self, status: str, message: str, size_bytes: Optional[int] = None, duration_sec: Optional[float] = None):
        """
        Send backup event to Grafana
        
        Args:
            status: 'success', 'failed', 'skipped'
            message: Event message
            size_bytes: Backup file size
            duration_sec: Backup duration
        """
        try:
            metadata = {}
            if size_bytes is not None:
                metadata['size_bytes'] = size_bytes
            if duration_sec is not None:
                metadata['duration_seconds'] = duration_sec
            
            self.grafana.push_backup_event(status, message, metadata)
            self.logger.debug(f"Backup event sent to Grafana: {status}")
        except Exception as e:
            self.logger.error(f"Failed to send backup event: {e}")

"""
Grafana/metrics integration module
Supports: Prometheus Pushgateway, InfluxDB, Loki
"""
from __future__ import annotations

import os
import json
import requests
from typing import Optional, Dict, Any
from datetime import datetime


class GrafanaClient:
    """Client for sending metrics to Grafana/Prometheus/InfluxDB"""
    
    def __init__(self, logger):
        self.logger = logger
        
        # Prometheus Push Gateway
        self.prometheus_url = os.getenv("GRAFANA_PROMETHEUS_URL") or os.getenv("PROMETHEUS_PUSHGATEWAY_URL")
        self.prometheus_user = os.getenv("GRAFANA_PROMETHEUS_USER")
        self.prometheus_password = os.getenv("GRAFANA_PROMETHEUS_PASSWORD")
        
        # Loki for logs
        self.loki_url = os.getenv("GRAFANA_LOKI_URL")
        self.loki_user = os.getenv("GRAFANA_LOKI_USER")
        self.loki_password = os.getenv("GRAFANA_LOKI_PASSWORD")
        
        # InfluxDB
        self.influxdb_url = os.getenv("INFLUXDB_URL")
        self.influxdb_token = os.getenv("INFLUXDB_TOKEN")
        self.influxdb_org = os.getenv("INFLUXDB_ORG")
        self.influxdb_bucket = os.getenv("INFLUXDB_BUCKET")
    
    def push_metrics_prometheus(self, metrics: Dict[str, Any], job: str = "onec_backup_bot") -> bool:
        """
        Send metrics to Prometheus Pushgateway endpoint
        
        Metrics format:
        {
            'cpu_percent': 45.2,
            'memory_percent': 67.1,
            'disk_percent': 82.3,
            ...
        }
        """
        if not self.prometheus_url:
            return False
        
        try:
            # Build Prometheus text format
            lines = []
            timestamp_ms = int(datetime.now().timestamp() * 1000)
            
            for metric_name, value in metrics.items():
                if value is None:
                    continue
                
                # Convert metric name to prometheus format
                prom_name = f"onec_{metric_name}"
                
                # Add TYPE and HELP comments for gauge metrics
                if metric_name.endswith('_percent') or metric_name.endswith('_count'):
                    lines.append(f"# TYPE {prom_name} gauge")
                
                # Add metric value with timestamp
                if isinstance(value, (int, float)):
                    lines.append(f"{prom_name} {value} {timestamp_ms}")
                elif isinstance(value, dict):
                    # Handle nested metrics with labels
                    for label_key, label_value in value.items():
                        if isinstance(label_value, (int, float)):
                            lines.append(f'{prom_name}{{{label_key}="{label_value}"}} {label_value} {timestamp_ms}')
            
            payload = "\n".join(lines) + "\n"
            
            # Determine endpoint (generic Pushgateway-compatible)
            url = f"{self.prometheus_url}/metrics/job/{job}"
            auth = None
            
            response = requests.post(
                url,
                data=payload,
                headers={"Content-Type": "text/plain"},
                auth=auth,
                timeout=10
            )
            
            if response.status_code in (200, 202):
                self.logger.debug(f"Metrics pushed to Prometheus: {len(metrics)} metrics")
                return True
            else:
                self.logger.warning(f"Failed to push metrics to Prometheus: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error pushing metrics to Prometheus: {e}")
            return False
    
    def push_metrics_influxdb(self, metrics: Dict[str, Any], measurement: str = "system_metrics") -> bool:
        """
        Send metrics to InfluxDB
        """
        if not self.influxdb_url or not self.influxdb_token:
            return False
        
        try:
            # Build InfluxDB Line Protocol
            lines = []
            timestamp_ns = int(datetime.now().timestamp() * 1_000_000_000)
            
            # Build tags and fields
            tags = f"host={os.environ.get('COMPUTERNAME', 'unknown')}"
            
            fields = []
            for key, value in metrics.items():
                if value is not None and isinstance(value, (int, float)):
                    fields.append(f"{key}={value}")
            
            if fields:
                line = f"{measurement},{tags} {','.join(fields)} {timestamp_ns}"
                lines.append(line)
            
            payload = "\n".join(lines)
            
            url = f"{self.influxdb_url}/api/v2/write?org={self.influxdb_org}&bucket={self.influxdb_bucket}&precision=ns"
            
            response = requests.post(
                url,
                data=payload,
                headers={
                    "Authorization": f"Token {self.influxdb_token}",
                    "Content-Type": "text/plain; charset=utf-8"
                },
                timeout=10
            )
            
            if response.status_code in (204, 200):
                self.logger.debug(f"Metrics pushed to InfluxDB: {len(metrics)} metrics")
                return True
            else:
                self.logger.warning(f"Failed to push metrics to InfluxDB: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error pushing metrics to InfluxDB: {e}")
            return False
    
    def push_log_loki(self, message: str, level: str = "info", labels: Optional[Dict[str, str]] = None) -> bool:
        """
        Send log message to Grafana Loki
        """
        if not self.loki_url:
            return False
        
        try:
            default_labels = {
                "job": "onec_backup_bot",
                "level": level,
                "host": os.environ.get('COMPUTERNAME', 'unknown')
            }
            
            if labels:
                default_labels.update(labels)
            
            # Build Loki JSON payload
            payload = {
                "streams": [
                    {
                        "stream": default_labels,
                        "values": [
                            [str(int(datetime.now().timestamp() * 1_000_000_000)), message]
                        ]
                    }
                ]
            }
            
            auth = (self.loki_user, self.loki_password) if self.loki_user else None
            
            response = requests.post(
                f"{self.loki_url}/loki/api/v1/push",
                json=payload,
                headers={"Content-Type": "application/json"},
                auth=auth,
                timeout=10
            )
            
            if response.status_code in (200, 204):
                return True
            else:
                self.logger.warning(f"Failed to push log to Loki: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error pushing log to Loki: {e}")
            return False
    
    def push_backup_event(self, status: str, message: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Push backup event to all configured backends
        """
        # Prepare metrics
        metrics = {
            "backup_status": 1 if status == "success" else 0,
            "backup_timestamp": int(datetime.now().timestamp())
        }
        
        if metadata:
            for key, value in metadata.items():
                if isinstance(value, (int, float)):
                    metrics[f"backup_{key}"] = value
        
        # Push to Prometheus
        if self.prometheus_url:
            self.push_metrics_prometheus(metrics, job="onec_backup_events")
        
        # Push to InfluxDB
        if self.influxdb_url:
            self.push_metrics_influxdb(metrics, measurement="backup_events")
        
        # Push log to Loki
        if self.loki_url:
            self.push_log_loki(
                message,
                level="info" if status == "success" else "error",
                labels={"event_type": "backup"}
            )

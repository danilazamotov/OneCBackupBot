from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

from aiohttp import web

from .metrics_extended import collect_all_metrics, flatten_metrics_for_prometheus


class APIServer:
    def __init__(self, *,
                 backup_service,
                 db,
                 logger,
                 api_host: str = "0.0.0.0",
                 api_port: int = 8080,
                 backup_dir: Path):
        self.backup_service = backup_service
        self.db = db
        self.logger = logger
        self.api_host = api_host
        self.api_port = int(api_port)
        self.backup_dir = backup_dir

        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None

    async def handle_health(self, request: web.Request) -> web.Response:
        last_ok = self.db.last_success()
        return web.json_response({
            "status": "ok",
            "last_backup": last_ok or None
        })

    async def handle_metrics(self, request: web.Request) -> web.Response:
        metrics = collect_all_metrics(self.backup_dir)
        return web.json_response(metrics)

    async def handle_backup_last(self, request: web.Request) -> web.Response:
        rows = self.db.recent_backups(limit=1)
        return web.json_response(rows[0] if rows else {})

    async def handle_metrics_prom(self, request: web.Request) -> web.Response:
        """Prometheus exposition format (text/plain)"""
        metrics = collect_all_metrics(self.backup_dir)
        flat = flatten_metrics_for_prometheus(metrics)
        # Build simple gauge metrics exposition
        lines = []
        for name, value in flat.items():
            prom_name = f"onec_{name}".replace('.', '_').replace('-', '_')
            lines.append(f"# TYPE {prom_name} gauge")
            lines.append(f"{prom_name} {value}")
        payload = "\n".join(lines) + "\n"
        return web.Response(text=payload, content_type="text/plain; version=0.0.4; charset=utf-8")

    def _build_app(self) -> web.Application:
        app = web.Application()
        app.add_routes([
            web.get("/api/health", self.handle_health),
            web.get("/api/metrics", self.handle_metrics),
            web.get("/api/backup/last", self.handle_backup_last),
            web.get("/api/metrics.prom", self.handle_metrics_prom),
        ])
        return app

    async def start(self):
        if self._runner:
            return
        self._app = self._build_app()
        self._runner = web.AppRunner(self._app, access_log=None)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, host=self.api_host, port=self.api_port)
        await self._site.start()
        self.logger.info(f"HTTP API started on http://{self.api_host}:{self.api_port}")

    async def stop(self):
        if self._site:
            await self._site.stop()
            self._site = None
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        self._app = None
        self.logger.info("HTTP API stopped")

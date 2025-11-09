from __future__ import annotations

import logging
from pathlib import Path

from telegram.ext import Application

from onec_backup_bot.config import load_config
from onec_backup_bot.logger import setup_logger
from onec_backup_bot.db import Database
from onec_backup_bot.backup import BackupService
from onec_backup_bot.bot import BotService
from onec_backup_bot.metrics_worker import MetricsWorker
from onec_backup_bot.api_server import APIServer


def main():
    cfg = load_config()

    # Prepare paths
    backup_dir = Path(cfg.backup.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Logger to backup_dir/log_file
    logger = setup_logger("OneCBackup", backup_dir, cfg.backup.log_file, level=logging.INFO)
    logger.info("Starting application")

    # SQLite database in backup_dir
    db_path = backup_dir / "app.sqlite3"
    db = Database(db_path)

    # Backup service
    backup_service = BackupService(
        onec_exe=cfg.onec.exe,
        base_path=cfg.onec.base_path,
        uc=cfg.onec.uc,
        up=cfg.onec.up,
        backup_dir=str(backup_dir),
        file_prefix=cfg.backup.file_prefix,
        logger=logger,
        db=db,
    )
    # Pass compression settings to the service
    setattr(backup_service, 'compress', cfg.backup.compress)
    setattr(backup_service, 'compress_level', cfg.backup.compress_level)
    setattr(backup_service, 'delete_dt_after_compress', cfg.backup.delete_dt_after_compress)

    # Start metrics worker for monitoring (optional, will auto-disable if no endpoints set)
    metrics_worker = MetricsWorker(backup_dir, logger)
    metrics_worker.start()

    # Start HTTP API server (pull model)
    api_server = APIServer(
        backup_service=backup_service,
        db=db,
        logger=logger,
        api_host=cfg.api.host,
        api_port=cfg.api.port,
        backup_dir=backup_dir,
    )

    # Run API server in background event loop
    import threading, asyncio
    api_loop = asyncio.new_event_loop()
    api_thread = threading.Thread(target=lambda: (api_loop.run_until_complete(api_server.start()), api_loop.run_forever()),
                                  name="APIServer", daemon=True)
    api_thread.start()

    # Telegram bot
    if not cfg.telegram.bot_token:
        logger.error("BOT_TOKEN is not set. Fill .env or config.yaml")
        logger.error("Application cannot run without Telegram bot token.")
        return

    application = Application.builder().token(cfg.telegram.bot_token).build()
    BotService(
        application=application,
        allowed_user_ids=cfg.security.allowed_user_ids,
        backup_service=backup_service,
        db=db,
        logger=logger,
        cfg=cfg,
    )

    logger.info("Bot started - manual backup mode")
    try:
        application.run_polling(drop_pending_updates=True)
    finally:
        logger.info("Shutting down...")
        # Stop API server
        try:
            if 'api_loop' in locals():
                api_loop.call_soon_threadsafe(lambda: asyncio.ensure_future(api_server.stop(), loop=api_loop))
                api_loop.call_soon_threadsafe(api_loop.stop)
                if 'api_thread' in locals() and api_thread.is_alive():
                    api_thread.join(timeout=5)
        except Exception:
            pass
        # Stop metrics worker
        metrics_worker.stop()
        logger.info("Stopped")


if __name__ == "__main__":
    main()

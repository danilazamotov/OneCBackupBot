from __future__ import annotations

import time
import logging
from pathlib import Path
import datetime as dt

from telegram.ext import Application

from onec_backup_bot.config import load_config
from onec_backup_bot.logger import setup_logger
from onec_backup_bot.db import Database
from onec_backup_bot.backup import BackupService
from onec_backup_bot.metrics import collect_system_metrics
from onec_backup_bot.uptime import push_status
from onec_backup_bot.scheduler import SchedulerService
from onec_backup_bot.bot import BotService


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

    # Services
    backup_service = BackupService(
        onec_exe=cfg.onec.exe,
        base_path=cfg.onec.base_path,
        uc=cfg.onec.uc,
        up=cfg.onec.up,
        backup_dir=str(backup_dir),
        file_prefix=cfg.backup.file_prefix,
        keep_hourly_days=cfg.backup.keep_hourly_days,
        keep_daily_count=cfg.backup.keep_daily_count,
        keep_monthly_count=cfg.backup.keep_monthly_count,
        daily_copy_hour=cfg.backup.daily_copy_hour,
        monthly_copy_day=cfg.backup.monthly_copy_day,
        monthly_copy_hour=cfg.backup.monthly_copy_hour,
        logger=logger,
        db=db,
        uptime_push_url=cfg.uptime_kuma.push_url,
    )
    # Pass compression settings to the service
    setattr(backup_service, 'compress', cfg.backup.compress)
    setattr(backup_service, 'compress_level', cfg.backup.compress_level)
    setattr(backup_service, 'delete_dt_after_compress', cfg.backup.delete_dt_after_compress)
    # Pass subdirectory names
    setattr(backup_service, 'hourly_subdir', cfg.backup.hourly_subdir)
    setattr(backup_service, 'daily_subdir', cfg.backup.daily_subdir)
    setattr(backup_service, 'monthly_subdir', cfg.backup.monthly_subdir)
    setattr(backup_service, 'yearly_subdir', cfg.backup.yearly_subdir)
    setattr(backup_service, 'halfyearly_subdir', cfg.backup.halfyearly_subdir)
    # Pass yearly/halfyearly rotation config
    setattr(backup_service, 'yearly_copy_month', cfg.backup.yearly_copy_month)
    setattr(backup_service, 'yearly_copy_day', cfg.backup.yearly_copy_day)
    setattr(backup_service, 'yearly_copy_hour', cfg.backup.yearly_copy_hour)
    setattr(backup_service, 'keep_yearly_count', cfg.backup.keep_yearly_count)
    setattr(backup_service, 'halfyearly_months', cfg.backup.halfyearly_months)
    setattr(backup_service, 'halfyearly_copy_day', cfg.backup.halfyearly_copy_day)
    setattr(backup_service, 'halfyearly_copy_hour', cfg.backup.halfyearly_copy_hour)
    setattr(backup_service, 'keep_halfyearly_count', cfg.backup.keep_halfyearly_count)

    # Scheduler
    scheduler = SchedulerService(timezone=cfg.app.timezone, logger=logger)

    def job_backup():
        now = dt.datetime.now()
        if 0 <= now.hour < 8:
            logger.info("Quiet hours (00:00-07:59). Skipping scheduled backup.")
            push_status(cfg.uptime_kuma.push_url, "up", "Quiet hours skip")
            return
        logger.info("Scheduled backup starting")
        path = backup_service.make_backup()
        backup_service.rotate_backups(path)

    def job_metrics():
        try:
            m = collect_system_metrics(backup_dir)
            db.insert_metrics(ts=dt.datetime.now(),
                              cpu_percent=m['cpu_percent'], mem_percent=m['mem_percent'], disk_percent=m['disk_percent'])
            push_status(cfg.uptime_kuma.push_url, "up", f"CPU {m['cpu_percent']:.0f} RAM {m['mem_percent']:.0f}")
        except Exception as e:
            logger.warning(f"Metrics job failed: {e}")

    scheduler.add_cron_job(job_backup, cfg.scheduler.backup_cron, id="backup")
    scheduler.add_cron_job(job_metrics, cfg.scheduler.metrics_cron, id="metrics")

    scheduler.start()

    # Telegram bot
    if not cfg.telegram.bot_token:
        logger.error("BOT_TOKEN is not set. Fill .env or config.yaml")
        logger.info("Scheduler will continue to run without Telegram bot.")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            logger.info("Shutting down scheduler")
            scheduler.shutdown()
            logger.info("Stopped")
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

    logger.info("Bot started")
    try:
        application.run_polling(drop_pending_updates=True)
    finally:
        logger.info("Shutting down scheduler")
        scheduler.shutdown()
        logger.info("Stopped")


if __name__ == "__main__":
    main()

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

import yaml
from dotenv import load_dotenv


@dataclass
class AppConfig:
    name: str = "OneC Backup Bot"
    timezone: str = "Europe/Moscow"


@dataclass
class SecurityConfig:
    allowed_user_ids: List[int] = field(default_factory=list)


@dataclass
class OneCConfig:
    exe: str = r"C:\\Program Files\\1cv8\\8.3.23.1865\\bin\\1cv8.exe"
    base_path: str = r"C:\\1C_Bases\\Zernosbyt"
    uc: str = ""
    up: str = ""


@dataclass
class BackupConfig:
    backup_dir: str = r"D:\\1C_Backups"
    log_file: str = "backup.log"
    hourly_subdir: str = "Hourly"
    daily_subdir: str = "Daily"
    monthly_subdir: str = "Monthly"
    keep_hourly_days: int = 3
    keep_daily_count: int = 30
    keep_monthly_count: int = 12
    daily_copy_hour: int = 23
    monthly_copy_day: int = 1
    monthly_copy_hour: int = 23
    file_prefix: str = "Zernosbyt_"
    compress: str = "none"  # none|zip
    compress_level: int = 6  # 0-9 for zip
    delete_dt_after_compress: bool = False
    # Yearly rotation
    yearly_subdir: str = "Yearly"
    yearly_copy_month: int = 1   # январь
    yearly_copy_day: int = 1
    yearly_copy_hour: int = 23
    keep_yearly_count: int = 5   # хранить 3–5 лет
    # Half-Yearly rotation (полугодовые чекпоинты)
    halfyearly_subdir: str = "HalfYearly"
    halfyearly_months: list[int] = field(default_factory=lambda: [1, 7])
    halfyearly_copy_day: int = 1
    halfyearly_copy_hour: int = 23
    keep_halfyearly_count: int = 6


@dataclass
class SchedulerConfig:
    backup_cron: str = "5 * * * *"  # every hour at minute 5
    metrics_cron: str = "*/5 * * * *"  # every 5 minutes


@dataclass
class UptimeKumaConfig:
    push_url: str = ""


@dataclass
class TelegramConfig:
    bot_token: str = ""
    broadcast_chat_id: str = ""


@dataclass
class Config:
    app: AppConfig = field(default_factory=AppConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    onec: OneCConfig = field(default_factory=OneCConfig)
    backup: BackupConfig = field(default_factory=BackupConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    uptime_kuma: UptimeKumaConfig = field(default_factory=UptimeKumaConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)


def load_config(config_path: Optional[Path] = None) -> Config:
    # Load .env first
    load_dotenv(override=False)

    # Load YAML
    data = {}
    if config_path is None:
        config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    def _get(path, default=None):
        cur = data
        for p in path.split('.'):
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                return default
        return cur

    cfg = Config(
        app=AppConfig(
            name=_get("app.name", "OneC Backup Bot"),
            timezone=_get("app.timezone", "Europe/Moscow"),
        ),
        security=SecurityConfig(
            allowed_user_ids=_get("security.allowed_user_ids", []) or [],
        ),
        onec=OneCConfig(
            exe=_get("onec.exe", OneCConfig.exe),
            base_path=_get("onec.base_path", OneCConfig.base_path),
            uc=os.getenv("ONEC_UC", _get("onec.uc", OneCConfig.uc)),
            up=os.getenv("ONEC_UP", _get("onec.up", OneCConfig.up)),
        ),
        backup=BackupConfig(
            backup_dir=_get("backup.backup_dir", BackupConfig.backup_dir),
            log_file=_get("backup.log_file", BackupConfig.log_file),
            hourly_subdir=_get("backup.hourly_subdir", BackupConfig.hourly_subdir),
            daily_subdir=_get("backup.daily_subdir", BackupConfig.daily_subdir),
            monthly_subdir=_get("backup.monthly_subdir", BackupConfig.monthly_subdir),
            keep_hourly_days=int(_get("backup.keep_hourly_days", BackupConfig.keep_hourly_days)),
            keep_daily_count=int(_get("backup.keep_daily_count", BackupConfig.keep_daily_count)),
            keep_monthly_count=int(_get("backup.keep_monthly_count", BackupConfig.keep_monthly_count)),
            daily_copy_hour=int(_get("backup.daily_copy_hour", BackupConfig.daily_copy_hour)),
            monthly_copy_day=int(_get("backup.monthly_copy_day", BackupConfig.monthly_copy_day)),
            monthly_copy_hour=int(_get("backup.monthly_copy_hour", BackupConfig.monthly_copy_hour)),
            file_prefix=_get("backup.file_prefix", BackupConfig.file_prefix),
            compress=str(_get("backup.compress", BackupConfig.compress)).lower(),
            compress_level=int(_get("backup.compress_level", BackupConfig.compress_level)),
            delete_dt_after_compress=bool(_get("backup.delete_dt_after_compress", BackupConfig.delete_dt_after_compress)),
            yearly_subdir=_get("backup.yearly_subdir", BackupConfig.yearly_subdir),
            yearly_copy_month=int(_get("backup.yearly_copy_month", BackupConfig.yearly_copy_month)),
            yearly_copy_day=int(_get("backup.yearly_copy_day", BackupConfig.yearly_copy_day)),
            yearly_copy_hour=int(_get("backup.yearly_copy_hour", BackupConfig.yearly_copy_hour)),
            keep_yearly_count=int(_get("backup.keep_yearly_count", BackupConfig.keep_yearly_count)),
            halfyearly_subdir=_get("backup.halfyearly_subdir", BackupConfig.halfyearly_subdir),
            halfyearly_months=_get("backup.halfyearly_months", [1, 7]) or [1, 7],
            halfyearly_copy_day=int(_get("backup.halfyearly_copy_day", BackupConfig.halfyearly_copy_day)),
            halfyearly_copy_hour=int(_get("backup.halfyearly_copy_hour", BackupConfig.halfyearly_copy_hour)),
            keep_halfyearly_count=int(_get("backup.keep_halfyearly_count", BackupConfig.keep_halfyearly_count)),
        ),
        scheduler=SchedulerConfig(
            backup_cron=_get("scheduler.backup_cron", SchedulerConfig.backup_cron),
            metrics_cron=_get("scheduler.metrics_cron", SchedulerConfig.metrics_cron),
        ),
        uptime_kuma=UptimeKumaConfig(
            push_url=os.getenv("UPTIME_KUMA_PUSH_URL", _get("uptime_kuma.push_url", "")),
        ),
        telegram=TelegramConfig(
            bot_token=os.getenv("BOT_TOKEN", _get("telegram.bot_token", "")),
            broadcast_chat_id=_get("telegram.broadcast_chat_id", ""),
        ),
    )

    # Merge allowed user IDs from env (comma-separated) if present
    env_allowed = os.getenv("ALLOWED_USER_IDS", "").strip()
    if env_allowed:
        try:
            ids = [int(x) for x in env_allowed.split(',') if x.strip()]
            cfg.security.allowed_user_ids = sorted(set(cfg.security.allowed_user_ids + ids))
        except Exception:
            pass

    # Normalize paths
    cfg.backup.backup_dir = str(Path(cfg.backup.backup_dir))
    return cfg

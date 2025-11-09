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
    file_prefix: str = "Zernosbyt_"
    compress: str = "none"  # none|zip
    compress_level: int = 6  # 0-9 for zip
    delete_dt_after_compress: bool = False


@dataclass
class TelegramConfig:
    bot_token: str = ""
    broadcast_chat_id: str = ""


@dataclass
class ApiConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    token: str = ""


@dataclass
class Config:
    app: AppConfig = field(default_factory=AppConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    onec: OneCConfig = field(default_factory=OneCConfig)
    backup: BackupConfig = field(default_factory=BackupConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    api: ApiConfig = field(default_factory=ApiConfig)


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
            exe=os.getenv("ONEC_EXE", _get("onec.exe", OneCConfig.exe)),
            base_path=os.getenv("ONEC_BASE_PATH", _get("onec.base_path", OneCConfig.base_path)),
            uc=os.getenv("ONEC_UC", _get("onec.uc", OneCConfig.uc)),
            up=os.getenv("ONEC_UP", _get("onec.up", OneCConfig.up)),
        ),
        backup=BackupConfig(
            backup_dir=os.getenv("BACKUP_DIR", _get("backup.backup_dir", BackupConfig.backup_dir)),
            log_file=_get("backup.log_file", BackupConfig.log_file),
            file_prefix=_get("backup.file_prefix", BackupConfig.file_prefix),
            compress=str(_get("backup.compress", BackupConfig.compress)).lower(),
            compress_level=int(_get("backup.compress_level", BackupConfig.compress_level)),
            delete_dt_after_compress=bool(_get("backup.delete_dt_after_compress", BackupConfig.delete_dt_after_compress)),
        ),
        telegram=TelegramConfig(
            bot_token=os.getenv("BOT_TOKEN", _get("telegram.bot_token", "")),
            broadcast_chat_id=_get("telegram.broadcast_chat_id", ""),
        ),
        api=ApiConfig(
            host=os.getenv("API_HOST", _get("api.host", ApiConfig.host)),
            port=int(os.getenv("API_PORT", _get("api.port", ApiConfig.port))),
            token=os.getenv("API_TOKEN", _get("api.token", ApiConfig.token)),
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

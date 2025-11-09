from __future__ import annotations

import asyncio
import io
import textwrap
from pathlib import Path
from typing import List

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from .metrics import collect_system_metrics


def _is_allowed(user_id: int, allowed: List[int]) -> bool:
    return (not allowed) or (user_id in allowed)


class BotService:
    def __init__(self, *, application: Application, allowed_user_ids: List[int],
                 backup_service, db, logger, cfg):
        self.app = application
        self.allowed = allowed_user_ids
        self.backup_service = backup_service
        self.db = db
        self.logger = logger
        self.cfg = cfg

        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("backup", self.cmd_backup))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("health", self.cmd_health))
        self.app.add_handler(CommandHandler("lastlog", self.cmd_lastlog))

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_help(update, context)

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user is None:
            return
        if not _is_allowed(user.id, self.allowed):
            await update.effective_message.reply_text("Access denied")
            return
        text = textwrap.dedent(
            """
            Команды:
            /backup — выполнить резервное копирование
            /status — последние результаты бэкапов
            /health — состояние системы (CPU, RAM, Disk)
            /lastlog — последние строки лога
            
            Режим работы: только ручные резервные копии через бота
            """
        ).strip()
        await update.effective_message.reply_text(text)

    async def cmd_backup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user is None:
            return
        if not _is_allowed(user.id, self.allowed):
            await update.effective_message.reply_text("Access denied")
            return
        await update.effective_message.reply_text("Запускаю бэкап...")
        try:
            path = await asyncio.to_thread(self.backup_service.make_backup)
            if path:
                await update.effective_message.reply_text(f"✅ Готово: {path}")
            else:
                await update.effective_message.reply_text("⚠️ Бэкап не создан (нет изменений или ошибка), см. лог")
        except Exception as e:
            self.logger.exception("/backup failed: %s", e)
            await update.effective_message.reply_text(f"❌ Исключение: {e}")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user is None:
            return
        if not _is_allowed(user.id, self.allowed):
            await update.effective_message.reply_text("Access denied")
            return
        rows = self.db.recent_backups(limit=20)
        if not rows:
            await update.effective_message.reply_text("Данных пока нет")
            return
        overall_code = 200
        for r in rows:
            st = (r["status"] or "").upper()
            if st == "OK":
                break
            if st in {"ERR", "EXC"}:
                overall_code = 500
                break
            if st == "SKIP" and overall_code != 500:
                overall_code = 204
        header = f"Общий статус: {overall_code}"
        lines = [header, "Последние бэкапы:"]
        for r in rows:
            size = (r["size_bytes"] or 0)
            dur = (r["duration_sec"] or 0)
            lines.append(f"{r['ts']} | {r['status']} | rc={r['rc']} | size={size} | t={dur:.1f}s")
        await update.effective_message.reply_text("\n".join(lines))

    async def cmd_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user is None:
            return
        if not _is_allowed(user.id, self.allowed):
            await update.effective_message.reply_text("Access denied")
            return
        m = collect_system_metrics(Path(self.cfg.backup.backup_dir))
        last_b = self.db.last_success()
        last_b_text = f"{last_b['ts']} size={last_b['size_bytes']}" if last_b else "нет"
        text = (
            f"CPU: {m['cpu_percent']:.1f}%\n"
            f"RAM: {m['mem_percent']:.1f}%\n"
            f"Disk: {m['disk_percent']:.1f}%\n"
            f"Последний успешный бэкап: {last_b_text}"
        )
        await update.effective_message.reply_text(text)

    async def cmd_lastlog(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user is None:
            return
        if not _is_allowed(user.id, self.allowed):
            await update.effective_message.reply_text("Access denied")
            return
        log_path = Path(self.cfg.backup.backup_dir) / self.cfg.backup.log_file
        if not log_path.exists():
            await update.effective_message.reply_text("Лог пока отсутствует")
            return
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()[-100:]
            text = "".join(lines)
            bio = io.BytesIO(text.encode("utf-8"))
            bio.name = "backup.log.txt"
            await update.effective_message.reply_document(bio)
        except Exception as e:
            await update.effective_message.reply_text(f"Ошибка чтения лога: {e}")


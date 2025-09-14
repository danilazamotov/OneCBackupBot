# OneC Backup Bot

Инструмент для резервного копирования файловой базы 1С, с телеграм‑ботом управления, журналом событий, планировщиком задач и ротациями копий.

## Возможности
- Выгрузка базы 1С в `.dt` через `DESIGNER /F ... /DumpIB` (поддержка авторизации `/N` и `/P`).
- Дополнительная упаковка в ZIP (настраиваемая степень сжатия).
- Ротации: Hourly / Daily / Monthly / Yearly / Half‑Yearly.
- Телеграм‑бот: `/backup`, `/status`, `/health`, `/lastlog`, `/schedule`.
- Метрики (CPU, RAM, Disk) и запись в SQLite.
- Uptime Kuma push‑уведомления (опционально).
- Защита от параллельных бэкапов (глобальный lock) и таймаут дампа.

## Быстрый старт
1) Требования: Windows, Python 3.10+, установленный 1С (путь к `1cv8.exe`).
2) Создайте виртуальное окружение и установите зависимости:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
3) Заполните `.env` (копия из `.env.example`):
```
BOT_TOKEN=...
ALLOWED_USER_IDS=11111111
# при необходимости:
ONEC_UC=Администратор
ONEC_UP=пароль
```
4) Отредактируйте `config.yaml`:
- `onec.exe` — путь к `1cv8.exe` (экранируйте `\` или используйте одинарные кавычки)
- `onec.base_path` — папка с вашей `1Cv8.1CD`
- `backup.backup_dir` — каталог для бэкапов (будет создан)
- при необходимости обновите расписание и политики хранения

5) Запуск:
```powershell
python main.py
```
В Telegram:
- `/help` — список команд
- `/backup` — создать копию сейчас
- `/schedule` — человеко‑читаемое расписание

## Настройка расписания
В `config.yaml`:
- `scheduler.backup_cron: "5 13,18 * * *"` — каждый день в 13:05 и 18:05
- `scheduler.metrics_cron: "*/5 * * * *"` — каждые 5 минут
Примечание: есть «тихие часы» 00:00–07:59 — в этот период плановый бэкап пропускается.

## S3 (оффсайт) — рекомендуемая схема при лимите 20 ГБ
- Держать РОВНО две копии с перезаписью (фиксированные имена):
  - `OneC/weekly/backup.zip` — воскресенье 06:00
  - `OneC/monthly/backup.zip` — 1‑е число 06:10
- Грузить через `rclone copyto` из локальных `Daily`/`Monthly`.
- Версионирование бакета — опционально (для weekly с noncurrent=1 день), если позволяет квота.

Примеры скриптов и подробности — см. `OPERATIONS.md`.

## Структура
- `main.py` — точка входа
- `onec_backup_bot/backup.py` — бэкап и ротации
- `onec_backup_bot/bot.py` — телеграм‑команды
- `onec_backup_bot/config.py` — конфигурация
- `onec_backup_bot/db.py` — SQLite
- `onec_backup_bot/logger.py` — логирование
- `onec_backup_bot/metrics.py` — метрики
- `onec_backup_bot/scheduler.py` — планировщик APScheduler
- `onec_backup_bot/uptime.py` — отправка в Uptime Kuma
- `config.yaml` — настройки окружения

## Безопасность
- Пароль 1С в логах маскируется.
- Не коммитьте `.env` (исключён в `.gitignore`).

## Лицензия
Proprietary/Internal (уточните при необходимости).

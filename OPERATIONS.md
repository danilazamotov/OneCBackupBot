# OneC Backup Bot — Операционная инструкция

Эта инструкция описывает полный цикл: установка, конфигурация, проверка, тестирование, развёртывание как сервиса, а также оффсайт‑резервирование в S3 с минимальными затратами места.

## 1. Требования
- Windows Server 2019/2022, Python 3.10+
- 1С 8.3 (тонкий клиент) — корректный путь к `1cv8.exe`
- Интернет (Telegram, Uptime Kuma по желанию)

## 2. Установка
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env -Force
```

## 3. Настройка
- `.env` — заполните `BOT_TOKEN`, `ALLOWED_USER_IDS`, при необходимости `ONEC_UC`/`ONEC_UP`, `UPTIME_KUMA_PUSH_URL`.
- `config.yaml` — проверьте поля:
  - `onec.exe` — путь к `1cv8.exe` (экранируйте `\` или используйте одинарные кавычки)
  - `onec.base_path` — каталог с `1Cv8.1CD`
  - `backup.backup_dir` — каталог для бэкапов
  - Политики хранения и расписания

## 4. Запуск и тест
```powershell
python main.py
```
В Telegram проверьте:
- `/help`, `/schedule` — человеко‑читаемое расписание
- `/backup` — создаст `.dt` (и `.zip`, если включено)
- `/status` — общий код и список последних бэкапов
- `/lastlog` — последние строки лога как файл

Проверьте на диске `backup_dir`:
- `Hourly/` — появился файл
- `backup.log` — содержит события
- `app.sqlite3` — история

## 5. Ротации
- Hourly — хранение `keep_hourly_days` дней.
- Daily — один файл в сутки в `daily_copy_hour`, хранение `keep_daily_count`.
- Monthly — в `monthly_copy_day`/`monthly_copy_hour`, хранение `keep_monthly_count`.
- Yearly — в `yearly_copy_month/day/hour`, хранение `keep_yearly_count`.
- Half‑Yearly — месяцы `halfyearly_months` (по умолчанию январь/июль), хранение `keep_halfyearly_count`.

## 6. Метрики и мониторинг
- Каждые `*/5` минут собираются метрики CPU/RAM/Disk, пишутся в SQLite.
- Если указан `uptime_kuma.push_url`, отправляются push‑сигналы `up/down`.

## 7. S3 (оффсайт) при лимите 20 ГБ
- Хранить только две копии в бакете с перезаписью (фиксированные имена):
  - `OneC/weekly/backup.zip` — каждое воскресенье 06:00
  - `OneC/monthly/backup.zip` — 1‑го числа 06:10
- `rclone` пример конфига:
```powershell
rclone config create swebs3 s3 env_auth=false provider=Other ^
  access_key_id=YOUR_KEY secret_access_key=YOUR_SECRET ^
  endpoint=https://<ваш_s3_endpoint> region=us-east-1
```
- Weekly‑скрипт:
```powershell
$SrcDir = "D:\1C_Backups\Daily"  # или ваш путь
$Latest = Get-ChildItem -Path $SrcDir -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($Latest) { rclone copyto "$($Latest.FullName)" "swebs3:OneC/weekly/backup$($Latest.Extension)" --transfers=1 --checkers=2 --fast-list }
```
- Monthly‑скрипт аналогично, только `monthly`.

Рекомендации:
- По возможности включить versioning и lifecycle на weekly (неактуальные версии 1 день).
- Использовать отдельный ключ доступа, ограниченный на бакет/префикс.

## 8. Запуск как сервис
- NSSM (рекомендуется):
  - Application: `...\.venv\Scripts\python.exe`
  - Arguments: `...\main.py`
  - Startup directory: каталог проекта
- Либо Планировщик заданий Windows (запуск при входе/старте системы).

## 9. Отладка
- Логи: `backup_dir/backup.log`, `/lastlog`.
- Uptime Kuma — статусы `Backup OK`, `Dump failed`, `Exception`, `Quiet hours skip`, `No changes`.
- Если дамп не запускается — проверьте путь `onec.exe`, права, авторизацию `/N`/`/P` и содержимое `dump_out.log`.

## 10. Безопасность
- Пароль 1С в логах маскируется.
- `.env` и `.venv` не коммитятся (см. `.gitignore`).

## 11. Зависимости
См. `requirements.txt`. Если файла нет, установите:
```powershell
pip install python-telegram-bot==21.* apscheduler==3.* pytz psutil pyyaml python-dotenv requests
```

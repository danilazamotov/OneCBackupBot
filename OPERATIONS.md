# OneC Backup Bot — Операционная инструкция

Бот для создания резервных копий 1С **только в ручном режиме** через команды Telegram.

## 1. Требования
- Windows Server 2019/2022, Python 3.10+
- 1С 8.3 (тонкий клиент) — корректный путь к `1cv8.exe`
- Интернет (Telegram)
- Telegram бот (токен от @BotFather)

## 2. Установка
```powershell
# Создать виртуальное окружение
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Установить зависимости
pip install -r requirements.txt

# Создать файл конфигурации
Copy-Item .env.example .env -Force
```

## 3. Настройка

### 3.1. Файл `.env`
Заполните обязательные параметры:
```env
BOT_TOKEN=your_bot_token_from_botfather
ALLOWED_USER_IDS=123456789,987654321
```

Опционально:
```env
ONEC_UC=username       # Если требуется аутентификация 1С
ONEC_UP=password
UPTIME_KUMA_PUSH_URL=  # Для мониторинга
```

### 3.2. Файл `config.yaml`
Проверьте и отредактируйте:
- `onec.exe` — полный путь к `1cv8.exe`
- `onec.base_path` — путь к файловой базе 1С (каталог с `.1CD`)
- `backup.backup_dir` — каталог для хранения бэкапов
- `backup.file_prefix` — префикс имени файла
- `backup.compress` — сжатие (`zip` или `none`)

## 4. Структура папок

Резервные копии сохраняются в следующей структуре:
```
backup_dir/
├── 2025-01-15/           # Папка с датой создания (YYYY-MM-DD)
│   ├── Zernosbyt_2025-01-15_10-30-45.zip
│   └── Zernosbyt_2025-01-15_14-15-30.zip
├── 2025-01-16/
│   └── Zernosbyt_2025-01-16_09-00-12.zip
├── backup.log            # Лог приложения
└── app.sqlite3           # История бэкапов
```

## 5. Запуск

### Тестовый запуск
```powershell
python main.py
```

### Проверка в Telegram
Отправьте боту команды:
- `/help` — список доступных команд
- `/backup` — создать резервную копию
- `/status` — последние результаты
- `/health` — состояние системы
- `/lastlog` — последние строки лога

## 6. Команды бота

| Команда | Описание |
|---------|----------|
| `/backup` | Создать резервную копию прямо сейчас |
| `/status` | Показать последние 20 бэкапов и их статусы |
| `/health` | CPU, RAM, Disk и время последнего успешного бэкапа |
| `/lastlog` | Получить последние 100 строк лога в виде файла |

## 7. Запуск как сервис (Windows)

### Вариант 1: NSSM (рекомендуется)
```powershell
# Скачать NSSM с https://nssm.cc/download
nssm install OneCBackupBot "C:\path\to\.venv\Scripts\python.exe" "C:\path\to\main.py"
nssm set OneCBackupBot AppDirectory "C:\path\to\project"
nssm start OneCBackupBot
```

### Вариант 2: Планировщик заданий Windows
- Создать задачу с триггером "При запуске системы"
- Программа: `.venv\Scripts\python.exe`
- Аргументы: `main.py`
- Рабочая папка: каталог проекта

## 8. Отладка

### Логи
- Основной лог: `backup_dir/backup.log`
- Вывод 1С: `backup_dir/dump_out.log`
- Команда бота: `/lastlog`

### Типичные проблемы
1. **Бот не отвечает** → Проверьте `BOT_TOKEN` и интернет
2. **Access denied** → Добавьте свой Telegram ID в `ALLOWED_USER_IDS`
3. **Ошибка при создании бэкапа** → Проверьте:
   - Путь к `1cv8.exe` корректен
   - Путь к базе 1С корректен
   - Есть права на запись в `backup_dir`
   - Если требуется — заданы `ONEC_UC` и `ONEC_UP`

### Uptime Kuma (опционально)
Если задан `UPTIME_KUMA_PUSH_URL`, бот отправляет статусы:
- `Backup OK` — успешно
- `No changes, backup skipped` — нет изменений
- `Dump failed` — ошибка 1С
- `Exception` — исключение

## 9. Безопасность
- Пароли 1С в логах маскируются (`***`)
- `.env` не коммитится в Git (см. `.gitignore`)
- Доступ к боту только для указанных пользователей
- Рекомендуется настроить файрвол и регулярно обновлять систему

## 10. Резервное копирование в облако (S3/другое хранилище)

Автоматическая отправка в S3 **удалена из бота**. Для оффсайт-копий используйте:

### Ручная отправка через rclone
```powershell
# Настройте rclone один раз
rclone config

# Отправить последний бэкап
$Latest = Get-ChildItem -Path "C:\path\to\backup_dir" -Recurse -File | 
          Where-Object { $_.Extension -eq ".zip" } | 
          Sort-Object LastWriteTime -Descending | 
          Select-Object -First 1

rclone copy $Latest.FullName "remote:bucket/path/"
```

### Планировщик заданий для S3
Создайте отдельную задачу в Windows Task Scheduler для периодической отправки в облако по нужному вам расписанию.

## 11. Обновление
```powershell
git pull
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt --upgrade
# Перезапустить сервис
```

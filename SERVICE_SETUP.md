# Запуск OneC Backup Bot как службы Windows

## Выбор учетной записи для запуска

### Вариант 1: SYSTEM (по умолчанию)
**Подходит если:**
- База 1С находится на **локальном диске** (C:, D:, E: и т.д.)
- Не требуется доступ к сетевым ресурсам

**Преимущества:**
- Максимальная безопасность
- Запускается автоматически при старте системы
- Не требует пароля

**Команда установки:**
```powershell
nssm install OneCBackupBot "C:\path\to\.venv\Scripts\python.exe" "C:\path\to\main.py"
nssm set OneCBackupBot AppDirectory "C:\path\to\project"
nssm start OneCBackupBot
```

---

### Вариант 2: Domain User / Local Administrator
**Подходит если:**
- База 1С находится на **сетевом диске** (\\server\share\...)
- Требуется доступ к сетевым ресурсам
- Нужно запускать 1С от имени конкретного пользователя

**Команда установки:**
```powershell
nssm install OneCBackupBot "C:\path\to\.venv\Scripts\python.exe" "C:\path\to\main.py"
nssm set OneCBackupBot AppDirectory "C:\path\to\project"

# Указать пользователя для запуска
nssm set OneCBackupBot ObjectName "DOMAIN\Username" "Password"
# Или для локального пользователя:
nssm set OneCBackupBot ObjectName ".\Administrator" "Password"

nssm start OneCBackupBot
```

---

### Вариант 3: Local Service
**Подходит если:**
- Нужен компромисс между безопасностью и функциональностью
- База на локальном диске
- Не требуется доступ к сетевым ресурсам

**Команда установки:**
```powershell
nssm install OneCBackupBot "C:\path\to\.venv\Scripts\python.exe" "C:\path\to\main.py"
nssm set OneCBackupBot AppDirectory "C:\path\to\project"
nssm set OneCBackupBot ObjectName "NT AUTHORITY\LocalService"
nssm start OneCBackupBot
```

---

## Полная инструкция установки с NSSM

### Шаг 1: Скачать NSSM
```powershell
# Скачайте с официального сайта
# https://nssm.cc/download

# Или через Chocolatey:
choco install nssm

# Распакуйте и добавьте в PATH, либо используйте полный путь
```

### Шаг 2: Установить службу
```powershell
# Перейдите в папку проекта
cd C:\Users\zamot\CascadeProjects\OneCBackupBot

# Установите службу (укажите ПРАВИЛЬНЫЕ пути!)
nssm install OneCBackupBot "C:\Users\zamot\CascadeProjects\OneCBackupBot\.venv\Scripts\python.exe" "C:\Users\zamot\CascadeProjects\OneCBackupBot\main.py"

# Установите рабочую директорию
nssm set OneCBackupBot AppDirectory "C:\Users\zamot\CascadeProjects\OneCBackupBot"

# Опционально: описание службы
nssm set OneCBackupBot Description "Telegram бот для резервного копирования 1С"

# Опционально: автозапуск с задержкой (рекомендуется)
nssm set OneCBackupBot Start SERVICE_DELAYED_AUTO_START
```

### Шаг 3: Настроить учетную запись (если нужно)

**Для сетевого доступа:**
```powershell
# Доменный пользователь
nssm set OneCBackupBot ObjectName "YOURDOMAIN\BackupUser" "SecurePassword123"

# Локальный администратор
nssm set OneCBackupBot ObjectName ".\Administrator" "AdminPassword"
```

### Шаг 4: Настроить перезапуск при сбое
```powershell
# Перезапуск при сбое
nssm set OneCBackupBot AppExit Default Restart

# Задержка перед перезапуском (в миллисекундах)
nssm set OneCBackupBot AppRestartDelay 30000

# Сброс счетчика перезапусков (в секундах)
nssm set OneCBackupBot AppThrottle 1500
```

### Шаг 5: Настроить логирование (опционально)
```powershell
# Лог stdout
nssm set OneCBackupBot AppStdout "C:\Users\zamot\CascadeProjects\OneCBackupBot\service_stdout.log"

# Лог stderr
nssm set OneCBackupBot AppStderr "C:\Users\zamot\CascadeProjects\OneCBackupBot\service_stderr.log"

# Ротация логов (байты)
nssm set OneCBackupBot AppStdoutCreationDisposition 4
nssm set OneCBackupBot AppStderrCreationDisposition 4
```

### Шаг 6: Запустить службу
```powershell
# Запуск
nssm start OneCBackupBot

# Проверка статуса
nssm status OneCBackupBot

# Или через PowerShell
Get-Service OneCBackupBot
```

---

## Управление службой

### Остановить
```powershell
nssm stop OneCBackupBot
# или
Stop-Service OneCBackupBot
```

### Перезапустить
```powershell
nssm restart OneCBackupBot
# или
Restart-Service OneCBackupBot
```

### Удалить
```powershell
nssm stop OneCBackupBot
nssm remove OneCBackupBot confirm
```

### Редактировать параметры
```powershell
# Открыть GUI редактор
nssm edit OneCBackupBot
```

### Посмотреть логи
```powershell
# Основной лог приложения
Get-Content "D:\1C_Backups\backup.log" -Tail 50

# Логи службы (если настроены)
Get-Content "C:\Users\zamot\CascadeProjects\OneCBackupBot\service_stdout.log" -Tail 50
Get-Content "C:\Users\zamot\CascadeProjects\OneCBackupBot\service_stderr.log" -Tail 50
```

---

## Альтернатива: Task Scheduler (Планировщик заданий Windows)

### Создание задачи через GUI

1. Откройте **Task Scheduler** (`taskschd.msc`)
2. **Action** → **Create Task**
3. **General**:
   - Name: `OneCBackupBot`
   - Description: `Telegram бот для резервного копирования 1С`
   - Security options: Выберите пользователя
   - ✅ Run whether user is logged on or not
   - ✅ Run with highest privileges (если нужно)

4. **Triggers**:
   - New → **At startup** или **At log on**
   - Delay task for: `1 minute` (опционально)

5. **Actions**:
   - Action: **Start a program**
   - Program: `C:\Users\zamot\CascadeProjects\OneCBackupBot\.venv\Scripts\python.exe`
   - Arguments: `main.py`
   - Start in: `C:\Users\zamot\CascadeProjects\OneCBackupBot`

6. **Conditions**:
   - ☐ Start the task only if the computer is on AC power (снять галочку)

7. **Settings**:
   - ✅ Allow task to be run on demand
   - If the task fails, restart every: `1 minute`
   - Attempt to restart up to: `3 times`

8. **OK** → Введите пароль пользователя

### Создание задачи через PowerShell

```powershell
$Action = New-ScheduledTaskAction -Execute "C:\Users\zamot\CascadeProjects\OneCBackupBot\.venv\Scripts\python.exe" `
    -Argument "main.py" `
    -WorkingDirectory "C:\Users\zamot\CascadeProjects\OneCBackupBot"

$Trigger = New-ScheduledTaskTrigger -AtStartup

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
# Или для пользователя:
# $Principal = New-ScheduledTaskPrincipal -UserId "DOMAIN\Username" -LogonType Password -RunLevel Highest

Register-ScheduledTask -TaskName "OneCBackupBot" `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Telegram бот для резервного копирования 1С"

# Запуск
Start-ScheduledTask -TaskName "OneCBackupBot"
```

---

## Проверка работы службы

### 1. Проверить статус
```powershell
Get-Service OneCBackupBot
# или
sc query OneCBackupBot
```

### 2. Проверить процесс
```powershell
Get-Process python | Where-Object {$_.Path -like "*OneCBackupBot*"}
```

### 3. Проверить логи
```powershell
# Основной лог
Get-Content "D:\1C_Backups\backup.log" -Tail 20 -Wait

# Event Viewer
Get-EventLog -LogName Application -Source "OneCBackupBot" -Newest 10
```

### 4. Проверить Telegram бота
Отправьте боту команду:
```
/health
```

Вы должны получить ответ с метриками системы.

---

## Troubleshooting

### Служба не запускается

1. **Проверьте пути:**
   ```powershell
   nssm dump OneCBackupBot
   ```
   Убедитесь что пути к `python.exe` и `main.py` правильные.

2. **Проверьте права:**
   - Учетная запись службы должна иметь права на чтение/запись в `backup_dir`
   - Права на запуск 1С (`1cv8.exe`)

3. **Проверьте .env:**
   - `BOT_TOKEN` должен быть заполнен
   - `ALLOWED_USER_IDS` должен содержать ваш Telegram ID

4. **Проверьте логи службы:**
   ```powershell
   Get-Content service_stderr.log -Tail 50
   ```

### Служба запускается, но бот не отвечает

1. **Проверьте интернет:**
   ```powershell
   Test-NetConnection -ComputerName api.telegram.org -Port 443
   ```

2. **Проверьте BOT_TOKEN:**
   - Создайте новый токен у @BotFather
   - Обновите `.env`
   - Перезапустите службу

3. **Проверьте ALLOWED_USER_IDS:**
   - Узнайте свой ID у @userinfobot
   - Добавьте в `.env`

---

## Рекомендации по безопасности

1. **Не используйте SYSTEM** если база на сетевом диске
2. **Создайте отдельного пользователя** для службы с минимальными правами:
   - Чтение базы 1С
   - Запись в `backup_dir`
   - Запуск `1cv8.exe`

3. **Используйте сильные пароли** для учетной записи службы

4. **Регулярно обновляйте** зависимости:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt --upgrade
   ```

5. **Мониторьте логи** на предмет ошибок и подозрительной активности

---

## Полезные команды

```powershell
# Список всех служб NSSM
nssm list

# Экспорт конфигурации
nssm dump OneCBackupBot > backup_service_config.txt

# Проверка переменных окружения службы
nssm get OneCBackupBot AppEnvironmentExtra

# Изменить путь к Python
nssm set OneCBackupBot Application "C:\new\path\python.exe"

# Просмотр всех параметров
nssm dump OneCBackupBot
```

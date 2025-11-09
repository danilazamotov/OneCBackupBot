# Интеграция с Grafana (локальный Prometheus)

Бот предоставляет системные метрики через HTTP эндпоинт в формате Prometheus exposition. Рекомендуемая схема:

Бот → Prometheus (scrape `/api/metrics.prom`) → Grafana (графики и алерты)

Никаких облачных сервисов не требуется.

## Собираемые метрики

### Системные метрики (отправляются каждые 60 секунд по умолчанию)

#### CPU
- `onec_cpu_percent` — общая загрузка процессора (%)
- `onec_cpu_count_logical` — количество логических ядер
- `onec_cpu_count_physical` — количество физических ядер
- `onec_cpu_freq_current` — текущая частота (MHz)
- `onec_cpu_freq_max` — максимальная частота (MHz)
- `onec_cpu_user_time` — время в user mode (%)
- `onec_cpu_system_time` — время в system mode (%)
- `onec_cpu_idle_time` — время простоя (%)

#### Память (RAM)
- `onec_memory_percent` — использование памяти (%)
- `onec_memory_total` — всего памяти (bytes)
- `onec_memory_available` — доступно (bytes)
- `onec_memory_used` — используется (bytes)
- `onec_memory_free` — свободно (bytes)
- `onec_memory_swap_percent` — использование swap (%)
- `onec_memory_swap_total` — всего swap (bytes)
- `onec_memory_swap_used` — используется swap (bytes)
- `onec_memory_swap_free` — свободно swap (bytes)

#### Диск
- `onec_disk_percent` — использование диска с бэкапами (%)
- `onec_disk_backup_disk_total` — размер диска (bytes)
- `onec_disk_backup_disk_used` — использовано (bytes)
- `onec_disk_backup_disk_free` — свободно (bytes)

#### Диск I/O
- `onec_disk_io_read_count` — количество операций чтения
- `onec_disk_io_write_count` — количество операций записи
- `onec_disk_io_read_bytes` — байт прочитано
- `onec_disk_io_write_bytes` — байт записано
- `onec_disk_io_read_time` — время чтения (ms)
- `onec_disk_io_write_time` — время записи (ms)

#### Сеть
- `onec_network_bytes_sent` — отправлено байт
- `onec_network_bytes_recv` — получено байт
- `onec_network_packets_sent` — отправлено пакетов
- `onec_network_packets_recv` — получено пакетов
- `onec_network_errin` — ошибок входящих
- `onec_network_errout` — ошибок исходящих
- `onec_network_dropin` — потерь входящих
- `onec_network_dropout` — потерь исходящих
- `onec_network_active_connections` — активных соединений

#### Процессы
- `onec_processes_total_count` — общее количество процессов

#### Пользователи и RDP сессии (Windows)
- `onec_logged_users_count` — количество залогиненных пользователей
- `onec_rdp_active_count` — количество активных RDP сессий

#### Система
- `onec_uptime_seconds` — время работы системы (секунды)
- `onec_timestamp_unix` — Unix timestamp метрики

### Метрики резервного копирования

- `onec_backup_status` — статус последнего бэкапа (1 = успех, 0 = ошибка)
- `onec_backup_timestamp` — время создания бэкапа
- `onec_backup_size_bytes` — размер файла бэкапа
- `onec_backup_duration_seconds` — длительность создания

---

## Настройка локального Prometheus

1) Установите Prometheus и Grafana (на одной машине/хостинге).

2) Добавьте в `prometheus.yml` конфиг скрейпа:
```yaml
scrape_configs:
  - job_name: 'onec_backup_bot'
    static_configs:
      - targets: ['<SERVER_IP>:8080']
    metrics_path: /api/metrics.prom
```

3) В Grafana добавьте Prometheus как Data Source и построите панели.

## Готовые дашборды для Grafana

### Дашборд №1: Обзор системы

Импортируйте JSON в Grafana (Create → Import):

```json
{
  "title": "OneC Backup Bot - System Overview",
  "panels": [
    {
      "title": "CPU Usage",
      "targets": [{
        "expr": "onec_cpu_percent"
      }],
      "type": "graph"
    },
    {
      "title": "Memory Usage",
      "targets": [{
        "expr": "onec_memory_percent"
      }],
      "type": "graph"
    },
    {
      "title": "Disk Usage",
      "targets": [{
        "expr": "onec_disk_percent"
      }],
      "type": "gauge"
    },
    {
      "title": "Active RDP Sessions",
      "targets": [{
        "expr": "onec_rdp_active_count"
      }],
      "type": "stat"
    },
    {
      "title": "Network Traffic",
      "targets": [{
        "expr": "rate(onec_network_bytes_recv[5m])"
      }],
      "type": "graph"
    }
  ]
}
```

### Дашборд №2: Мониторинг бэкапов

```json
{
  "title": "OneC Backup Monitoring",
  "panels": [
    {
      "title": "Backup Status (Last 24h)",
      "targets": [{
        "expr": "onec_backup_status"
      }],
      "type": "stat"
    },
    {
      "title": "Backup Size",
      "targets": [{
        "expr": "onec_backup_size_bytes / 1024 / 1024 / 1024"
      }],
      "type": "graph",
      "yaxis": {
        "label": "GB"
      }
    },
    {
      "title": "Backup Duration",
      "targets": [{
        "expr": "onec_backup_duration_seconds / 60"
      }],
      "type": "graph",
      "yaxis": {
        "label": "Minutes"
      }
    }
  ]
}
```

---

## Prometheus Query Examples

### CPU загрузка (средняя за 5 минут)
```promql
avg_over_time(onec_cpu_percent[5m])
```

### Память: доступная в GB
```promql
onec_memory_available / 1024 / 1024 / 1024
```

### Диск: свободное место в GB
```promql
onec_disk_backup_disk_free / 1024 / 1024 / 1024
```

### Сеть: скорость приема (MB/s)
```promql
rate(onec_network_bytes_recv[5m]) / 1024 / 1024
```

### Количество активных RDP пользователей
```promql
onec_rdp_active_count
```

### Успешность последних 10 бэкапов
```promql
sum_over_time(onec_backup_status[24h])
```

---

## Алерты (Alerts)

### Пример 1: Высокая загрузка CPU
```yaml
- alert: HighCPUUsage
  expr: onec_cpu_percent > 90
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "CPU usage is above 90%"
```

### Пример 2: Мало свободного места
```yaml
- alert: LowDiskSpace
  expr: onec_disk_percent > 85
  for: 10m
  labels:
    severity: critical
  annotations:
    summary: "Disk usage is above 85%"
```

### Пример 3: Бэкап failed
```yaml
- alert: BackupFailed
  expr: onec_backup_status == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Latest backup failed!"
```

### Пример 4: Много RDP сессий
```yaml
- alert: TooManyRDPSessions
  expr: onec_rdp_active_count > 5
  for: 15m
  labels:
    severity: info
  annotations:
    summary: "More than 5 active RDP sessions"
```

---

## HTTP эндпоинты бота

- `GET /api/metrics.prom` — Prometheus формат (используйте в `metrics_path`)
- `GET /api/metrics` — JSON (для отладки и интеграций)
- `GET /api/health` — быстрый статус
- `GET /api/backup/last` — информация о последнем бэкапе

---

## Troubleshooting

### Метрики не отправляются

1. **Проверьте логи:**
   ```powershell
   # В логе должны быть строки:
   # "Metrics worker started (interval: 60s)"
   # "Sent N metrics to Prometheus"
   ```

2. **Проверьте переменные окружения:**
   ```powershell
   # В .env должны быть заполнены:
   GRAFANA_PROMETHEUS_URL=...
   ```

3. **Проверьте доступность endpoint:**
   ```powershell
   curl http://localhost:9091/metrics
   # Или
   Invoke-WebRequest -Uri "http://localhost:9091/metrics"
   ```

### Ошибки аутентификации (401)

- Проверьте правильность `GRAFANA_PROMETHEUS_USER` и `GRAFANA_PROMETHEUS_PASSWORD`
- Для Grafana Cloud используйте API Token, а не пароль от аккаунта

### Метрики не видны в Grafana

1. Проверьте, что Prometheus scrape настроен на Pushgateway
2. В Grafana проверьте правильность Data Source
3. Подождите интервал scrape (обычно 15-60 сек)

---

## Рекомендации по продакшену

1. Ограничьте доступ к `API_PORT` файрволом (только ваши подсети/VPN)
2. Настройте алерты в Grafana/Prometheus (CPU>90%, Disk>85%, отсутствие метрик, статус бэкапа)
3. Хранение Prometheus: выберите срок хранения данных 30–90 дней под ваши требования

---

## Дополнительная информация

- **Prometheus**: https://prometheus.io/docs/introduction/overview/
- **Grafana**: https://grafana.com/docs/grafana/latest/

## Поддержка

При возникновении проблем проверьте:
1. Логи бота: `backup_dir/backup.log`
2. Статус метрик worker: должны быть строки "Metrics worker started"
3. Сетевую доступность endpoints

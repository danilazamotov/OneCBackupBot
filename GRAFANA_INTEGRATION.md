# Интеграция с Grafana — Полное руководство

## Обзор

Бот поддерживает отправку метрик в **Grafana** через несколько протоколов:
1. **Prometheus Push Gateway** (рекомендуется) — для метрик
2. **Grafana Cloud Prometheus** — облачное решение
3. **InfluxDB** — альтернативная TSDB
4. **Grafana Loki** — для логов (опционально)

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

## Настройка

### Вариант 1: Grafana Cloud (рекомендуется)

#### 1. Создайте аккаунт Grafana Cloud
- Зарегистрируйтесь на https://grafana.com/
- Получите бесплатный план (до 10k метрик)

#### 2. Получите учетные данные Prometheus
В Grafana Cloud:
1. Перейдите в **Configuration** → **Data Sources**
2. Выберите **Prometheus**
3. Скопируйте:
   - **URL**: `https://prometheus-prod-XX-xxx.grafana.net/api/prom/push`
   - **User**: обычно это числовой ID
   - **Password**: API ключ (Generate Now)

#### 3. Настройте .env
```env
GRAFANA_PROMETHEUS_URL=https://prometheus-prod-XX-xxx.grafana.net/api/prom/push
GRAFANA_PROMETHEUS_USER=123456
GRAFANA_PROMETHEUS_PASSWORD=glc_eyJrIjoixxxxxxxx...
METRICS_INTERVAL=60
```

#### 4. Запустите бота
```powershell
python main.py
```

Метрики начнут отправляться каждые 60 секунд!

---

### Вариант 2: Локальный Prometheus + Pushgateway

#### 1. Установите Prometheus Pushgateway

**Docker:**
```powershell
docker run -d -p 9091:9091 prom/pushgateway
```

**Скачать напрямую:**
https://github.com/prometheus/pushgateway/releases

#### 2. Настройте Prometheus для сбора данных

`prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'pushgateway'
    honor_labels: true
    static_configs:
      - targets: ['localhost:9091']
```

#### 3. Настройте .env
```env
PROMETHEUS_PUSHGATEWAY_URL=http://localhost:9091
METRICS_INTERVAL=60
```

#### 4. Настройте Grafana для визуализации
1. Добавьте Prometheus как Data Source в Grafana
2. Используйте готовые дашборды (см. ниже)

---

### Вариант 3: InfluxDB

#### 1. Установите InfluxDB
```powershell
# Docker
docker run -d -p 8086:8086 influxdb:2.7

# Или скачайте: https://portal.influxdata.com/downloads/
```

#### 2. Создайте bucket и token
```bash
# Через UI: http://localhost:8086
# Или через CLI:
influx setup
influx bucket create -n onec_metrics
influx auth create --org myorg --all-access
```

#### 3. Настройте .env
```env
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_token_here
INFLUXDB_ORG=myorg
INFLUXDB_BUCKET=onec_metrics
METRICS_INTERVAL=60
```

---

### Вариант 4: Grafana Loki (логи)

#### 1. Установите Loki
```powershell
docker run -d -p 3100:3100 grafana/loki:latest
```

#### 2. Настройте .env
```env
GRAFANA_LOKI_URL=http://localhost:3100
# Или для Grafana Cloud:
GRAFANA_LOKI_URL=https://logs-prod-xxx.grafana.net
GRAFANA_LOKI_USER=123456
GRAFANA_LOKI_PASSWORD=your_token_here
```

Логи событий бэкапа будут отправляться в Loki!

---

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

## API Endpoints

### Prometheus Push Gateway API

**Отправка метрик:**
```http
POST /metrics/job/onec_backup_bot HTTP/1.1
Host: localhost:9091
Content-Type: text/plain

onec_cpu_percent 45.2
onec_memory_percent 67.1
onec_disk_percent 82.3
```

**Удаление метрик:**
```http
DELETE /metrics/job/onec_backup_bot HTTP/1.1
Host: localhost:9091
```

### Grafana Cloud Prometheus API

**Отправка метрик:**
```http
POST /api/prom/push HTTP/1.1
Host: prometheus-prod-XX-xxx.grafana.net
Authorization: Basic <base64(user:password)>
Content-Type: text/plain

onec_cpu_percent 45.2 1699999999000
onec_memory_percent 67.1 1699999999000
```

### InfluxDB API

**Отправка метрик (Line Protocol):**
```http
POST /api/v2/write?org=myorg&bucket=onec_metrics&precision=ns HTTP/1.1
Host: localhost:8086
Authorization: Token your_token_here
Content-Type: text/plain

system_metrics,host=server01 cpu_percent=45.2,memory_percent=67.1 1699999999000000000
```

### Grafana Loki API

**Отправка логов:**
```http
POST /loki/api/v1/push HTTP/1.1
Host: localhost:3100
Content-Type: application/json

{
  "streams": [
    {
      "stream": {
        "job": "onec_backup_bot",
        "level": "info"
      },
      "values": [
        ["1699999999000000000", "Backup completed successfully"]
      ]
    }
  ]
}
```

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

## Рекомендации по производству

1. **Интервал метрик:** 60 секунд оптимально для большинства случаев
2. **Retention:** Настройте в Prometheus/InfluxDB хранение 30-90 дней
3. **Алерты:** Настройте уведомления в Telegram через Grafana Alerting
4. **Backup метрик:** InfluxDB/Prometheus также нужно бэкапить!
5. **Безопасность:** Используйте HTTPS для Grafana Cloud и локальных endpoints

---

## Дополнительная информация

- **Grafana Cloud Docs:** https://grafana.com/docs/grafana-cloud/
- **Prometheus Pushgateway:** https://github.com/prometheus/pushgateway
- **InfluxDB v2 Docs:** https://docs.influxdata.com/influxdb/v2/
- **Grafana Loki:** https://grafana.com/docs/loki/latest/

## Поддержка

При возникновении проблем проверьте:
1. Логи бота: `backup_dir/backup.log`
2. Статус метрик worker: должны быть строки "Metrics worker started"
3. Сетевую доступность endpoints

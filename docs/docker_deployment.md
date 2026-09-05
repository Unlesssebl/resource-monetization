---
title: Развертывание в Docker и Docker Compose
updated_at: 2026-09-05
tags:
  - docker
  - deployment
  - devops
  - microservices
  - redis
aliases:
  - Docker Deployment Guide
---

# 🐳 Развертывание в Docker и Docker Compose

> **Связанные документы:** [[architecture|Архитектура микросервисов]] | [[monetization_cases|Карта кейсов]]  
> 🕒 **Дата актуальности:** Сентябрь 2026

---

## ⚡ Архитектурный принцип контейнеризации (Pragmatic Lean)

1. **Легковесная инфраструктура в Docker:**
   * Сервис `redis` (`redis:alpine`) вынесен в контейнер для межхостовой координации и буферизации данных скрейперов перед записью в DuckDB.
   * Контейнер ограничен скромными ресурсами (0.5 CPU, 256M RAM).

2. **Нативный запуск тяжелых AI/GPU сервисов:**
   * Локальная LLM **Ollama Qwen 2.5** на RTX 3050 CUDA и **Whisper Engine** (DirectML / DirectCompute) на RX 6800 XT работают **нативно на Windows**.
   * Это устраняет накладные расходы виртуализации WSL2, гарантирует прямой доступ к VRAM и максимальную скорость вычислений.

3. **Graceful Fallback:**
   * Если Docker не запущен, скрипты платформы (`rmon.py`) не падают, а автоматически используют локальный файловый буфер `data/queue/`.

---

## 🚀 Команды управления

### 1. Запуск очереди Redis:
```bash
docker compose up -d redis
```

### 2. Запуск полного стека (Redis + Telegram Bot + Монитор):
```bash
docker compose up -d --build
```

### 3. Просмотр логов:
```bash
docker compose logs -f redis
docker compose logs -f telegram_bot
```

### 4. Остановка:
```bash
docker compose down
```

---

## 🏗️ Спецификация контейнеров (`docker-compose.yml`)

| Контейнер | Образ / Сборка | Назначение | Лимиты ресурсов |
|---|---|---|:---:|
| `rmon_redis` | `redis:alpine` | Очередь задач и буфер перед DuckDB DataLake | 0.5 CPU / 256M RAM |
| `rmon_telegram_bot` | `Dockerfile` | Telegram AI-шлюз (24/7 прием аудио/видео) | 8.0 CPU / 16 GB RAM |
| `rmon_market_monitor` | `Dockerfile` | Фоновый парсер e-com и мониторинг | 4.0 CPU / 8 GB RAM |

---

## 📁 Монтирование данных (Volumes)

* `./data/redis:/data` — персистентность данных очереди Redis.
* `./data:/app/data` — общие базы DuckDB, отчеты и транскрипты.
* `./logs:/app/logs` — файлы логов.
* `./configs:/app/configs:ro` — защищенные переменные `.env` и настройки.

#docker #devops #deployment #redis #duckdb
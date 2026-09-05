---
title: Масштабируемая чистая архитектура платформы RMon (Standard Python src-layout)
updated_at: 2026-09-05
tags:
  - architecture
  - clean-architecture
  - src-layout
  - python
  - modular-monolith
  - task-queue
aliases:
  - Project Architecture
---

# 🏗️ Масштабируемая чистая архитектура платформы RMon

> **Стандарт проекта:** Полное соответствие PEP 518, правилам Clean Architecture и принципам `GEMINI.md`.  
> 🕒 **Дата актуальности:** Сентябрь 2026

---

## 🏛️ Организация структуры файлов

```text
resource-monetization/
├── configs/                     # ⚙️ Конфигурации и шаблоны (targets.json, cases.json)
│   ├── .env                     # Локальные переменные окружения
│   └── .env.example             # Безопасный шаблон
├── data/                        # 💾 Локальные данные, базы DuckDB и очереди (в .gitignore)
│   ├── cloud/media/             # ☁️ Централизованное медиа-хранилище (rclone 8 TB)
│   ├── queue/                   # ⚡ Локальный JSONL-буфер задач (LocalFallbackTaskQueue)
│   └── market_monitor.duckdb    # 📊 Аналитическая база DuckDB OLAP
├── logs/                        # 📜 Логи работы процессов
├── docs/                        # 📚 Документация, аналитика и интерактивный дашборд
├── src/                         # 📦 Изолированный исходный код приложения
│   └── rmon/                    # Основной пакет платформы
│       ├── core/                # 🏛️ Ядро инфраструктуры и контракты
│       │   ├── models.py        # Базовые DTO (ListingItem, MarketSummary, DealOpportunity, AuditVerdict, QueueTask)
│       │   ├── queue.py         # Двухуровневая очередь задач (RedisTaskQueue + LocalFallbackTaskQueue)
│       │   ├── media.py         # Кластерное хранилище медиафайлов с дедупликацией (MediaStorage)
│       │   ├── interfaces.py    # Абстрактные протоколы (LLMProvider, MarketDataSource, SpeechTranscriber)
│       │   ├── lake.py          # Аналитический движок DuckDB DataLake + Parquet
│       │   ├── hardware.py      # Арбитр телеметрии мульти-GPU кластера
│       │   ├── gateway.py       # Telegram Gateway
│       │   ├── gemini.py        # Ротация пула бесплатных ключей Gemini API
│       │   ├── config.py        # Единая конфигурация настроек
│       │   └── logger.py        # Форматирование и ротация логов
│       └── services/            # 🧩 Доменные микросервисы
│           ├── scraper/         # 📊 Сбор данных, фасад хранилища и фоновый воркер
│           │   ├── avito.py     # Playwright Stealth Scraper
│           │   ├── daemon.py    # 24/7 цикл мониторинга
│           │   ├── ingest_worker.py # Пакетная запись в DuckDB из TaskQueue
│           │   └── storage.py   # Фасад DuckDBStorage поверх DataLake
│           ├── ai/              # 🧠 Анализ ликвидности и AI-аудит
│           │   ├── deal_intelligence.py # Скорость просмотров, юнит-экономика, торг
│           │   └── deal_auditor.py      # Гибридный аудит (Gemini / Ollama RTX 3050 CUDA)
│           ├── whisper/         # 🎙️ Транскрибация и контент-фабрика
│           │   ├── engine.py    # DirectCompute / CUDA Whisper транскрибатор
│           │   ├── repurpose.py # Авто-упаковка видео/аудио в клипы и статьи
│           │   └── bot.py       # aiogram 3.x Telegram-бот
│           ├── knowledge/       # 💎 База знаний моделей монетизации (Idea Radar)
│           │   └── case_manager.py # Синхронизация Markdown и DuckDB
│           └── seo/             # 🌐 Генератор Programmatic SEO витрин
├── scripts/                     # 🚀 Единая консоль управления и скрипты
│   ├── rmon.py                  # Главная CLI точка входа (status, worker, monitor, inspect, audit, transcribe, cases, sync)
│   ├── run_bot.py               # Запуск Telegram-бота
│   ├── run_daemon.py            # Запуск демона мониторинга
│   └── start_services.bat       # Windows лаунчер
├── docker-compose.yml           # 🐳 Docker Compose (Redis очередь + контейнеризированные сервисы)
├── Dockerfile                   # 🐳 Базовый Dockerfile
├── requirements.txt             # 📌 Зависимости проекта
└── README.md
```

---

## ⚡ Ключевые архитектурные решения

### 1. Border Gateway DTO (Безопасная типизация)
Все сущности платформы ([`ListingItem`](file:///f:/Work/Projects/resource-monetization/src/rmon/core/models.py), [`DealOpportunity`](file:///f:/Work/Projects/resource-monetization/src/rmon/core/models.py), [`AuditVerdict`](file:///f:/Work/Projects/resource-monetization/src/rmon/core/models.py)) снабжены методами `.to_dict()` и `.from_dict(strict=False)`. Это обеспечивает строгую типизацию и валидацию внутри модулей, сохраняя 100% совместимость со старым кодом, оперирующим сырыми словарями.

### 2. Двухуровневая очередь задач с Graceful Fallback
Очередь [`TaskQueue`](file:///f:/Work/Projects/resource-monetization/src/rmon/core/queue.py) работает по гибридной схеме:
* При наличии Redis (`redis:alpine`) используется распределенная очередь `rmon:queue:*`.
* Если Redis выключен или недоступен (локальная разработка/оффлайн), система прозрачно переключается на `LocalFallbackTaskQueue` с персистентным JSONL-файлом в `data/queue/`. Никаких сбоев и исключений.

### 3. Решение проблемы блокировок DuckDB (Single-Writer)
Парсеры не пишут напрямую в DuckDB одновременно. Они отправляют задачи в очередь `scrape_ingest`. Пакетный воркер [`IngestWorker`](file:///f:/Work/Projects/resource-monetization/src/rmon/services/scraper/ingest_worker.py) вычитывает задачи пачками (`batch_size=50`) и атомарно фиксирует транзакции в [`DataLake`](file:///f:/Work/Projects/resource-monetization/src/rmon/core/lake.py).

### 4. Дедуплицированное медиа-хранилище (No Split-Brain)
Модуль [`MediaStorage`](file:///f:/Work/Projects/resource-monetization/src/rmon/core/media.py) дедуплицирует изображения по SHA256-хэшу и сохраняет их в директорию `data/cloud/media`, синхронизируемую через rclone между всеми узлами мульти-хост кластера.

---

#architecture #cleancode #python #standard #duckdb #task-queue
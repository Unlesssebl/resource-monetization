---
title: Архитектура микросервисов и Clean Architecture
updated_at: 2026-08-30
tags:
  - architecture
  - microservices
  - clean-code
  - orchestrator
aliases:
  - Microservices Architecture
---

# 🏗️ Модульная архитектура микросервисов (Clean Architecture)

> **Связанные документы:** [[monetization_cases|Карта кейсов]] | [[sales_and_distribution_strategies|Гайд по продажам]] | [[dashboard.html|Интерактивный дашборд]]  
> 🕒 **Дата актуальности:** Август 2026

---

## 🏛️ Общая схема микросервисов

Проект разделен на изолированные, слабосвязанные сервисы (**Decoupled Microservices**) под управлением единого оркестратора manage.py:

`mermaid
graph TD
    User([Клиент / Заказчик]) --> TG_GW["Telegram Gateway<br>(services.telegram_bot)"]
    Cron([Windows Task Scheduler / 24/7]) --> M_MON["Market Monitor Service<br>(services.market_monitor)"]
    VOD_Trig([Стримы / Нарезчики]) --> VOD["VOD Vault Service<br>(services.vod_vault)"]

    subgraph CoreServices["Изолированные микросервисы"]
        TG_GW --> TR_SVC["Transcription Service<br>(services.transcription)"]
        M_MON --> DUCK["DuckDB Storage<br>(data/market_monitor.duckdb)"]
        VOD --> AMF["FFmpeg AMF Engine<br>(RX 6800 XT Hardware Encoder)"]
        TR_SVC --> W_ENG["Whisper CTranslate2 Engine<br>(Int8 Quantized Core)"]
    end

    subgraph SharedLayer["Shared Infrastructure Layer"]
        CONF["shared.config (Settings & Env)"]
        LOG["shared.logger (Unified File/Console Logs)"]
    end

    CoreServices --> SharedLayer
`

---

## 📁 Структура каталогов

`
resource-monetization/
├── manage.py                     # 🎮 Центральный CLI-оркестратор
├── shared/                       # 🌐 Общие модули и конфигурация
│   ├── config.py                 # Pydantic / Dataclass настройки окружения (.env)
│   └── logger.py                 # Ротация и форматирование логов в logs/
├── services/                     # 🧩 Независимые микросервисы
│   ├── transcription/            # 🎙️ Сервис AI-транскрибации речи
│   │   ├── engine.py             # Инференс faster-whisper и генерация .srt/.txt/.md
│   │   └── __main__.py           # CLI точка входа
│   ├── telegram_bot/             # 🤖 Шлюз Telegram бота
│   │   ├── handlers.py           # Роутинг сообщений, кружочков, аудиофайлов
│   │   ├── keyboards.py          # Интерактивные кнопки и тарифы
│   │   └── __main__.py           # Точка входа бота
│   ├── market_monitor/           # 📊 Сервис парсинга и мониторинга цен
│   │   ├── scraper.py            # Playwright Stealth / API сборщик
│   │   ├── storage.py            # DuckDB хранилище временных рядов
│   │   ├── reporter.py           # Экспорт отчетов CSV / Markdown
│   │   └── __main__.py           # Точка входа парсера
│   └── vod_vault/                # 📹 Сервис архивации и аппаратного сжатия
│       ├── transcoder.py         # FFmpeg AMF кодек (GPU HEVC)
│       └── __main__.py           # Точка входа видеомодуля
├── configs/                      # ⚙️ Конфигурации (.env, cases.json)
├── data/                         # 💾 Локальные базы данных, отчеты, транскрипты
├── logs/                         # 📜 Логи всех микросервисов
└── docs/                         # 📚 Obsidian база знаний
`

---

## 🎮 Команды управления оркестратором (manage.py)

### 1. Проверка статуса здоровья всех сервисов:
`ash
python manage.py status
`

### 2. Запуск сервисов:
* **Запуск Telegram AI-бота 24/7:**
  `ash
  python manage.py run bot
  `
* **Пакетная транскрибация аудио/видео файла:**
  `ash
  python manage.py run transcribe "data/audio.mp3" --model medium
  `
* **Мониторинг цен маркетплейсов и генерация отчетов:**
  `ash
  python manage.py run monitor --query "авточехлы" --limit 20
  `
* **Пересборка интерактивного дашборда:**
  `ash
  python manage.py run dashboard
  `

---

## 💎 Преимущества новой архитектуры:
1. **Zero Coupling (Нулевая связность):** Каждый сервис можно запускать, тестировать и масштабировать отдельно от других.
2. **Изолированное логирование:** Каждый микросервис пишет в свой файл (logs/transcriptionengine.log, logs/telegramgatewayservice.log, logs/marketscraper.log).
3. **Единый источник правды:** Все настройки читаются через shared.config.settings.
4. **Готовность к контейнеризации:** При необходимости любой сервис оборачивается в Docker за 1 команду.

#architecture #microservices #cleancode #python
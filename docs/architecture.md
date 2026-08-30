---
title: Чистая архитектура проекта (Standard Python src-layout)
updated_at: 2026-08-30
tags:
  - architecture
  - clean-architecture
  - src-layout
  - python
aliases:
  - Project Architecture
---

# 🏗️ Чистая архитектура проекта (Standard Python src-layout)

> **Стандарт проекта:** Полное соответствие PEP 518 и правилам GEMINI.md.  
> 🕒 **Дата актуальности:** Август 2026

---

## 🏛️ Организация структуры файлов

`
resource-monetization/
├── configs/                     # ⚙️ Все конфигурации и шаблоны
│   ├── .env                     # Локальные переменные окружения
│   ├── .env.example             # Безопасный шаблон
│   └── cases.json               # Данные аналитики и кейсов
├── data/                        # 💾 Данные, кэш, базы DuckDB и отчеты (в .gitignore)
├── logs/                        # 📜 Логи работы процессов
├── docs/                        # 📚 База знаний Obsidian и дашборд
├── src/                         # 📦 Изолированный исходный код приложения
│   └── rmon/                    # Основной пакет проекта
│       ├── core/                # Ядро инфраструктуры
│       │   ├── config.py        # Единая конфигурация настроек
│       │   └── logger.py        # Ротация и форматирование логов
│       └── services/            # Доменные сервисы
│           ├── whisper/         # 🎙️ AI-транскрибатор и Telegram-бот
│           │   ├── engine.py    # faster-whisper движок (SRT/TXT/MD)
│           │   └── bot.py       # aiogram 3.x Telegram шлюз
│           ├── scraper/         # 📊 Сборщик цен и DuckDB хранилище
│           │   └── scraper.py   # Playwright / DuckDB / Отчеты
│           └── vod/             # 📹 VOD Vault
│               └── transcoder.py # FFmpeg AMF кодек
├── scripts/                     # 🚀 Исполняемые скрипты и точки входа
│   ├── run_bot.py               # Запуск Telegram-бота 24/7
│   ├── run_transcribe.py        # Запуск транскрибации аудио/видео
│   ├── run_monitor.py           # Запуск парсинга маркетплейсов
│   ├── run_dashboard.py         # Пересборка интерактивного дашборда
│   ├── start_services.bat       # Windows лаунчер в 1 клик
│   └── meta/                    # Утилиты сбора мета-метрик GitHub/Wordstat
├── Dockerfile                   # 🐳 Продакшн Dockerfile
├── docker-compose.yml           # 🐳 Docker Compose оркестрация
├── requirements.txt             # 📌 Зафиксированные зависимости
└── README.md
`

---

## ⚡ Как запускать скрипты:

`ash
# 1. Запустить Telegram-бота:
python scripts/run_bot.py

# 2. Транскрибировать любой файл:
python scripts/run_transcribe.py "data/test_sample.wav" --model medium

# 3. Собрать цены в DuckDB и выгрузить CSV/MD отчет:
python scripts/run_monitor.py --query "авточехлы" --limit 20

# 4. Пересобрать дашборд аналитики:
python scripts/run_dashboard.py
`

#architecture #cleancode #python #standard
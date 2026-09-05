# Resource Monetization (RMon) Platform

Автономная платформа автоматизации, упаковки и монетизации свободных вычислительных и облачных ресурсов с нулевым стартовым бюджетом (0 ₽) на базе Open Source стека.

---

## 🚀 Возможности платформы

* **📊 Аналитический мониторинг цен**: Скрытный сбор данных (Авито / e-com) с хранением в DuckDB OLAP Lake и детекцией аномалий ниже рынка (дисконт ≥ 20%).
* **🧠 AI-аудит и арбитраж сделок**: Гибридный анализ лотов на скам/брак (Gemini Flash API + локальная Ollama Qwen 2.5 на RTX 3050 CUDA), расчет чистой маржи и скриптов быстрого торга.
* **🎙️ Мультимедиа-фабрика**: Аппаратная транскрибация аудио/видео через Faster-Whisper (DirectCompute на RX 6800 XT / CUDA на RTX 3050) и переупаковка контента в вирусные форматы.
* **🌐 Programmatic SEO & витрины**: Генерация дата-дривен страниц, интерактивных калькуляторов и синхронизация с облачным хранилищем 8 TB.
* **⚡ Асинхронный Task Queue & Buffer**: Очередь на базе Redis с автоматическим fallback на локальный JSONL-буфер для устранения блокировок DuckDB.

---

## ⚡ Быстрый старт (CLI)

Управление платформой осуществляется через единый диспетчер [`scripts/rmon.py`](file:///f:/Work/Projects/resource-monetization/scripts/rmon.py):

```bash
# 1. Телеметрия кластера, статус DuckDB и буфера задач
python scripts/rmon.py status

# 2. Мониторинг рынка и выявление аномалий
python scripts/rmon.py monitor --query "RTX 3080" --city moskva --limit 20

# 3. Запуск фонового воркера пакетной записи в DataLake
python scripts/rmon.py worker --batch 50 --interval 3.0

# 4. Локальный AI-аудит лотов на RTX 3050 CUDA
python scripts/rmon.py audit --target "rtx_3080_moskva"

# 5. Аппаратная транскрибация аудио/видео
python scripts/rmon.py transcribe "path/to/audio.mp3" --model medium

# 6. База знаний и радар идей монетизации
python scripts/rmon.py cases list
```

---

## 🏛️ Аппаратный кластер

Платформа спроектирована для работы в распределенном мульти-хост окружении:
* **Host 2 (`Unlesss` — Heavy Compute & Storage Node):** AMD Radeon RX 6800 XT (16 GB VRAM, DirectML/DirectCompute), 48 GB RAM, 2.3 TB SSD + доступ к общему облаку 8 TB.
* **Host 1 (`itt0666` — AI & Scraping Node):** NVIDIA GeForce RTX 3050 (8 GB VRAM, CUDA), 56 GB DDR5, 1 Gbps Ethernet.

---

## 📚 Документация (SSOT)

Вся техническая спецификация вынесена в специализированные руководства:

* 🏗️ **[Архитектура платформы (docs/architecture.md)](file:///f:/Work/Projects/resource-monetization/docs/architecture.md)** — **Единый источник правды (SSOT)**: полное дерево директорий, структура `src/rmon/core`, DTO-контракты, TaskQueue, DataLake и MediaStorage.
* 🐳 **[Развертывание и Docker (docs/docker_deployment.md)](file:///f:/Work/Projects/resource-monetization/docs/docker_deployment.md)** — Контейнеризация Redis, оркестрация Docker Compose и нативный запуск AI.
* 💎 **[Кейсы монетизации (docs/monetization_cases.md)](file:///f:/Work/Projects/resource-monetization/docs/monetization_cases.md)** — Бизнес-модели, расчет юнит-экономики и Idea Radar.
* 📊 **[Интерактивный дашборд (docs/dashboard.html)](file:///f:/Work/Projects/resource-monetization/docs/dashboard.html)** — Локальный веб-дашборд аналитики.

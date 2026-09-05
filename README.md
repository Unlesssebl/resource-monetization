# Resource Monetization (RMon) Platform

Автономная платформа автоматизации, упаковки и монетизации свободных вычислительных и облачных ресурсов с нулевым стартовым бюджетом (0 ₽) и открытым стеком (Open Source First).

---

## 🏛️ Мульти-хост кластер

* **Хост 2 (`Unlesss` — Heavy Compute & Storage Node):**
  * **CPU:** Intel Core i5-12600KF (10 ядер / 16 потоков, до 4.9 GHz)
  * **RAM:** 48 GB DDR4
  * **GPU:** AMD Radeon RX 6800 XT (16 GB VRAM, Navi 21) — DirectML / ROCm / Vulkan / DirectCompute
  * **Накопители:** 2.3 TB SSD локально + доступ к общему облаку 8 TB (Google Drive / Яндекс.Диск via rclone)
* **Хост 1 (`itt0666` — AI & Scraping Node):**
  * **CPU:** Intel Core i7-12700 (12 ядер / 20 потоков)
  * **RAM:** 56 GB DDR5
  * **Compute GPU:** NVIDIA GeForce RTX 3050 (8 GB VRAM, CUDA 13.x / Tensor Cores) — AI-аудит (Ollama Qwen 2.5)

---

## 📦 Архитектурная структура (`src/rmon/`)

Платформа следует принципам Clean Architecture, DIP (инверсия зависимостей) и модульного монолита:

* **`src/rmon/core/`**:
  * `models.py` — Типизированные доменные DTO (`ListingItem`, `MarketSummary`, `DealOpportunity`, `AuditVerdict`, `QueueTask`) с поддержкой обратной совместимости (`.to_dict()`, `.from_dict()`).
  * `queue.py` — Двухуровневая очередь задач (`RedisTaskQueue` + аварийный автономный `LocalFallbackTaskQueue` на JSONL).
  * `media.py` — `MediaStorage` с дедупликацией изображений по SHA256 и синхронизацией в `data/cloud/media` (8 TB Cloud).
  * `interfaces.py` — Контракты и протоколы (`LLMProvider`, `MarketDataSource`, `SpeechTranscriber`).
  * `lake.py` — Высокопроизводительное аналитическое хранилище на базе DuckDB OLAP и Parquet.
  * `hardware.py` — Арбитр телеметрии мульти-GPU и ресурсов кластера.
  * `gateway.py` — Telegram Gateway с поддержкой медиа и инлайн-клавиатур.
  * `gemini.py` — Ротация пула бесплатных ключей Gemini API.
* **`src/rmon/services/`**:
  * `scraper/` — Скрытный парсер Авито (`avito.py`), фоновый мониторинг (`daemon.py`), пакетный обработчик записей (`ingest_worker.py`), фасад хранилища (`storage.py`).
  * `ai/` — Оценка ликвидности и офферы торга (`deal_intelligence.py`), гибридный AI-аудитор (`deal_auditor.py`).
  * `whisper/` — DirectCompute / CUDA транскрибатор (`engine.py`), контент-фабрика (`repurpose.py`), бот (`bot.py`).
  * `knowledge/` — База знаний кейсов и радар идей (`case_manager.py`).
  * `seo/` — Генератор Programmatic SEO витрин.

---

## ⚡ Единая консоль управления (`scripts/rmon.py`)

Все сервисы запускаются через единый CLI интерфейс:

```bash
# Телеметрия кластера, статус DuckDB и очереди задач
python scripts/rmon.py status

# Запуск пакетного IngestWorker для DuckDB DataLake
python scripts/rmon.py worker --batch 50 --interval 3.0

# Мониторинг рынка и цен с выявлением аномалий
python scripts/rmon.py monitor --query "RTX 3080" --city moskva --limit 20

# Глубокая инспекция карточки товара и скачивание фото
python scripts/rmon.py inspect --url "<URL>"

# Локальный AI-аудит сделок на RTX 3050 CUDA
python scripts/rmon.py audit --target "rtx_3080_moskva"

# Аппаратная транскрибация аудио/видео
python scripts/rmon.py transcribe "path/to/audio.mp3" --model medium

# База знаний кейсов монетизации (Idea Radar)
python scripts/rmon.py cases list

# Экспорт DataLake в сжатый Parquet
python scripts/rmon.py sync
```

---

## 🐳 Docker & Инфраструктура

* **Redis Buffer (`redis:alpine`)**: Запускается в легковесном контейнере (0.5 CPU, 256M RAM) для межхостовой координации.
* **Нативный инференс (Windows)**: GPU-сервисы (Ollama Qwen 2.5 на RTX 3050 и DirectML на RX 6800 XT) запускаются нативно без накладных расходов виртуализации.
* **Graceful Fallback**: При выключенном Docker платформа автоматически переходит на локальный буфер без потери задач.

---

## 📚 Документация

* 🏗️ [Чистая архитектура платформы (docs/architecture.md)](file:///f:/Work/Projects/resource-monetization/docs/architecture.md)
* 🐳 [Развертывание и Docker Compose (docs/docker_deployment.md)](file:///f:/Work/Projects/resource-monetization/docs/docker_deployment.md)
* 💎 [Практические кейсы монетизации (docs/monetization_cases.md)](file:///f:/Work/Projects/resource-monetization/docs/monetization_cases.md)
* 📊 [Интерактивный дашборд (docs/dashboard.html)](file:///f:/Work/Projects/resource-monetization/docs/dashboard.html)

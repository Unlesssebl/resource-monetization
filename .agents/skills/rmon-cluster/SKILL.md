---
name: rmon-cluster
description: >-
  Управление мульти-хост кластером и микросервисами Resource Monetization (RMon).
  Позволяет агенту AGY проверять телеметрию GPU (RTX 3050 VRAM), запускать транскрибацию Whisper,
  координировать фоновые сервисы и синхронизировать 8 ТБ Cloud Data Lake.
---

# Skill: rmon-cluster (Управление платформой и кластером RMon)

## Назначение
Этот навык дает агенту `agy` полное руководство по управлению двух-хостовым кластером монетизации ресурсов:
- **Host 1 (itt0666):** Intel Core i7-12700 + 56 GB DDR5 + NVIDIA RTX 3050 (8 GB VRAM) — AI & Fast Inference Node.
- **Host 2 (Heavy Node 24/7):** Intel Core i5-12600KF + 48 GB RAM + AMD Radeon RX 6800 XT (16 GB) + 8 TB Cloud Vault.

---

## 🎮 Команды управления платформой (`scripts/rmon.py`)

### 1. Проверка статуса кластера и телеметрии GPU:
```bash
.\.venv\Scripts\python scripts/rmon.py status
```
*Показывает:* Занятость VRAM RTX 3050, температуру, размер базы DuckDB и активные сервисы.

### 2. Транскрибация аудио/видео файлов через Whisper GPU:
```bash
.\.venv\Scripts\python scripts/rmon.py transcribe "data/input_audio.mp3" --model "medium" --language "ru"
```
*Результаты:* Сохраняются в `data/output_transcripts/` в форматах `.txt`, `.srt`, `.md`.

### 3. Синхронизация Data Lake в Parquet:
```bash
.\.venv\Scripts\python scripts/rmon.py sync
```
*Экспортирует:* Сжатый Parquet-файл `data/market_data_lake.parquet` для репликации в 8 ТБ Cloud Pool.

### 4. Запуск единого Telegram Gateway:
```bash
.\.venv\Scripts\python scripts/rmon.py bot
```

---

## 🛡️ Правила координации VRAM (Hardware Arbiter)
1. **Координация GPU:** Перед запуском тяжелых AI-задач скрипты автоматически вызывают `HardwareArbiter.acquire_gpu_slot()`, что предотвращает одновременную перегрузку VRAM RTX 3050 (8 GB).
2. **Безопасность данных:** Все учетные данные (токены ботов, ID чатов) загружаются строго из `.env`.

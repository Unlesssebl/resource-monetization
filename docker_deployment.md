---
title: Развертывание в Docker и Docker Compose
updated_at: 2026-08-30
tags:
  - docker
  - deployment
  - devops
  - microservices
aliases:
  - Docker Deployment Guide
---

# 🐳 Развертывание в Docker и Docker Compose

> **Связанные документы:** [[architecture|Архитектура микросервисов]] | [[monetization_cases|Карта кейсов]]  
> 🕒 **Дата актуальности:** Август 2026

---

## ⚡ Быстрый запуск в 1 команду

### 1. Запуск всех микросервисов в фоне:
`ash
docker compose up -d --build
`

### 2. Просмотр логов сервисов в реальном времени:
`ash
docker compose logs -f telegram_bot
docker compose logs -f market_monitor
`

### 3. Остановка сервисов:
`ash
docker compose down
`

---

## 🏗️ Спецификация контейнеров

| Контейнер | Назначение | Команда запуска | Ресурсы |
|---|---|---|:---:|
| mon_telegram_bot | Telegram AI-шлюз (24/7 прием аудио/видео) | python manage.py run bot | до 8 CPU / 16 GB RAM |
| mon_market_monitor | Фоновый парсер e-com и мониторинг DuckDB | python manage.py run monitor | до 4 CPU / 8 GB RAM |

---

## 📁 Монтирование постоянных данных (Volumes)
Все критические данные сохраняются на хост-машине:
* ./data:/app/data — базы данных DuckDB, отчеты и транскрипты.
* ./logs:/app/logs — файлы логов каждого микросервиса.
* ./configs:/app/configs:ro — защищенные переменные .env и настройки.

#docker #devops #deployment
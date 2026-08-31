---
name: avito-monitor
description: >-
  Автономный мониторинг и аналитика цен Авито на базе Playwright и DuckDB Data Lake.
  Позволяет отслеживать динамику цен, рассчитывать медианы, выявлять аномалии ниже рынка
  (дисконт >= 20%), скачивать фото и проводить мультимодальный AI-аудит сделок агентом AGY.
---

# Skill: avito-monitor (Мониторинг, глубокая инспекция и AI-аудит Авито)

## Назначение
Этот навык используется агентом `agy` для:
1. **Фонового мониторинга цен** на площадке Avito.ru и анализа истории в DuckDB Data Lake.
2. **Глубокой инспекции конкретных лотов** (`python scripts/rmon.py inspect`) со скачиванием описания продавца и оригинальных фотографий.
3. **Мультимодального AI-аудита фотографий** (тесты FurMark, GPU-Z, Battery Health, пломбы, сколы) с расчетом чистой прибыли и генерацией скрипта торга.

---

## 🚀 Команды управления через единый CLI `scripts/rmon.py`

### 1. Запуск сбора по поисковому запросу и городу:
```bash
.\.venv\Scripts\python scripts/rmon.py monitor --query "RTX 3080" --city "moskva" --limit 15 --threshold 20
```

### 2. Глубокая инспекция лота и скачивание фото для агента AGY:
```bash
# Инспекция по прямой ссылке:
.\.venv\Scripts\python scripts/rmon.py inspect --url "https://www.avito.ru/..."

# Инспекция топ-аномалии из базы DuckDB:
.\.venv\Scripts\python scripts/rmon.py inspect --top-anomaly --target "rtx_3080_moskva"
```

### 3. Локальный AI-аудит аномалий на RTX 3050 (Qwen 2.5 CUDA):
```bash
.\.venv\Scripts\python scripts/rmon.py audit --target "rtx_3080_moskva"
```

### 4. Запуск 24/7 фонового демона мониторинга с Telegram-алертами:
```bash
.\.venv\Scripts\python scripts/rmon.py monitor --daemon
```

---

## 👁️ Протокол Мультимодального Аудита для Агента AGY

Когда пользователь просит: *«AGY, проверь сделку <URL>»* или *«AGY, сделай аудит лота»*:

1. **Шаг 1:** Выполни команду `.\.venv\Scripts\python scripts/rmon.py inspect --url "<URL>"`.
2. **Шаг 2:** Вызови `view_file` для каждой скачанной фотографии в папке `data/deal_photos/{item_id}/photo_*.jpg`.
3. **Шаг 3:** Проанализируй визуальные артефакты:
   * **FurMark / GPU-Z:** Температура GPU Core, HotSpot, память, FPS, отсутствие артефактов.
   * **Состояние железа:** Пломбы на винтах, пыль/окислы на радиаторах, потемнение текстолита.
   * **iPhone / Смартфоны:** Скриншоты 3uTools, Battery Health (емкость в %), следы замены дисплея.
   * **Комплектность:** Реальное устройство vs пустая коробка / переходник.
4. **Шаг 4:** Сформируй **Deal Memorandum**:
   * **Вердикт:** `🟢 ВЫКУПАТЬ` / `⚠️ ТРЕБУЕТ ПРОВЕРКИ` / `⛔ СКАМ ИЛИ БРАК`
   * **Чистая прибыль (₽):** $\text{Медиана} - \text{Цена} - \text{Комиссия 7\%}$
   * **Скрипт торга (Copy-Paste):** Готовое сообщение для продавца на быстрый выкуп за наличные со скидкой.

---

## 📊 Доступные SQL-запросы к DuckDB (`data/market_monitor.duckdb`)

### Быстрый расчет медианы и перцентилей:
```sql
SELECT 
    target_id,
    count(DISTINCT item_id) as total_items,
    median(price_current) as median_price,
    quantile_cont(price_current, 0.25) as p25_price,
    min(price_current) as min_price,
    max(price_current) as max_price
FROM price_history
WHERE price_current > 100
GROUP BY target_id;
```

### Топ аномалий с дисконтом $\ge 20\%$ от медианы:
```sql
WITH latest AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY scraped_at DESC) as rn
    FROM price_history
    WHERE price_current > 100
),
medians AS (
    SELECT target_id, median(price_current) as median_price
    FROM latest WHERE rn = 1 GROUP BY target_id
)
SELECT l.title, l.price_current, m.median_price,
       round(((m.median_price - l.price_current) / m.median_price) * 100, 1) as discount_pct,
       l.location, l.url
FROM latest l
JOIN medians m ON l.target_id = m.target_id
WHERE l.rn = 1 AND l.price_current <= m.median_price * 0.8
ORDER BY discount_pct DESC;
```

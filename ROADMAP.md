# 🗺️ Resource Monetization (RMon) — Strategic Roadmap 2026–2027

> **Стратегическая цель:** Автоматизация, упаковка и монетизация свободных вычислительных и облачных ресурсов мульти-хост кластера с нулевым стартовым бюджетом (0 ₽) и опорой на Open Source First.

---

## 🏛️ Архитектура и мощности кластера

* **Хост 2 (Active Compute & Storage Node — `Unlesss`):**
  * **GPU:** AMD Radeon RX 6800 XT (16 GB VRAM, DirectML / DirectCompute)
  * **CPU:** Intel Core i5-12600KF (10C / 16T, до 4.9 GHz) | **RAM:** 48 GB DDR4
  * **SSD:** 2.3 TB (>1.5 TB свободно) | **Облако:** 8 TB (Яндекс.Диск + Google Drive via rclone)
* **Хост 1 (AI & Scraping Node — `itt0666`):**
  * **GPU:** NVIDIA GeForce RTX 3050 (8 GB VRAM, CUDA 13.x / Tensor Cores)
  * **CPU:** Intel Core i7-12700 (12C / 20T, 56 GB DDR5)
* **Точки монетизации:**
  * [Boosty Канал](https://boosty.to/unlesss) (Рекуррентные подписки 390–790 ₽/мес)
  * itch.io Storefront (Цифровые 2D/3D ассеты $4.99–$9.99)
  * Telegram VIP Bot (Токены доступа к 8 TB Vault + Whisper GPU транскрибация)

---

## 🧭 Фазы реализации и статус

```mermaid
gantt
    title RMon Execution Roadmap
    dateFormat  YYYY-MM-DD
    section Фаза 1: Цифровые ассеты
    PBR Texture Engine & Собель нормали :done, p1, 2026-08-30, 2026-08-31
    DirectML Diffusion на RX 6800 XT    :done, p2, 2026-08-31, 2026-08-31
    2D RPG Icon Pack Vol. 1 (26 спрайтов) :done, p3, 2026-08-31, 2026-08-31
    itch.io & Reddit Storefront Kits     :done, p4, 2026-08-31, 2026-08-31
    section Фаза 2: Telegram & Paywall
    Telegram Gateway с Whisper GPU      :done, b1, 2026-08-30, 2026-08-31
    Интеграция Boosty (https://boosty.to/unlesss) :done, b2, 2026-08-31, 2026-08-31
    Генератор 48h VIP-токенов (/redeem) :done, b3, 2026-08-31, 2026-08-31
    Telegram Stars & CryptoPay Webhook  :active, b4, 2026-09-01, 2026-09-05
    section Фаза 3: ComfyUI 8 TB Vault
    Портативный сборщик DirectML / CUDA :done, c1, 2026-08-31, 2026-08-31
    Нарезка 4 GB томов 7-Zip в Облако   :active, c2, 2026-09-02, 2026-09-07
    Воркфлоу апскейла 8K и FaceSwap     :active, c3, 2026-09-05, 2026-09-10
    section Фаза 4: Органический трафик
    Programmatic SEO портал цен         :done, s1, 2026-08-30, 2026-08-31
    УБТ Видео-Фабрика (Shorts/Reels)    :active, s2, 2026-09-03, 2026-09-12
```

---

## 🎯 Подробный план этапов

### ✅ ФАЗА 1: Конвейер цифровых товаров (itch.io & Unity Store) — ВЫПОЛНЕНО
- [x] Разработка локального генератора текстур с физическими картами (`PBRTextureEngine`).
- [x] Подключение нейросетевого DirectML-ускорения на AMD Radeon RX 6800 XT (`NeuralAssetEngine`, 18.9 it/s).
- [x] Генерация и упаковка первого коммерческого релиза 2D-графики: **Fantasy RPG Inventory & Skill Icons Vol. 1** (`fantasy_rpg_icons_vol1.zip`, 26 спрайтов с прозрачным фоном, атлас, обложка 1280x720).
- [x] Генерация и упаковка PBR-биома: **Dark Fantasy Dungeon PBR Essentials** (`neural_dark_fantasy_dungeon_4k.zip`, 5 материалов, 25 карт).
- [x] Автоматизация очистки промежуточного кэша (`cleanup_source=True` в `ItchPackager`).
- [x] Подготовка маркетинговых комплектов (`STORE_LISTING_RPG.md`) для itch.io и Reddit.

---

### 🚀 ФАЗА 2: Подписочная воронка (Telegram VIP & Boosty) — В ПРОЦЕССЕ
- [x] Подключение официальной страницы [Boosty https://boosty.to/unlesss](https://boosty.to/unlesss) в бота и релизные файлы.
- [x] Создание системы криптографических одноразовых токенов с TTL 48 часов (`PaywallManager`).
- [x] Обработчик команды активации `/redeem <token>` в Telegram-боте.
- [x] Внедрение инлайн-каталога товаров (`assets_catalog`) и меню тарифов (`vip_paywall`).
- [ ] Подключение Telegram Stars для мгновенных микроплатежей внутри мессенджера.
- [ ] Настройка Webhook для авто-выдачи токенов после доната на Boosty / Tribute.

---

### 📦 ФАЗА 3: ComfyUI SuperPack & 8 TB Cloud Data Lake — В ОЧЕРЕДИ
- [x] Разработка каркаса портативной сборки ComfyUI под DirectML (AMD) и CUDA (NVIDIA) без необходимости ручной настройки Python (`ComfyUIBuilder`).
- [ ] Загрузка и структурирование GGUF/Safetensors чекпоинтов (SDXL, Flux-Schnell, InstantID, Real-ESRGAN).
- [ ] Нарезка портативной сборки на многотомные 7z архивы по 4 GB для обхода лимитов браузера.
- [ ] Синхронизация архивов через `rclone` в 8 ТБ Cloud Data Lake (Яндекс.Диск + Google Drive).

---

### 📈 ФАЗА 4: Органический трафик (0 ₽ затрат) — В ОЧЕРЕДИ
- [x] Генерация статического Programmatic SEO портала цен (`docs/` и `data/seo_site/`).
- [ ] Автоматизация публикации постов-релизов в Reddit (`r/gamedev`, `r/IndieDev`, `r/itchio`).
- [ ] Запуск фабрики вирусных роликов (`src/rmon/services/whisper/repurpose.py`): нарезка инсайтов, автоматические kinetic-субтитры, кроп 9:16 под Shorts / VK Клипы.

---

## 📊 Таблица ключевых метрик (KPI)

| Метрика | Цель (1 месяц) | Цель (3 месяца) | Текущий статус |
|---|---|---|---|
| **Релизы на itch.io** | 3 пака | 10 паков | 2 готовых релизных архива |
| **Подписчики Boosty** | 5–10 чел | 30–50 чел | Ссылка внедрена в бот и листинги |
| **Объем 8 TB Vault** | 500 GB готовых данных | 2.5 TB данных | Каркас и манифест созданы |
| **Ежемесячный доход** | **3 000 – 7 000 ₽** | **25 000 – 50 000 ₽** | Стадия запуска витрин |

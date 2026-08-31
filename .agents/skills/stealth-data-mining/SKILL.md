---
name: stealth-data-mining
description: >-
  Современный двухуровневый стек скрытного парсинга и сбора рыночных данных без блокировок (2026 Standard).
  Включает высокоскоростную C-библиотеку curl_cffi с TLS/JA3/HTTP2-имперсонацией браузеров (Tier 1)
  и защищенные движки Camoufox / Patchright с удалением флагов автоматизации и CDP-утечек (Tier 2)
  для обхода Cloudflare Turnstile, Kasada и DataDome.
---

# Skill: stealth-data-mining (Скрытный Сбор Данных и Анти-Блокировка)

## 🎯 Назначение
Этот навык регламентирует методы бесперебойного парсинга маркетплейсов, досок объявлений и бирж без риска попадания в капчи (Cloudflare, Kasada, DataDome) и с минимальным потреблением оперативной памяти.

---

## 🏛️ Двухуровневая архитектура сбора (Tiered Architecture)

```mermaid
graph TD
    A["Целевой URL / Поисковый запрос"] --> B{"Требуется ли выполнение JS?"}
    B -->|НЕТ (API / HTML)| C["Tier 1: curl_cffi (C-библиотека)\n• TLS / JA3 / HTTP2 Chrome Fingerprint\n• 15 МБ RAM, 0.05 сек на запрос"]
    B -->|ДА (SPA / Cloudflare Challenge)| D["Tier 2: Camoufox / Patchright\n• Hardened C++ Firefox / Protocol Patch\n• Полное сокрытие CDP и WebDriver"]
    C & D --> E["DuckDB Data Lake (Паркет и OLAP)"]
```

---

## ⚡ 1. Tier 1: curl_cffi (Высокоскоростная C-имперсонация)

Когда страница отдает данные напрямую или через внутренние JSON API, использование тяжелого браузера Playwright является избыточным. `curl_cffi` подменяет отпечаток криптографического рукопожатия TLS на уровне Си:

```python
from curl_cffi import requests

def fetch_stealth_json(url: str, impersonate: str = "chrome124"):
    """
    Выполняет HTTP-запрос с точной копией TLS-отпечатка Chrome.
    Обходит базовые WAF и Cloudflare без запуска браузера.
    """
    session = requests.Session(impersonate=impersonate)
    headers = {
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    }
    resp = session.get(url, headers=headers, timeout=10)
    return resp
```

---

## 🛡️ 2. Tier 2: Camoufox & Patchright (Браузерная автоматизация без утечек)

Стандартный `playwright-stealth` в 2026 году легко детектируется по флагам протокола CDP (Chrome DevTools Protocol). Для обхода сложных WAF применяется **Camoufox** (модифицированный бинарник Firefox):

* **Удалены сигнатуры:** `navigator.webdriver`, утечки `Runtime.enable`, отпечатки WebGL и WebRTC.
* **Человеческий тайминг (Human Jitter):** Рандомизация задержек с логнормальным распределением (12–28 секунд) и эмуляция кривых движения мыши (Bezier curves).

---

## 📋 Чек-лист проверки парсера на скрытность
- [ ] Заголовки `User-Agent`, `Sec-Ch-Ua` и TLS-отпечаток соответствуют одной и той же версии браузера?
- [ ] Включен ли рандомный джиттер между запросами (не менее 10–20 сек)?
- [ ] Очищаются ли временные профили браузера после завершения цикла, чтобы не забивать SSD?
- [ ] При получении HTTP 403 / 429 — парсер делает экспоненциальный откат (backoff), а не долбит сервер?

import re
import asyncio
import random
import urllib.parse
from typing import List, Dict, Any, Optional
from rmon.core.config import settings
from rmon.core.logger import get_logger

logger = get_logger("AvitoScraper")

class AvitoScraper:
    """Stealth парсер поисковой выдачи Авито на базе Playwright"""

    DEFAULT_USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0"
    ]

    @staticmethod
    def clean_price(price_raw: str) -> float:
        """Очистка строки цены от пробелов, символов валют и конвертация в float"""
        if not price_raw:
            return 0.0
        cleaned = re.sub(r"[^\d]", "", price_raw)
        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0

    @classmethod
    async def scrape_search(
        cls,
        query: str,
        city: str = "moskva",
        limit: int = 30,
        headless: bool = True,
        max_retries: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Сбор списка объявлений по поисковому запросу.
        
        :param query: Текстовый поисковый запрос (например, 'RTX 3080')
        :param city: Транслитерированный город ('moskva', 'sankt-peterburg', 'rossiya')
        :param limit: Максимальное количество карточек для сбора
        :param headless: Флаг скрытого режима браузера
        """
        from playwright.async_api import async_playwright
        from playwright_stealth import Stealth

        encoded_query = urllib.parse.quote(query)
        search_url = f"https://www.avito.ru/{city}?q={encoded_query}&s=104"
        logger.info(f"Запуск сбора Авито: query='{query}', city='{city}', url='{search_url}'")

        items: List[Dict[str, Any]] = []
        profile_dir = settings.DATA_DIR / "browser_profile_firefox"
        profile_dir.mkdir(parents=True, exist_ok=True)

        for attempt in range(1, max_retries + 1):
            try:
                async with async_playwright() as p:
                    context = await p.firefox.launch_persistent_context(
                        user_data_dir=str(profile_dir),
                        headless=headless,
                        viewport={"width": 1440 + random.randint(-40, 40), "height": 900 + random.randint(-30, 30)},
                        locale="ru-RU",
                        timezone_id="Europe/Moscow",
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
                        extra_http_headers={
                            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
                        }
                    )

                    page = context.pages[0] if context.pages else await context.new_page()

                    # Умный переход с задержкой
                    logger.info(f"Переход на страницу (попытка {attempt}/{max_retries}): {search_url}")
                    resp = await page.goto(search_url, timeout=35000, wait_until="domcontentloaded")
                    
                    # Имитация чтения страницы человеком (микро-скролл для триггера ленивой загрузки)
                    await asyncio.sleep(random.uniform(2.5, 4.0))
                    await page.evaluate("window.scrollBy(0, 500);")
                    await asyncio.sleep(2.0)

                    # Проверка наличия защиты / капчи
                    content_html = await page.content()
                    if "Доступ ограничен" in content_html or ("captcha" in content_html.lower() and "firewall" in content_html.lower()):
                        if not headless:
                            logger.info("⚡ Открыто окно браузера! Если отображается проверка/капча Авито — пройдите её (ожидание 20 сек)...")
                            try:
                                await page.wait_for_selector("[data-marker='item'], div[class*='iva-item']", timeout=20000)
                                logger.info("✓ Проверка пройдена! Карточки товаров обнаружены.")
                            except Exception:
                                logger.warning("Время ожидания прохождения капчи истекло.")
                        else:
                            logger.warning(f"Обнаружен защитный экран / рейтлимит Авито на попытке {attempt}.")

                    # Поиск карточек объявлений
                    card_selectors = [
                        "[data-marker='item']",
                        "div[data-marker='catalog-serp'] > div",
                        "div[class*='iva-item-root']",
                        "div[class*='items-items'] > div"
                    ]

                    cards = []
                    for sel in card_selectors:
                        cards = await page.query_selector_all(sel)
                        if cards:
                            logger.info(f"Найдено {len(cards)} карточек по селектору '{sel}'")
                            break

                    for card in cards[:limit]:
                        try:
                            # Извлечение заголовка и ссылки
                            title_el = await card.query_selector("[data-marker='item-title'], h3, a[data-marker='item-title']")
                            link_el = await card.query_selector("a[data-marker='item-title'], a[itemprop='url'], a[href*='/items/'], a[href*='_']")
                            price_el = await card.query_selector("[data-marker='item-price'], meta[itemprop='price'], [class*='price-text']")

                            title = (await title_el.inner_text()).strip() if title_el else ""
                            href = await link_el.get_attribute("href") if link_el else ""
                            if not href or not title:
                                continue

                            full_url = href if href.startswith("http") else f"https://www.avito.ru{href}"
                            
                            # Извлечение ID объявления из URL
                            item_id_match = re.search(r"_(\d+)(?:\?|$)", href)
                            item_id = item_id_match.group(1) if item_id_match else str(abs(hash(full_url)))

                            # Извлечение цены
                            price_text = (await price_el.inner_text()).strip() if price_el else "0"
                            cleaned = re.sub(r"[^\d]", "", price_text)
                            price_val = float(cleaned) if cleaned else 0.0

                            # Извлечение локации / метро
                            geo_el = await card.query_selector("[data-marker='item-address'], div[class*='geo-root'], div[class*='style-item-address']")
                            location = (await geo_el.inner_text()).strip() if geo_el else city

                            # Извлечение продавца
                            seller_el = await card.query_selector("[data-marker='item-line/seller-info'], div[class*='seller-info'], div[class*='style-item-seller']")
                            seller = (await seller_el.inner_text()).strip() if seller_el else "Частное лицо"

                            if price_val > 0:
                                items.append({
                                    "id": item_id,
                                    "title": title,
                                    "price_current": price_val,
                                    "price_original": price_val,
                                    "location": location,
                                    "seller": seller,
                                    "url": full_url,
                                    "image_url": ""
                                })
                        except Exception as err:
                            logger.debug(f"Ошибка парсинга отдельной карточки: {err}")
                            continue

                    await context.close()

                    if items:
                        break

            except Exception as e:
                logger.error(f"Ошибка в процессе Playwright сбора Авито (попытка {attempt}): {e}")

            if not items and attempt < max_retries:
                wait_sec = random.uniform(8.0, 14.0)
                logger.info(f"Пауза безопасности перед повторной попыткой: {wait_sec:.1f} сек...")
                await asyncio.sleep(wait_sec)

        logger.info(f"Сбор завершен. Получено реальных позиций с Авито: {len(items)}")
        return items

    @classmethod
    async def get_listing_details(
        cls,
        url: str,
        download_photos: bool = True,
        headless: bool = True
    ) -> Dict[str, Any]:
        """
        Глубокий парсинг страницы конкретного объявления:
        - Полное описание продавца
        - Профиль продавца (имя, рейтинг, количество отзывов)
        - Дата публикации и просмотры
        - Скачивание всех оригинальных фотографий лота в высоком разрешении
        """
        from playwright.async_api import async_playwright
        import urllib.request
        from pathlib import Path

        # Извлечение ID лота
        item_id_match = re.search(r"_(\d+)(?:\?|$)", url)
        item_id = item_id_match.group(1) if item_id_match else str(abs(hash(url)))
        
        logger.info(f"Глубокий сбор карточки объявления [{item_id}]: {url}")
        profile_dir = settings.DATA_DIR / "browser_profile_firefox"
        profile_dir.mkdir(parents=True, exist_ok=True)

        details: Dict[str, Any] = {
            "id": item_id,
            "url": url,
            "title": "",
            "price": 0.0,
            "description": "",
            "seller_name": "Частное лицо",
            "seller_rating": 0.0,
            "seller_reviews": 0,
            "location": "",
            "views": "",
            "date_posted": "",
            "image_urls": [],
            "local_photos": []
        }

        try:
            async with async_playwright() as p:
                context = await p.firefox.launch_persistent_context(
                    user_data_dir=str(profile_dir),
                    headless=headless,
                    viewport={"width": 1440, "height": 900},
                    locale="ru-RU",
                    timezone_id="Europe/Moscow",
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0"
                )

                page = context.pages[0] if context.pages else await context.new_page()
                await page.goto(url, timeout=35000, wait_until="domcontentloaded")
                
                # Задержка и микро-скролл для подгрузки динамических данных
                await asyncio.sleep(random.uniform(2.0, 3.5))
                await page.evaluate("window.scrollBy(0, 400);")
                await asyncio.sleep(1.5)

                # 1. Заголовок
                title_el = await page.query_selector("[data-marker='item-view/title-info'], h1[itemprop='name'], h1")
                if title_el:
                    details["title"] = (await title_el.inner_text()).strip()

                # 2. Цена
                price_el = await page.query_selector("[data-marker='item-view/item-price'], span[itemprop='price'], [class*='style-price-value']")
                if price_el:
                    details["price"] = cls.clean_price(await price_el.inner_text())

                # 3. Полное описание
                desc_el = await page.query_selector("[data-marker='item-view/item-description'], div[itemprop='description'], div[class*='style-item-description']")
                if desc_el:
                    details["description"] = (await desc_el.inner_text()).strip()

                # 4. Продавец и рейтинг
                seller_el = await page.query_selector("[data-marker='seller-info/name'], [data-marker='seller-link/link'], a[class*='style-seller-name']")
                if seller_el:
                    details["seller_name"] = (await seller_el.inner_text()).strip()

                rating_el = await page.query_selector("[data-marker='seller-rating/score'], [class*='seller-rating-score']")
                if rating_el:
                    try:
                        details["seller_rating"] = float((await rating_el.inner_text()).replace(",", ".").strip())
                    except ValueError:
                        pass

                reviews_el = await page.query_selector("[data-marker='seller-rating/summary'], [class*='seller-rating-summary']")
                if reviews_el:
                    cleaned_rev = re.sub(r"[^\d]", "", await reviews_el.inner_text())
                    details["seller_reviews"] = int(cleaned_rev) if cleaned_rev else 0

                # 5. Локация
                loc_el = await page.query_selector("[data-marker='delivery/location'], span[class*='style-item-address'], div[itemprop='address']")
                if loc_el:
                    details["location"] = (await loc_el.inner_text()).strip()

                # 6. Дата и просмотры
                date_el = await page.query_selector("[data-marker='item-view/item-date']")
                if date_el:
                    details["date_posted"] = (await date_el.inner_text()).strip()

                views_el = await page.query_selector("[data-marker='item-view/total-views']")
                if views_el:
                    details["views"] = (await views_el.inner_text()).strip()

                # 7. Извлечение ссылок на фотографии
                img_elements = await page.query_selector_all(
                    "div[data-marker='image-frame/image-wrapper'] img, "
                    "li[data-marker='image-preview'] img, "
                    "div[class*='gallery'] img, "
                    "img[class*='image-frame']"
                )

                seen_urls = set()
                image_urls = []
                for img in img_elements:
                    src = await img.get_attribute("src") or await img.get_attribute("data-src")
                    if src and src.startswith("http") and "avito.st" in src:
                        # Заменяем превью на высокое разрешение (1280x960)
                        hi_res = re.sub(r"/\d+x\d+/", "/1280x960/", src)
                        if hi_res not in seen_urls:
                            seen_urls.add(hi_res)
                            image_urls.append(hi_res)

                details["image_urls"] = image_urls
                await context.close()

        except Exception as e:
            logger.error(f"Ошибка глубокого сбора карточки {url}: {e}")

        # 8. Скачивание фотографий на диск
        if download_photos and details["image_urls"]:
            photos_dir = settings.DATA_DIR / "deal_photos" / item_id
            photos_dir.mkdir(parents=True, exist_ok=True)
            local_paths = []

            for idx, img_url in enumerate(details["image_urls"], 1):
                photo_file = photos_dir / f"photo_{idx:02d}.jpg"
                try:
                    req = urllib.request.Request(
                        img_url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/130.0"}
                    )
                    with urllib.request.urlopen(req, timeout=15) as resp, open(photo_file, "wb") as f:
                        f.write(resp.read())
                    local_paths.append(str(photo_file.resolve()))
                except Exception as err:
                    logger.debug(f"Не удалось скачать фото {img_url}: {err}")

            details["local_photos"] = local_paths
            logger.info(f"Успешно скачано {len(local_paths)} фото лота [{item_id}] в {photos_dir}")

        return details

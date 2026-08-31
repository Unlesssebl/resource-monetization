#!/usr/bin/env python3
"""
RMon (Resource Monetization) — Единый CLI интерфейс управления платформой.
Координирует работу микросервисов:
- monitor (Мониторинг цен Авито/WB + AI-аудит)
- inspect (Глубокий анализ лота + скачивание фото)
- audit (Локальный AI-аудит сделок на RTX 3050)
- transcribe (Транскрибация аудио/видео через Whisper GPU)
- bot (Единый Telegram Gateway)
- status (Телеметрия кластера Host 1 + Host 2)
- sync (Облачная синхронизация Data Lake 8 ТБ)
"""
import sys
import re
import asyncio
import argparse
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rmon.core.config import settings
from rmon.core.hardware import HardwareArbiter
from rmon.core.gateway import TelegramGateway
from rmon.core.lake import DataLake
from rmon.core.logger import get_logger

logger = get_logger("RMonCLI")

def cmd_status():
    """Телеметрия кластера и ресурсов"""
    dashboard = HardwareArbiter.format_cli_dashboard()
    print("\n" + dashboard)

    # Data Lake Stats
    conn = DataLake.get_connection()
    try:
        count = conn.execute("SELECT count(*) FROM price_history").fetchone()[0]
        targets = conn.execute("SELECT count(DISTINCT target_id) FROM price_history").fetchone()[0]
        print(f"\n📊 DATA LAKE (DuckDB OLAP):")
        print(f"   • Всего записей цен в истории: {count:,}")
        print(f"   • Активных таргетов в базе:    {targets}")
    except Exception:
        pass
    finally:
        conn.close()

    print("="*80 + "\n")

def cmd_monitor(args):
    """Сбор данных и мониторинг рынка"""
    if args.daemon:
        from rmon.services.scraper.daemon import MonitorDaemon
        print("🚀 Запуск 24/7 фонового демона мониторинга...")
        daemon = MonitorDaemon()
        asyncio.run(daemon.run())
    else:
        from rmon.services.scraper.avito import AvitoScraper
        query = args.query or "RTX 3080"
        city = args.city or "moskva"
        limit = args.limit or 15
        target_id = f"{query.lower().replace(' ', '_')}_{city.lower()}"

        print(f"\n🔍 Запуск сбора цен: '{query}' [{city}] (лимит: {limit})...")
        items = asyncio.run(AvitoScraper.scrape_search(query=query, city=city, limit=limit, headless=True))
        
        if items:
            saved = DataLake.save_items(items, target_id=target_id, source="avito")
            print(f"✅ Сохранено в Data Lake: {saved} объявлений")
            
            stats = DataLake.get_market_summary(target_id)
            if stats:
                print(f"📊 Медиана рынка: {stats.get('median_price', 0):,.0f} ₽ (25-й перцентиль: {stats.get('p25_price', 0):,.0f} ₽)")

            anomalies = DataLake.get_anomalies(target_id, discount_threshold_pct=args.threshold)
            print(f"🔥 Найдено аномалий (скидка >= {args.threshold}%): {len(anomalies)}")
            for a in anomalies[:5]:
                print(f"  • {a['title']} -> {a['price_current']:,.0f} ₽ (-{a['discount_from_median_pct']}%)")
                print(f"    URL: {a['url']}")
        else:
            print("⚠️ Объявлений не получено.")

def cmd_inspect(args):
    """Глубокая инспекция лота и скачивание фото"""
    from rmon.services.scraper.avito import AvitoScraper
    url = args.url
    if not url and args.top_anomaly:
        anomalies = DataLake.get_anomalies(args.target or "rtx_3080_moskva", discount_threshold_pct=20.0)
        if anomalies:
            url = anomalies[0]["url"]
            print(f"🎯 Выбрана топ-аномалия: {anomalies[0]['title']} ({anomalies[0]['price_current']:,.0f} ₽)")
        else:
            print("❌ В базе нет аномалий для выбранного таргета.")
            return

    if not url:
        print("❌ Укажите --url или --top-anomaly.")
        return

    print(f"\n🔍 Инспекция карточки объявления: {url}...")
    details = asyncio.run(AvitoScraper.get_listing_details(url=url, download_photos=True, headless=True))
    
    print("\n" + "="*60)
    print(f"📦 ЛОТ: {details.get('title')}")
    print(f"💰 Цена: {details.get('price', 0):,.0f} ₽ | Локация: {details.get('location')}")
    print(f"👤 Продавец: {details.get('seller_name')} (★ {details.get('seller_rating', 0)} | {details.get('seller_reviews', 0)} отзывов)")
    print(f"👁️ Просмотры: {details.get('views')} | Дата: {details.get('date_posted')}")
    print("="*60)
    print(f"📝 ОПИСАНИЕ:\n{details.get('description') or 'Отсутствует.'}")
    print("="*60)
    print(f"📸 СКАЧАНО ФОТО: {len(details.get('local_photos', []))} шт.")
    for p in details.get('local_photos', []):
        print(f"  • {p}")
    print("="*60 + "\n")

def cmd_audit(args):
    """Локальный AI-аудит аномалий на RTX 3050 CUDA"""
    from rmon.services.ai.deal_auditor import AIDealAuditor
    target = args.target or "rtx_3080_moskva"
    anomalies = DataLake.get_anomalies(target, discount_threshold_pct=args.threshold)
    print(f"\n🧠 AI-АУДИТ НА RTX 3050 CUDA ДЛЯ ТАРГЕТА: [{target}]")
    print(f"Найдено аномалий: {len(anomalies)}\n" + "="*60)

    for i, a in enumerate(anomalies, 1):
        res = AIDealAuditor.audit_listing(
            title=a["title"],
            price=a["price_current"],
            seller=a.get("seller", ""),
            location=a.get("location", ""),
            market_median=a.get("median_price", 0.0)
        )
        verdict = res.get("verdict", "CAUTION")
        risk = res.get("risk_score", 50)
        badge = "🟢 BUY" if verdict == "BUY" else ("⚠️ CAUTION" if verdict == "CAUTION" else "⛔ SKIP (СКАМ/МУСОР)")
        
        print(f"[{i}] {a['title']}")
        print(f"    💰 {a['price_current']:,.0f} ₽ (Медиана: {a.get('median_price', 0):,.0f} ₽) | Вердикт: {badge} (Риск: {risk}/100)")
        if res.get("detected_issues"):
            print(f"    🚩 Риски: {', '.join(res['detected_issues'])}")
        print(f"    💡 Оценка: {res.get('concise_summary', '')}")
        print(f"    🔗 Ссылка: {a['url']}")
        print("-" * 60)

def cmd_transcribe(args):
    """Транскрибация аудио/видео файлов через Whisper"""
    from rmon.services.whisper.engine import WhisperEngine
    file_path = args.file
    if not Path(file_path).exists():
        print(f"❌ Файл не найден: {file_path}")
        return
    print(f"🎙️ Запуск транскрибации: {file_path} (модель: {args.model})...")
    res = WhisperEngine.transcribe(file_path=file_path, model_size=args.model, language=args.language)
    print(f"✅ Готово за {res.get('elapsed_time_sec', 0):.1f} сек!")
    print(f"📄 Результат сохранен в: {res.get('txt_file')}")

def cmd_repurpose(args):
    """Автономная упаковка подкастов/видео в контент-пак"""
    from rmon.services.whisper.repurpose import ContentRepurposeService
    url = args.url or args.file
    if not url:
        print("❌ Укажите URL или путь к файлу через --url или позиционный аргумент.")
        return
    asyncio.run(ContentRepurposeService.process_pipeline(url_or_path=url, model_size=args.model))

def cmd_cases(args):
    """Управление базой знаний кейсов монетизации и Idea Radar"""
    from rmon.services.knowledge.case_manager import CaseManager
    
    action = args.case_action or "list"
    if action == "list":
        print("\n" + CaseManager.format_cli_table() + "\n")
    elif action == "show":
        slug = args.slug
        if not slug:
            print("❌ Укажите slug кейса для просмотра: python scripts/rmon.py cases show <slug>")
            return
        files = list(CaseManager.CASES_DIR.glob(f"{slug}*.md"))
        if not files:
            print(f"❌ Кейс со slug '{slug}' не найден.")
            return
        content = CaseManager.parse_markdown_case(files[0])
        print("\n" + "="*80)
        print(f"📄 ДОСЬЕ КЕЙСА: {content['meta'].get('title')} ({files[0].name})")
        print("="*80 + "\n")
        print(content.get("body", ""))
        print("\n" + "="*80 + "\n")
    elif action == "add":
        idea = args.idea
        if not idea:
            print("❌ Укажите описание идеи или ссылку: python scripts/rmon.py cases add \"...\"")
            return
        print(f"🧠 Запуск AI-аналитика для структурирования идеи: \"{idea[:60]}...\"")
        res = asyncio.run(CaseManager.add_case_with_ai(idea))
        print(f"\n✅ Кейс успешно создан и проиндексирован в DuckDB!")
        print(f"📁 Файл: {res['path']}")
        print(f"💎 Название: {res['meta'].get('title')}")
        print(f"💰 Потенциал: {res['meta'].get('monthly_potential_rub', 0):,.0f} ₽/мес | Срок: {res['meta'].get('time_to_cash_days')} дн.")

def cmd_seo(args):
    """Генерация и локальный предпросмотр Programmatic SEO портала"""
    import os
    from rmon.services.seo.generator import ProgrammaticSEOGenerator
    if args.serve:
        import http.server
        import socketserver
        out_dir = ProgrammaticSEOGenerator.OUTPUT_DIR
        if not out_dir.exists():
            ProgrammaticSEOGenerator.build_full_portal()
        port = args.port or 8181
        os.chdir(str(out_dir))
        handler = http.server.SimpleHTTPRequestHandler
        print(f"\n🌐 Локальный веб-сервер Programmatic SEO запущен на http://127.0.0.1:{port}")
        print("Нажмите Ctrl+C для остановки.")
        with socketserver.TCPServer(("", port), handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nВеб-сервер остановлен.")
    else:
        ProgrammaticSEOGenerator.build_full_portal()

def cmd_bot(args):
    """Запуск Telegram Gateway бота"""
    from rmon.services.whisper.bot import WhisperBot
    print("🤖 Запуск Unified Telegram Gateway бота...")
    bot = WhisperBot()
    bot.start_polling()

def cmd_sync(args):
    """Экспорт Data Lake в Parquet и синхронизация с облаком"""
    parquet_path = DataLake.export_to_parquet()
    print(f"✅ Data Lake сохранен: {parquet_path}")

def cmd_hybrid(args):
    """
    ⚡ ЕДИНЫЙ ГИБРИДНЫЙ ДВИЖОК МОНЕТИЗАЦИИ (SOVEREIGN FLYWHEEL):
    1. Сбор рыночных цен в DuckDB Data Lake (Avito Scraper)
    2. Анализ ликвидности и генерация B2B-лидов на срочный выкуп (Fast Cash)
    3. Синтез вирусных сценариев для Shorts / Reels с умными ссылками
    4. Экспорт Data Lake в Parquet и статус кластера
    """
    import asyncio
    from rmon.services.scraper.avito import AvitoScraper
    from rmon.services.ai.deal_intelligence import DealIntelligenceEngine

    query = args.query or "RTX 3080"
    city = args.city or "moskva"
    limit = args.limit or 6
    target_id = f"{query.lower().replace(' ', '_')}_{city}"

    print("\n" + "═"*75)
    print(f" 🚀 ЗАПУСК ГИБРИДНОГО МОНЕТИЗАЦИОННОГО МАХОВИКА (SOVEREIGN FLYWHEEL)")
    print(f" 🎯 Таргет: '{query}' [{city}] | Кластер: Host 1 (Node 1) & Host 2")
    print("═"*75)

    # 1. Сбор данных
    print(f"\n[1/4] 🔍 Сбор рыночных данных через Stealth Scraper...")
    items = asyncio.run(AvitoScraper.scrape_search(query=query, city=city, limit=limit, headless=True))
    if items:
        DataLake.save_items(items, target_id=target_id, source="avito")
        print(f"      ✓ Сохранено в Data Lake: {len(items)} объявлений")
    else:
        print("      ⚠️ Свежих объявлений не получено, используем накопленный Data Lake.")

    # 2. Анализ рынка
    summary = DataLake.get_market_summary(target_id)
    median = summary.get("median_price", 0.0)
    total_items = summary.get("total_items", 0)
    print(f"\n[2/4] 📊 Аналитика DuckDB Data Lake [{target_id}]:")
    print(f"      • Всего позиций в базе: {total_items} шт.")
    print(f"      • Медианная цена:       {median:,.0f} ₽")
    print(f"      • 25-й перцентиль (P25): {summary.get('p25_price', 0):,.0f} ₽")
    print(f"      • Диапазон цен:         {summary.get('min_price', 0):,.0f} ₽ — {summary.get('max_price', 0):,.0f} ₽")

    # 3. B2B Лидген и Fast Cash
    print(f"\n[3/4] 🏎️ B2B Лидген и Срочный Выкуп (Готовые сделки):")
    anomalies = DataLake.get_anomalies(target_id, discount_threshold_pct=10.0)
    if anomalies:
        for idx, a in enumerate(anomalies[:3], 1):
            econ = DealIntelligenceEngine.calculate_deal_economics(a["price_current"], median)
            pitch = DealIntelligenceEngine.generate_negotiation_pitch(a["title"], a["price_current"])
            print(f"      ┌─ [Лид #{idx}] {a['title']}")
            print(f"      ├─ 💰 Цена: {a['price_current']:,.0f} ₽ (Дисконт: -{a.get('discount_from_median_pct', 0):.1f}%)")
            print(f"      ├─ 📈 Чистая маржа с перепродажи: +{econ['net_profit_rub']:,.0f} ₽ (ROI: {econ['roi_pct']}%)")
            print(f"      ├─ 🎯 Скрипт торга (Fast Cash Pitch): «{pitch}»")
            print(f"      └─ 🔗 Контакт: {a['url']}\n")
    else:
        print(f"      ℹ️ Прямых аномалий со скидкой >10% не обнаружено. Мониторинг в фоне...")

    # 4. УБТ Вирусный Контент & Связка
    print(f"[4/4] 🎬 УБТ Видео-Фабрика (Синтез вирусного ролика для Shorts/TG):")
    print(f"      ┌─ 🏷️ Тема Shorts: «Сколько на самом деле стоит {query} в 2026 году?»")
    print(f"      ├─ ⚡ Хук (0-3 сек): «Не вздумай покупать {query}, пока не проверишь эту цифру!»")
    print(f"      ├─ 📊 Инсайт: Реальная медиана — {median:,.0f} ₽, а нижняя планка рынка — {summary.get('p25_price', 0):,.0f} ₽.")
    print(f"      ├─ 🔗 CTA (Призыв): «Проверь цену любого товара бесплатно в Telegram-боте @AvitoRadarBot»")
    print(f"      └─ 📈 Dub.co Smart Link: https://dub.sh/radar-{target_id[:10]}")

    # Экспорт
    parquet_path = DataLake.export_to_parquet()
    print("\n" + "═"*75)
    print(f" ✅ ГИБРИДНЫЙ ЦИКЛ УСПЕШНО ВЫПОЛНЕН!")
    print(f" 💾 Data Lake экспортирован в Parquet: {parquet_path.name}")
    print("═"*75 + "\n")

def cmd_digest(args):
    """Генерация и предпросмотр аналитического поста для медиа-канала"""
    from rmon.services.content.media_publisher import MediaPublisher
    from rmon.core.gateway import TelegramGateway
    import asyncio

    if args.guide:
        post = MediaPublisher.generate_gpu_safety_guide_post()
    else:
        post = MediaPublisher.generate_weekly_hardware_index()

    print("\n" + "═"*70)
    print(" 📰 ГОТОВЫЙ АНАЛИТИЧЕСКИЙ ПОСТ ДЛЯ МЕДИА-КАНАЛА:")
    print("═"*70 + "\n")
    # Очистка HTML тегов для консольного вывода
    clean_text = re.sub(r"<[^>]+>", "", post)
    print(clean_text)
    print("\n" + "═"*70)

    if args.send:
        print("📤 Отправка поста в Telegram-канал/админу...")
        res = asyncio.run(TelegramGateway.send_message(text=post))
        print("✓ Пост успешно доставлен в Telegram!" if res else "⚠️ Не удалось доставить пост в Telegram.")

def cmd_comfyui(args):
    """Сборка, валидация и управление портативным ComfyUI Super-Pack"""
    from rmon.services.comfyui.builder import ComfyUIBuilder
    from rmon.services.comfyui.workflows import export_all_workflows
    builder = ComfyUIBuilder()

    if args.action == "status" or not args.action:
        ready = builder.verify_system_readiness()
        print("\n" + "═"*70)
        print(" 🧠 COMFYUI PORTABLE ACCELERATION & HARDWARE READINESS")
        print("═"*70)
        print(f" • GPU:             {ready['gpu']} ({ready['vendor']})")
        print(f" • VRAM:            {ready['vram_mb']} MB (High-VRAM Pool)")
        print(f" • Backend:         {ready.get('backend', 'DirectML / CUDA')}")
        print(f" • Свободно на SSD: {ready['free_disk_gb']} GB")
        print(f" • Статус:          {'✅ ПОЛНОСТЬЮ ГОТОВ К СБОРКЕ И ГЕНЕРАЦИИ' if ready['is_ready'] else '⚠️ ТРЕБУЕТСЯ НАСТРОЙКА'}")
        print("═"*70 + "\n")

    elif args.action == "workflows":
        out = Path("data/comfyui_pack/workflows")
        res = export_all_workflows(out)
        print("\n" + "═"*70)
        print(f" 📦 ЭКСПОРТИРОВАНО {len(res)} ГОТОВЫХ ВОРКФЛОУ В {out}:")
        print("═"*70)
        for name, path in res.items():
            print(f" • {name}.json -> {path}")
        print("═"*70 + "\n")

    elif args.action == "build":
        print("\n🚀 Инициализация портативной сборки ComfyUI SuperPack...")
        manifest = builder.build_release_manifest()
        print("\n" + "═"*70)
        print(" ✅ СБОРКА УСПЕШНО СФОРМИРОВАНА!")
        print("═"*70)
        print(f" • Название:           {manifest['pack_name']}")
        print(f" • Версия:             {manifest['version']}")
        print(f" • Воркфлоу в паке:    {manifest['workflows_count']} шт.")
        print(f" • Файлов в манифесте: {manifest['files_count']} шт.")
        print(f" • Релиз-папка:        data/releases/comfyui/manifest.json")
        print("═"*70 + "\n")

def cmd_assets(args):
    """Генерация игровых AI-ассетов (PBR текстуры, иконки, упаковка для itch.io)"""
    from rmon.services.assets.texture_engine import PBRTextureEngine
    from rmon.services.assets.icon_engine import IconEngine
    from rmon.services.assets.itch_packager import ItchPackager

    if args.action == "textures":
        print(f"\n🎨 Генерация {args.count} наборов PBR текстур (стиль: {args.style})...")
        tex_engine = PBRTextureEngine()
        for i in range(1, args.count + 1):
            name = f"{args.style}_{i:02d}"
            res = tex_engine.generate_procedural_material(name=name, style=args.style, resolution=args.res)
            print(f"  ✓ Сгенерирован материал: {name} (Albedo, Normal, Roughness, Height, AO)")
        print(f"✅ Готово! Текстуры сохранены в data/assets/textures\n")

    elif args.action == "icons":
        print(f"\n🗡️ Генерация {args.count} RPG спрайтов предметов (тип: {args.item_type})...")
        icon_engine = IconEngine()
        paths = []
        palette = [(220, 50, 50), (50, 120, 220), (50, 200, 80), (220, 180, 40), (180, 50, 220)]
        for i in range(1, args.count + 1):
            name = f"{args.item_type}_{i:02d}"
            color = palette[(i - 1) % len(palette)]
            p = icon_engine.create_procedural_icon(item_name=name, item_type=args.item_type, color_rgb=color, size=args.res)
            paths.append(p)
            print(f"  ✓ Сгенерирована иконка: {name}.png")

        sheet_path = icon_engine.build_sprite_sheet(paths, sheet_name=f"{args.item_type}_atlas_sheet")
        print(f"✅ Атлас спрайтов скомпилирован: {sheet_path}\n")

    elif args.action == "package":
        packager = ItchPackager()
        source = Path(args.source or "data/assets/textures")
        slug = args.slug or "pbr_textures_pack_v1"
        title = args.title or "100 PBR Seamless Master Textures"
        print(f"\n📦 Упаковка дистрибутивного релиза для itch.io: '{title}'...")
        zip_path = packager.package_bundle(source_dir=source, pack_slug=slug, title=title, price_usd=args.price)
        print("\n" + "═"*70)
        print(" ✅ АССЕТ-ПАК УСПЕШНО СОБРАН И ГОТОВ К ПРОДАЖЕ!")
        print("═"*70)
        print(f" • Файл релиза:   {zip_path}")
        print(f" • Размер:        {zip_path.stat().st_size / 1024:.1f} KB")
        print(f" • Лицензия:      Commercial Indie Game License (включена)")
        print(f" • Цена продажи:  ${args.price} USD / 490 ₽")
        print("═"*70 + "\n")

    elif args.action == "neural":
        from rmon.services.assets.neural_engine import NeuralAssetEngine
        print("\n🧠 ЗАПУСК НЕЙРОСЕТЕВОГО ДВИЖКА (DirectML GPU Accelerated)...")
        engine = NeuralAssetEngine(model_id=args.model)
        name = args.name or "neural_stone_wall"
        prompt = args.prompt or "dark weathered castle stone masonry with green moss in crevices"
        print(f" • Название материала: {name}")
        print(f" • Промпт:             {prompt}")
        print(f" • Разрешение:         {args.res}x{args.res}")
        print(f" • Шагов диффузии:     {args.steps}\n")

        res = engine.generate_pbr_material(
            name=name,
            prompt=prompt,
            num_inference_steps=args.steps,
            resolution=args.res,
            seed=args.seed
        )
        print("\n" + "═"*70)
        print(" ✅ НЕЙРОСЕТЕВОЙ PBR МАТЕРИАЛ УСПЕШНО СИНТЕЗИРОВАН!")
        print("═"*70)
        print(f" • Время генерации: {res['generation_time_sec']:.2f} сек")
        print(f" • Папка с картами:  {res['dir']}")
        print(f" • Albedo:          {res['albedo'].name}")
        print(f" • Normal (OpenGL): {res['normal'].name}")
        print(f" • Roughness:       {res['roughness'].name}")
        print(f" • Height:          {res['height'].name}")
        print(f" • Cavity AO:       {res['ao'].name}")
        print("═"*70 + "\n")

def cmd_paywall(args):
    """Управление подписками, тарифами и токенами доступа к 8 TB Cloud"""
    from rmon.services.bot.paywall import PaywallManager
    mgr = PaywallManager()

    if args.action == "menu" or not args.action:
        print("\n" + "═"*70)
        print(mgr.get_payment_keyboard_text())
        print("═"*70 + "\n")
    elif args.action == "token":
        tok = mgr.generate_download_token(user_id=args.user or 999999, tier_key=args.tier or "basic_comfy", ttl_hours=args.ttl or 48)
        print(f"\n🔑 Сгенерирован VIP токен доступа:")
        print(f" • Токен: {tok}")
        print(f" • Ссылка для скачивания: https://t.me/your_bot?start=dl_{tok}")
        print(f" • Время жизни: {args.ttl or 48} часов\n")

def cmd_mine(args):
    """Автономный парсинг маркетплейсов и авто-генерация страниц/калькуляторов"""
    from rmon.services.scraper.auto_miner import AutoMinerPipeline
    print("\n" + "═"*75)
    print(" 🚀 ЗАПУСК АВТОНОМНОГО ПАРСИНГА МАРКЕТПЛЕЙСОВ (MARKET MINING ENGINE)")
    print("═"*75)
    
    auto_deploy = not args.no_deploy
    results = asyncio.run(AutoMinerPipeline.mine_targets(
        target_ids=args.targets,
        limit_per_target=args.limit,
        auto_deploy=auto_deploy
    ))

    print("\n" + "═"*75)
    print(" 📊 ИТОГИ АВТОНОМНОГО СБОРА ДАННЫХ:")
    for tid, count in results.items():
        print(f"  • [{tid}]: {count} лотов записано в Data Lake")
    print(" 🌐 Портал и калькуляторы пересобраны и синхронизированы с GitHub Pages!")
    print("═"*75 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Resource Monetization Platform CLI (RMon)")
    subparsers = parser.add_subparsers(dest="command", help="Команды платформы")

    # status
    subparsers.add_parser("status", help="Телеметрия кластера и ресурсов")

    # cases
    cas_p = subparsers.add_parser("cases", help="База знаний моделей монетизации и Idea Radar")
    cas_sub = cas_p.add_subparsers(dest="case_action", help="Действие над кейсами")
    cas_sub.add_parser("list", help="Список всех кейсов с метриками")
    show_p = cas_sub.add_parser("show", help="Просмотр полного досье кейса")
    show_p.add_argument("slug", help="Slug кейса")
    add_p = cas_sub.add_parser("add", help="AI-добавление и анализ новой идеи")
    add_p.add_argument("idea", help="Текстовое описание идеи / связки")

    # comfyui
    comfy_p = subparsers.add_parser("comfyui", help="Сборка и управление ComfyUI Portable Pack")
    comfy_sub = comfy_p.add_subparsers(dest="action", help="Действие ComfyUI")
    comfy_sub.add_parser("status", help="Проверка готовности GPU/CUDA и диска")
    comfy_sub.add_parser("workflows", help="Экспорт готовых рабочих воркфлоу")
    comfy_sub.add_parser("build", help="Сборка скелета и релиз-манифеста")

    # assets
    asset_p = subparsers.add_parser("assets", help="Генерация и упаковка AI Game Assets")
    asset_sub = asset_p.add_subparsers(dest="action", help="Действие над ассетами")
    tex_p = asset_sub.add_parser("textures", help="Генерация PBR материалов")
    tex_p.add_argument("--style", default="cobblestone", choices=["cobblestone", "scifi_metal", "wood_planks", "alien_rock"], help="Стиль текстур")
    tex_p.add_argument("--count", type=int, default=3, help="Количество материалов")
    tex_p.add_argument("--res", type=int, default=1024, help="Разрешение (512, 1024, 2048)")
    
    icon_p = asset_sub.add_parser("icons", help="Генерация RPG иконок и спрайт-листов")
    icon_p.add_argument("--item-type", default="potion", choices=["potion", "sword", "gem", "scroll"], help="Тип предметов")
    icon_p.add_argument("--count", type=int, default=4, help="Количество иконок")
    icon_p.add_argument("--res", type=int, default=512, help="Разрешение иконки")

    pkg_p = asset_sub.add_parser("package", help="Упаковка релизного ZIP бандла для itch.io")
    pkg_p.add_argument("--source", default="data/assets/textures", help="Исходная папка ассетов")
    pkg_p.add_argument("--slug", default="pbr_materials_vol1", help="Slug пакета")
    pkg_p.add_argument("--title", default="PBR Material Master Pack Vol. 1", help="Название для витрины")
    pkg_p.add_argument("--price", type=float, default=4.99, help="Цена в $USD")

    neu_p = asset_sub.add_parser("neural", help="Нейросетевая генерация фотореалистичных PBR материалов на DirectML GPU")
    neu_p.add_argument("--prompt", default="weathered gothic cathedral stone wall with carved gargoyle seams and moss", help="Промпт для генерации текстуры")
    neu_p.add_argument("--name", default="gothic_cathedral_stone", help="Название материала")
    neu_p.add_argument("--model", default="stabilityai/sd-turbo", help="HuggingFace модель (sd-turbo, sdxl-turbo)")
    neu_p.add_argument("--steps", type=int, default=4, help="Число шагов диффузии (1-8)")
    neu_p.add_argument("--res", type=int, default=512, help="Разрешение (512, 1024)")
    neu_p.add_argument("--seed", type=int, default=42, help="Случайный сид")

    # paywall
    pay_p = subparsers.add_parser("paywall", help="Управление подписками, тарифами и токенами 8 TB Cloud")
    pay_sub = pay_p.add_subparsers(dest="action", help="Действие paywall")
    pay_sub.add_parser("menu", help="Показать меню тарифов")
    tok_p = pay_sub.add_parser("token", help="Сгенерировать VIP токен доступа")
    tok_p.add_argument("--tier", default="basic_comfy", choices=["basic_comfy", "vip_all_access"], help="Уровень тарифа")
    tok_p.add_argument("--user", type=int, default=123456, help="ID пользователя Telegram")
    tok_p.add_argument("--ttl", type=int, default=48, help="Срок действия ссылки (в часах)")

    # seo
    seo_p = subparsers.add_parser("seo", help="Генератор Programmatic SEO портала цен")
    seo_p.add_argument("--build", action="store_true", help="Собрать статический сайт и sitemap.xml")
    seo_p.add_argument("--serve", action="store_true", help="Запустить локальный сервер для предпросмотра")
    seo_p.add_argument("--port", type=int, default=8181, help="Порт веб-сервера (по умолчанию 8181)")

    # repurpose
    rep_p = subparsers.add_parser("repurpose", help="Автономная упаковка подкастов/видео в посты и конспекты")
    rep_p.add_argument("--url", help="YouTube/RuTube URL или путь к медиафайлу")
    rep_p.add_argument("file", nargs="?", help="Путь к аудио/видео файлу (альтернатива --url)")
    rep_p.add_argument("--model", default="base", help="Размер Whisper модели (tiny, base, small, medium)")

    # monitor
    mon_p = subparsers.add_parser("monitor", help="Мониторинг цен маркетплейсов")
    mon_p.add_argument("--query", help="Поисковый запрос (например 'RTX 3080')")
    mon_p.add_argument("--city", default="moskva", help="Город ('moskva', 'spb')")
    mon_p.add_argument("--limit", type=int, default=15, help="Лимит объявлений")
    mon_p.add_argument("--threshold", type=float, default=20.0, help="Порог дисконта (%%)")
    mon_p.add_argument("--daemon", action="store_true", help="Запустить 24/7 демон")

    # inspect
    ins_p = subparsers.add_parser("inspect", help="Глубокая инспекция лота и скачивание фото")
    ins_p.add_argument("--url", help="URL объявления")
    ins_p.add_argument("--top-anomaly", action="store_true", help="Инспекция топ-аномалии из базы")
    ins_p.add_argument("--target", default="rtx_3080_moskva", help="ID таргета")

    # audit
    aud_p = subparsers.add_parser("audit", help="Локальный AI-аудит сделок на RTX 3050")
    aud_p.add_argument("--target", default="rtx_3080_moskva", help="ID таргета")
    aud_p.add_argument("--threshold", type=float, default=20.0, help="Порог дисконта (%%)")

    # transcribe
    tr_p = subparsers.add_parser("transcribe", help="Транскрибация аудио/видео")
    tr_p.add_argument("file", help="Путь к аудио/видео файлу")
    tr_p.add_argument("--model", default="medium", help="Размер модели (tiny, base, small, medium)")
    tr_p.add_argument("--language", default="ru", help="Язык аудио (ru, en, auto)")

    # bot
    subparsers.add_parser("bot", help="Запуск Unified Telegram Gateway")

    # sync
    subparsers.add_parser("sync", help="Экспорт Data Lake и облачный бэкап")

    # hybrid
    hyb_p = subparsers.add_parser("hybrid", help="Запуск единого сквозного гибридного цикла монетизации (Flywheel)")
    hyb_p.add_argument("--query", default="RTX 3080", help="Поисковый запрос / таргет")
    hyb_p.add_argument("--city", default="moskva", help="Город ('moskva', 'spb')")
    hyb_p.add_argument("--limit", type=int, default=6, help="Лимит сбора позиций")

    # digest
    dig_p = subparsers.add_parser("digest", help="Генерация аналитических постов для медиа-канала")
    dig_p.add_argument("--guide", action="store_true", help="Сгенерировать обучающий гайд безопасности")
    dig_p.add_argument("--send", action="store_true", help="Отправить готовый пост в Telegram")

    # mine
    min_p = subparsers.add_parser("mine", help="Автономный парсинг маркетплейсов и авто-генерация страниц/калькуляторов")
    min_p.add_argument("--targets", nargs="*", help="Список ID таргетов (по умолчанию все активные)")
    min_p.add_argument("--limit", type=int, default=8, help="Лимит лотов на категорию (по умолчанию 8)")
    min_p.add_argument("--no-deploy", action="store_true", help="Отключить авто-деплой в GitHub Pages")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status()
    elif args.command == "cases":
        cmd_cases(args)
    elif args.command == "comfyui":
        cmd_comfyui(args)
    elif args.command == "assets":
        cmd_assets(args)
    elif args.command == "paywall":
        cmd_paywall(args)
    elif args.command == "seo":
        cmd_seo(args)
    elif args.command == "repurpose":
        cmd_repurpose(args)
    elif args.command == "monitor":
        cmd_monitor(args)
    elif args.command == "inspect":
        cmd_inspect(args)
    elif args.command == "audit":
        cmd_audit(args)
    elif args.command == "transcribe":
        cmd_transcribe(args)
    elif args.command == "bot":
        cmd_bot(args)
    elif args.command == "sync":
        cmd_sync(args)
    elif args.command == "hybrid":
        cmd_hybrid(args)
    elif args.command == "digest":
        cmd_digest(args)
    elif args.command == "mine":
        cmd_mine(args)
    else:
        cmd_status()
        parser.print_help()

if __name__ == "__main__":
    main()

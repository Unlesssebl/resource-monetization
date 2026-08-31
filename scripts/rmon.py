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

    args = parser.parse_args()

    if args.command == "status":
        cmd_status()
    elif args.command == "cases":
        cmd_cases(args)
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
    else:
        cmd_status()
        parser.print_help()

if __name__ == "__main__":
    main()

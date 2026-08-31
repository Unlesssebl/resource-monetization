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
    print("\n" + "="*65)
    print("🖥️  RESOURCE MONETIZATION PLATFORM — КЛАСТЕРНЫЙ СТАТУС")
    print("="*65)
    
    # GPU VRAM Telemetry
    gpu = HardwareArbiter.get_gpu_telemetry()
    if gpu["available"]:
        print(f"🎮 GPU 1 (AI/Compute): {gpu['name']}")
        print(f"   • VRAM: {gpu['vram_used_mb']} MB / {gpu['vram_total_mb']} MB ({gpu['vram_free_mb']} MB свободно)")
        print(f"   • Нагрузка: {gpu['gpu_util_pct']}% | Температура: {gpu['temperature_c']}°C")
    else:
        print("🎮 GPU 1: Акселерация DirectCompute / CPU Fallback")

    print("\n📦 Host 2 (Heavy Node 24/7):")
    print("   • CPU: Core i5-12600KF | RAM: 48 GB DDR4 | GPU: RX 6800 XT (16 GB)")
    print("   • Cloud Vault: 8 TB Pool (Google Drive + Яндекс.Диск)")

    # Data Lake Stats
    conn = DataLake.get_connection()
    try:
        count = conn.execute("SELECT count(*) FROM price_history").fetchone()[0]
        targets = conn.execute("SELECT count(DISTINCT target_id) FROM price_history").fetchone()[0]
        print(f"\n📊 Data Lake (DuckDB):")
        print(f"   • Всего записей цен: {count:,}")
        print(f"   • Активных таргетов: {targets}")
    except Exception:
        pass
    finally:
        conn.close()

    print("="*65 + "\n")

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

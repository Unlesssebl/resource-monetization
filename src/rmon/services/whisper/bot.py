"""
Unified Telegram Sovereign Assistant & Price Radar Bot for RMon Platform.
Объединяет:
1. Бесплатный чекер и AI-аудитор цен Авито (Product-Led защита покупателей)
2. Аналитику рынка и ценовые барометры из DuckDB Data Lake
3. Аппаратную AI-транскрибацию аудио/видео/кружков через Faster-Whisper на GPU
"""
import re
import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from rmon.core.config import settings
from rmon.core.logger import get_logger
from rmon.core.lake import DataLake
from rmon.services.whisper.engine import WhisperEngine
from rmon.services.scraper.avito import AvitoScraper
from rmon.services.ai.deal_auditor import AIDealAuditor

from rmon.services.bot.paywall import PaywallManager

logger = get_logger("TelegramBot")
router = Router()
paywall_mgr = PaywallManager()

def get_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎮 Каталог AI-Ассетов", callback_data="assets_catalog"),
        InlineKeyboardButton(text="💎 VIP Доступ к 8 TB Vault", callback_data="vip_paywall")
    )
    builder.row(
        InlineKeyboardButton(text="🔍 Проверить цену лота", callback_data="help_check"),
        InlineKeyboardButton(text="📊 Аналитика рынка", callback_data="market_stats")
    )
    builder.row(
        InlineKeyboardButton(text="🎙️ AI Транскрибатор", callback_data="whisper_info"),
        InlineKeyboardButton(text="🛡️ Памятка безопасности", callback_data="safety_guide")
    )
    return builder.as_markup()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name if message.from_user else "друг"
    welcome_text = (
        f"👋 <b>Здравствуйте, {user_name}!</b>\n\n"
        "Добро пожаловать в <b>RMon Multi-Host AI Hub</b> — экосистему цифровых продуктов, GPU-сервисов и аналитики.\n\n"
        "🎯 <b>Возможности:</b>\n"
        "1. <b>🎮 Каталог Game Ready Ассетов:</b> Наборы 2D RPG иконок, бесшовные 4K PBR текстуры с коммерческой лицензией.\n"
        "2. <b>💎 VIP 8 TB Cloud Vault:</b> Доступ к портативным сборкам ComfyUI (DirectML/CUDA) и терабайтам архивов.\n"
        "3. <b>🎙️ Аппаратный Whisper GPU:</b> Пришлите любое голосовое, видео или кружок — мгновенно расшифрую в текст и субтитры (.srt).\n"
        "4. <b>🔍 Аудитор цен Авито:</b> Отправьте ссылку на объявление или название товара — рассчитаю рыночную цену и риски.\n\n"
        "💡 <i>Выберите раздел ниже или отправьте файл / ссылку в чат!</i>"
    )
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=get_main_keyboard())

@router.callback_query(F.data == "assets_catalog")
async def cb_assets_catalog(callback: types.CallbackQuery):
    text = (
        "🎮 <b>Каталог цифровых AI-Ассетов (Commercial Game Ready):</b>\n\n"
        "1. ⚔️ <b>Fantasy RPG Inventory & Skill Icons (Vol. 1):</b>\n"
        "   • 26+ стилизованных спрайтов (зелья, мечи, руны, свитки, реликвии)\n"
        "   • Прозрачный фон (RGBA) + готовый атлас спрайтов\n"
        "   • <i>Цена: $4.99 / 390 ₽ (или бесплатно на itch.io)</i>\n\n"
        "2. 🏰 <b>Dark Fantasy Dungeon PBR Essentials:</b>\n"
        "   • 5 нейросетевых материалов (стены, пол, железо, дерево, магма)\n"
        "   • Все 5 карт: Albedo, Normal (OpenGL), Roughness, Height, AO\n"
        "   • <i>Цена: $4.99 / 390 ₽</i>\n\n"
        "👉 <i>Все паки включают Commercial Indie License для коммерческих игр!</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Получить все паки по VIP-подписке", callback_data="vip_paywall")]
    ])
    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "vip_paywall")
async def cb_vip_paywall(callback: types.CallbackQuery):
    text = paywall_mgr.get_payment_keyboard_text()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить 390 ₽ (ComfyUI Pack)", url="https://boosty.to")],
        [InlineKeyboardButton(text="👑 Оплатить 790 ₽ (8 TB All-Access)", url="https://boosty.to")],
        [InlineKeyboardButton(text="🔑 Ввести токен доступа", callback_data="enter_token")]
    ])
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "enter_token")
async def cb_enter_token(callback: types.CallbackQuery):
    await callback.message.answer(
        "🔑 <b>Активация VIP-токена:</b>\n\n"
        "Отправьте команду <code>/redeem ВАШ_ТОКЕН</code>, чтобы получить персональную ссылку на скачивание.",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(Command("redeem"))
async def cmd_redeem(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Укажите токен: <code>/redeem ВАШ_ТОКЕН</code>", parse_mode="HTML")
        return
    token = args[1].strip()
    verified = paywall_mgr.verify_token(token)
    if verified:
        await message.answer(
            f"✅ <b>Токен успешно активирован!</b>\n\n"
            f"• <b>Тариф:</b> <code>{verified['tier']}</code>\n"
            f"• <b>Ссылка на 8 TB Cloud Vault:</b> https://drive.google.com/drive/folders/your_vault_id\n"
            f"• <b>Зеркало Яндекс.Диск:</b> https://disk.yandex.ru/d/your_mirror_id\n\n"
            f"⏳ <i>Ссылка активна 48 часов.</i>",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Токен недействителен или срок его действия истек.", parse_mode="HTML")

@router.callback_query(F.data == "help_check")
async def cb_help_check(callback: types.CallbackQuery):
    text = (
        "🔍 <b>Как работает чекер цен:</b>\n\n"
        "1. Скопируйте ссылку на любое объявление на Авито (через кнопку «Поделиться»).\n"
        "2. Отправьте ссылку сюда в чат.\n"
        "3. Бот сопоставит цену с тысячами аналогичных лотов в DuckDB Data Lake, "
        "рассчитает медиану и проанализирует текст на триггеры недобросовестных продавцов."
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "market_stats")
async def cb_market_stats(callback: types.CallbackQuery):
    targets = ["rtx_3080_moskva", "iphone_15_pro_moskva", "playstation_5_moskva", "rtx_4080_moskva"]
    lines = ["📊 <b>Текущие медианные цены (Срез Data Lake):</b>\n"]
    
    for t in targets:
        s = DataLake.get_market_summary(t)
        if s and s.get("median_price", 0) > 0:
            name = t.replace("_moskva", "").replace("_", " ").upper()
            lines.append(
                f"• <b>{name}:</b> медиана <code>{s['median_price']:,.0f} ₽</code> "
                f"(P25: {s.get('p25_price', 0):,.0f} ₽ | база: {s.get('total_items', 0)} шт.)"
            )
            
    if len(lines) == 1:
        lines.append("<i>База данных обновляется в фоновом режиме. Отправьте название товара для прямого замера!</i>")
    
    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "safety_guide")
async def cb_safety_guide(callback: types.CallbackQuery):
    guide_text = (
        "🛡️ <b>Чек-лист безопасной покупки на вторичном рынке:</b>\n\n"
        "1. <b>Видеокарты:</b> Всегда требуйте 10-минутный тест в FurMark + Superposition при вас. Следите за температурой HotSpot (дельта с GPU не должна превышать 15-20°C).\n"
        "2. <b>Смартфоны:</b> Проверяйте статус блокировки iCloud/Google, оригинальность дисплея (TrueTone/автояркость) и остаточную емкость АКБ через 3uTools.\n"
        "3. <b>Оплата:</b> Никогда не переходите по сторонним ссылкам на «доставку» из мессенджеров. Используйте только встроенную Авито Доставку с проверкой при получении."
    )
    await callback.message.answer(guide_text, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "whisper_info")
async def cb_whisper_info(callback: types.CallbackQuery):
    text = (
        "🎙️ <b>Аппаратный Whisper Транскрибатор:</b>\n\n"
        "• Обработка идет на выделенном GPU-кластере (RTX 3050 / RX 6800 XT).\n"
        "• 1 час аудио расшифровывается всего за <b>3.5 минуты</b>.\n"
        "• На выходе формируются готовые субтитры <code>.srt</code> и полный текст <code>.txt</code>.\n\n"
        "🚀 <i>Просто перешлите любое голосовое или видео сюда!</i>"
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

# 🔍 Хэндлер ссылок на Авито (Чекинг лота)
@router.message(F.text.regexp(r"https?://(?:www\.)?avito\.ru/[^\s]+"))
async def handle_avito_link(message: types.Message):
    url = message.text.strip()
    status_msg = await message.answer("⏳ <b>Анализирую объявление и сверяю с рыночной базой...</b>", parse_mode="HTML")

    try:
        # 1. Сбор детальной информации
        details = await AvitoScraper.get_listing_details(url=url, download_photos=False, headless=True)
        title = details.get("title") or "Товар на Авито"
        price = details.get("price", 0.0)
        desc = details.get("description", "")
        seller = details.get("seller_name", "Частное лицо")
        location = details.get("location", "Москва")

        if price <= 0:
            await status_msg.edit_text(
                "⚠️ Не удалось извлечь точную цену с этой страницы (возможно, лот снят с продажи или защищен капчей).",
                parse_mode="HTML"
            )
            return

        # 2. Определение таргет-ключа для поиска в DuckDB
        clean_title = re.sub(r"[^\w\s]", "", title).lower()
        target_candidates = ["rtx_3080_moskva", "iphone_15_pro_moskva", "playstation_5_moskva", "rtx_4080_moskva"]
        matched_target = None
        for t in target_candidates:
            key_part = t.replace("_moskva", "").replace("_", " ")
            if key_part in clean_title:
                matched_target = t
                break

        summary = DataLake.get_market_summary(matched_target) if matched_target else {}
        median = summary.get("median_price", 0.0)

        # 3. AI-Аудит рисков
        audit = AIDealAuditor.audit_listing(
            title=title,
            price=price,
            description=desc,
            seller=seller,
            location=location,
            market_median=median if median > 0 else None
        )

        # 4. Формирование отчета
        verdict = audit.get("verdict", "CAUTION")
        risk_score = audit.get("risk_score", 30)
        summary_note = audit.get("concise_summary", "Объявление выглядит стандартно.")
        issues = audit.get("detected_issues", [])

        if verdict == "BUY":
            badge = "🟢 <b>Выгодное предложение</b>"
        elif verdict == "CAUTION":
            badge = "🟡 <b>Требует внимательной проверки</b>"
        else:
            badge = "🔴 <b>Высокий риск переплаты или дефектов</b>"

        price_analysis = ""
        if median > 0:
            diff_pct = ((price - median) / median) * 100.0
            if diff_pct < -10:
                price_analysis = f"📉 <b>Цена ниже медианы на {abs(diff_pct):.1f}%!</b> (Рыночная медиана: <code>{median:,.0f} ₽</code>)"
            elif diff_pct > 10:
                price_analysis = f"📈 <b>Цена выше медианы на {diff_pct:.1f}%.</b> (Рыночная медиана: <code>{median:,.0f} ₽</code>)"
            else:
                price_analysis = f"⚖️ <b>Цена полностью в рынке.</b> (Медиана: <code>{median:,.0f} ₽</code>)"
        else:
            price_analysis = "ℹ️ <i>Прямая медиана формируется в базе.</i>"

        report_lines = [
            f"📦 <b>{title}</b>\n",
            f"💰 <b>Цена продавца:</b> <code>{price:,.0f} ₽</code>",
            price_analysis,
            f"👤 <b>Продавец:</b> {seller} | 📍 {location}\n",
            f"🛡️ <b>Вердикт безопасности:</b> {badge} (Индекс риска: <b>{risk_score}/100</b>)",
            f"💡 <i>{summary_note}</i>"
        ]

        if issues:
            report_lines.append("\n🚩 <b>На что обратить внимание:</b>")
            for iss in issues[:3]:
                report_lines.append(f"• {iss}")

        encoded_title = re.sub(r'\s+', '+', title[:30])
        buttons = [
            [InlineKeyboardButton(text="🛒 Найти новый с гарантией на Яндекс.Маркете", url=f"https://market.yandex.ru/search?text={encoded_title}")],
            [InlineKeyboardButton(text="🔔 Отслеживать снижение цены", callback_data=f"track_{details.get('id', 'item')}")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await status_msg.edit_text("\n".join(report_lines), parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        logger.exception(f"Ошибка анализа ссылки {url}")
        await status_msg.edit_text(f"⚠️ Не удалось выполнить аудит ссылки: {str(e)[:100]}")

# 📊 Хэндлер текстового поиска товара
@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_query(message: types.Message):
    query = message.text.strip()
    if len(query) < 3:
        return

    target_id = f"{query.lower().replace(' ', '_')}_moskva"
    summary = DataLake.get_market_summary(target_id)
    
    if summary and summary.get("total_items", 0) > 0:
        median = summary["median_price"]
        p25 = summary.get("p25_price", 0)
        total = summary.get("total_items", 0)
        
        reply = (
            f"📊 <b>Ценовой срез для «{query}» (Москва):</b>\n\n"
            f"• <b>Медианная цена:</b> <code>{median:,.0f} ₽</code>\n"
            f"• <b>Нижняя планка (P25):</b> <code>{p25:,.0f} ₽</code>\n"
            f"• <b>Диапазон цен:</b> <code>{summary.get('min_price', 0):,.0f} ₽</code> — <code>{summary.get('max_price', 0):,.0f} ₽</code>\n"
            f"• <b>Позиций в базе:</b> {total} объявлений\n\n"
            f"💡 <i>Отправьте ссылку на конкретное объявление, чтобы получить детальный AI-аудит лота!</i>"
        )
        encoded_query = re.sub(r'\s+', '+', query)
        btn = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🛒 Найти новый {query} на Маркете", url=f"https://market.yandex.ru/search?text={encoded_query}")]
        ])
        await message.answer(reply, parse_mode="HTML", reply_markup=btn)
    else:
        await message.answer(
            f"🔍 Ищу свежие данные по запросу <b>«{query}»</b>...\n\n"
            f"💡 Вы также можете просто прислать прямую ссылку на объявление с Авито для мгновенного разбора!",
            parse_mode="HTML"
        )

# 🎙️ Хэндлер медиафайлов (Whisper GPU)
@router.message(F.voice | F.audio | F.video | F.video_note | F.document)
async def handle_media(message: types.Message, bot: Bot):
    status_msg = await message.answer("⏳ <b>Скачиваю файл и запускаю Whisper на GPU...</b>", parse_mode="HTML")
    
    try:
        file_obj = message.voice or message.audio or message.video or message.video_note or message.document
        file_id = file_obj.file_id
        
        ext = ".mp3"
        if message.voice:
            ext = ".ogg"
        elif message.video or message.video_note:
            ext = ".mp4"
        elif message.document and message.document.file_name:
            ext = Path(message.document.file_name).suffix or ".mp3"

        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_id = message.from_user.id if message.from_user else 0
        msg_id = message.message_id
        
        local_dir = settings.DATA_DIR / "bot_downloads"
        local_dir.mkdir(parents=True, exist_ok=True)
        unique_name = f"audio_{user_id}_{msg_id}_{ts_str}"
        local_filename = local_dir / f"{unique_name}{ext}"

        file_info = await bot.get_file(file_id)
        await bot.download_file(file_info.file_path, destination=local_filename)
        await status_msg.edit_text("⚡ <b>Обработка на GPU...</b>", parse_mode="HTML")

        res = await asyncio.to_thread(
            WhisperEngine.transcribe,
            file_path=str(local_filename),
            output_dir=str(local_dir / "transcripts"),
            model_size=settings.WHISPER_MODEL
        )

        preview = res["full_text"][:800] + ("..." if len(res["full_text"]) > 800 else "")
        if not preview:
            preview = "(речь не обнаружена)"

        summary_msg = (
            f"✅ <b>Транскрибация завершена за {res['elapsed']:.1f} сек!</b>\n"
            f"🚀 <b>Скорость:</b> {res['speed_factor']:.1f}x в реальном времени | <b>Язык:</b> {res['language'].upper()}\n\n"
            f"📝 <b>Текст:</b>\n<i>«{preview}»</i>\n\n"
            f"👇 Готовые субтитры (.srt) и полный текст прикреплены ниже:"
        )

        await status_msg.edit_text(summary_msg, parse_mode="HTML")

        srt_file = FSInputFile(res["srt_path"], filename=f"subtitles_{ts_str}.srt")
        txt_file = FSInputFile(res["txt_path"], filename=f"transcript_{ts_str}.txt")

        await message.answer_document(srt_file, caption="🎬 Готовые субтитры (.srt)")
        await message.answer_document(txt_file, caption="📄 Полный текст (.txt)")

        try:
            if local_filename.exists():
                local_filename.unlink(missing_ok=True)
        except Exception:
            pass

    except Exception as e:
        logger.exception("Ошибка при транскрибации файла")
        await status_msg.edit_text(f"❌ Ошибка обработки: {str(e)[:150]}")

class WhisperBot:
    """Обертка для синхронного запуска бота в потоке или процессе"""
    def start_polling(self):
        asyncio.run(start_bot())

async def start_bot():
    if not settings.BOT_TOKEN:
        logger.warning("BOT_TOKEN не установлен в .env")
        return

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("🤖 Sovereign Telegram Assistant активен и слушает сообщения...")
    await dp.start_polling(bot)
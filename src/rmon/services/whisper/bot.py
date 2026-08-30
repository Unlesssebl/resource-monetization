import asyncio
from pathlib import Path
from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from rmon.core.config import settings
from rmon.core.logger import get_logger
from rmon.services.whisper.engine import WhisperEngine

logger = get_logger("TelegramBot")
router = Router()

def get_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⚡ Тарифы и подписка", callback_data="pricing"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats")
    )
    builder.row(
        InlineKeyboardButton(text="💬 Поддержка / B2B Заказ", url="https://t.me/BotFather")
    )
    return builder.as_markup()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name if message.from_user else "друг"
    welcome_text = (
        f"👋 Привет, {user_name}!\n\n"
        "🎙️ **Я — автономный AI-транскрибатор сверхвысокой скорости.**\n\n"
        "⚡ **Что я умею:**\n"
        "• Мгновенно расшифровывать голосовые сообщения, аудио и видео в текст.\n"
        "• Создавать готовые субтитры (.srt) с таймкодами для монтажа Shorts/Reels/YouTube.\n"
        "• 0 ₽ себестоимость на локальном оборудовании 24/7.\n\n"
        "🚀 Отправь мне голосовое сообщение или аудиофайл!"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

@router.callback_query(F.data == "pricing")
async def cb_pricing(callback: types.CallbackQuery):
    pricing_text = (
        "💎 **Тарифы на AI-транскрибацию:**\n\n"
        "• **Бесплатный тест:** первые файлы до 5 минут — бесплатно.\n"
        "• **Разовый пакет (до 3 часов аудио):** 500 ₽ (сдача за 15 минут).\n"
        "• **B2B Подписка для подкастеров (до 30 часов/мес):** 3 500 ₽/мес.\n"
        "• **Мониторинг маркетплейсов под ключ:** от 2 500 ₽/мес."
    )
    await callback.message.answer(pricing_text, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "stats")
async def cb_stats(callback: types.CallbackQuery):
    stats_text = (
        "📊 **Статус системы:**\n\n"
        f"• **AI Engine:** faster-whisper ({settings.WHISPER_MODEL})\n"
        f"• **Compute:** {settings.WHISPER_DEVICE.upper()} ({settings.WHISPER_COMPUTE})\n"
        "• **Режим:** 24/7 локальная обработка"
    )
    await callback.message.answer(stats_text, parse_mode="Markdown")
    await callback.answer()

@router.message(F.voice | F.audio | F.video | F.video_note | F.document)
async def handle_media(message: types.Message, bot: Bot):
    status_msg = await message.answer("⏳ Скачиваю файл и запускаю локальный AI-инференс...")
    
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

        file_info = await bot.get_file(file_id)
        local_dir = settings.DATA_DIR / "bot_downloads"
        local_dir.mkdir(parents=True, exist_ok=True)
        local_filename = local_dir / f"{file_id[:12]}_{message.from_user.id}{ext}"

        await bot.download_file(file_info.file_path, destination=local_filename)
        await status_msg.edit_text("⚡ Файл загружен. Выполняю транскрибацию Whisper...")

        res = await asyncio.to_thread(
            WhisperEngine.transcribe,
            file_path=str(local_filename),
            output_dir=str(local_dir / "transcripts"),
            model_size=settings.WHISPER_MODEL
        )

        preview = res["full_text"][:1000] + ("..." if len(res["full_text"]) > 1000 else "")

        summary_msg = (
            f"✅ **Транскрибация завершена за {res['elapsed']:.1f} сек!**\n"
            f"🚀 **Скорость:** {res['speed_factor']:.1f}x в реальном времени\n"
            f"🌍 **Язык:** {res['language'].upper()}\n\n"
            f"📝 **Текст:**\n_{preview}_\n\n"
            f"👇 Ниже прикреплены файлы субтитров (.srt) и полный текст:"
        )

        await status_msg.edit_text(summary_msg, parse_mode="Markdown")

        srt_file = FSInputFile(res["srt_path"], filename=f"subtitles_{local_filename.stem}.srt")
        txt_file = FSInputFile(res["txt_path"], filename=f"transcript_{local_filename.stem}.txt")

        await message.answer_document(srt_file, caption="🎬 Готовые субтитры (.srt)")
        await message.answer_document(txt_file, caption="📄 Полный текст (.txt)")

        # Clean up temporary downloaded file safely
        try:
            if local_filename.exists():
                local_filename.unlink(missing_ok=True)
        except Exception as err:
            logger.debug(f"Файл еще удерживается системой: {err}")

    except Exception as e:
        logger.exception("Ошибка при обработке файла")
        await status_msg.edit_text(f"❌ Ошибка обработки: {str(e)[:150]}")

async def start_bot():
    if not settings.BOT_TOKEN or settings.BOT_TOKEN == "your_telegram_bot_token_here":
        logger.warning("BOT_TOKEN не установлен в configs/.env.")
        print("\n⚠️ Укажите BOT_TOKEN в configs/.env для подключения к Telegram.")
        return

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("🚀 AI-движок GPU DirectCompute (AMD Radeon RX 6800 XT) активен!")
    logger.info("🤖 Telegram-бот слушает 24/7...")
    await dp.start_polling(bot)
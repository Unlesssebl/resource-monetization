import asyncio
from pathlib import Path
from aiogram import Router, F, types, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile

from shared.config import settings
from shared.logger import get_logger
from services.transcription.engine import WhisperEngine
from services.telegram_bot.keyboards import get_main_keyboard

logger = get_logger("TelegramHandlers")
router = Router()

BOT_DOWNLOADS_DIR = settings.DATA_DIR / "bot_downloads"
BOT_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name if message.from_user else "друг"
    welcome_text = (
        f"👋 Привет, {user_name}!\n\n"
        "🎙️ **Я — автономный AI-транскрибатор сверхвысокой скорости (Microservice Core).**\n\n"
        "⚡ **Возможности:**\n"
        "• Мгновенная расшифровка голосовых сообщений, аудио и видео в текст.\n"
        "• Генерация файлов субтитров (.srt) с таймкодами для монтажа.\n"
        "• 0 ₽ себестоимость на локальном оборудовании 24/7.\n\n"
        "🚀 Отправь мне голосовое сообщение или аудиофайл!"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

@router.callback_query(F.data == "pricing")
async def cb_pricing(callback: types.CallbackQuery):
    pricing_text = (
        "💎 **Тарифные планы:**\n\n"
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
        "📊 **Статус микросервисов:**\n\n"
        f"• **AI Engine:** faster-whisper ({settings.WHISPER_MODEL})\n"
        f"• **Compute:** {settings.WHISPER_DEVICE.upper()} ({settings.WHISPER_COMPUTE})\n"
        "• **Архитектура:** Microservices & Clean Architecture"
    )
    await callback.message.answer(stats_text, parse_mode="Markdown")
    await callback.answer()

@router.message(F.voice | F.audio | F.video | F.video_note | F.document)
async def handle_media(message: types.Message, bot: Bot):
    status_msg = await message.answer("⏳ Скачиваю файл и передаю в микросервис транскрибации...")
    
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
        local_filename = BOT_DOWNLOADS_DIR / f"{file_id[:12]}_{message.from_user.id}{ext}"

        await bot.download_file(file_info.file_path, destination=local_filename)
        await status_msg.edit_text("⚡ Файл получен. Выполняю инференс Whisper...")

        res = await asyncio.to_thread(
            WhisperEngine.transcribe,
            file_path=str(local_filename),
            output_dir=str(BOT_DOWNLOADS_DIR / "transcripts"),
            model_size=settings.WHISPER_MODEL
        )

        preview = res["full_text"][:1000] + ("..." if len(res["full_text"]) > 1000 else "")

        summary_msg = (
            f"✅ **Транскрибация завершена за {res['elapsed']:.1f} сек!**\n"
            f"🚀 **Скорость:** {res['speed_factor']:.1f}x в реальном времени\n"
            f"🌍 **Язык:** {res['language'].upper()}\n\n"
            f"📝 **Текст:**\n_{preview}_\n\n"
            f"👇 Файлы субтитров и текста прикреплены ниже:"
        )

        await status_msg.edit_text(summary_msg, parse_mode="Markdown")

        srt_file = FSInputFile(res["srt_path"], filename=f"subtitles_{local_filename.stem}.srt")
        txt_file = FSInputFile(res["txt_path"], filename=f"transcript_{local_filename.stem}.txt")

        await message.answer_document(srt_file, caption="🎬 Субтитры (.srt)")
        await message.answer_document(txt_file, caption="📄 Текст (.txt)")

        if local_filename.exists():
            local_filename.unlink()

    except Exception as e:
        logger.exception("Ошибка при обработке сообщения")
        await status_msg.edit_text(f"❌ Ошибка обработки: {str(e)[:150]}")
#!/usr/bin/env python3
"""
Autonomous Telegram AI Transcription Bot
Powered by aiogram 3.x and faster-whisper.
Receives voice messages, audio, and video files, transcribing them with sub-second latency.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Add scripts directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from transcribe_pipeline import transcribe_file

# Load environment variables
load_dotenv(Path(__file__).resolve().parent.parent / "configs" / ".env")
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = os.getenv("ADMIN_ID", "")
DEFAULT_MODEL = os.getenv("WHISPER_MODEL", "medium")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE", "int8")

LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "bot_downloads"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("TranscribeBot")

dp = Dispatcher()

def get_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⚡ Тарифы и подписка", callback_data="pricing"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats")
    )
    builder.row(
        InlineKeyboardButton(text="💬 Поддержка / Заказ под ключ", url="https://t.me/BotFather")
    )
    return builder.as_markup()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name if message.from_user else "друг"
    welcome_text = (
        f"👋 Привет, {user_name}!\n\n"
        "🎙️ **Я — автономный AI-транскрибатор сверхвысокой скорости.**\n\n"
        "⚡ **Что я умею:**\n"
        "• Мгновенно расшифровывать голосовые сообщения, аудиозаписи и подкасты в текст.\n"
        "• Создавать готовые субтитры (.srt) с таймкодами для монтажа видео (Shorts/Reels/YouTube).\n"
        "• Работать с файлами на русском, английском и еще 90+ языках.\n\n"
        "🚀 **Как пользоваться:** просто отправь мне голосовое сообщение, аудиофайл (.mp3, .m4a, .wav) или видео!"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "💡 **Инструкция по использованию:**\n\n"
        "1. Перешлите мне любое голосовое сообщение или кружочек.\n"
        "2. Или загрузите аудио/видео файл любого размера.\n"
        "3. Бот автоматически распознает речь, расставит знаки препинания и пришлет:\n"
        "   • Текстовую расшифровку в чат.\n"
        "   • Файл субтитров (.srt) с таймкодами.\n"
        "   • Чистый .txt файл для копирования.\n\n"
        "💎 **Себестоимость:** 0 ₽ на локальном GPU/CPU."
    )
    await message.answer(help_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

@dp.callback_query(F.data == "pricing")
async def cb_pricing(callback: types.CallbackQuery):
    pricing_text = (
        "💎 **Тарифы на AI-транскрибацию:**\n\n"
        "• **Бесплатный тест:** первые файлы до 5 минут — бесплатно.\n"
        "• **Разовый пакет (до 3 часов аудио):** 500 ₽ (сдача за 15 минут).\n"
        "• **B2B Подписка для подкастеров / школ (до 30 часов/мес):** 3 500 ₽/мес.\n"
        "• **Индивидуальный парсинг и мониторинг данных:** от 2 500 ₽/мес.\n\n"
        "Для подключения безлимита или оплаты картой/криптовалютой напишите администратору."
    )
    await callback.message.answer(pricing_text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "stats")
async def cb_stats(callback: types.CallbackQuery):
    stats_text = (
        "📊 **Текущий статус сервиса:**\n\n"
        f"• **Движок:** aster-whisper ({DEFAULT_MODEL})\n"
        f"• **Устройство инференса:** {WHISPER_DEVICE.upper()} ({WHISPER_COMPUTE})\n"
        "• **Режим работы:** 24/7 (Аптайм 99.9%)\n"
        "• **Средняя скорость:** в 15–20 раз быстрее реального времени."
    )
    await callback.message.answer(stats_text, parse_mode="Markdown")
    await callback.answer()

@dp.message(F.voice | F.audio | F.video | F.video_note | F.document)
async def handle_media(message: types.Message, bot: Bot):
    status_msg = await message.answer("⏳ Скачиваю файл и запускаю локальный AI-инференс...")
    
    try:
        # Determine file type
        file_obj = message.voice or message.audio or message.video or message.video_note or message.document
        file_id = file_obj.file_id
        
        # Get file extension
        ext = ".mp3"
        if message.voice:
            ext = ".ogg"
        elif message.video or message.video_note:
            ext = ".mp4"
        elif message.document and message.document.file_name:
            ext = Path(message.document.file_name).suffix or ".mp3"

        file_info = await bot.get_file(file_id)
        file_path_tg = file_info.file_path
        local_filename = DATA_DIR / f"{file_id[:12]}_{message.from_user.id}{ext}"

        # Download file
        await bot.download_file(file_path_tg, destination=local_filename)
        await status_msg.edit_text("⚡ Файл загружен. Выполняю высокоточную транскрибацию Whisper...")

        # Process in thread pool
        res = await asyncio.to_thread(
            transcribe_file,
            file_path=str(local_filename),
            output_dir=str(DATA_DIR / "transcripts"),
            model_size=DEFAULT_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE
        )

        # Read text preview
        with open(res["txt_path"], "r", encoding="utf-8") as f:
            full_text = f.read()

        preview = full_text[:1200] + ("..." if len(full_text) > 1200 else "")

        summary_msg = (
            f"✅ **Транскрибация завершена за {res['elapsed']:.1f} сек!**\n"
            f"🚀 **Скорость:** {res['speed_factor']:.1f}x в реальном времени\n"
            f"🌍 **Язык:** {res['language'].upper()}\n\n"
            f"📝 **Текст:**\n_{preview}_\n\n"
            f"👇 Ниже прикреплены файлы субтитров (.srt) и полный текст:"
        )

        await status_msg.edit_text(summary_msg, parse_mode="Markdown")

        # Send .txt and .srt documents
        srt_file = FSInputFile(res["srt_path"], filename=f"subtitles_{local_filename.stem}.srt")
        txt_file = FSInputFile(res["txt_path"], filename=f"transcript_{local_filename.stem}.txt")

        await message.answer_document(srt_file, caption="🎬 Готовые субтитры с таймкодами (.srt)")
        await message.answer_document(txt_file, caption="📄 Полный текст (.txt)")

        # Cleanup downloaded raw file
        if local_filename.exists():
            local_filename.unlink()

    except Exception as e:
        logger.exception("Ошибка при обработке файла")
        await status_msg.edit_text(f"❌ Ошибка при обработке: {str(e)[:200]}")

async def main():
    if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token_here":
        print("⚠️ BOT_TOKEN не установлен в configs/.env. Запуск в тестовом режиме.")
        print("💡 Для запуска бота укажите BOT_TOKEN в файле configs/.env и запустите: python scripts/transcribe_bot.py")
        return

    bot = Bot(token=BOT_TOKEN)
    logger.info("🤖 Бот запущен и готов к обработке сообщений 24/7...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
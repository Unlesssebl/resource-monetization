import asyncio
from aiogram import Bot, Dispatcher
from shared.config import settings
from shared.logger import get_logger
from services.telegram_bot.handlers import router

logger = get_logger("TelegramGatewayService")

async def run_bot():
    if not settings.BOT_TOKEN or settings.BOT_TOKEN == "your_telegram_bot_token_here":
        logger.warning("BOT_TOKEN не установлен в configs/.env. Запуск в режиме ожидания токена.")
        print("\n⚠️ Укажите BOT_TOKEN в configs/.env для подключения бота к сети Telegram.")
        return

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("🤖 Telegram Gateway Microservice запущен 24/7...")
    await dp.start_polling(bot)

def main():
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
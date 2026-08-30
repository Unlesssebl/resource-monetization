from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⚡ Тарифы и подписка", callback_data="pricing"),
        InlineKeyboardButton(text="📊 Статистика сервиса", callback_data="stats")
    )
    builder.row(
        InlineKeyboardButton(text="💬 Поддержка / B2B Заказ", url="https://t.me/BotFather")
    )
    return builder.as_markup()
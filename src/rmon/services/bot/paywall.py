"""Telegram Paywall & VIP Cloud Access Manager (Boosty, Telegram Stars & CryptoPay)."""

import hashlib
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

from rmon.core.config import settings
from rmon.core.logger import get_logger

logger = get_logger("PaywallManager")


class PaywallManager:
    """Manages subscription tiers, crypto/boosty payments, and time-limited cloud download tokens."""

    def __init__(self):
        self.tiers = {
            "basic_comfy": {
                "name": "ComfyUI SuperPack (Стандарт)",
                "price_rub": 390,
                "price_crypto_usdt": 4.5,
                "description": "Доступ к ComfyUI Portable + 4 готовых воркфлоу + обновления 1 месяц",
                "cloud_folder": "ComfyUI_v1_Release"
            },
            "vip_all_access": {
                "name": "VIP All-Access (8 TB Mega-Vault)",
                "price_rub": 790,
                "price_crypto_usdt": 8.9,
                "description": "Полный доступ ко всему хранилищу 8 ТБ (ComfyUI, AI-Ассеты, Видео-паки, Сборки модов)",
                "cloud_folder": "MegaVault_All_Access"
            }
        }
        # In-memory token store (or backed by DuckDB)
        self.issued_tokens: Dict[str, Dict[str, Any]] = {}

    def generate_download_token(self, user_id: int, tier_key: str, ttl_hours: int = 48) -> str:
        """Generate a cryptographically secure, time-limited download token for cloud mirrors."""
        if tier_key not in self.tiers:
            raise ValueError(f"Unknown tier: {tier_key}")
            
        raw = f"{user_id}:{tier_key}:{time.time()}:{settings.TELEGRAM_BOT_TOKEN or 'secret'}"
        token = hashlib.sha256(raw.encode()).hexdigest()[:24]
        
        expires_at = time.time() + (ttl_hours * 3600)
        self.issued_tokens[token] = {
            "user_id": user_id,
            "tier": tier_key,
            "expires_at": expires_at,
            "downloads_count": 0
        }
        logger.info(f"Generated VIP download token for user {user_id} (Tier: {tier_key}, TTL: {ttl_hours}h)")
        return token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify if token is valid and not expired."""
        info = self.issued_tokens.get(token)
        if not info:
            return None
        if time.time() > info["expires_at"]:
            del self.issued_tokens[token]
            return None
        info["downloads_count"] += 1
        return info

    def get_payment_keyboard_text(self) -> str:
        """Generate formatted pricing and payment menu for Telegram bot users."""
        lines = [
            "💎 **Выберите уровень доступа к Облачному Хранилищу (8 TB):**\n",
            "1️⃣ **ComfyUI SuperPack** — 390 ₽ / 4.5 USDT",
            "   • Готовая портативная сборка ComfyUI на RTX/CUDA в 1 клик",
            "   • Воркфлоу для 4K текстур, RPG иконок и апскейла 8K",
            "   • Скоростные ссылки на Яндекс Диск и Google Drive\n",
            "2️⃣ **VIP All-Access 8 TB Vault** — 790 ₽ / 8.9 USDT",
            "   • Полный доступ ко всем терабайтам данных (AI, Монтаж, Ассеты, Сборки)",
            "   • Приоритетные зеркала без квот и ожиданий",
            "   • Закрытый чат поддержки и ранние обновления\n",
            "💳 **Способы оплаты:**",
            "• Банковские карты РФ (через Boosty / Tribute)",
            "• Telegram Stars (мгновенно внутри Telegram)",
            "• Криптовалюта (USDT / TON через Telegram Wallet)"
        ]
        return "\n".join(lines)

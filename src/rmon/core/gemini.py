"""
Gemini API Client with Dynamic Key Rotation & Multimodal Vision for RMon Platform.
Портирован и адаптирован из tempo-ai-assistant.
Поддерживает:
- Пул множественных API-ключей Google AI Studio (ротация при 429 Rate Limit)
- Умную балансировку нагрузки (Smart Load-Balancing)
- Мультимодальный анализ изображений (тесты FurMark, фото лотов, пломбы)
- Автоматический fallback моделей: gemini-2.5-flash -> gemini-2.0-flash -> gemini-1.5-flash
- Работу без сторонних зависимостей через стандартную библиотеку urllib.request
"""
import os
import json
import time
import base64
import random
import asyncio
import urllib.request
import urllib.error
from threading import RLock
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

from rmon.core.config import settings
from rmon.core.logger import get_logger

logger = get_logger("GeminiRotator")

class ApiKeyManager:
    """Thread-safe менеджер ротации пула API-ключей Gemini"""

    _global_lock = RLock()
    _global_exhausted_keys: Set[str] = set()
    _global_current_index = 0
    _global_last_reset_time = time.time()

    def __init__(self, api_keys: List[str], reset_interval: int = 300, auto_rotate: bool = True):
        if not api_keys:
            logger.warning("ApiKeyManager инициализирован с пустым списком ключей.")
        self.api_keys = list(api_keys)
        self.reset_interval = reset_interval
        self.auto_rotate = auto_rotate

    @staticmethod
    def mask_key(key: str) -> str:
        if not key or len(key) < 8:
            return "***"
        return f"{key[:6]}...{key[-4:]}"

    def _check_reset_exhausted(self):
        with self._global_lock:
            now = time.time()
            if now - ApiKeyManager._global_last_reset_time > self.reset_interval:
                if ApiKeyManager._global_exhausted_keys:
                    logger.info(f"♻️ Сброс cooldown для {len(ApiKeyManager._global_exhausted_keys)} ключей Gemini")
                    ApiKeyManager._global_exhausted_keys.clear()
                ApiKeyManager._global_last_reset_time = now

    def get_current_key(self) -> Optional[str]:
        if not self.api_keys:
            return None
        with self._global_lock:
            self._check_reset_exhausted()
            available = [k for k in self.api_keys if k not in ApiKeyManager._global_exhausted_keys]
            if available:
                selected = random.choice(available) if self.auto_rotate else available[0]
                ApiKeyManager._global_current_index = self.api_keys.index(selected)
                return selected
            # Если все исчерпаны, берем первый с предупреждением
            logger.warning(f"⚠️ Все {len(self.api_keys)} ключей Gemini исчерпаны по лимитам! Пробуем резервный.")
            return self.api_keys[0]

    def mark_key_exhausted(self, key: str, reason: str = "429 Rate Limit"):
        with self._global_lock:
            if key in self.api_keys:
                ApiKeyManager._global_exhausted_keys.add(key)
                masked = self.mask_key(key)
                logger.warning(
                    f"⛔ Ключ Gemini {masked} помечен как исчерпанный ({reason}). "
                    f"Активно: {len(self.api_keys) - len(ApiKeyManager._global_exhausted_keys)}/{len(self.api_keys)}"
                )

    def get_pool_health(self) -> Dict[str, Any]:
        with self._global_lock:
            self._check_reset_exhausted()
            return {
                "total_keys": len(self.api_keys),
                "active_keys": len(self.api_keys) - len(ApiKeyManager._global_exhausted_keys),
                "exhausted_keys": len(ApiKeyManager._global_exhausted_keys)
            }


class GeminiClient:
    """Высокопроизводительный асинхронный клиент Gemini API с пулом ротации ключей"""

    FALLBACK_MODELS = [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro"
    ]

    def __init__(self, key_manager: Optional[ApiKeyManager] = None):
        keys = settings.GEMINI_API_KEYS
        self.key_manager = key_manager or ApiKeyManager(keys)

    async def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        image_paths: Optional[List[str]] = None,
        json_mode: bool = False,
        temperature: float = 0.2,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Универсальный вызов Gemini API с поддержкой текста, мультимодальных картинок и JSON.
        Автоматически переключает ключи при 429 и модели при 404/сбоях.
        """
        target_model = model or settings.GEMINI_MODEL
        if target_model == "gemini-2.5-flash":
            target_model = "gemini-2.0-flash"
            
        models_to_try = [target_model] + [m for m in self.FALLBACK_MODELS if m != target_model]
        
        loop = asyncio.get_event_loop()
        max_attempts = max(4, len(self.key_manager.api_keys) * 2)

        for attempt in range(1, max_attempts + 1):
            key = self.key_manager.get_current_key()
            if not key:
                raise ValueError("Не задан ни один GEMINI_API_KEY в .env!")

            current_model = models_to_try[(attempt - 1) % len(models_to_try)]
            masked_k = self.key_manager.mask_key(key)

            try:
                result = await loop.run_in_executor(
                    None,
                    lambda: self._call_gemini_rest(
                        api_key=key,
                        model=current_model,
                        prompt=prompt,
                        system_instruction=system_instruction,
                        image_paths=image_paths,
                        json_mode=json_mode,
                        temperature=temperature
                    )
                )
                return result

            except urllib.error.HTTPError as e:
                status = e.code
                err_body = e.read().decode("utf-8", errors="ignore")
                logger.warning(f"HTTP {status} от Gemini ({current_model}, ключ {masked_k}): {err_body[:120]}")

                if status == 429 or "RESOURCE_EXHAUSTED" in err_body:
                    self.key_manager.mark_key_exhausted(key, reason="429 Resource Exhausted")
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                    continue
                elif status == 404:
                    # Недоступная модель — сразу пробуем следующую модель из списка
                    logger.info(f"Модель {current_model} недоступна, переключение на следующую...")
                    continue
                elif status in [500, 503, 504]:
                    await asyncio.sleep(2.0)
                    continue
                else:
                    raise

            except Exception as ex:
                logger.error(f"Ошибка запроса к Gemini API: {ex}")
                await asyncio.sleep(1.0)

        raise RuntimeError("Все попытки обращения к пулу Gemini API исчерпаны.")

    def _call_gemini_rest(
        self,
        api_key: str,
        model: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        image_paths: Optional[List[str]] = None,
        json_mode: bool = False,
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """Синхронный REST вызов Gemini v1beta endpoint"""
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        parts: List[Dict[str, Any]] = [{"text": prompt}]

        # Добавление картинок в payload (Base64)
        if image_paths:
            for img_p in image_paths:
                p = Path(img_p)
                if p.exists() and p.is_file():
                    with open(p, "rb") as f:
                        img_b64 = base64.b64encode(f.read()).decode("utf-8")
                    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
                    parts.append({
                        "inline_data": {
                            "mime_type": mime,
                            "data": img_b64
                        }
                    })

        payload: Dict[str, Any] = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": temperature
            }
        }

        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))

        text = ""
        try:
            candidates = resp_data.get("candidates", [])
            if candidates:
                parts_out = candidates[0].get("content", {}).get("parts", [])
                text = "".join([p.get("text", "") for p in parts_out])
        except Exception:
            pass

        parsed_json = None
        if json_mode and text:
            try:
                # Очистка markdown блоков если есть
                cleaned = re.sub(r"^```json\s*", "", text.strip())
                cleaned = re.sub(r"\s*```$", "", cleaned)
                parsed_json = json.loads(cleaned)
            except Exception:
                pass

        return {
            "model_used": model,
            "text": text,
            "json": parsed_json,
            "raw": resp_data
        }

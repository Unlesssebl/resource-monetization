import json
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional
from rmon.core.logger import get_logger

logger = get_logger("AIDealAuditor")

class AIDealAuditor:
    """Локальный нейросетевой аудитор объявлений на базе Ollama (Qwen 2.5 на RTX 3050 CUDA)"""

    OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
    DEFAULT_MODEL = "qwen2.5:7b"
    FAST_MODEL = "qwen2.5:1.5b"

    SYSTEM_PROMPT = """Ты — профессиональный эксперт по оценке б/у техники, электроники и комплектующих на Авито.
Твоя цель: защитить перекупа и покупателя от скама, скрытых дефектов, прогретого железа и неликвида.

Проанализируй заголовок, цену, локацию и описание лота.
Обязательно обрати внимание на следующие красные флаги (red flags):
1. Видеокарты: прогретый чип/память, артефакты, после сервиса/пайки, майнинг ферма в тяжелых условиях, не крутятся вентиляторы, цена за пустую коробку.
2. Смартфоны (iPhone/Samsung): не работает FaceID/TouchID, заменен экран на неоригинал/копию, заблокирован iCloud/MDM, восстановленный (refurbished без гарантии), трещины на матрице.
3. Продавец/Скам: подозрительно низкая цена без объяснения причин, требование предоплаты, доставка только сторонней курьерской службой.

Ответь СТРОГО в формате JSON со следующими полями:
{
  "is_scam_or_broken": boolean,
  "risk_score": integer (от 0 - абсолютно безопасно, до 100 - явный скам/брак),
  "verdict": "BUY" (выгодная безопасная сделка) | "CAUTION" (требует проверки на месте) | "SKIP" (мусор/скам/брак),
  "detected_issues": [список найденных проблем или рисков, если есть],
  "concise_summary": "краткое резюме для покупателя на 1 предложение (русский язык)"
}"""

    @classmethod
    def audit_listing(
        cls,
        title: str,
        price: float,
        description: str = "",
        seller: str = "",
        location: str = "",
        market_median: Optional[float] = None,
        use_fast_model: bool = False,
        image_paths: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Гибридный аудит карточки товара:
        1. Пробует облачный Gemini API с пулом ротации ключей (если заданы)
        2. При ошибке/отсутствии ключей — мгновенный fallback на локальный Ollama Qwen 2.5 (RTX 3050 CUDA)
        """
        import asyncio
        from rmon.core.config import settings

        user_content = f"""Объявление:
- Заголовок: {title}
- Цена: {price:,.0f} руб.
- Медианная цена рынка: {f'{market_median:,.0f} руб.' if market_median else 'Не указана'}
- Локация: {location}
- Продавец: {seller}
- Описание лота: {description or 'Описание отсутствует'}"""

        # 1. Попытка через Gemini API с пулом ключей
        if settings.GEMINI_API_KEYS:
            try:
                from rmon.core.gemini import GeminiClient
                client = GeminiClient()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                res = loop.run_until_complete(
                    client.generate_content(
                        prompt=user_content,
                        system_instruction=cls.SYSTEM_PROMPT,
                        image_paths=image_paths,
                        json_mode=True
                    )
                )
                loop.close()
                if res.get("json"):
                    logger.info(f"✓ AI Audit выполнен через Gemini [{res.get('model_used')}]")
                    return res["json"]
            except Exception as e:
                logger.debug(f"Gemini API недоступен ({e}), переключение на локальный Ollama GPU...")

        # 2. Локальный инференс через Ollama на RTX 3050 CUDA
        model = cls.FAST_MODEL if use_fast_model else cls.DEFAULT_MODEL
        payload = {
            "model": model,
            "system": cls.SYSTEM_PROMPT,
            "prompt": user_content,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_ctx": 2048
            }
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                cls.OLLAMA_URL,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                result_json = json.loads(resp_data.get("response", "{}"))
                logger.info(f"AI Audit [Ollama {model}] для '{title[:30]}': verdict={result_json.get('verdict')}, risk={result_json.get('risk_score')}")
                return result_json

        except Exception as e:
            logger.error(f"Ошибка Ollama инференса: {e}")
            return {
                "is_scam_or_broken": False,
                "risk_score": 50,
                "verdict": "CAUTION",
                "detected_issues": [f"Ошибка AI-аудитора: {e}"],
                "concise_summary": "Требуется ручная проверка лота."
            }

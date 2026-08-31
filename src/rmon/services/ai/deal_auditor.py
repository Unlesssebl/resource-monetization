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
        use_fast_model: bool = False
    ) -> Dict[str, Any]:
        """
        Синхронный / быстрый аудит карточки товара через локальную LLM.
        """
        model = cls.FAST_MODEL if use_fast_model else cls.DEFAULT_MODEL
        
        user_content = f"""Объявление:
- Заголовок: {title}
- Цена: {price:,.0f} руб.
- Медианная цена рынка: {f'{market_median:,.0f} руб.' if market_median else 'Не указана'}
- Локация: {location}
- Продавец: {seller}
- Описание лота: {description or 'Описание отсутствует'}"""

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
                resp_json = json.loads(resp.read().decode("utf-8"))
                output_text = resp_json.get("response", "{}")
                result = json.loads(output_text)
                logger.info(f"AI Audit [{model}] для '{title[:30]}': verdict={result.get('verdict')}, risk={result.get('risk_score')}")
                return result

        except Exception as e:
            logger.error(f"Ошибка вызова локальной нейросети Ollama: {e}")
            return {
                "is_scam_or_broken": False,
                "risk_score": -1,
                "verdict": "ERROR",
                "detected_issues": [f"Ошибка нейросети: {str(e)}"],
                "concise_summary": "Нейросетевой аудит не выполнен из-за технической ошибки Ollama."
            }

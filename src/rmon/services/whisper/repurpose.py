"""
Content Repurposing & Podcast AI Engine for RMon Platform.
Автоматизирует полный цикл:
1. Скачивание аудио с YouTube / Rutube / VK через yt-dlp
2. Быстрая транскрибация через Whisper GPU (DirectCompute / CUDA)
3. AI-генерация:
   - Краткого конспекта и тезисов
   - 3 готовых вирусных постов для Telegram с эмодзи и форматированием
   - YouTube-таймкодов и оглавления
   - Списка ключевых цитат
"""
import os
import re
import json
import time
import shutil
import urllib.request
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import timedelta

from rmon.core.config import settings
from rmon.core.gemini import GeminiClient
from rmon.core.hardware import HardwareArbiter
from rmon.core.logger import get_logger

logger = get_logger("ContentRepurposer")

class ContentRepurposeService:
    """Сервис автономной упаковки подкастов и видео в контент-паки"""

    FFMPEG_PATH = Path.home() / "AppData" / "Local" / "ms-playwright" / "ffmpeg-1011" / "ffmpeg-win64.exe"
    MODELS_DIR = settings.DATA_DIR / "models"
    OUTPUT_DIR = settings.DATA_DIR / "repurpose"
    WHISPER_BIN = settings.ROOT_DIR / "tools" / "whisper_gpu" / "main.exe"

    HF_MODELS = {
        "tiny": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin",
        "base": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
        "small": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin",
        "medium": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin"
    }

    @classmethod
    def ensure_model_downloaded(cls, model_size: str = "base") -> Path:
        """Проверка и авто-скачивание GGML модели с Hugging Face"""
        cls.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model_path = cls.MODELS_DIR / f"ggml-{model_size}.bin"
        if not model_path.exists() or model_path.stat().st_size < 1024 * 1024:
            url = cls.HF_MODELS.get(model_size, cls.HF_MODELS["base"])
            logger.info(f"📥 Скачивание модели Whisper ({model_size}) с HuggingFace...")
            urllib.request.urlretrieve(url, str(model_path))
            logger.info(f"✓ Модель ggml-{model_size}.bin успешно сохранена ({model_path.stat().st_size / (1024*1024):.1f} MB)")
        return model_path

    @classmethod
    def download_audio(cls, url_or_path: str, target_dir: Path) -> Dict[str, Any]:
        """Скачивание аудио с YouTube/RuTube или конвертация локального файла в WAV 16kHz"""
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Если передан локальный файл
        p = Path(url_or_path)
        if p.exists() and p.is_file():
            title = p.stem
            out_wav = target_dir / f"{title}_16k.wav"
            cls._convert_to_wav(p, out_wav)
            return {"title": title, "wav_path": out_wav, "url": str(p)}

        # Скачивание через yt-dlp
        import yt_dlp
        logger.info(f"🌐 Скачивание аудиопотока: {url_or_path}")

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(target_dir / "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True
        }
        if cls.FFMPEG_PATH.exists():
            ydl_opts["ffmpeg_location"] = str(cls.FFMPEG_PATH.parent)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url_or_path, download=True)
            title = re.sub(r'[\\/*?:"<>|]', "", info.get("title", "audio_track"))
            downloaded_file = Path(ydl.prepare_filename(info))
            duration = info.get("duration", 0)

        # Конвертация в 16kHz моно WAV для Whisper
        out_wav = target_dir / f"{title[:40]}_16k.wav"
        cls._convert_to_wav(downloaded_file, out_wav)
        
        # Очистка исходного тяжелого аудио/видео
        if downloaded_file.exists() and downloaded_file != out_wav:
            downloaded_file.unlink(missing_ok=True)

        return {
            "title": title,
            "wav_path": out_wav,
            "duration_sec": duration,
            "url": url_or_path
        }

    @classmethod
    def _convert_to_wav(cls, input_file: Path, output_wav: Path):
        """Конвертация любого аудио/видео в 16kHz 16-bit Mono PCM WAV через ffmpeg"""
        if not cls.FFMPEG_PATH.exists():
            raise FileNotFoundError(f"FFmpeg не найден по пути {cls.FFMPEG_PATH}")

        cmd = [
            str(cls.FFMPEG_PATH),
            "-y",
            "-i", str(input_file),
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            str(output_wav)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @classmethod
    async def transcribe_audio(cls, wav_path: Path, model_size: str = "base", language: str = "ru") -> Dict[str, Any]:
        """Транскрибация WAV файла через Whisper GPU DirectCompute/CUDA"""
        model_file = cls.ensure_model_downloaded(model_size)
        out_srt = wav_path.with_suffix(".srt")
        out_txt = wav_path.with_suffix(".txt")

        # Блокировка слота GPU для безопасного распределения VRAM
        await HardwareArbiter.acquire_gpu_slot("WhisperEngine", required_vram_mb=1500)
        start_t = time.time()
        try:
            cmd = [
                str(cls.WHISPER_BIN),
                "-m", str(model_file),
                "-f", str(wav_path),
                "-gpu", "1", # NVIDIA RTX 3050 (Compute GPU)
                "-osrt",
                "-otxt",
                "-l", language
            ]
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))

            txt_content = out_txt.read_text(encoding="utf-8").strip() if out_txt.exists() else ""
            srt_content = out_srt.read_text(encoding="utf-8").strip() if out_srt.exists() else ""

        finally:
            HardwareArbiter.release_gpu_slot("WhisperEngine")

        elapsed = time.time() - start_t
        logger.info(f"✓ Транскрибация завершена за {elapsed:.2f} сек ({len(txt_content)} символов)")

        return {
            "text": txt_content,
            "srt": srt_content,
            "elapsed_sec": round(elapsed, 1),
            "model": f"ggml-{model_size}"
        }

    @classmethod
    async def generate_content_pack(cls, title: str, transcript: str, duration_sec: float = 0) -> Dict[str, Any]:
        """
        AI-генерация контент-пака на базе Gemini / Qwen:
        - Executive Summary (выжимка)
        - 3 вирусных поста для Telegram
        - YouTube таймкоды
        - 3 яркие цитаты
        """
        system_instruction = """Ты — ведущий контент-стратег и редактор премиальных Telegram-каналов и подкастов.
Твоя задача: превратить сырой транскрипт аудио/видео в дорогой, увлекательный контент-пак, готовый к публикации.

Ответь СТРОГО валидным JSON со следующей структурой:
{
  "executive_summary": "Главная мысль и саммари выпуска в 2-3 абзацах",
  "key_insights": [
    "5 самых глубоких практических инсайтов с деталями"
  ],
  "telegram_posts": [
    {
      "title": "Заголовок поста с эмодзи",
      "hook": "Цепляющий первый абзац (крючок внимания)",
      "body": "Основная суть с жирным шрифтом <b></b> и буллетами",
      "cta": "Призыв к действию / вопрос для комментариев"
    }
  ],
  "youtube_timestamps": [
    "00:00 - Введение",
    "04:20 - Ключевая тема"
  ],
  "quote_cards": [
    "3 самые мощные авторские цитаты"
  ]
}"""

        prompt = f"""Название материала: {title}
Длительность: {timedelta(seconds=int(duration_sec))}

ТРАНСКРИПТ:
\"\"\"{transcript[:15000]}\"\"\"

Сгенерируй полноценный контент-пак (3 уникальных поста разного формата: провокационный, пошаговый разбор и инсайт-история)."""

        client = GeminiClient()
        logger.info("🧠 AI Генерация контент-пака через Gemini Flash...")
        res = await client.generate_content(prompt=prompt, system_instruction=system_instruction, json_mode=True)
        return res.get("json") or {}

    @classmethod
    async def process_pipeline(cls, url_or_path: str, model_size: str = "base") -> Path:
        """Полный запуск конвейера упаковки подкаста"""
        start_all = time.time()
        slug = f"repurpose_{int(time.time())}"
        work_dir = cls.OUTPUT_DIR / slug
        work_dir.mkdir(parents=True, exist_ok=True)

        print("\n" + "="*70)
        print(f"🎙️  CONTENT REPURPOSING FACTORY | URL/Path: {url_or_path[:50]}")
        print("="*70)

        # 1. Скачивание и конвертация
        print("⏳ Шаг 1/3: Скачивание и подготовка аудио (16kHz Mono)...")
        media = cls.download_audio(url_or_path, work_dir)
        title = media["title"]
        wav_path = media["wav_path"]
        duration = media.get("duration_sec", 0)
        print(f"   ✓ Аудио готово: '{title}' ({timedelta(seconds=int(duration))})")

        # 2. Транскрибация через GPU
        print("\n⚡ Шаг 2/3: Транскрибация Whisper GPU (DirectCompute / CUDA)...")
        trans = await cls.transcribe_audio(wav_path, model_size=model_size)
        txt = trans["text"]
        (work_dir / "01_transcript.txt").write_text(txt, encoding="utf-8")
        if trans["srt"]:
            (work_dir / "01_subtitles.srt").write_text(trans["srt"], encoding="utf-8")
        print(f"   ✓ Расшифровано: {len(txt)} символов за {trans['elapsed_sec']} сек")

        # 3. AI-генерация постов и конспектов
        print("\n🧠 Шаг 3/3: Генерация контент-пака и вирусных постов в Telegram...")
        pack = await cls.generate_content_pack(title, txt, duration)

        # Сохранение артефактов
        (work_dir / "05_pack.json").write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")

        # Форматирование Markdown постов
        posts_md = [f"# 📱 Готовые посты для Telegram по выпуску: {title}\n"]
        for idx, post in enumerate(pack.get("telegram_posts", []), 1):
            posts_md.append(f"## 📝 Пост #{idx}: {post.get('title')}\n")
            posts_md.append(f"{post.get('hook')}\n\n{post.get('body')}\n\n💡 {post.get('cta')}\n")
            posts_md.append("---\n")
        (work_dir / "03_telegram_posts.md").write_text("\n".join(posts_md), encoding="utf-8")

        # Форматирование саммари и таймкодов
        summary_md = [
            f"# 📋 Конспект и таймкоды: {title}\n",
            f"### 💡 Саммари:\n{pack.get('executive_summary', '')}\n",
            "### 🎯 Ключевые инсайты:\n" + "\n".join([f"- {i}" for i in pack.get("key_insights", [])]) + "\n",
            "### ⏱️ Таймкоды YouTube:\n" + "\n".join([f"`{t}`" for t in pack.get("youtube_timestamps", [])]) + "\n",
            "### 💬 Топ цитаты:\n" + "\n".join([f"> «{q}»" for q in pack.get("quote_cards", [])])
        ]
        (work_dir / "02_summary.md").write_text("\n".join(summary_md), encoding="utf-8")

        # Удаление временного WAV файла
        if wav_path.exists():
            wav_path.unlink(missing_ok=True)

        total_time = time.time() - start_all
        print("\n" + "="*70)
        print(f"🎉 КОНТЕНТ-ПАК УСПЕШНО СОЗДАН ЗА {total_time:.1f} СЕК!")
        print(f"📁 Папка с готовыми файлами: {work_dir}")
        print(f"   • 01_transcript.txt    (Сырой текст расшифровки)")
        print(f"   • 02_summary.md       (Конспект, инсайты и таймкоды)")
        print(f"   • 03_telegram_posts.md (3 готовых поста для публикации)")
        print("="*70 + "\n")

        return work_dir

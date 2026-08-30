import os
import time
from pathlib import Path
from datetime import timedelta
from faster_whisper import WhisperModel
from rmon.core.config import settings
from rmon.core.logger import get_logger

logger = get_logger("WhisperEngine")

def format_timestamp(seconds: float) -> str:
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

class WhisperEngine:
    _model = None
    _current_model_size = None

    @classmethod
    def get_model(cls, model_size: str = None):
        model_size = model_size or settings.WHISPER_MODEL
        device = settings.WHISPER_DEVICE
        compute_type = settings.WHISPER_COMPUTE

        if cls._model is None or cls._current_model_size != model_size:
            cpu_threads = min(os.cpu_count() or 4, 16)
            logger.info(f"Инициализация faster-whisper ({model_size}) на {device.upper()} ({compute_type})...")
            cls._model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                cpu_threads=cpu_threads
            )
            cls._current_model_size = model_size
        return cls._model

    @classmethod
    def transcribe(
        cls,
        file_path: str,
        output_dir: str = None,
        model_size: str = None,
        language: str = None
    ) -> dict:
        start_time = time.time()
        file_path = Path(file_path).resolve()
        out_dir = Path(output_dir or (settings.DATA_DIR / "output_transcripts")).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        if not file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        model = cls.get_model(model_size)
        logger.info(f"Старт транскрибации: {file_path.name}")

        segments, info = model.transcribe(
            str(file_path),
            beam_size=5,
            language=language,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        detected_lang = info.language
        lang_prob = info.language_probability
        duration = info.duration

        base_name = file_path.stem
        srt_path = out_dir / f"{base_name}.srt"
        txt_path = out_dir / f"{base_name}.txt"
        md_path = out_dir / f"{base_name}.md"

        srt_lines = []
        text_segments = []

        for idx, seg in enumerate(segments, start=1):
            start_ts = format_timestamp(seg.start)
            end_ts = format_timestamp(seg.end)
            text = seg.text.strip()

            srt_lines.append(f"{idx}\n{start_ts} --> {end_ts}\n{text}\n")
            text_segments.append(f"[{format_timestamp(seg.start)[:8]}] {text}")

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_lines))

        full_text = " ".join([seg.split("] ", 1)[-1] for seg in text_segments])
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)

        elapsed = time.time() - start_time
        speed_factor = duration / elapsed if elapsed > 0 else 0

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# 📝 Транскрипт: {file_path.name}\n\n")
            f.write(f"- **Длительность:** {timedelta(seconds=int(duration))}\n")
            f.write(f"- **Время обработки:** {elapsed:.2f} сек ({speed_factor:.1f}x)\n")
            f.write(f"- **Язык:** {detected_lang.upper()} ({lang_prob:.1%})\n\n")
            f.write("---\n\n## ⏱️ Таймкоды и текст\n\n")
            for line in text_segments:
                f.write(f"{line}\n\n")

        logger.info(f"Успешно обработано за {elapsed:.2f} сек ({speed_factor:.1f}x speed)")

        return {
            "duration": duration,
            "elapsed": elapsed,
            "speed_factor": speed_factor,
            "language": detected_lang,
            "srt_path": str(srt_path),
            "txt_path": str(txt_path),
            "md_path": str(md_path),
            "full_text": full_text
        }
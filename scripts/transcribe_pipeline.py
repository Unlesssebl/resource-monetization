#!/usr/bin/env python3
"""
High-Performance Audio/Video AI Transcription Pipeline
Powered by faster-whisper (CTranslate2) & Open Source First.
Zero-cost inference on local hardware with subtitle (.srt) & text (.md/.txt) export.
"""

import os
import sys
import time
import argparse
from pathlib import Path
from datetime import timedelta
from faster_whisper import WhisperModel

def format_timestamp(seconds: float) -> str:
    """Format seconds into SRT timestamp (HH:MM:SS,mmm)"""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def transcribe_file(
    file_path: str,
    output_dir: str = "data/output_transcripts",
    model_size: str = "medium",
    device: str = "cpu",
    compute_type: str = "int8",
    language: str = None
) -> dict:
    start_time = time.time()
    file_path = Path(file_path).resolve()
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    print(f"🎙️ Загрузка модели faster-whisper ({model_size}) на {device.upper()} ({compute_type})...")
    # i5-12600KF has 16 threads
    cpu_threads = min(os.cpu_count() or 4, 16)
    model = WhisperModel(model_size, device=device, compute_type=compute_type, cpu_threads=cpu_threads)

    print(f"⚡ Начало транскрибации: {file_path.name}")
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
    print(f"🌍 Обнаружен язык: {detected_lang.upper()} (уверенность: {lang_prob:.1%}), Длительность: {duration:.1f} сек ({timedelta(seconds=int(duration))})")

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

        # SRT format
        srt_lines.append(f"{idx}\n{start_ts} --> {end_ts}\n{text}\n")
        
        # Readable Markdown / Text format
        text_segments.append(f"[{format_timestamp(seg.start)[:8]}] {text}")

    # Write SRT
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    # Write TXT
    full_text = " ".join([seg.split("] ", 1)[-1] for seg in text_segments])
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    # Write Markdown
    elapsed = time.time() - start_time
    speed_factor = duration / elapsed if elapsed > 0 else 0

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 📝 Транскрипт: {file_path.name}\n\n")
        f.write(f"- **Длительность аудио:** {timedelta(seconds=int(duration))}\n")
        f.write(f"- **Время обработки:** {elapsed:.2f} сек ({speed_factor:.1f}x быстрее реального времени)\n")
        f.write(f"- **Язык:** {detected_lang.upper()} ({lang_prob:.1%})\n")
        f.write(f"- **Модель:** aster-whisper/{model_size}\n\n")
        f.write("---\n\n## ⏱️ Таймкоды и текст\n\n")
        for line in text_segments:
            f.write(f"{line}\n\n")

    print(f"\n✅ Успешно завершено за {elapsed:.2f} сек!")
    print(f"🚀 Скорость: {speed_factor:.1f}x в реальном времени (1 час аудио обрабатывается за {3600 / speed_factor / 60:.1f} мин)")
    print(f"📁 Файлы сохранены:")
    print(f"   • Субтитры: {srt_path}")
    print(f"   • Текст:    {txt_path}")
    print(f"   • Markdown: {md_path}")

    return {
        "duration": duration,
        "elapsed": elapsed,
        "speed_factor": speed_factor,
        "language": detected_lang,
        "srt_path": str(srt_path),
        "txt_path": str(txt_path),
        "md_path": str(md_path)
    }

def main():
    parser = argparse.ArgumentParser(description="AI Audio/Video Transcription Pipeline")
    parser.add_argument("file", help="Путь к аудио или видео файлу")
    parser.add_argument("--model", default="medium", choices=["tiny", "base", "small", "medium", "large-v3"], help="Размер модели Whisper")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda", "auto"], help="Устройство инференса")
    parser.add_argument("--compute", default="int8", choices=["int8", "float16", "float32"], help="Тип квантования")
    parser.add_argument("--lang", default=None, help="Принудительный язык (ru, en, etc.)")
    parser.add_argument("--out", default="data/output_transcripts", help="Папка для результатов")

    args = parser.parse_args()
    transcribe_file(args.file, args.out, args.model, args.device, args.compute, args.lang)

if __name__ == "__main__":
    main()
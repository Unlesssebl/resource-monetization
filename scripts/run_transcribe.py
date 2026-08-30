#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from rmon.services.whisper.engine import WhisperEngine

def main():
    parser = argparse.ArgumentParser(description="Whisper AI Transcription Runner")
    parser.add_argument("file", help="Путь к аудио/видео файлу")
    parser.add_argument("--model", default=None, help="Модель Whisper (tiny, base, small, medium, large-v3)")
    parser.add_argument("--lang", default=None, help="Принудительный язык (ru, en)")
    parser.add_argument("--out", default=None, help="Папка сохранения")

    args = parser.parse_args()
    res = WhisperEngine.transcribe(args.file, output_dir=args.out, model_size=args.model, language=args.lang)
    print(f"\n✅ Транскрибация завершена!")
    print(f"📄 Текст:    {res['txt_path']}")
    print(f"🎬 Субтитры: {res['srt_path']}")
    print(f"📝 Отчет:    {res['md_path']}")

if __name__ == "__main__":
    main()
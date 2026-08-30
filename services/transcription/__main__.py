import sys
import argparse
from pathlib import Path
from services.transcription.engine import WhisperEngine

def main():
    parser = argparse.ArgumentParser(description="Whisper Transcription Microservice CLI")
    parser.add_argument("file", help="Путь к аудио или видео файлу")
    parser.add_argument("--model", default=None, help="Модель (tiny, base, small, medium, large-v3)")
    parser.add_argument("--lang", default=None, help="Принудительный язык (ru, en)")
    parser.add_argument("--out", default=None, help="Директория сохранения")

    args = parser.parse_args()
    res = WhisperEngine.transcribe(args.file, output_dir=args.out, model_size=args.model, language=args.lang)
    print(f"\n✅ Готово! Текст: {res['txt_path']}, Субтитры: {res['srt_path']}")

if __name__ == "__main__":
    main()
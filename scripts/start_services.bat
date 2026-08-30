@echo off
chcp 65001 >nul
title Resource Monetization Hub - 24/7 Automation

echo ========================================================
echo   🚀 RESOURCE MONETIZATION HUB (LEAN & OPEN SOURCE)
echo   Hardware: Intel i5-12600KF ^| 48GB RAM ^| RX 6800 XT 16GB
echo ========================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [!] Виртуальное окружение не найдено. Создание через uv...
    uv venv .venv --python 3.12
    uv pip install faster-whisper playwright duckdb aiogram python-dotenv tqdm
)

if not exist "configs\.env" (
    if exist "configs\.env.example" (
        copy "configs\.env.example" "configs\.env" >nul
        echo [*] Создан файл конфигурации configs\.env. Пожалуйста, укажите BOT_TOKEN.
    )
)

echo [1] Запустить Telegram AI-транскрибатор (24/7)
echo [2] Запустить транскрибацию тестового аудио
echo [3] Запустить мониторинг цен маркетплейсов и выгрузить отчет
echo [4] Пересобрать интерактивный HTML-дашборд
echo [5] Выход
echo.

set /p choice="Выберите действие (1-5): "

if "%choice%"=="1" (
    echo [*] Запуск Telegram AI-бота...
    .venv\Scripts\python.exe scripts\transcribe_bot.py
)
if "%choice%"=="2" (
    echo [*] Транскрибация тестового файла...
    .venv\Scripts\python.exe scripts\transcribe_pipeline.py data\test_sample.wav --model medium
    pause
)
if "%choice%"=="3" (
    echo [*] Сбор цен и генерация отчетов...
    .venv\Scripts\python.exe scripts\market_monitor.py --query "авточехлы" --limit 15
    pause
)
if "%choice%"=="4" (
    echo [*] Пересборка дашборда...
    .venv\Scripts\python.exe scripts\meta\build_dashboard.py
    pause
)

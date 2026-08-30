#!/usr/bin/env python3
"""
Evidence & Hypothesis Validator Orchestrator (Lean & Zero-Auth)
Единый комбайн для мгновенного сбора и оформления доказательной базы:
1. Опрос поисковых подсказок (Google/Яндекс).
2. Аналитика GitHub репозитория (звезды, форки, релизы).
3. Проверка краудфандинга (Graphtreon).
4. Автоматическое форматирование Триплета Доказательств с текущей датой.
"""

import sys
import os
import argparse
from datetime import datetime, timezone

# Гарантируем корректный импорт модулей из scripts/meta/ независимо от рабочей директории
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from search_trends import analyze_search_demand
from github_stats import fetch_github_stats
from graphtreon_metrics import fetch_creator_metrics
from evidence_formatter import format_evidence_block

def validate_hypothesis(title: str, query: str = None, repo: str = None, creator: str = None, extra_metrics: list = None, extra_sources: list = None) -> str:
    metrics = []
    sources = []
    
    # 1. Поисковый спрос
    if query:
        search_res = analyze_search_demand(query)
        suggs = search_res.get("google_suggestions", []) + search_res.get("yandex_suggestions", [])
        top_suggs = list(dict.fromkeys(suggs))[:4] # убираем дубли
        if top_suggs:
            suggs_str = ", ".join([f'"{s}"' for s in top_suggs])
            metrics.append(f"Поисковый спрос по запросу '{query}': горячие ассоциации — {suggs_str}")
        sources.append(f"Поисковые тренды (Google/Яндекс Suggest по запросу '{query}')")
        
    # 2. GitHub статистика
    if repo:
        gh_res = fetch_github_stats(repo)
        if gh_res.get("status") == "success":
            stars = gh_res.get("stars", 0)
            forks = gh_res.get("forks", 0)
            rel = gh_res.get("latest_release")
            rel_info = f", последний релиз {rel['tag']} ({rel['published_at'][:10]})" if rel else ""
            metrics.append(f"GitHub `{gh_res['repo']}`: **{stars:,} ⭐**, {forks:,} форков{rel_info}")
            sources.append(f"[{gh_res['repo']} на GitHub]({gh_res['url']})")
            
    # 3. Graphtreon / Creator статистика
    if creator:
        cr_res = fetch_creator_metrics(creator)
        if cr_res.get("status") == "success":
            rank_str = f", глобальный ранг #{cr_res['rank']}" if cr_res.get("rank") else ""
            metrics.append(f"Краудфандинг автора `{creator}`: активный профиль{rank_str}")
            sources.append(f"[Graphtreon: {creator}]({cr_res['graphtreon_url']})")
            
    # Дополнительные метрики и источники
    if extra_metrics:
        metrics.extend(extra_metrics)
    if extra_sources:
        sources.extend(extra_sources)
        
    return format_evidence_block(title=title, metrics=metrics, sources=sources)

def main():
    parser = argparse.ArgumentParser(description="Валидация гипотез и сбор доказательной базы.")
    parser.add_argument("--title", required=True, help="Название гипотезы / кейса")
    parser.add_argument("--query", help="Поисковый запрос для проверки спроса")
    parser.add_argument("--repo", help="Репозиторий GitHub (owner/repo или URL)")
    parser.add_argument("--creator", help="Имя автора для проверки Graphtreon")
    parser.add_argument("--metric", action="append", help="Дополнительная числовая метрика")
    parser.add_argument("--source", action="append", help="Дополнительная ссылка / источник")
    
    args = parser.parse_args()
    
    result = validate_hypothesis(
        title=args.title,
        query=args.query,
        repo=args.repo,
        creator=args.creator,
        extra_metrics=args.metric,
        extra_sources=args.source
    )
    print(result)

if __name__ == "__main__":
    main()

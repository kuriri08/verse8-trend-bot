#!/usr/bin/env python3
"""
VERSE8 데이터 수집 전용 — 하루 4회 실행 (09:00, 15:00, 21:00, 03:00)
수집만 하고 Slack 발송은 안 함. 스냅샷에 누적 저장.
"""

import sys
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / '.env', override=True)

from collectors import naver_news

HISTORY_DIR = PROJECT_ROOT / 'data' / 'history'


def collect_and_save():
    """네이버 뉴스 수집 후 오늘 스냅샷에 누적"""
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M')

    print(f"📥 Collecting naver_news at {time_str}...")
    try:
        naver_data = naver_news.collect()
        articles = naver_data.get('articles', [])
        print(f"  ✅ {len(articles)} articles collected")
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return

    # 오늘 스냅샷 로드 (있으면)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    filepath = HISTORY_DIR / f'{date_str}.json'

    snapshot = {}
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            snapshot = json.load(f)

    # 기존 네이버 기사와 합치기 (중복 제거)
    existing = snapshot.get('naver_articles', [])
    existing_titles = {a['title'] for a in existing}

    new_count = 0
    for article in articles:
        if article['title'] not in existing_titles:
            article['collected_at'] = time_str
            existing.append(article)
            existing_titles.add(article['title'])
            new_count += 1

    snapshot['naver_articles'] = existing
    snapshot['naver_last_collected'] = time_str

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    print(f"  💾 {new_count} new articles added (total: {len(existing)})")
    print(f"  📁 Saved: {filepath}")


if __name__ == '__main__':
    print("=" * 50)
    print("📥 VERSE8 Data Collection")
    print("=" * 50)
    collect_and_save()
    print("\n✅ Done!")

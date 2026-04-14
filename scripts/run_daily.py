#!/usr/bin/env python3
"""
VERSE8 Daily Trend Bot — 메인 파이프라인
매일 오전 10시 실행: 전날 데이터 수집 → 분석 → Slack 발송
"""

import sys
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / '.env', override=True)

from collectors import google_trends, hackernews, rss_feeds, steam, google_play, reddit, naver_news
from collectors.weekly_diff import save_snapshot, compute_diff, get_yesterday_naver
from analyzer.trend_analyzer import analyze
from analyzer.weekly_game_analyzer import analyze_weekly_games
from reporter.slack_reporter import send_dm


def _insert_weekly_games(daily_briefing: str, weekly_games: str) -> str:
    """데일리 브리핑의 Game Trends Mobile 뒤, Dev Community 앞에 주간 게임 분석 삽입"""
    lines = daily_briefing.split('\n')
    result = []
    inserted = False

    for line in lines:
        # Dev Community 카테고리 시작 전에 삽입
        if '👥' in line and not inserted:
            result.append("")
            result.append("*📈 이번 주 게임 트렌드 종합 (주간 분석)*")
            result.append(weekly_games.strip())
            result.append("")
            inserted = True
        result.append(line)

    # 삽입 못 했으면 끝에 추가
    if not inserted:
        result.append("")
        result.append("*📈 이번 주 게임 트렌드 종합 (주간 분석)*")
        result.append(weekly_games.strip())

    return '\n'.join(result)


def get_date_label():
    """2026.04.07 TUE 형태의 오늘 날짜 라벨 생성"""
    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst)
    day_names = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
    day_name = day_names[today.weekday()]
    return f"{today.strftime('%Y.%m.%d')} {day_name}"


def collect_all():
    """모든 수집기 실행 (실패 시 스킵)"""
    collected = {}

    collectors = {
        'google_trends': google_trends.collect,
        'hackernews': hackernews.collect,
        'rss_feeds': rss_feeds.collect,
        'reddit': reddit.collect,
        'naver_news': naver_news.collect,
        'steam': steam.collect,
        'google_play': google_play.collect,
    }

    for name, collector_fn in collectors.items():
        try:
            print(f"📥 Collecting {name}...")
            data = collector_fn()
            collected[name] = data
            print(f"  ✅ {name} done")
        except Exception as e:
            print(f"  ⚠️ {name} failed: {e}")
            collected[name] = {'error': str(e)}

    return collected


def save_raw_data(collected, date_label):
    """수집 데이터 아카이브 저장"""
    kst = timezone(timedelta(hours=9))
    date_str = datetime.now(kst).strftime('%Y-%m-%d')
    raw_dir = PROJECT_ROOT / 'data' / 'raw' / date_str
    raw_dir.mkdir(parents=True, exist_ok=True)

    filepath = raw_dir / 'collected.json'
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(collected, f, ensure_ascii=False, indent=2)

    print(f"💾 Raw data saved: {filepath}")


def main():
    print("=" * 50)
    print("🚀 VERSE8 Daily Trend Bot")
    print("=" * 50)

    # 1) 날짜 라벨
    date_label = get_date_label()
    print(f"📅 {date_label}\n")

    # 2) 데이터 수집
    collected = collect_all()
    save_raw_data(collected, date_label)

    # 수집 성공 여부 확인
    has_data = any(
        not v.get('error') for v in collected.values()
        if isinstance(v, dict)
    )
    if not has_data:
        print("❌ 모든 수집기 실패. 중단.")
        sys.exit(1)

    # 3) 네이버 뉴스를 어제 저장분으로 교체 (오늘 수집분은 내일용으로 저장만)
    yesterday_naver = get_yesterday_naver()
    if yesterday_naver:
        collected['naver_news'] = {'articles': yesterday_naver, 'source': 'naver_news (어제 인기 기사)'}
        print(f"📰 네이버 뉴스: 어제 저장분 {len(yesterday_naver)}건 사용")
    else:
        print("📰 네이버 뉴스: 어제 데이터 없음, 오늘 수집분 사용")

    # 4) 전일 대비 변동 비교
    print("\n📊 Computing daily diff...")
    diff = compute_diff(collected)
    if diff.get('has_diff'):
        collected['daily_diff'] = diff
        print("  ✅ Diff computed (previous data found)")
    else:
        print(f"  ℹ️ {diff.get('note', 'No previous data')}")

    # 4) 히스토리 저장 (내일 비교용)
    snapshot_path = save_snapshot(collected)
    print(f"  💾 Snapshot saved: {snapshot_path}")

    # 5) 월요일이면 주간 게임 트렌드 분석 추가
    kst = timezone(timedelta(hours=9))
    is_monday = datetime.now(kst).weekday() == 0
    weekly_game_briefing = None
    if is_monday:
        print("\n🎮 Monday — analyzing weekly game trends...")
        result = analyze_weekly_games()
        if result:
            weekly_game_briefing, _ = result
            print("  ✅ Weekly game analysis done")
        else:
            print("  ℹ️ Not enough data for weekly comparison")

    # 6) Gemini API로 트렌드 분석
    print("\n🤖 Analyzing trends with Gemini...")
    try:
        briefing = analyze(collected, date_label)
        # 월요일이면 Game Trends Mobile과 Dev Community 사이에 주간 분석 삽입
        if weekly_game_briefing:
            briefing = _insert_weekly_games(briefing, weekly_game_briefing)
        full_message = briefing
        print("  ✅ Analysis done")
    except Exception as e:
        print(f"  ❌ Analysis failed: {e}")
        sys.exit(1)

    # 6) Slack 발송 (여러 채널 지원)
    print("\n📨 Sending to Slack...")
    from reporter.slack_reporter import send_to_channel
    channel_ids = os.environ.get('SLACK_CHANNEL_IDS', os.environ.get('SLACK_CHANNEL_ID', ''))
    channels = [c.strip() for c in channel_ids.split(',') if c.strip()]

    if channels:
        for ch in channels:
            result = send_to_channel(full_message, ch, week_label=date_label)
            if result.get('ok'):
                print(f"  ✅ {ch} sent!")
            else:
                print(f"  ❌ {ch} error: {result.get('error', 'unknown')}")
    else:
        result = send_dm(full_message, week_label=date_label)
        if result.get('ok'):
            print("  ✅ DM sent!")
        sys.exit(1)

    print("\n✅ Done!")


if __name__ == '__main__':
    main()

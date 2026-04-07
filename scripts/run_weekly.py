#!/usr/bin/env python3
"""
VERSE8 Weekly Trend Bot — 메인 파이프라인
수집 → 분석 → Slack 발송
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

from collectors import google_trends, hackernews, rss_feeds, steam, google_play
from collectors.weekly_diff import save_snapshot, compute_diff
from analyzer.trend_analyzer import analyze
from reporter.slack_reporter import send_dm


def get_week_label():
    """W14 (2026.03.31 ~ 04.06) 형태의 지난 7일 라벨 생성"""
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    # 오늘 기준 지난 7일
    end_date = now - timedelta(days=1)  # 어제까지
    start_date = end_date - timedelta(days=6)  # 7일 전부터
    week_num = start_date.isocalendar()[1]
    return f"W{week_num} ({start_date.strftime('%Y.%m.%d')} ~ {end_date.strftime('%m.%d')})"


def collect_all():
    """모든 수집기 실행 (실패 시 스킵)"""
    collected = {}

    collectors = {
        'google_trends': google_trends.collect,
        'hackernews': hackernews.collect,
        'rss_feeds': rss_feeds.collect,
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


def save_raw_data(collected, week_label):
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
    print("🚀 VERSE8 Weekly Trend Bot")
    print("=" * 50)

    # 1) 주차 라벨
    week_label = get_week_label()
    print(f"📅 {week_label}\n")

    # 2) 데이터 수집
    collected = collect_all()
    save_raw_data(collected, week_label)

    # 수집 성공 여부 확인
    has_data = any(
        not v.get('error') for v in collected.values()
        if isinstance(v, dict)
    )
    if not has_data:
        print("❌ 모든 수집기 실패. 중단.")
        sys.exit(1)

    # 3) 주간 변동 비교
    print("\n📊 Computing weekly diff...")
    diff = compute_diff(collected)
    if diff.get('has_diff'):
        collected['weekly_diff'] = diff
        print("  ✅ Diff computed (previous data found)")
    else:
        print(f"  ℹ️ {diff.get('note', 'No previous data')}")

    # 4) 히스토리 저장 (다음 주 비교용)
    snapshot_path = save_snapshot(collected)
    print(f"  💾 Snapshot saved: {snapshot_path}")

    # 5) Claude API로 트렌드 분석
    print("\n🤖 Analyzing trends with Claude...")
    try:
        briefing = analyze(collected, week_label)
        full_message = briefing
        print("  ✅ Analysis done")
    except Exception as e:
        print(f"  ❌ Analysis failed: {e}")
        sys.exit(1)

    # 4) Slack 발송
    print("\n📨 Sending to Slack...")
    result = send_dm(full_message, week_label=week_label)
    if result.get('ok'):
        print("  ✅ Slack DM sent!")
    else:
        print(f"  ❌ Slack error: {result.get('error', 'unknown')}")
        # Slack 실패해도 브리핑은 출력
        print("\n--- Briefing (fallback) ---")
        print(full_message)
        sys.exit(1)

    print("\n✅ Done!")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
VERSE8 주간 게임 트렌드 분석 — 매주 월요일 실행
7일치 스냅샷을 비교하여 게임 트렌드 분석 리포트 발송
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / '.env', override=True)

from analyzer.weekly_game_analyzer import analyze_weekly_games
from reporter.slack_reporter import send_dm


def main():
    print("=" * 50)
    print("🎮 VERSE8 주간 게임 트렌드 분석")
    print("=" * 50)

    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst)
    week_start = today - timedelta(days=6)
    week_label = f"{week_start.strftime('%Y.%m.%d')} ~ {today.strftime('%m.%d')}"
    print(f"📅 {week_label}\n")

    # 1) 주간 분석
    print("🤖 Analyzing weekly game trends...")
    result = analyze_weekly_games()

    if not result:
        print("❌ 비교할 데이터 부족 (최소 2일치 필요). 내일 다시 시도.")
        sys.exit(0)

    briefing, label = result
    print("  ✅ Analysis done")

    # 2) Slack 발송
    print("\n📨 Sending to Slack...")
    send_result = send_dm(briefing, week_label=f"주간 게임 트렌드 {label}")
    if send_result.get('ok'):
        print("  ✅ Slack DM sent!")
    else:
        print(f"  ❌ Slack error: {send_result.get('error', 'unknown')}")
        print("\n--- Briefing (fallback) ---")
        print(briefing)
        sys.exit(1)

    print("\n✅ Done!")


if __name__ == '__main__':
    main()

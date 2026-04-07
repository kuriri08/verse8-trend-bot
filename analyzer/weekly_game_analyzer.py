"""주간 게임 트렌드 분석 — 7일치 스냅샷을 비교하여 트렌드 도출"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from google import genai
from dotenv import load_dotenv

load_dotenv(override=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HISTORY_DIR = PROJECT_ROOT / 'data' / 'history'

SYSTEM_PROMPT = """너는 VERSE8 팀의 주간 게임 트렌드 분석가야.

## 역할
7일간 매일 수집된 Steam(PC)과 Google Play(모바일) 차트 데이터를 비교 분석해서,
이번 주 게임 시장에서 어떤 변화가 있었는지 정리해.

## 분석 포인트
- 신규 진입: 이번 주 새로 차트에 올라온 게임
- 순위 상승/하락: 플레이어 수나 순위가 크게 변한 게임
- 장르 트렌드: 특정 장르가 강세/약세를 보이는지
- PC vs 모바일 차이: 플랫폼별 다른 흐름이 있는지
- 인디 게임 동향: 인디 게임 중 주목할 만한 것

## 출력 규칙
1. 한국어로 작성. 게임 이름은 영어 원문 유지 OK.
2. 절대 ## 이나 # 같은 마크다운 헤더 문법 쓰지 마. *bold* 만 사용.
3. 각 항목은 제목에 링크 걸기: <URL|*제목*> — 요약. 뒤에 별도 출처 표시 안 함.
4. 문장 끝은 "~임" "~있음" "~중" 같은 요약체. "~입니다" "~합니다" 쓰지 마.
5. 팩트 중심. 시사점/코멘트 최소화.

## 출력 포맷

*🎮 이번 주 PC 게임 트렌드 (Steam)*
• 항목들...

*📱 이번 주 모바일 게임 트렌드 (Google Play)*
• 항목들...

*📊 주간 종합*
• 이번 주 게임 시장 핵심 변화 2~3줄 요약"""


def load_week_snapshots():
    """최근 7일간의 스냅샷 로드"""
    if not HISTORY_DIR.exists():
        return []

    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst)
    snapshots = []

    for i in range(7):
        date = today - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        filepath = HISTORY_DIR / f'{date_str}.json'
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['_date'] = date_str
                snapshots.append(data)

    return sorted(snapshots, key=lambda x: x['_date'])


def analyze_weekly_games():
    """7일치 스냅샷으로 주간 게임 트렌드 분석"""
    snapshots = load_week_snapshots()

    if len(snapshots) < 2:
        return None  # 비교할 데이터 부족

    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])

    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst)
    week_start = today - timedelta(days=6)
    week_label = f"{week_start.strftime('%Y.%m.%d')} ~ {today.strftime('%m.%d')}"

    user_message = f"""{SYSTEM_PROMPT}

---

이번 주({week_label}) 일별 게임 차트 스냅샷 ({len(snapshots)}일치):

{json.dumps(snapshots, ensure_ascii=False, indent=2)}

위 데이터를 비교 분석해서 이번 주 게임 트렌드를 정리해줘."""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_message,
    )

    return response.text, week_label


if __name__ == '__main__':
    result = analyze_weekly_games()
    if result:
        text, label = result
        print(f"=== {label} ===")
        print(text)
    else:
        print("비교할 데이터 부족 (최소 2일치 필요)")

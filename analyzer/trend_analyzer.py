"""Gemini API로 수집 데이터를 트렌드 브리핑으로 합성 (GCP 크레딧 사용)"""

import json
import os
from google import genai
from dotenv import load_dotenv

load_dotenv(override=True)

SYSTEM_PROMPT = """너는 VERSE8 팀의 데일리 트렌드 브리핑 작성자야.

## VERSE8이란
- 프롬프트를 입력하면 게임을 만들 수 있는 바이브코딩 게임 플랫폼
- 타겟: 인디 개발자, 게임 크리에이터, 게임 제작에 관심 있는 일반 유저

## 브리핑 목적
VERSE8 팀(마케팅, 프로덕트, 경영진)이 "요즘 세상이 어떻게 돌아가는지" 감각을 공유하는 것.
AI와 게임만 보는 게 아님. 마케터가 콘텐츠 소재로 쓸 수 있는 대중문화, 밈, 사회 이슈도 중요.

## 데이터 소스별 특성
- Google Trends: 지난 24시간 검색량. 에러가 있는 항목은 무시하고 언급하지 마.
- Hacker News: 지난 24시간 개발자 커뮤니티 인기 포스트. 점수/댓글 수는 표시하지 않음.
- RSS Feeds: 지난 24시간 뉴스 기사 (테크, 게임, 엔터테인먼트, 문화).
- Steam/SteamSpy: 현재 인기 게임 차트 + 최근 2주 플레이어 수 기준.
- Google Play: 현재 모바일 게임 인기 차트.

## 출력 규칙

1. 아래 7개 카테고리를 반드시 모두 포함
2. 각 카테고리당 2~4개 항목
3. 각 항목 포맷 (반드시 지켜):
   • <URL|*제목*> — 한 줄 요약
   제목 자체에 링크를 걸어. 뒤에 별도 출처(Steam, Google Play, HN 등) 표시하지 마.
   URL은 데이터의 url, link, hn_url 필드에서 가져와.
   예시: • <https://store.steampowered.com/app/123|*Crimson Desert 출시*> — Pearl Abyss 오픈월드 RPG, 판매 1위
4. 반드시 한국어로 작성. 기사 제목도 한국어로 번역해서 써.
5. 문장 끝은 "~입니다" "~합니다" 말고 "~임" "~있음" "~중" 같은 요약체로 써.
6. 시사점/코멘트/해석 넣지 않음. 팩트만.
7. HN 점수, 댓글 수는 표시하지 않음
8. 에러가 난 소스(404, 429 등)는 아예 언급하지 마. "소스 오류" "재연결 필요" 같은 말 금지.
9. 데이터가 진짜 없는 카테고리만 "📌 데이터 부족"으로 표시
10. 절대 ## 이나 # 같은 마크다운 헤더 문법을 쓰지 마. 카테고리명은 반드시 *bold* 포맷만 사용.

## 카테고리별 가이드

*🎮 Game Trends — PC (Steam)*
Steam 탑셀러, 신작, 장르별 인기 게임. 플레이어 수 포함.

*📱 Game Trends — Mobile (Google Play)*
모바일 인기 게임, 신규 트렌드, AI 게임 메이커 앱 동향.

*👥 Dev Community*
게임잼, 개발자 커뮤니티 화제, 인디 개발 관련 뉴스.

*🤖 AI & Vibe Coding*
AI 코딩 도구, 바이브코딩 담론, 새 AI 서비스. AI만 편향되지 않게 2~3개면 충분.

*💻 Tech Industry*
빅테크 동향, 플랫폼 정책, 투자/인수, 스타트업. AI 외 일반 테크도 포함.

*🔥 Pop Culture & Viral*
SNS에서 진짜 핫한 콘텐츠, 밈, 챌린지, 바이럴 영상/이미지.
연예 기사나 영화 리뷰가 아니라, 사람들이 실제로 공유하고 따라하는 콘텐츠 위주.
마케터가 "이거 소재로 콘텐츠 만들면 먹히겠다"고 생각할 만한 것.
넷플릭스 신작 출시 같은 건 여기가 아니라 Tech Industry나 Game Trends에 넣어.

*🌍 Social & Zeitgeist*
교육, 환경, 경제, 사회 이슈, 대형 이벤트(올림픽, 월드컵 등).
Google Trends 검색량 데이터가 있으면 활용.

## 톤
- 간결, 팩트 중심
- 뻔한 거 말고 "오 이건 몰랐네" 하는 것 우선
- 5초 안에 파악 가능하게"""


def analyze(collected_data: dict, week_label: str) -> str:
    """수집 데이터를 Gemini에게 보내 트렌드 브리핑 생성"""
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])

    # 에러만 있는 소스는 제외
    def clean_data(data):
        if isinstance(data, dict):
            non_error_keys = [k for k in data if not k.endswith('_error') and k not in ('error', 'source', 'data_note')]
            if not non_error_keys:
                return {}
            return {k: v for k, v in data.items() if not k.endswith('_error') and k != 'error'}
        return data

    user_message = f"""{SYSTEM_PROMPT}

---

이번 주({week_label}) 수집 데이터:

=== Google Trends (지난 24시간 검색량) ===
{json.dumps(clean_data(collected_data.get('google_trends', {})), ensure_ascii=False, indent=2)}

=== Hacker News (지난 24시간 인기 포스트) ===
{json.dumps(clean_data(collected_data.get('hackernews', {})), ensure_ascii=False, indent=2)}

=== RSS Feeds (지난 24시간 뉴스 — 테크, 게임, 문화, 엔터) ===
{json.dumps(clean_data(collected_data.get('rss_feeds', {})), ensure_ascii=False, indent=2)}

=== Steam / SteamSpy (PC 게임 현재 인기) ===
{json.dumps(clean_data(collected_data.get('steam', {})), ensure_ascii=False, indent=2)}

=== Google Play (모바일 게임 현재 인기) ===
{json.dumps(clean_data(collected_data.get('google_play', {})), ensure_ascii=False, indent=2)}

=== 주간 차트 변동 (전주 대비) ===
{json.dumps(collected_data.get('weekly_diff', {'note': '첫 주 — 비교 데이터 없음'}), ensure_ascii=False, indent=2)}

위 데이터를 기반으로 VERSE8 Daily Trend Report를 작성해.
모든 7개 카테고리를 빠짐없이 포함해.
주간 변동 데이터가 있으면 "신규 진입", "이탈" 등을 Game Trends에 반영해."""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_message,
    )

    return response.text


if __name__ == '__main__':
    sample = {
        'google_trends': {'keyword_interest': {'vibe coding': 50}},
        'hackernews': {'stories': [{'title': 'Test', 'url': 'https://example.com'}]},
        'rss_feeds': {'articles': [{'title': 'News', 'source': 'TechCrunch'}]},
    }
    result = analyze(sample, 'W14 (2026.03.31 ~ 04.06)')
    print(result)

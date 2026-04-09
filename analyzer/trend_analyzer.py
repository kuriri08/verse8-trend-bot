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

## 핵심 원칙
이 브리핑의 목적은 "지난 24시간 동안 가장 트렌디했던 소식"을 전달하는 것임.
"지금 이 순간 인기 있는 것"이 아니라 "어제 하루 동안 가장 화제가 됐던 것"을 골라야 함.
화제성 판단 기준: Reddit 업보트 수, HN 점수, 댓글 수가 높은 것 = 사람들이 많이 반응한 것 = 트렌디한 것.
단순히 최신 기사라고 트렌디한 게 아님. 사람들이 실제로 관심을 가지고 반응한 것 위주로 선별해.

## 데이터 소스별 특성
- Reddit: 지난 24시간 인기 포스트. 업보트 수가 높을수록 화제성 높음. 가장 신뢰할 수 있는 트렌드 지표. 점수는 표시하지 않음.
- Hacker News: 지난 24시간 개발자 커뮤니티 인기 포스트. 점수/댓글 수는 표시하지 않음.
- 네이버 뉴스: 한국 IT/과학, 생활/문화, 경제 카테고리 인기 뉴스. 한국에서 실제로 많이 읽힌 기사.
- RSS Feeds: 글로벌 뉴스 (TechCrunch, The Verge 등). 최신 발행 기사.
- Google Trends: 지난 24시간 검색량. 에러가 있는 항목은 무시하고 언급하지 마.
- Steam/SteamSpy: 차트 변동 데이터가 있으면 신규 진입/이탈만 활용. 매일 똑같은 인기 게임 나열하지 마.
- Google Play: 동일. 변동이 없으면 굳이 채우지 마.

## 출력 규칙

1. 아래 7개 카테고리를 반드시 모두 포함
2. 각 카테고리당 2~4개 항목
3. 각 항목 포맷 (반드시 지켜):
   • <URL|*제목*> — 한 줄 요약
   제목 자체에 링크를 걸어. 뒤에 별도 출처(Steam, Google Play, HN 등) 표시하지 마.
   URL은 데이터의 url, link, hn_url 필드에서 가져와.
   예시: • <https://store.steampowered.com/app/123|*Crimson Desert 출시*> — Pearl Abyss 오픈월드 RPG, 판매 1위
4. 반드시 한국어로 작성. 영어 원문 기사라도 제목을 한국어로 번역해서 써. 절대 영어 제목 그대로 쓰지 마. 예: "OpenAI launches new model" → "OpenAI 새 모델 출시"
5. 문장 끝은 "~입니다" "~합니다" 말고 "~임" "~있음" "~중" 같은 요약체로 써.
6. 시사점/코멘트/해석 넣지 않음. 팩트만.
7. HN 점수, 댓글 수는 표시하지 않음
8. 에러가 난 소스(404, 429 등)는 아예 언급하지 마. "소스 오류" "재연결 필요" "데이터 부족" 같은 말 절대 금지.
9. 📌 이모지로 시작하는 데이터 부족/미연결/오류 관련 문구를 절대 넣지 마. 데이터가 없으면 그 카테고리에서 있는 데이터로만 채워.
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

## 중요: 글로벌 + 한국 균형
- 글로벌 소식만 치우치지 말고, 한국 관련 뉴스도 반드시 포함해.
- 각 카테고리에 가능하면 글로벌 + 한국 소식을 섞어서 구성.

## 뉴스 선별 기준 (매우 중요)
VERSE8은 바이브코딩 게임 플랫폼이고, 읽는 사람은 마케팅/프로덕트/경영진이야.
아래 기준으로 뉴스를 골라:

포함해야 할 것:
- 게임/IT/AI 업계에 실질적 영향이 있는 뉴스 (정책 변화, 대형 투자, 신규 서비스 출시)
- 플랫폼 전략에 영향을 줄 수 있는 것 (앱스토어 정책, 크리에이터 이코노미 변화)
- 마케터가 콘텐츠 소재로 활용 가능한 문화 트렌드 (밈, 바이럴, 새로운 소비 트렌드)
- 한국 시장에서의 주요 변화 (규제, 투자, 새로운 서비스)
- 대중의 관심이 집중된 사회 현상 (새로운 문화 흐름, 세대 트렌드)

제외해야 할 것:
- 단순 사건사고 (홍수, 화재, 교통사고, 자연재해)
- 기업 노사/인사 이슈 (정규직 전환, 파업, 임원 인사, 대규모 채용 등)
- 단순 가격/요금 변동 (넷플릭스 요금 인상, 통신비 등)
- 연예인 개인 활동/공연/콘서트 후기
- 정치 뉴스 (선거, 국회, 정당, 외교)
- 제조업/중공업/건설 등 IT·게임·문화와 무관한 산업 뉴스
- 스포츠 경기 결과
- 읽는 사람이 "이게 우리랑 무슨 상관?" 하고 넘길 만한 것

판단 기준: "이 뉴스가 VERSE8 팀의 의사결정이나 콘텐츠 기획에 도움이 되는가?"

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

=== Reddit (지난 24시간 인기 포스트, 업보트 순) ===
{json.dumps(clean_data(collected_data.get('reddit', {})), ensure_ascii=False, indent=2)}

=== Hacker News (지난 24시간 인기 포스트) ===
{json.dumps(clean_data(collected_data.get('hackernews', {})), ensure_ascii=False, indent=2)}

=== 네이버 뉴스 (한국 인기 뉴스 — IT/과학, 생활/문화, 경제) ===
{json.dumps(clean_data(collected_data.get('naver_news', {})), ensure_ascii=False, indent=2)}

=== RSS Feeds (글로벌 뉴스 — 테크, 게임, 문화, 엔터) ===
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

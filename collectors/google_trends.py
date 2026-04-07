"""Google Trends 수집기 — pytrends 사용, API 키 불필요"""

import json
import time
from pytrends.request import TrendReq


def collect():
    """Google Trends 데이터 수집 (지난 7일)"""
    pytrends = TrendReq(hl='en-US', tz=540)
    results = {}

    # 1) 게임/AI/문화 관련 키워드 관심도 (지난 7일)
    keyword_groups = [
        ['indie game', 'vibe coding', 'AI game', 'game jam', 'no code game'],
        ['roblox', 'minecraft', 'steam game', 'mobile game', 'godot'],
        ['netflix', 'tiktok trend', 'viral meme', 'kpop', 'anime'],
    ]
    all_interest = {}
    for keywords in keyword_groups:
        try:
            pytrends.build_payload(keywords, timeframe='now 1-d')
            interest = pytrends.interest_over_time()
            if not interest.empty:
                for kw in keywords:
                    if kw in interest.columns:
                        all_interest[kw] = int(interest[kw].mean())
            time.sleep(2)  # rate limit
        except Exception as e:
            results.setdefault('errors', []).append(str(e))

    results['keyword_interest'] = all_interest

    # 2) 관련 급상승 검색어
    try:
        pytrends.build_payload(['vibe coding', 'AI game', 'indie game'], timeframe='now 1-d')
        related = pytrends.related_queries()
        rising_queries = {}
        for kw in ['vibe coding', 'AI game', 'indie game']:
            if kw in related and related[kw]['rising'] is not None:
                rising_df = related[kw]['rising'].head(5)
                rising_queries[kw] = rising_df[['query', 'value']].to_dict('records')
        results['rising_queries'] = rising_queries
    except Exception as e:
        results['rising_queries_error'] = str(e)

    # 3) 급상승 검색어 (한국/미국)
    for region, pn in [('kr', 'south_korea'), ('us', 'united_states')]:
        try:
            time.sleep(1)
            trending = pytrends.trending_searches(pn=pn)
            results[f'trending_{region}'] = trending[0].tolist()[:20]
        except Exception as e:
            results[f'trending_{region}'] = []

    return results


if __name__ == '__main__':
    data = collect()
    print(json.dumps(data, ensure_ascii=False, indent=2))

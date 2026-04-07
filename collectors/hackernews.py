"""Hacker News 수집기 — Algolia Search API로 지난 7일 인기 포스트 조회"""

import json
import requests
from datetime import datetime, timedelta, timezone

ALGOLIA_API = "https://hn.algolia.com/api/v1/search"

# 게임, AI, 테크, 문화 전반 키워드
SEARCH_QUERIES = [
    # 게임/인디
    'indie game', 'game dev', 'game jam', 'steam',
    # AI/코딩 (과도하지 않게)
    'vibe coding', 'AI game', 'no-code',
    # 테크 전반
    'startup funding', 'app store', 'platform',
    # 문화/바이럴
    'viral', 'trending', 'creator economy',
    # 사회/비즈니스
    'remote work', 'education tech', 'gen z',
]


def collect():
    """HN Algolia API로 지난 7일간 인기 포스트 수집"""
    results = {'stories': [], 'source': 'hackernews'}

    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    timestamp_start = int(yesterday.timestamp())
    timestamp_end = int(now.timestamp())

    seen_ids = set()
    all_stories = []

    for query in SEARCH_QUERIES:
        try:
            r = requests.get(
                ALGOLIA_API,
                params={
                    'query': query,
                    'tags': 'story',
                    'numericFilters': f'created_at_i>{timestamp_start},created_at_i<{timestamp_end}',
                    'hitsPerPage': 10,
                },
                timeout=10,
            )
            data = r.json()

            for hit in data.get('hits', []):
                obj_id = hit.get('objectID', '')
                if obj_id in seen_ids:
                    continue
                seen_ids.add(obj_id)

                points = hit.get('points', 0) or 0
                if points < 5:  # 최소 5포인트 이상만
                    continue

                all_stories.append({
                    'title': hit.get('title', ''),
                    'url': hit.get('url', ''),
                    'score': points,
                    'comments': hit.get('num_comments', 0) or 0,
                    'hn_url': f"https://news.ycombinator.com/item?id={obj_id}",
                    'created_at': hit.get('created_at', ''),
                    'matched_query': query,
                })

        except Exception as e:
            results.setdefault('errors', []).append(f"query '{query}': {str(e)}")

    # 점수 순 정렬, 상위 20개
    all_stories.sort(key=lambda x: x['score'], reverse=True)
    results['stories'] = all_stories[:20]
    results['period'] = f"{yesterday.strftime('%Y-%m-%d')} ~ {now.strftime('%Y-%m-%d')}"

    return results


if __name__ == '__main__':
    data = collect()
    print(json.dumps(data, ensure_ascii=False, indent=2))

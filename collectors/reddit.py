"""Reddit 수집기 — 인증 없이 .json 엔드포인트 사용 (무료)"""

import json
import requests
from datetime import datetime, timedelta, timezone

HEADERS = {'User-Agent': 'verse8-trend-bot/1.0'}

# 서브레딧별 수집 설정
SUBREDDITS = {
    # 게임
    'gaming': {'sort': 'hot', 'limit': 15},
    'indiegaming': {'sort': 'hot', 'limit': 10},
    'gamedev': {'sort': 'hot', 'limit': 10},
    # AI/테크
    'artificial': {'sort': 'hot', 'limit': 10},
    'technology': {'sort': 'hot', 'limit': 10},
    # 문화/바이럴
    'popular': {'sort': 'hot', 'limit': 15},
    'OutOfTheLoop': {'sort': 'hot', 'limit': 10},
}


def collect():
    """Reddit 서브레딧별 인기 포스트 수집 (24시간 내)"""
    results = {'posts': [], 'source': 'reddit'}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    for subreddit, config in SUBREDDITS.items():
        try:
            url = f"https://www.reddit.com/r/{subreddit}/{config['sort']}.json?limit={config['limit']}"
            r = requests.get(url, headers=HEADERS, timeout=10)

            if r.status_code != 200:
                continue

            data = r.json()
            for post in data.get('data', {}).get('children', []):
                p = post['data']

                # 고정 포스트 스킵
                if p.get('stickied'):
                    continue

                # 24시간 내 포스트만
                created = datetime.fromtimestamp(p.get('created_utc', 0), tz=timezone.utc)
                if created < cutoff:
                    continue

                # 최소 업보트 기준 (화제성 필터)
                score = p.get('score', 0)
                if subreddit in ('popular', 'gaming', 'technology') and score < 100:
                    continue
                elif score < 10:
                    continue

                results['posts'].append({
                    'subreddit': subreddit,
                    'title': p.get('title', ''),
                    'score': score,
                    'comments': p.get('num_comments', 0),
                    'url': f"https://reddit.com{p.get('permalink', '')}",
                    'created_utc': p.get('created_utc', 0),
                })

        except Exception as e:
            results.setdefault('errors', []).append(f"r/{subreddit}: {str(e)}")

    # 업보트 순 정렬
    results['posts'].sort(key=lambda x: x['score'], reverse=True)
    results['posts'] = results['posts'][:25]

    return results


if __name__ == '__main__':
    data = collect()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\nTotal: {len(data['posts'])} posts")

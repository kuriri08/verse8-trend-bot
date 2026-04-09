"""RSS Feed 수집기 — feedparser 사용, 키 불필요"""

import json
from datetime import datetime, timedelta, timezone
import feedparser

FEEDS = {
    # 글로벌 테크
    'TechCrunch': 'https://techcrunch.com/feed/',
    'The Verge': 'https://www.theverge.com/rss/index.xml',
    # 글로벌 게임
    'Ars Technica Gaming': 'https://feeds.arstechnica.com/arstechnica/gaming',
    'Game Developer': 'https://www.gamedeveloper.com/rss.xml',
    # 글로벌 문화/엔터
    'BBC Culture': 'https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml',
    'Variety': 'https://variety.com/feed/',
    # 한국 소스는 naver_news.py에서 수집 (인기순 정렬 가능)
}

# 키워드 필터 없이 모든 기사를 수집 (Claude가 분류)
# RSS 소스 자체가 이미 관련 분야로 한정됨
KEYWORDS = None  # None이면 필터 없이 전체 수집


def collect():
    """RSS 피드에서 최근 7일 기사 수집"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    results = {'articles': [], 'source': 'rss_feeds'}

    for feed_name, feed_url in FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:30]:
                # 날짜 파싱
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

                if published and published < cutoff:
                    continue

                results['articles'].append({
                    'source': feed_name,
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'published': published.isoformat() if published else None,
                    'summary': entry.get('summary', '')[:300],
                })
        except Exception as e:
            results.setdefault('errors', []).append(f"{feed_name}: {str(e)}")

    # 최신순 정렬
    results['articles'].sort(
        key=lambda x: x.get('published') or '', reverse=True
    )
    results['articles'] = results['articles'][:40]

    return results


if __name__ == '__main__':
    data = collect()
    print(json.dumps(data, ensure_ascii=False, indent=2))

"""네이버 뉴스 수집기 — 카테고리별 인기 뉴스 (한국에서 실제로 화제인 뉴스)"""

import json
import requests
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 네이버 뉴스 섹션 (인기순 정렬)
SECTIONS = {
    'IT/과학': 'https://news.naver.com/section/105',
    '생활/문화': 'https://news.naver.com/section/103',
    '경제': 'https://news.naver.com/section/101',
}


def collect():
    """네이버 뉴스 카테고리별 주요 기사 수집"""
    results = {'articles': [], 'source': 'naver_news'}

    for section_name, url in SECTIONS.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, 'html.parser')

            for a in soup.select('a.sa_text_title')[:8]:
                title = a.text.strip()
                href = a.get('href', '')

                if not title:
                    continue

                results['articles'].append({
                    'section': section_name,
                    'title': title,
                    'url': href,
                })

        except Exception as e:
            results.setdefault('errors', []).append(f"{section_name}: {str(e)}")

    return results


if __name__ == '__main__':
    data = collect()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\nTotal: {len(data['articles'])} articles")

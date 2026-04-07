"""Google Play 게임 인기 차트 수집기 — 웹 스크래핑"""

import json
import requests
from bs4 import BeautifulSoup


CHART_URLS = {
    'top_free_games': 'https://play.google.com/store/games?hl=en&gl=us',
    'top_grossing_games': 'https://play.google.com/store/apps/collection/cluster?clp=0g4jCiEKG3RvcHNlbGxpbmdfZ3Jvc3NfR0FNRRoECAEQAw%3D%3D&gsr=CibSDiMKIQobdG9wc2VsbGluZ19ncm9zc19HQU1FGgQIARAD&hl=en&gl=us',
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}


def _scrape_play_store_page(url: str, max_items: int = 15) -> list:
    """Google Play 페이지에서 앱 정보 추출"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')

        apps = []
        # Google Play의 앱 카드 링크 찾기
        for link in soup.select('a[href*="/store/apps/details"]'):
            if len(apps) >= max_items:
                break

            title_el = link.select_one('span, div.Epkrse')
            title = title_el.get_text(strip=True) if title_el else link.get_text(strip=True)

            if not title or len(title) < 2:
                continue

            href = link.get('href', '')
            app_id = ''
            if 'id=' in href:
                app_id = href.split('id=')[1].split('&')[0]

            # 중복 방지
            if any(a['app_id'] == app_id for a in apps if app_id):
                continue

            apps.append({
                'title': title,
                'app_id': app_id,
                'url': f"https://play.google.com/store/apps/details?id={app_id}" if app_id else '',
            })

        return apps
    except Exception as e:
        return [{'error': str(e)}]


def collect():
    """Google Play 게임 차트 수집 (스크래핑 + search API 병행)"""
    results = {'source': 'google_play'}

    # 1) 차트 페이지 스크래핑
    for chart_name, url in CHART_URLS.items():
        apps = _scrape_play_store_page(url)
        results[chart_name] = apps

    # 2) google-play-scraper search로 보완 (특정 트렌드 키워드)
    try:
        from google_play_scraper import search

        trend_keywords = {
            'trending_new': 'new game 2026',
            'ai_game_makers': 'AI game maker creator',
            'hyper_casual': 'hyper casual game new',
        }

        for key, query in trend_keywords.items():
            try:
                search_results = search(query, lang="en", country="us", n_hits=10)
                results[key] = [
                    {
                        'title': app['title'],
                        'developer': app.get('developer', ''),
                        'score': round(app.get('score', 0) or 0, 1),
                        'installs': app.get('realInstalls', app.get('installs', '')),
                        'url': f"https://play.google.com/store/apps/details?id={app['appId']}",
                    }
                    for app in search_results
                ]
            except Exception as e:
                results[key] = []
                results[f'{key}_error'] = str(e)

    except ImportError:
        results['search_error'] = 'google-play-scraper not installed'

    return results


if __name__ == '__main__':
    data = collect()
    print(json.dumps(data, ensure_ascii=False, indent=2))

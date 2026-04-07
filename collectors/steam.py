"""Steam / SteamSpy 수집기 — 공개 API, 키 불필요"""

import json
import requests
import time


def collect():
    """Steam 인기 게임 + SteamSpy 태그 트렌드 수집"""
    results = {'source': 'steam', 'data_note': 'Steam featured = 현재 시점 차트, SteamSpy = 최근 2주 플레이어 기준'}

    # 1) Steam 인기 신작 (최근 2주 탑셀러)
    try:
        r = requests.get(
            "https://store.steampowered.com/api/featuredcategories/",
            params={"cc": "us", "l": "english"},
            timeout=15,
        )
        data = r.json()

        # Top Sellers
        top_sellers = []
        if 'top_sellers' in data:
            for item in data['top_sellers'].get('items', [])[:15]:
                top_sellers.append({
                    'name': item.get('name', ''),
                    'id': item.get('id', ''),
                    'discount_percent': item.get('discount_percent', 0),
                    'final_price': item.get('final_price', 0) / 100 if item.get('final_price') else 0,
                    'url': f"https://store.steampowered.com/app/{item.get('id', '')}",
                })
        results['top_sellers'] = top_sellers

        # New Releases
        new_releases = []
        if 'new_releases' in data:
            for item in data['new_releases'].get('items', [])[:10]:
                new_releases.append({
                    'name': item.get('name', ''),
                    'id': item.get('id', ''),
                    'url': f"https://store.steampowered.com/app/{item.get('id', '')}",
                })
        results['new_releases'] = new_releases

    except Exception as e:
        results['steam_error'] = str(e)

    # 2) SteamSpy — 최근 2주 인기 게임
    try:
        r = requests.get(
            "https://steamspy.com/api.php",
            params={"request": "top100in2weeks"},
            timeout=15,
        )
        steamspy_data = r.json()

        top_games = []
        for app_id, info in sorted(
            steamspy_data.items(),
            key=lambda x: x[1].get('players_2weeks', 0) if isinstance(x[1], dict) else 0,
            reverse=True,
        )[:15]:
            if not isinstance(info, dict):
                continue
            top_games.append({
                'name': info.get('name', ''),
                'app_id': app_id,
                'players_2weeks': info.get('players_2weeks', 0),
                'average_2weeks': info.get('average_2weeks', 0),
                'genre': info.get('genre', ''),
                'tags': info.get('tags', {}),
                'url': f"https://store.steampowered.com/app/{app_id}",
            })
        results['top_by_players'] = top_games

    except Exception as e:
        results['steamspy_error'] = str(e)

    time.sleep(1)  # SteamSpy rate limit

    # 3) SteamSpy — 장르별 태그 트렌드 (인디, 로그라이크 등)
    indie_tags = ['Indie', 'Roguelike', 'Puzzle', 'Survival', 'Simulation']
    tag_trends = {}
    for tag in indie_tags:
        try:
            r = requests.get(
                "https://steamspy.com/api.php",
                params={"request": "tag", "tag": tag},
                timeout=10,
            )
            tag_data = r.json()
            top_in_tag = sorted(
                [(k, v) for k, v in tag_data.items() if isinstance(v, dict)],
                key=lambda x: x[1].get('players_2weeks', 0),
                reverse=True,
            )[:5]
            tag_trends[tag] = [
                {
                    'name': v.get('name', ''),
                    'players_2weeks': v.get('players_2weeks', 0),
                    'url': f"https://store.steampowered.com/app/{k}",
                }
                for k, v in top_in_tag
            ]
            time.sleep(1)  # rate limit
        except Exception as e:
            tag_trends[tag] = []

    results['tag_trends'] = tag_trends

    return results


if __name__ == '__main__':
    data = collect()
    print(json.dumps(data, ensure_ascii=False, indent=2))

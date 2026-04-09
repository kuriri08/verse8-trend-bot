"""주간 차트 비교 모듈 — 이전 주 데이터와 비교하여 변동 감지"""

import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HISTORY_DIR = PROJECT_ROOT / 'data' / 'history'


def save_snapshot(collected_data: dict):
    """이번 주 차트 데이터를 히스토리에 저장"""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    kst = timezone(timedelta(hours=9))
    date_str = datetime.now(kst).strftime('%Y-%m-%d')

    snapshot = {}

    # Steam 탑셀러 이름 목록
    steam = collected_data.get('steam', {})
    snapshot['steam_top_sellers'] = [
        g['name'] for g in steam.get('top_sellers', []) if isinstance(g, dict)
    ]
    snapshot['steam_top_players'] = [
        {'name': g['name'], 'players': g.get('players_2weeks', 0)}
        for g in steam.get('top_by_players', []) if isinstance(g, dict)
    ]

    # Google Play 인기 게임
    gp = collected_data.get('google_play', {})
    snapshot['gplay_top_free'] = [
        g.get('title', '') for g in gp.get('top_free_games', []) if isinstance(g, dict)
    ]
    snapshot['gplay_trending_new'] = [
        g.get('title', '') for g in gp.get('trending_new', []) if isinstance(g, dict)
    ]

    # 네이버 뉴스 (다음날 리포트에 사용)
    naver = collected_data.get('naver_news', {})
    snapshot['naver_articles'] = naver.get('articles', [])

    filepath = HISTORY_DIR / f'{date_str}.json'
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    return filepath


def get_previous_snapshot():
    """가장 최근 이전 스냅샷 로드"""
    if not HISTORY_DIR.exists():
        return None

    files = sorted(HISTORY_DIR.glob('*.json'), reverse=True)
    # 오늘 파일 제외, 가장 최근 것
    kst = timezone(timedelta(hours=9))
    today_str = datetime.now(kst).strftime('%Y-%m-%d')

    for f in files:
        if f.stem != today_str:
            with open(f, 'r', encoding='utf-8') as fp:
                return json.load(fp)
    return None


def get_yesterday_naver() -> list:
    """어제 저장된 네이버 뉴스 데이터 로드"""
    prev = get_previous_snapshot()
    if prev and 'naver_articles' in prev:
        return prev['naver_articles']
    return []


def compute_diff(collected_data: dict) -> dict:
    """이전 주 대비 변동 계산"""
    prev = get_previous_snapshot()
    if not prev:
        return {'has_diff': False, 'note': '첫 주 데이터 — 다음 주부터 변동 비교 가능'}

    diff = {'has_diff': True}

    # Steam 탑셀러 변동
    steam = collected_data.get('steam', {})
    current_sellers = [g['name'] for g in steam.get('top_sellers', []) if isinstance(g, dict)]
    prev_sellers = prev.get('steam_top_sellers', [])

    new_entries = [g for g in current_sellers if g not in prev_sellers]
    dropped = [g for g in prev_sellers if g not in current_sellers]
    diff['steam'] = {
        'new_entries': new_entries[:5],
        'dropped': dropped[:5],
    }

    # Google Play 변동
    gp = collected_data.get('google_play', {})
    current_gplay = [g.get('title', '') for g in gp.get('top_free_games', []) if isinstance(g, dict)]
    prev_gplay = prev.get('gplay_top_free', [])

    new_gplay = [g for g in current_gplay if g not in prev_gplay]
    dropped_gplay = [g for g in prev_gplay if g not in current_gplay]
    diff['google_play'] = {
        'new_entries': new_gplay[:5],
        'dropped': dropped_gplay[:5],
    }

    return diff


if __name__ == '__main__':
    diff = compute_diff({})
    print(json.dumps(diff, ensure_ascii=False, indent=2))

"""Slack 발송 모듈 — Bot Token API + Block Kit"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv(override=True)


def send_dm(text: str, user_id: str = None, week_label: str = "") -> dict:
    """Slack DM으로 트렌드 브리핑 발송 (Block Kit 포맷)"""
    token = os.environ.get('SLACK_BOT_TOKEN', '')
    target = user_id or os.environ.get('SLACK_TEST_USER_ID', '')

    if not token:
        return {'ok': False, 'error': 'SLACK_BOT_TOKEN not set'}
    if not target:
        return {'ok': False, 'error': 'No target user ID'}

    blocks = _build_blocks(text, week_label=week_label)

    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    # Block Kit은 50블록 제한 → 분할
    chunk_size = 45
    last_result = None

    for i in range(0, len(blocks), chunk_size):
        chunk = blocks[i:i + chunk_size]
        payload = {
            "channel": target,
            "blocks": chunk,
            "text": "VERSE8 데일리 트렌드 리포트",  # fallback
            "unfurl_links": False,
            "unfurl_media": False,
        }
        r = requests.post(url, headers=headers, json=payload)
        last_result = r.json()

        if not last_result.get('ok'):
            return last_result

    return last_result


def send_to_channel(text: str, channel_id: str, week_label: str = "") -> dict:
    """Slack 채널로 제목 발송 → 쓰레드에 상세 내용 발송"""
    token = os.environ.get('SLACK_BOT_TOKEN', '')

    if not token:
        return {'ok': False, 'error': 'SLACK_BOT_TOKEN not set'}

    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    # 1) 메인 채널에 제목만 발송
    if week_label:
        header_text = f"VERSE8 Daily Trend Briefing ({week_label})"
    else:
        header_text = "VERSE8 Daily Trend Briefing"

    header_blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": header_text, "emoji": True}
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "_상세 내용은 쓰레드를 확인하세요_"}
            ]
        },
    ]

    payload = {
        "channel": channel_id,
        "blocks": header_blocks,
        "text": header_text,
        "unfurl_links": False,
        "unfurl_media": False,
    }
    r = requests.post(url, headers=headers, json=payload)
    main_result = r.json()

    if not main_result.get('ok'):
        return main_result

    # 2) 쓰레드에 상세 내용 발송
    thread_ts = main_result.get('ts', '')
    blocks = _build_blocks(text, week_label="")  # 헤더 없이 내용만

    chunk_size = 45
    last_result = None

    for i in range(0, len(blocks), chunk_size):
        chunk = blocks[i:i + chunk_size]
        payload = {
            "channel": channel_id,
            "blocks": chunk,
            "text": "VERSE8 Daily Trend Briefing",
            "thread_ts": thread_ts,
            "unfurl_links": False,
            "unfurl_media": False,
        }
        r = requests.post(url, headers=headers, json=payload)
        last_result = r.json()

        if not last_result.get('ok'):
            return last_result

    return last_result


def _ensure_bold_links(text: str) -> str:
    """링크가 포함된 항목의 제목이 볼드인지 확인하고, 빠져있으면 보정"""
    import re
    lines = text.split('\n')
    result = []
    for line in lines:
        # • 로 시작하는 항목에서 <URL|제목> 패턴의 제목에 볼드가 없으면 추가
        # 패턴: <URL|제목> (볼드 없음) → <URL|*제목*>
        line = re.sub(
            r'<(https?://[^|]+)\|([^*>][^>]*)>',
            lambda m: f'<{m.group(1)}|*{m.group(2)}*>',
            line
        )
        result.append(line)
    return '\n'.join(result)


def _build_blocks(text: str, week_label: str = "") -> list:
    """텍스트를 Slack Block Kit 블록으로 변환"""
    blocks = []
    category_emojis = ['🎮', '📱', '📈', '👥', '🤖', '💻', '🔥', '🌍']

    # 메인 헤더 (크게)
    if week_label:
        header_text = f"VERSE8 Daily Trend Briefing ({week_label})"
    else:
        header_text = "VERSE8 Daily Trend Briefing"
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": header_text, "emoji": True}
    })

    text = _ensure_bold_links(text)
    lines = text.strip().split('\n')
    current_section = ""

    for line in lines:
        stripped = line.strip()
        # ## 마크다운 헤더 제거
        while stripped.startswith('#'):
            stripped = stripped.lstrip('#').strip()
        if not stripped:
            if current_section.strip():
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": current_section.strip()}
                })
                current_section = ""
            continue

        # 카테고리 헤더 감지
        is_category = False
        for emoji in category_emojis:
            if emoji in stripped:
                # 이전 섹션 플러시
                if current_section.strip():
                    blocks.append({
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": current_section.strip()}
                    })
                    current_section = ""
                # 구분선 + 카테고리명
                blocks.append({"type": "divider"})
                category_text = stripped if stripped.startswith('*') else f"*{stripped}*"
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": category_text}
                })
                is_category = True
                break

        # 메인 제목줄 스킵 (Gemini가 출력하는 첫 줄 제목)
        if not is_category:
            if 'Weekly Trend' in stripped or 'VERSE8' in stripped:
                continue
            current_section += stripped + "\n"

    if current_section.strip():
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": current_section.strip()}
        })

    # 푸터
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": "_Powered by VERSE8 Trend Bot_"}
        ]
    })

    return blocks


if __name__ == '__main__':
    result = send_dm("🧪 VERSE8 Trend Bot 테스트 메시지입니다!")
    print(json.dumps(result, indent=2))

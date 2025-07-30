"""
utils/teams.py

Microsoft Teams への通知に使用するモジュール。Incoming Webhook を利用し、
Markdown フォーマットのメッセージを送信する。
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests


logger = logging.getLogger(__name__)


def send_to_teams(webhook_url: str, markdown: str) -> None:
    """
    Microsoft Teams の Incoming Webhook に Markdown メッセージを送信する。

    Args:
        webhook_url: Teams で設定した Incoming Webhook の URL。
        markdown: 送信する Markdown 形式のメッセージ。

    Raises:
        Exception: 通信エラーや Webhook 応答エラーが発生した場合。
    """
    headers = {"Content-Type": "application/json"}
    payload: dict[str, Any] = {"text": markdown}
    try:
        response = requests.post(webhook_url, headers=headers, data=json.dumps(payload), timeout=10)
        if not response.ok:
            logger.error("Teams 通知に失敗しました: %s", response.text)
            response.raise_for_status()
        logger.info("Teams へ通知しました。ステータスコード: %s", response.status_code)
    except Exception as e:
        logger.error("Teams 通知中に例外が発生しました: %s", e)
        raise

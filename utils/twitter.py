"""
utils/twitter.py

Twitter (X) への投稿を行うモジュール。Bearer Token を用いて API v2 に
テキストを投稿する。実環境で動作させるには、必要な権限を持つトークン
およびアプリケーション設定が必要。ここでは簡易的な実装としており、
詳細なエラーハンドリングやリクエスト署名は省いている。
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests


logger = logging.getLogger(__name__)


def post_to_twitter(bearer_token: str | None, tweet: str) -> None:
    """
    Twitter(X) にツイートを投稿する。

    Args:
        bearer_token: Twitter API の Bearer Token。None の場合は投稿しない。
        tweet: 投稿するツイート本文。

    Raises:
        Exception: API 呼び出しに失敗した場合。
    """
    if not bearer_token:
        logger.info("Twitter のトークンが設定されていないため投稿をスキップします。")
        return
    url = "https://api.twitter.com/2/tweets"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {"text": tweet}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        if response.status_code not in (200, 201):
            logger.error("Twitter 投稿に失敗しました: %s", response.text)
            response.raise_for_status()
        logger.info("Twitter へ投稿しました。ステータスコード: %s", response.status_code)
    except Exception as e:
        logger.error("Twitter 投稿中に例外が発生しました: %s", e)
        raise

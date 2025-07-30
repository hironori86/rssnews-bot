"""
utils/note.py

note への記事投稿を行うモジュール。実際の note API 仕様に応じて
エンドポイントや認証方法を調整する必要があるが、ここでは簡易的な
実装としてトークンを用いた POST リクエストを行う例を示す。
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests


logger = logging.getLogger(__name__)


def post_to_note(token: str | None, title: str, content: str) -> None:
    """
    note に記事を投稿する。トークンが無ければ処理をスキップする。

    Args:
        token: note API のアクセストークン。
        title: 記事のタイトル。
        content: 記事本文。

    Raises:
        Exception: 投稿処理中にエラーが発生した場合。
    """
    if not token:
        logger.info("note のトークンが設定されていないため投稿をスキップします。")
        return
    # 仮の API エンドポイント。実際には note の公式 API ドキュメントに従う必要がある。
    url = "https://note.com/api/v1/notes"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "title": title,
        "text": content,
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        if response.status_code not in (200, 201):
            logger.error("note 投稿に失敗しました: %s", response.text)
            response.raise_for_status()
        logger.info("note へ投稿しました。ステータスコード: %s", response.status_code)
    except Exception as e:
        logger.error("note 投稿中に例外が発生しました: %s", e)
        raise

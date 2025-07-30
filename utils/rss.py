"""
utils/rss.py
RSS フィードから記事を取得し、キーワードでフィルタリングする機能を提供する。

依存ライブラリとして `feedparser` を利用して RSS を解析する。
指定した期間内に公開された記事を収集し、タイトルや概要にキーワードが含まれる
もののみを抽出する。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import feedparser


logger = logging.getLogger(__name__)


def parse_rss_feed(url: str, since: datetime) -> List[Dict[str, str]]:
    """
    単一の RSS フィード URL から記事を取得する。

    Args:
        url: RSS フィードの URL。
        since: この日時以降に公開された記事のみを対象とする。

    Returns:
        記事の辞書リスト。各記事は title, link, published, summary を含む。
    """
    entries: List[Dict[str, str]] = []
    try:
        parsed = feedparser.parse(url)
    except Exception as e:
        logger.error("RSS フィードの取得に失敗しました: %s", e)
        return entries

    for entry in parsed.entries:
        try:
            # published_parsed は time.struct_time なので datetime に変換
            published_struct = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
            if not published_struct:
                continue
            published_dt = datetime(*published_struct[:6], tzinfo=timezone.utc)
            if published_dt < since:
                continue
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            summary = entry.get("summary", "") or entry.get("description", "")
            summary = summary.strip()
            entries.append(
                {
                    "title": title,
                    "link": link,
                    "published": published_dt,
                    "summary": summary,
                }
            )
        except Exception as e:
            logger.warning("RSS エントリの解析に失敗しました: %s", e)
    return entries


def filter_by_keywords(articles: List[Dict[str, str]], keywords: List[str]) -> List[Dict[str, str]]:
    """
    記事リストからキーワードが含まれるものだけを抽出する。

    Args:
        articles: 記事のリスト。
        keywords: 検索対象となるキーワードのリスト。

    Returns:
        キーワードを含む記事のリスト。
    """
    if not keywords:
        return articles
    filtered: List[Dict[str, str]] = []
    lower_keywords = [kw.lower() for kw in keywords]
    for article in articles:
        text = (article.get("title", "") + " " + article.get("summary", "")).lower()
        if any(kw in text for kw in lower_keywords):
            filtered.append(article)
    return filtered


def fetch_articles(feeds: List[str], days: int, keywords: List[str]) -> List[Dict[str, str]]:
    """
    複数の RSS フィードから期間内の記事をまとめて取得し、キーワードでフィルタリングする。

    Args:
        feeds: RSS フィード URL のリスト。
        days: 取得対象期間（日数）。現在時刻からこの日数遡った日時以降の記事を取得する。
        keywords: キーワードのリスト。

    Returns:
        フィルタ済み記事のリスト。
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    articles: List[Dict[str, str]] = []
    for url in feeds:
        logger.info("RSS 取得中: %s", url)
        articles.extend(parse_rss_feed(url, since))
    logger.info("RSS 記事数: %d", len(articles))
    filtered = filter_by_keywords(articles, keywords)
    logger.info("キーワードでフィルタ後の記事数: %d", len(filtered))
    return filtered

"""
utils/clustering.py

記事タイトルの類似度に基づいて重複記事をクラスタリングするモジュール。
単純な SequenceMatcher による文字列類似度を用い、一定の閾値以上
類似している記事を同じクラスタにまとめる。クラスタリングされた記事
リストは、配信やトピック抽出の際に重複を排除するために使用される。
"""

from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import Dict, List


logger = logging.getLogger(__name__)


def _similarity(a: str, b: str) -> float:
    """タイトル同士の類似度を返す関数。"""
    return SequenceMatcher(None, a, b).ratio()


def cluster_articles(articles: List[Dict[str, str]], threshold: float = 0.8) -> List[List[Dict[str, str]]]:
    """
    記事リストをタイトル類似度でクラスタリングする。

    Args:
        articles: 記事のリスト。各記事は title を必ず持つ必要がある。
        threshold: 類似度の閾値。この値以上の類似度を持つ記事同士は同じクラスタに属するとみなす。

    Returns:
        クラスタのリスト。各クラスタは記事辞書のリスト。
    """
    clusters: List[List[Dict[str, str]]] = []
    visited = [False] * len(articles)
    for i, article in enumerate(articles):
        if visited[i]:
            continue
        cluster = [article]
        visited[i] = True
        for j in range(i + 1, len(articles)):
            if visited[j]:
                continue
            try:
                sim = _similarity(article.get("title", ""), articles[j].get("title", ""))
            except Exception as e:
                logger.debug("類似度計算に失敗: %s", e)
                sim = 0.0
            if sim >= threshold:
                cluster.append(articles[j])
                visited[j] = True
        clusters.append(cluster)
    return clusters

"""
utils/categorizer.py

ニュース記事を3つのカテゴリに分類するモジュール。
1. 最新技術動向
2. 導入・活用事例
3. その他
"""

from __future__ import annotations

import logging
from typing import Dict, List, Literal

logger = logging.getLogger(__name__)

# カテゴリタイプ
Category = Literal["最新技術動向", "導入・活用事例", "その他"]


def categorize_article(title: str, summary: str) -> Category:
    """
    記事のタイトルと要約から適切なカテゴリを判定する。
    
    Args:
        title: 記事のタイトル
        summary: 記事の要約
        
    Returns:
        判定されたカテゴリ
    """
    text = f"{title} {summary}".lower()
    
    # 最新技術動向のキーワード
    tech_keywords = [
        "新技術", "新機能", "アップデート", "リリース", "発表", "開発",
        "研究", "イノベーション", "次世代", "最新", "新しい", "革新",
        "breakthrough", "announce", "release", "launch", "develop",
        "introduce", "unveil", "reveal", "新型", "新版", "β版", "ベータ版"
    ]
    
    # 導入・活用事例のキーワード
    case_keywords = [
        "導入", "活用", "事例", "採用", "利用", "実装", "運用",
        "成功", "効果", "改善", "業務", "企業", "組織", "実践",
        "case study", "implementation", "adopt", "deploy", "use case",
        "活かす", "使う", "適用", "実証", "実験", "試験"
    ]
    
    # キーワードマッチングによるスコア計算
    tech_score = sum(1 for keyword in tech_keywords if keyword in text)
    case_score = sum(1 for keyword in case_keywords if keyword in text)
    
    # スコアに基づいて分類
    if tech_score > case_score and tech_score > 0:
        return "最新技術動向"
    elif case_score > 0:
        return "導入・活用事例"
    else:
        return "その他"


def categorize_articles(
    articles: List[Dict[str, str]], 
    summaries: Dict[str, str]
) -> Dict[Category, List[Dict[str, str]]]:
    """
    記事リストをカテゴリ別に分類する。
    
    Args:
        articles: 記事のリスト
        summaries: 記事の要約（key: リンク）
        
    Returns:
        カテゴリ別の記事辞書
    """
    categorized: Dict[Category, List[Dict[str, str]]] = {
        "最新技術動向": [],
        "導入・活用事例": [],
        "その他": []
    }
    
    for article in articles:
        title = article.get("title", "")
        link = article.get("link", "")
        summary = summaries.get(link, "")
        
        category = categorize_article(title, summary)
        categorized[category].append(article)
    
    # ログ出力
    for category, items in categorized.items():
        logger.info(f"{category}: {len(items)}件")
    
    return categorized


def build_categorized_markdown(
    categorized: Dict[Category, List[Dict[str, str]]],
    summaries: Dict[str, str]
) -> str:
    """
    カテゴリ別にMarkdown形式のレポートを生成する。
    
    Args:
        categorized: カテゴリ別の記事辞書
        summaries: 記事の要約
        
    Returns:
        Markdown形式の文字列
    """
    lines: List[str] = []
    
    for category in ["最新技術動向", "導入・活用事例", "その他"]:
        articles = categorized.get(category, [])
        if not articles:
            continue
            
        lines.append(f"\n### {category} ({len(articles)}件)")
        
        for article in articles[:10]:  # 各カテゴリ最大10件
            title = article.get("title", "(タイトル不明)")
            link = article.get("link", "")
            summary = summaries.get(link, "")
            lines.append(f"- [{title}]({link})")
            if summary:
                lines.append(f"  {summary}")
    
    return "\n".join(lines)
"""
weekly_generator.py

日次データから週間ニュースを生成するスクリプト。

過去7日分の日次データを読み込み、統合・再クラスタリングして
週次ツイート・note記事を生成する。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from config import CONFIG, Config
from utils import categorizer, clustering, llm as llm_module


def setup_logging() -> None:
    """基本的なロギング設定を行う。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def load_daily_data(base_dir: str, days: int = 7) -> List[Dict]:
    """
    過去N日分の日次データを読み込む。

    Args:
        base_dir: 出力ディレクトリのベースパス
        days: 読み込む日数

    Returns:
        日次データのリスト
    """
    logger = logging.getLogger("data_loader")
    daily_data = []
    base_path = Path(base_dir) / "daily"
    
    # 過去N日分の日付を生成
    today = datetime.now()
    for i in range(days):
        target_date = today - timedelta(days=i)
        date_str = target_date.strftime("%Y%m%d")
        daily_dir = base_path / date_str
        
        if not daily_dir.exists():
            logger.warning(f"日次データが見つかりません: {date_str}")
            continue
            
        # インデックスファイルを読み込み
        index_file = daily_dir / "index.json"
        if not index_file.exists():
            logger.warning(f"インデックスファイルが見つかりません: {date_str}")
            continue
            
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # 記事データファイルを読み込み
            data_path = daily_dir / index_data["data_path"]
            if not data_path.exists():
                logger.warning(f"記事データファイルが見つかりません: {data_path}")
                continue
                
            with open(data_path, 'r', encoding='utf-8') as f:
                articles_data = json.load(f)
            
            daily_data.append({
                "date": date_str,
                "index": index_data,
                "articles": articles_data
            })
            logger.info(f"日次データを読み込みました: {date_str} ({len(articles_data['articles'])}件)")
            
        except Exception as e:
            logger.error(f"日次データの読み込みに失敗しました ({date_str}): {e}")
            continue
    
    return daily_data


def merge_articles(daily_data: List[Dict]) -> tuple[List[Dict[str, str]], Dict[str, str]]:
    """
    複数日分の記事データを統合し、重複を除去する。

    Args:
        daily_data: 日次データのリスト

    Returns:
        統合された記事リストと要約辞書のタプル
    """
    logger = logging.getLogger("article_merger")
    
    merged_articles = []
    summaries = {}
    seen_links = set()
    
    for day_data in daily_data:
        articles_data = day_data["articles"]
        
        for article in articles_data["articles"]:
            link = article.get("link", "")
            
            # 重複チェック
            if link in seen_links:
                continue
                
            seen_links.add(link)
            
            # 記事データの統合
            merged_article = {
                "title": article.get("title", ""),
                "link": link,
                "published": article.get("published", ""),
                "source": article.get("source", ""),
                "summary": article.get("summary", ""),
                "category": article.get("category", "その他")
            }
            
            merged_articles.append(merged_article)
            summaries[link] = article.get("summary", "")
    
    logger.info(f"記事を統合しました: {len(merged_articles)}件 (重複除去前: {sum(len(d['articles']['articles']) for d in daily_data)}件)")
    return merged_articles, summaries


def categorize_merged_articles(articles: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    """
    統合された記事をカテゴリ別に分類する。

    Args:
        articles: 統合された記事リスト

    Returns:
        カテゴリ別記事辞書
    """
    categorized = {
        "最新技術動向": [],
        "導入・活用事例": [],
        "その他": []
    }
    
    for article in articles:
        category = article.get("category", "その他")
        if category in categorized:
            categorized[category].append(article)
        else:
            categorized["その他"].append(article)
    
    return categorized


def generate_weekly_content(
    articles: List[Dict[str, str]], 
    summaries: Dict[str, str],
    categorized: Dict[str, List[Dict[str, str]]],
    config: Config,
    start_date: str,
    end_date: str
) -> tuple[List[str], List[Dict[str, str]]]:
    """
    週間コンテンツ（ツイート・note記事）を生成する。

    Args:
        articles: 統合された記事リスト
        summaries: 記事の要約辞書
        categorized: カテゴリ別記事
        config: 設定オブジェクト
        start_date: 開始日
        end_date: 終了日

    Returns:
        ツイートリストとnote記事リストのタプル
    """
    logger = logging.getLogger("content_generator")
    
    # クラスタリング
    clusters = clustering.cluster_articles(articles)
    logger.info(f"クラスタ数: {len(clusters)}")
    
    # LLMクライアント初期化
    llm_client = llm_module.LLMClient(api_key=config.openai_api_key)
    
    # トピック抽出（上位3つ）
    topic_clusters = sorted(
        clusters,
        key=lambda cl: (
            -len(cl),
            max((art.get("published") for art in cl if art.get("published")), default=""),
        ),
    )[:3]
    
    # 注目トピックの情報を取得
    top_topics = []
    for cl in topic_clusters:
        canonical = cl[0]
        title = canonical.get("title", "")
        link = canonical.get("link", "")
        summary = summaries.get(link, "")
        top_topics.append({"title": title, "link": link, "summary": summary})
    
    # 週次ツイート案生成
    tweet_messages = []
    try:
        weekly_tweet = llm_client.generate_weekly_tweet(
            articles, 
            [t["title"] for t in top_topics],
            start_date,
            end_date
        )
        tweet_messages.append(weekly_tweet)
    except Exception as e:
        logger.error(f"週次ツイート案生成に失敗しました: {e}")
        fallback_tweet = (
            f"📊今週のDXニュース({start_date}〜{end_date})\n\n"
            f"総記事数: {len(articles)}件\n"
            f"注目: {top_topics[0]['title'] if top_topics else ''}など\n\n"
            f"詳細はリンクから👇\n"
            f"#DX週報 #AIニュース"
        )
        tweet_messages.append(fallback_tweet[:280])
    
    # 週次note記事案生成
    note_articles = []
    try:
        weekly_note = llm_client.generate_weekly_note_article(
            articles,
            top_topics,
            start_date,
            end_date,
            categorized,
            summaries
        )
        note_articles.append({
            "title": f"今週のDXニュースまとめ({start_date}〜{end_date})",
            "content": weekly_note
        })
    except Exception as e:
        logger.error(f"週次note記事生成に失敗しました: {e}")
        fallback_note = (
            f"今週({start_date}〜{end_date})のDXニュースまとめ\n\n"
            f"総記事数: {len(articles)}件\n\n"
            f"注目トピック:\n"
        )
        for i, topic in enumerate(top_topics[:3], 1):
            fallback_note += f"{i}. {topic['title']}\n{topic['summary']}\n\n"
        note_articles.append({
            "title": f"今週のDXニュースまとめ({start_date}〜{end_date})",
            "content": fallback_note
        })
    
    return tweet_messages, note_articles


def save_weekly_content(
    tweet_messages: List[str],
    note_articles: List[Dict[str, str]],
    articles: List[Dict[str, str]],
    summaries: Dict[str, str],
    categorized: Dict[str, List[Dict[str, str]]],
    output_base_dir: str,
    start_date: str,
    end_date: str
) -> str:
    """
    週間コンテンツをファイルに保存する。

    Args:
        tweet_messages: ツイート案のリスト
        note_articles: note記事のリスト
        articles: 統合された記事リスト
        summaries: 記事の要約辞書
        categorized: カテゴリ別記事
        output_base_dir: 出力ディレクトリのベースパス
        start_date: 開始日
        end_date: 終了日

    Returns:
        保存先ディレクトリのパス
    """
    # 週間データ用のディレクトリ構造
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    weekly_dir = Path(output_base_dir) / "weekly" / f"{start_date}_{end_date}"
    output_dir = weekly_dir / timestamp
    tweets_dir = output_dir / "tweets"
    notes_dir = output_dir / "notes"
    
    # ディレクトリ作成
    tweets_dir.mkdir(parents=True, exist_ok=True)
    notes_dir.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("file_saver")
    
    # ツイート保存
    for i, tweet in enumerate(tweet_messages, 1):
        tweet_file = tweets_dir / f"tweet_{i:02d}.txt"
        tweet_file.write_text(tweet, encoding="utf-8")
    
    # note記事保存（noteにコピペしやすい形式）
    for i, article in enumerate(note_articles, 1):
        # ファイル名をより分かりやすく
        import re
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', article['title'][:50])
        note_file = notes_dir / f"note_{i:02d}_{safe_title}.md"
        
        # noteにそのままコピペできる形式
        content = f"""# {article['title']}

{article['content']}

---
🔗 この記事をnoteにコピペする際は、上記の内容をそのまま貼り付けてください。
📝 マークダウン形式で記述されているため、noteでも適切に表示されます。
"""
        note_file.write_text(content, encoding="utf-8")
    
    # サマリー情報をJSONで保存
    summary_data = {
        "type": "weekly",
        "start_date": start_date,
        "end_date": end_date,
        "generated_at": datetime.now().isoformat(),
        "total_articles": len(articles),
        "tweets_count": len(tweet_messages),
        "notes_count": len(note_articles),
        "categorized": {
            category: len(category_articles)
            for category, category_articles in categorized.items()
        }
    }
    
    summary_file = output_dir / "summary.json"
    summary_file.write_text(
        json.dumps(summary_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    # 保存結果のサマリーをログ出力
    logger.info(f"📁 週間コンテンツを以下に保存しました:")
    logger.info(f"  📦 出力ディレクトリ: {output_dir}")
    logger.info(f"  🔊 X投稿案: {len(tweet_messages)}件")
    logger.info(f"  📝 note記事案: {len(note_articles)}件")
    logger.info(f"  📋 サマリー: {summary_file.name}")
    
    return str(output_dir)


def main() -> None:
    """メイン関数。"""
    setup_logging()
    
    parser = argparse.ArgumentParser(description="日次データから週間ニュースを生成")
    parser.add_argument("--days", type=int, default=7, help="対象とする日数（デフォルト: 7）")
    parser.add_argument("--output-dir", default="outputs", help="出力ディレクトリ（デフォルト: outputs）")
    args = parser.parse_args()
    
    config = CONFIG
    if not config:
        logging.error("設定の読み込みに失敗しました。必須環境変数を確認してください。")
        sys.exit(1)
    
    logger = logging.getLogger("weekly_generator")
    logger.info("週間ニュース生成を開始します。")
    
    # 日次データの読み込み
    daily_data = load_daily_data(args.output_dir, args.days)
    if not daily_data:
        logger.error("有効な日次データが見つかりませんでした。")
        sys.exit(1)
    
    # 記事データの統合
    merged_articles, summaries = merge_articles(daily_data)
    if not merged_articles:
        logger.error("統合する記事がありませんでした。")
        sys.exit(1)
    
    # カテゴリ別分類
    categorized = categorize_merged_articles(merged_articles)
    
    # 日付範囲の計算
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days-1)
    start_date_str = start_date.strftime("%Y/%m/%d")
    end_date_str = end_date.strftime("%Y/%m/%d")
    
    # 週間コンテンツ生成
    tweet_messages, note_articles = generate_weekly_content(
        merged_articles, summaries, categorized, config, 
        start_date_str, end_date_str
    )
    
    # ファイル保存
    output_dir = save_weekly_content(
        tweet_messages, note_articles, merged_articles, summaries, categorized,
        args.output_dir, start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")
    )
    
    logger.info(f"週間ニュース生成が完了しました: {output_dir}")


if __name__ == "__main__":
    main()
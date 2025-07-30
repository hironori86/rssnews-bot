"""
main.py

DX ニュース自動収集・配信アプリのエントリポイント。

CLI で実行する際は `--run-now` による即時実行と、指定曜日・時刻に
自動実行するスケジュールモードを提供する。また、`--post` オプション
を指定すると、生成したツイート案や note 記事を実際に投稿する。
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta
from html import unescape
from pathlib import Path
from typing import Dict, List

import schedule

from config import CONFIG, Config
from utils import (
    categorizer, clustering, email_sender, line_sender,
    llm as llm_module, note, rss, teams, twitter
)


def setup_logging() -> None:
    """基本的なロギング設定を行う。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def strip_html_tags(text: str) -> str:
    """HTML タグを簡易的に除去し、生のテキストを返す。"""
    clean = re.sub(r"<[^>]+>", "", text)
    return unescape(clean)


def build_markdown(
    clusters: List[List[Dict[str, str]]], 
    summaries: Dict[str, str],
    categorized: Dict[str, List[Dict[str, str]]] | None = None
) -> str:
    """
    Teams へ送信する Markdown メッセージを組み立てる。

    Args:
        clusters: クラスタリングされた記事リスト。
        summaries: 各記事の要約。key は記事のリンク。
        categorized: カテゴリ別の記事辞書

    Returns:
        Markdown 形式の文字列。
    """
    lines: List[str] = []
    today = datetime.now().strftime("%Y-%m-%d")
    
    lines.append(f"## DXニュース日次まとめ ({today})")
    lines.append(f"集計期間: {today}")
    lines.append(f"総記事数: {sum(len(cluster) for cluster in clusters)}件")
    
    if not clusters:
        lines.append("\n本期間内に該当するニュースはありませんでした。")
        return "\n".join(lines)
    
    # カテゴリ別に表示
    if categorized:
        lines.append(categorizer.build_categorized_markdown(categorized, summaries))
    else:
        # 従来の表示
        lines.append("\n### 主要ニュース")
        for cluster in clusters[:10]:
            article = cluster[0]
            title = article.get("title", "(タイトル不明)")
            link = article.get("link", "")
            summary = summaries.get(link, "")
            lines.append(f"- [{title}]({link})")
            if summary:
                lines.append(f"  {summary}")
    
    return "\n".join(lines)


def select_topic_clusters(clusters: List[List[Dict[str, str]]], max_topics: int = 5) -> List[List[Dict[str, str]]]:
    """
    トピック候補クラスタを選択する。サイズの大きい順に並べ替え、最大数を返す。

    Args:
        clusters: クラスタリングされた記事リスト。
        max_topics: 抽出するトピック数の上限。

    Returns:
        抽出されたトピッククラスタのリスト。
    """
    # クラスタサイズと公開日でソート（まずサイズ降順、次に最新日付降順）
    sorted_clusters = sorted(
        clusters,
        key=lambda cl: (
            -len(cl),
            max((art.get("published") for art in cl if art.get("published")), default=datetime.min),
        ),
    )
    return sorted_clusters[:max_topics]


def save_generated_content(
    tweet_messages: List[str],
    note_articles: List[Dict[str, str]],
    clusters: List[List[Dict[str, str]]],
    summaries: Dict[str, str],
    output_base_dir: str = "outputs",
    teams_markdown: str = "",
    categorized: Dict[str, List[Dict[str, str]]] | None = None,
    all_articles: List[Dict[str, str]] | None = None,
) -> str:
    """
    生成されたコンテンツをファイルに保存する。

    Args:
        tweet_messages: ツイート案のリスト
        note_articles: note記事のリスト
        clusters: クラスタリングされた記事
        summaries: 記事の要約
        all_articles: 全記事データ（週間ニュース作成用）

    Returns:
        保存先ディレクトリのパス
    """
    # 現在の日時でディレクトリを作成（日次データ用の構造）
    today = datetime.now()
    date_str = today.strftime("%Y%m%d")
    timestamp = today.strftime("%Y%m%d_%H%M%S")
    
    # 日付ベースのディレクトリ構造
    daily_dir = Path(output_base_dir) / "daily" / date_str
    output_dir = daily_dir / timestamp
    tweets_dir = output_dir / "tweets"
    notes_dir = output_dir / "notes"
    teams_dir = output_dir / "teams"
    raw_data_dir = output_dir / "raw_data"
    
    # ディレクトリ作成
    tweets_dir.mkdir(parents=True, exist_ok=True)
    notes_dir.mkdir(parents=True, exist_ok=True)
    teams_dir.mkdir(parents=True, exist_ok=True)
    raw_data_dir.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("file_saver")
    
    # ツイート保存
    for i, tweet in enumerate(tweet_messages, 1):
        tweet_file = tweets_dir / f"tweet_{i:02d}.txt"
        tweet_file.write_text(tweet, encoding="utf-8")
    
    # note記事保存（noteにコピペしやすい形式）
    for i, article in enumerate(note_articles, 1):
        # ファイル名をより分かりやすく
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
    
    # Teams通知内容を保存
    if teams_markdown:
        teams_file = teams_dir / "teams_notification.md"
        teams_file.write_text(teams_markdown, encoding="utf-8")
    
    # 週間ニュース作成用の生データを保存
    if all_articles:
        raw_articles_data = {
            "date": date_str,
            "generated_at": today.isoformat(),
            "articles": [
                {
                    "title": article.get("title", ""),
                    "link": article.get("link", ""),
                    "published": article.get("published", "").isoformat() if isinstance(article.get("published"), datetime) else str(article.get("published", "")),
                    "source": article.get("source", ""),
                    "summary": summaries.get(article.get("link", ""), ""),
                    "category": None  # カテゴリ情報を後で追加
                }
                for article in all_articles
            ]
        }
        
        # カテゴリ情報を追加
        if categorized:
            for category, category_articles in categorized.items():
                for category_article in category_articles:
                    article_link = category_article.get("link", "")
                    for raw_article in raw_articles_data["articles"]:
                        if raw_article["link"] == article_link:
                            raw_article["category"] = category
                            break
        
        # 生データファイルを保存
        raw_data_file = raw_data_dir / "articles.json"
        raw_data_file.write_text(
            json.dumps(raw_articles_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 日付別のインデックスファイルも作成（週間集計用）
        daily_index_file = daily_dir / "index.json"
        daily_index = {
            "date": date_str,
            "processed_at": today.isoformat(),
            "data_path": raw_data_file.relative_to(daily_dir).as_posix(),
            "total_articles": len(all_articles),
            "categories": {
                category: len(articles)
                for category, articles in (categorized.items() if categorized else {})
            }
        }
        daily_index_file.write_text(
            json.dumps(daily_index, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    # サマリー情報をJSONで保存
    summary_data = {
        "type": "daily",
        "date": date_str,
        "generated_at": today.isoformat(),
        "total_articles": sum(len(cluster) for cluster in clusters),
        "total_clusters": len(clusters),
        "tweets_count": len(tweet_messages),
        "notes_count": len(note_articles),
        "tweets": [
            {
                "index": i,
                "content": tweet,
                "length": len(tweet)
            }
            for i, tweet in enumerate(tweet_messages, 1)
        ],
        "notes": [
            {
                "index": i,
                "title": article["title"],
                "length": len(article["content"])
            }
            for i, article in enumerate(note_articles, 1)
        ],
        "clusters": [
            {
                "cluster_index": i,
                "articles_count": len(cluster),
                "main_article": {
                    "title": cluster[0].get("title", ""),
                    "link": cluster[0].get("link", ""),
                    "summary": summaries.get(cluster[0].get("link", ""), "")
                }
            }
            for i, cluster in enumerate(clusters[:5], 1)
        ],
        "categorized": {
            category: len(articles)
            for category, articles in (categorized.items() if categorized else {})
        }
    }
    
    summary_file = output_dir / "summary.json"
    summary_file.write_text(
        json.dumps(summary_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    # 保存結果のサマリーをログ出力
    logger.info(f"📁 コンテンツを以下に保存しました:")
    logger.info(f"  📦 出力ディレクトリ: {output_dir}")
    logger.info(f"  🔊 X投稿案: {len(tweet_messages)}件")
    logger.info(f"  📝 note記事案: {len(note_articles)}件")
    logger.info(f"  📋 サマリー: {summary_file.name}")
    
    return str(output_dir)


def run_task(config: Config, post: bool) -> None:
    """
    ニュース取得から要約、投稿生成、Teams への通知およびオプションで投稿を実行する主処理関数。

    Args:
        config: アプリケーション設定。
        post: X と note への実投稿を行うかどうか。
    """
    logger = logging.getLogger("runner")
    logger.info("ニュース取得を開始します。")
    try:
        articles = rss.fetch_articles(config.rss_feeds, days=1, keywords=config.keywords)
    except Exception as e:
        logger.error("RSS の取得に失敗しました: %s", e)
        return
    if not articles:
        # 記事がない場合でも Teams へ通知する
        markdown = build_markdown([], {})
        try:
            teams.send_to_teams(config.team_webhook_url, markdown)
        except Exception:
            logger.exception("Teams への通知に失敗しました")
        return

    # 重複クラスタリング
    clusters = clustering.cluster_articles(articles)
    logger.info("クラスタ数: %d", len(clusters))

    # LLM クライアント初期化
    llm_client = llm_module.LLMClient(api_key=config.openai_api_key)

    # 各記事要約を生成
    summaries: Dict[str, str] = {}
    for article in articles:
        link = article.get("link", "")
        text = article.get("summary") or article.get("title") or ""
        clean_text = strip_html_tags(text)
        try:
            summary = llm_client.summarize(clean_text, max_chars=200)
        except Exception as e:
            logger.error("要約生成に失敗しました (%s): %s", link, e)
            summary = clean_text[:200]
        summaries[link] = summary

    # 記事をカテゴリ別に分類
    categorized = categorizer.categorize_articles(articles, summaries)
    
    # Teams 用 Markdown を作成して送信
    markdown = build_markdown(clusters, summaries, categorized)
    try:
        teams.send_to_teams(config.team_webhook_url, markdown)
    except Exception:
        logger.exception("Teams への通知に失敗しました")

    # トピック抽出
    topic_clusters = select_topic_clusters(clusters, max_topics=3)
    logger.info("トピック数: %d", len(topic_clusters))
    
    # 日次サマリー用の日付設定
    today = datetime.now()
    today_str = today.strftime("%Y/%m/%d")
    
    # 注目トピックの情報を取得
    top_topics = []
    for cl in topic_clusters[:3]:
        canonical = cl[0]
        title = canonical.get("title", "")
        link = canonical.get("link", "")
        summary = summaries.get(link, "")
        top_topics.append({"title": title, "link": link, "summary": summary})
    
    # 日次ツイート案生成
    tweet_messages: List[str] = []
    try:
        daily_tweet = llm_client.generate_daily_tweet(
            articles, 
            [t["title"] for t in top_topics],
            today_str
        )
        tweet_messages.append(daily_tweet)
    except Exception as e:
        logger.error("日次ツイート案生成に失敗しました: %s", e)
        fallback_tweet = (
            f"📊今日のDXニュース({today_str})\n\n"
            f"総記事数: {len(articles)}件\n"
            f"注目: {top_topics[0]['title'] if top_topics else ''}など\n\n"
            f"詳細はリンクから👇\n"
            f"#DX日報 #AIニュース"
        )
        tweet_messages.append(fallback_tweet[:280])
    
    # 日次note記事案生成
    note_articles: List[Dict[str, str]] = []
    try:
        daily_note = llm_client.generate_daily_note_article(
            articles,
            top_topics,
            today_str,
            categorized,
            summaries
        )
        note_articles.append({
            "title": f"今日のDXニュースまとめ({today_str})",
            "content": daily_note
        })
    except Exception as e:
        logger.error("日次note記事生成に失敗しました: %s", e)
        fallback_note = (
            f"今日({today_str})のDXニュースまとめ\n\n"
            f"総記事数: {len(articles)}件\n\n"
            f"注目トピック:\n"
        )
        for i, topic in enumerate(top_topics[:3], 1):
            fallback_note += f"{i}. {topic['title']}\n{topic['summary']}\n\n"
        note_articles.append({
            "title": f"今日のDXニュースまとめ({today_str})",
            "content": fallback_note
        })

    # 生成されたコンテンツをファイルに保存
    output_dir = save_generated_content(
        tweet_messages, note_articles, clusters, summaries, 
        config.output_dir, markdown, categorized, articles
    )
    logger.info(f"生成されたコンテンツを保存しました: {output_dir}")

    # メール送信
    if config.smtp_server and config.email_recipients:
        try:
            email_client = email_sender.EmailSender(
                config.smtp_server,
                config.smtp_port,
                config.smtp_username or "",
                config.smtp_password or "",
                config.from_email or ""
            )
            
            # カテゴリ別記事数を取得
            category_counts = {
                category: len(articles)
                for category, articles in categorized.items()
            }
            
            html_content = email_sender.format_weekly_report_html(
                today_str, today_str, len(articles),
                top_topics, category_counts
            )
            text_content = email_sender.format_weekly_report_text(
                today_str, today_str, len(articles),
                top_topics, category_counts
            )
            
            subject = f"DXニュース日次レポート ({today_str})"
            email_client.send_weekly_report(
                config.email_recipients,
                subject,
                html_content,
                text_content
            )
        except Exception:
            logger.exception("メール送信に失敗しました")
    
    # LINE送信
    if config.line_channel_access_token:
        try:
            line_client = line_sender.LineSender(config.line_channel_access_token)
            
            # カテゴリ別記事数を取得
            category_counts = {
                category: len(articles)
                for category, articles in categorized.items()
            }
            
            # ユーザーIDが指定されている場合は個別送信、そうでなければブロードキャスト
            if config.line_user_ids:
                for user_id in config.line_user_ids:
                    line_client.send_weekly_report(
                        today_str, today_str,
                        len(articles), top_topics, 
                        category_counts, markdown, user_id
                    )
            else:
                line_client.send_weekly_report(
                    today_str, today_str,
                    len(articles), top_topics,
                    category_counts, markdown
                )
        except Exception:
            logger.exception("LINE送信に失敗しました")
    
    # 実投稿
    if post:
        logger.info("post オプションが有効なため、X/note へ投稿します。")
        for tweet_text in tweet_messages:
            try:
                twitter.post_to_twitter(config.twitter_bearer_token, tweet_text)
            except Exception:
                logger.exception("Twitter への投稿に失敗しました")
        for article in note_articles:
            try:
                note.post_to_note(config.note_token, article["title"], article["content"])
            except Exception:
                logger.exception("note への投稿に失敗しました")


def schedule_tasks(config: Config, post: bool) -> None:
    """
    schedule ライブラリを利用して指定曜日・時刻にタスクを実行する。

    Args:
        config: 設定オブジェクト。
        post: post オプション。
    """
    logger = logging.getLogger("scheduler")

    # スケジュール関数にクロージャを渡す
    def job_wrapper() -> None:
        run_task(config, post)

    # 曜日文字列から schedule のメソッド名にマッピング
    day_method_map = {
        "mon": schedule.every().monday,
        "tue": schedule.every().tuesday,
        "wed": schedule.every().wednesday,
        "thu": schedule.every().thursday,
        "fri": schedule.every().friday,
        "sat": schedule.every().saturday,
        "sun": schedule.every().sunday,
    }
    method = day_method_map.get(config.post_day_of_week.lower())
    if not method:
        logger.error("無効な POST_DAY_OF_WEEK: %s", config.post_day_of_week)
        sys.exit(1)
    time_str = f"{config.post_hour_24}:00"
    logger.info("スケジューラを設定します: %s %s", config.post_day_of_week, time_str)
    method.at(time_str).do(job_wrapper)
    while True:
        schedule.run_pending()
        time.sleep(60)


def main() -> None:
    """コマンドライン引数を解析し、処理を開始する。"""
    setup_logging()
    parser = argparse.ArgumentParser(description="DX ニュース自動収集・配信アプリ")
    parser.add_argument("--run-now", action="store_true", help="直ちに実行する (スケジュールを無視)")
    parser.add_argument("--post", action="store_true", help="生成したツイートおよび note 記事を実際に投稿する")
    args = parser.parse_args()

    config = CONFIG
    if not config:
        logging.error("設定の読み込みに失敗しました。必須環境変数を確認してください。")
        sys.exit(1)

    if args.run_now:
        run_task(config, args.post)
    else:
        schedule_tasks(config, args.post)


if __name__ == "__main__":
    main()

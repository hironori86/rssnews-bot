"""
config.py
各種設定や環境変数の読み込みを行うモジュール。

このモジュールでは `.env` ファイルや環境変数から設定値を読み込み、
アプリケーション全体で共有できる形に整形する。DX ニュース自動収集・配信アプリの
動作に必要なキーや RSS フィード URL、キーワード、投稿の曜日や時間などを管理する。
Python 3.12 以降で動作することを前提としている。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv


@dataclass
class Config:
    """アプリケーション設定を保持するデータクラス。"""

    # OpenAI の API キー
    openai_api_key: str
    # Teams の Incoming Webhook URL
    team_webhook_url: str
    # Twitter(X) の Bearer Token
    twitter_bearer_token: str | None = None
    # note 投稿用のアクセストークン
    note_token: str | None = None
    # 投稿実行曜日 (cron 用)。月曜日: mon, 火曜日: tue ...
    post_day_of_week: str = "mon"
    # 投稿実行時刻 (24 時間制 HH)。例: "09"
    post_hour_24: str = "09"
    # RSS フィードの URL リスト
    rss_feeds: List[str] = field(default_factory=list)
    # 記事フィルタに利用するキーワード
    keywords: List[str] = field(default_factory=list)
    # 出力ディレクトリ
    output_dir: str = "outputs"
    # メール送信設定
    smtp_server: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    from_email: str | None = None
    email_recipients: List[str] = field(default_factory=list)
    # LINE送信設定
    line_channel_access_token: str | None = None
    line_user_ids: List[str] = field(default_factory=list)

    @staticmethod
    def load(dotenv_path: str | None = None) -> "Config":
        """
        .env ファイルや環境変数から設定を読み込む。

        Args:
            dotenv_path: .env ファイルのパス。指定しない場合はカレントディレクトリの `.env` を読み込む。

        Returns:
            Config: 読み込んだ設定を保持する Config インスタンス。

        Raises:
            ValueError: 必須環境変数が設定されていない場合。
        """
        # .env を読み込む
        load_dotenv(dotenv_path)

        def get_env(name: str, default: str | None = None, required: bool = False) -> str | None:
            value = os.getenv(name, default)
            if required and not value:
                raise ValueError(f"環境変数 {name} が設定されていません")
            return value

        openai_api_key = get_env("OPENAI_API_KEY", required=True)
        team_webhook_url = get_env("TEAM_WEBHOOK_URL", required=True)
        twitter_bearer_token = get_env("TWITTER_BEARER_TOKEN")
        note_token = get_env("NOTE_TOKEN")
        post_day_of_week = get_env("POST_DAY_OF_WEEK", "mon")
        post_hour_24 = get_env("POST_HOUR_24", "09")

        # RSS フィードはカンマ区切りで指定
        rss_feeds_raw = get_env("RSS_FEEDS", "")
        rss_feeds = [url.strip() for url in rss_feeds_raw.split(",") if url.strip()]
        # キーワードはカンマ区切り
        keywords_raw = get_env("KEYWORDS", "生成AI,BIツール,DX")
        keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
        # 出力ディレクトリ
        output_dir = get_env("OUTPUT_DIR", "outputs")
        
        # メール設定
        smtp_server = get_env("SMTP_SERVER")
        smtp_port = int(get_env("SMTP_PORT", "587") or "587")
        smtp_username = get_env("SMTP_USERNAME")
        smtp_password = get_env("SMTP_PASSWORD")
        from_email = get_env("FROM_EMAIL")
        email_recipients_raw = get_env("EMAIL_RECIPIENTS", "")
        email_recipients = [email.strip() for email in email_recipients_raw.split(",") if email.strip()]
        
        # LINE設定
        line_channel_access_token = get_env("LINE_CHANNEL_ACCESS_TOKEN")
        line_user_ids_raw = get_env("LINE_USER_IDS", "")
        line_user_ids = [uid.strip() for uid in line_user_ids_raw.split(",") if uid.strip()]

        return Config(
            openai_api_key=openai_api_key or "",
            team_webhook_url=team_webhook_url or "",
            twitter_bearer_token=twitter_bearer_token,
            note_token=note_token,
            post_day_of_week=post_day_of_week or "mon",
            post_hour_24=post_hour_24 or "09",
            rss_feeds=rss_feeds,
            keywords=keywords,
            output_dir=output_dir or "outputs",
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            from_email=from_email,
            email_recipients=email_recipients,
            line_channel_access_token=line_channel_access_token,
            line_user_ids=line_user_ids,
        )


# デフォルト設定を読み込む。スクリプト内から import して利用可能。
try:
    CONFIG = Config.load()
except Exception:
    # .env が無い場合や必須変数が不足している場合でもプログラム全体がクラッシュしないようにする
    CONFIG = None

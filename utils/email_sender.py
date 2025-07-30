"""
utils/email_sender.py

メール送信機能を提供するモジュール。
SMTPを使用して、登録されたメールアドレスに週次レポートを送信する。
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

logger = logging.getLogger(__name__)


class EmailSender:
    """メール送信を行うクラス。"""
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str,
    ) -> None:
        """
        コンストラクタ。
        
        Args:
            smtp_server: SMTPサーバーのホスト名
            smtp_port: SMTPサーバーのポート番号
            username: SMTP認証用のユーザー名
            password: SMTP認証用のパスワード
            from_email: 送信元メールアドレス
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
    
    def send_weekly_report(
        self,
        recipients: List[str],
        subject: str,
        html_content: str,
        text_content: str,
    ) -> bool:
        """
        週次レポートをメールで送信する。
        
        Args:
            recipients: 送信先メールアドレスのリスト
            subject: メールの件名
            html_content: HTML形式の本文
            text_content: テキスト形式の本文
            
        Returns:
            送信成功時True、失敗時False
        """
        if not recipients:
            logger.warning("送信先メールアドレスが設定されていません")
            return False
        
        try:
            # メッセージの作成
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = ", ".join(recipients)
            
            # テキストパートとHTMLパートを追加
            text_part = MIMEText(text_content, "plain", "utf-8")
            html_part = MIMEText(html_content, "html", "utf-8")
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # SMTP接続と送信
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"メールを送信しました: {', '.join(recipients)}")
            return True
            
        except Exception as e:
            logger.error(f"メール送信に失敗しました: {e}")
            return False


def format_weekly_report_html(
    start_date: str,
    end_date: str,
    total_articles: int,
    top_topics: List[dict],
    categorized: dict,
) -> str:
    """
    週次レポートのHTML形式を生成する。
    
    Args:
        start_date: 開始日
        end_date: 終了日
        total_articles: 総記事数
        top_topics: 注目トピックのリスト
        categorized: カテゴリ別記事情報
        
    Returns:
        HTML形式の文字列
    """
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: 'Hiragino Sans', 'Meiryo', sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .summary {{ background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .topic {{ margin: 15px 0; padding: 15px; background: #fff; border-left: 4px solid #3498db; }}
        .category {{ margin: 20px 0; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>DXニュース週次レポート</h1>
        <div class="summary">
            <p><strong>期間:</strong> {start_date} 〜 {end_date}</p>
            <p><strong>総記事数:</strong> {total_articles}件</p>
        </div>
        
        <h2>🎯 今週の注目トピック</h2>
"""
    
    for i, topic in enumerate(top_topics[:3], 1):
        html += f"""
        <div class="topic">
            <h3>{i}. {topic['title']}</h3>
            <p>{topic['summary']}</p>
            <p><a href="{topic['link']}">詳細を読む →</a></p>
        </div>
"""
    
    html += """
        <h2>📊 カテゴリ別記事数</h2>
        <div class="category">
"""
    
    for category, count in categorized.items():
        html += f"            <p><strong>{category}:</strong> {count}件</p>\n"
    
    html += """
        </div>
        
        <div class="footer">
            <p>このメールは自動送信されています。</p>
            <p>配信停止をご希望の場合は、管理者までご連絡ください。</p>
        </div>
    </div>
</body>
</html>
"""
    return html


def format_weekly_report_text(
    start_date: str,
    end_date: str,
    total_articles: int,
    top_topics: List[dict],
    categorized: dict,
) -> str:
    """
    週次レポートのテキスト形式を生成する。
    
    Args:
        start_date: 開始日
        end_date: 終了日
        total_articles: 総記事数
        top_topics: 注目トピックのリスト
        categorized: カテゴリ別記事情報
        
    Returns:
        テキスト形式の文字列
    """
    text = f"""DXニュース週次レポート
{'=' * 50}

期間: {start_date} 〜 {end_date}
総記事数: {total_articles}件

今週の注目トピック
{'-' * 30}

"""
    
    for i, topic in enumerate(top_topics[:3], 1):
        text += f"{i}. {topic['title']}\n"
        text += f"   {topic['summary']}\n"
        text += f"   詳細: {topic['link']}\n\n"
    
    text += f"\nカテゴリ別記事数\n{'-' * 30}\n"
    
    for category, count in categorized.items():
        text += f"{category}: {count}件\n"
    
    text += "\n" + "=" * 50 + "\n"
    text += "このメールは自動送信されています。\n"
    text += "配信停止をご希望の場合は、管理者までご連絡ください。\n"
    
    return text
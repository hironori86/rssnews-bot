"""
utils/line_sender.py

LINE Messaging APIを使用してメッセージを送信するモジュール。
"""

from __future__ import annotations

import json
import logging
from typing import List

import requests

logger = logging.getLogger(__name__)


class LineSender:
    """LINE Messaging APIを使用してメッセージを送信するクラス。"""
    
    def __init__(self, channel_access_token: str) -> None:
        """
        コンストラクタ。
        
        Args:
            channel_access_token: LINE Messaging APIのチャンネルアクセストークン
        """
        self.channel_access_token = channel_access_token
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {channel_access_token}"
        }
        self.broadcast_url = "https://api.line.me/v2/bot/message/broadcast"
        self.push_url = "https://api.line.me/v2/bot/message/push"
    
    def send_weekly_report(
        self,
        start_date: str,
        end_date: str,
        total_articles: int,
        top_topics: List[dict],
        categorized: dict,
        teams_markdown: str,
        user_id: str | None = None,
    ) -> bool:
        """
        週次レポートをLINEで送信する。
        
        Args:
            start_date: 開始日
            end_date: 終了日
            total_articles: 総記事数
            top_topics: 注目トピックのリスト
            categorized: カテゴリ別記事数
            teams_markdown: Teams通知の内容
            user_id: 特定のユーザーに送信する場合のユーザーID（Noneの場合はブロードキャスト）
            
        Returns:
            送信成功時True、失敗時False
        """
        try:
            messages = self._create_weekly_report_messages(
                start_date, end_date, total_articles, top_topics, categorized, teams_markdown
            )
            
            if user_id:
                # 特定のユーザーに送信
                payload = {
                    "to": user_id,
                    "messages": messages
                }
                response = requests.post(self.push_url, headers=self.headers, json=payload)
            else:
                # 全体にブロードキャスト
                payload = {"messages": messages}
                response = requests.post(self.broadcast_url, headers=self.headers, json=payload)
            
            if response.status_code == 200:
                logger.info("LINEメッセージを送信しました")
                return True
            else:
                logger.error(f"LINE送信エラー: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"LINE送信に失敗しました: {e}")
            return False
    
    def _create_weekly_report_messages(
        self,
        start_date: str,
        end_date: str,
        total_articles: int,
        top_topics: List[dict],
        categorized: dict,
        teams_markdown: str,
    ) -> List[dict]:
        """
        週次レポートのLINEメッセージを作成する。
        
        Args:
            start_date: 開始日
            end_date: 終了日
            total_articles: 総記事数
            top_topics: 注目トピックのリスト
            categorized: カテゴリ別記事数
            teams_markdown: Teams通知の内容
            
        Returns:
            LINEメッセージオブジェクトのリスト
        """
        # Flex Messageを作成
        flex_message = {
            "type": "flex",
            "altText": f"DXニュース週次レポート（{start_date}〜{end_date}）",
            "contents": {
                "type": "bubble",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "📊 DXニュース週次レポート",
                            "weight": "bold",
                            "size": "lg",
                            "color": "#1e88e5"
                        },
                        {
                            "type": "text",
                            "text": f"{start_date} 〜 {end_date}",
                            "size": "sm",
                            "color": "#666666",
                            "margin": "sm"
                        }
                    ]
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "総記事数",
                                    "color": "#666666",
                                    "flex": 3
                                },
                                {
                                    "type": "text",
                                    "text": f"{total_articles}件",
                                    "weight": "bold",
                                    "flex": 2
                                }
                            ]
                        },
                        {
                            "type": "separator",
                            "margin": "lg"
                        },
                        {
                            "type": "text",
                            "text": "🎯 今週の注目トピック",
                            "weight": "bold",
                            "size": "md",
                            "margin": "lg"
                        }
                    ]
                }
            }
        }
        
        # 注目トピックを追加
        for i, topic in enumerate(top_topics[:3], 1):
            topic_box = {
                "type": "box",
                "layout": "vertical",
                "margin": "lg",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{i}. {topic['title']}",
                        "weight": "bold",
                        "size": "sm",
                        "wrap": True
                    }
                ]
            }
            flex_message["contents"]["body"]["contents"].append(topic_box)
        
        # フッターを追加
        flex_message["contents"]["footer"] = {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "uri",
                        "label": "詳細を見る",
                        "uri": "https://example.com"  # 実際のレポートURLに置き換え
                    },
                    "style": "primary",
                    "color": "#1e88e5"
                }
            ]
        }
        
        # Teamsマークダウンをテキストに変換
        text_content = convert_markdown_to_text(teams_markdown)
        
        # LINEの文字数制限に対応（5000文字）
        if len(text_content) > 4900:
            text_content = text_content[:4900] + "\n\n...（省略）"
        
        # カテゴリ別記事数をFlex Messageに追加
        category_contents = []
        for category, count in categorized.items():
            category_contents.append({
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": category,
                        "color": "#666666",
                        "flex": 3
                    },
                    {
                        "type": "text",
                        "text": f"{count}件",
                        "flex": 2
                    }
                ],
                "margin": "sm"
            })
        
        # Flex Messageにカテゴリ情報を追加
        flex_message["contents"]["body"]["contents"].insert(2, {
            "type": "text",
            "text": "📋 カテゴリ別記事数",
            "weight": "bold",
            "size": "md",
            "margin": "lg"
        })
        for cat_content in category_contents:
            flex_message["contents"]["body"]["contents"].insert(3, cat_content)
        
        # テキストメッセージはTeamsと同じ内容を送信
        text_message = {
            "type": "text",
            "text": text_content
        }
        
        return [flex_message, text_message]


def send_simple_notification(
    channel_access_token: str,
    message: str,
    user_id: str | None = None,
) -> bool:
    """
    シンプルなテキストメッセージを送信する。
    
    Args:
        channel_access_token: LINE Messaging APIのチャンネルアクセストークン
        message: 送信するメッセージ
        user_id: 特定のユーザーに送信する場合のユーザーID
        
    Returns:
        送信成功時True、失敗時False
    """
    sender = LineSender(channel_access_token)
    
    messages = [{"type": "text", "text": message}]
    
    try:
        if user_id:
            payload = {"to": user_id, "messages": messages}
            url = sender.push_url
        else:
            payload = {"messages": messages}
            url = sender.broadcast_url
        
        response = requests.post(url, headers=sender.headers, json=payload)
        
        if response.status_code == 200:
            logger.info("LINEメッセージを送信しました")
            return True
        else:
            logger.error(f"LINE送信エラー: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"LINE送信に失敗しました: {e}")
        return False


def convert_markdown_to_text(markdown_text: str) -> str:
    """
    MarkdownテキストをLINE用のプレーンテキストに変換する。
    
    Args:
        markdown_text: Markdown形式のテキスト
        
    Returns:
        変換されたプレーンテキスト
    """
    import re
    
    text = markdown_text
    
    # マークダウンリンクをテキストに変換 [text](url) -> text: url
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1: \2', text)
    
    # マークダウンのヘッダーを削除
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # 太字を取り除く
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    
    # 空行を整理
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text.strip()
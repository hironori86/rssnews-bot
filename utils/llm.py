"""
utils/llm.py

OpenAI の Chat API を利用するためのラッパーを提供するモジュール。
ニュース記事の要約やソーシャルメディア投稿の文案生成を担う。リトライや
レート制限の考慮を行い、インターフェースをシンプルに保つ。
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List

from openai import OpenAI


logger = logging.getLogger(__name__)


class LLMClient:
    """OpenAI Chat API クライアントのラッパークラス。"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        """
        コンストラクタ。API キーとモデル名を設定する。

        Args:
            api_key: OpenAI の API キー。
            model: 利用するモデル名。デフォルトは gpt-4o-mini。
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def _chat(self, messages: List[dict], max_tokens: int = 512, temperature: float = 0.7, retries: int = 3) -> str:
        """
        OpenAI Chat API への汎用呼び出し。

        Args:
            messages: ChatGPT 形式のメッセージリスト。
            max_tokens: レスポンスの最大トークン数。
            temperature: 出力の多様性を制御する温度パラメータ。
            retries: レート制限時などにリトライする回数。

        Returns:
            生成された文字列。

        Raises:
            Exception: API 呼び出しに失敗した場合。
        """
        for attempt in range(retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                content: str = response.choices[0].message.content  # type: ignore[union-attr]
                return content.strip() if content else ""
            except Exception as e:
                if "rate_limit" in str(e).lower():
                    wait_time = 2 ** attempt
                    logger.warning("Rate limit に達しました。%s 秒後に再試行します。", wait_time)
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error("OpenAI API 呼び出しに失敗しました: %s", e)
                    time.sleep(1)
                    continue
        raise RuntimeError("OpenAI API からの応答を取得できませんでした")

    def summarize(self, text: str, max_chars: int = 200) -> str:
        """
        ニュース記事のテキストを指定した文字数以内で日本語要約する。

        Args:
            text: 要約対象のテキスト。
            max_chars: 要約結果の最大文字数。

        Returns:
            要約された日本語テキスト。
        """
        system_prompt = "あなたは有能な編集者です。ユーザーが提供するニュース記事を指定された文字数以内で日本語に要約してください。"
        user_prompt = (
            f"次のニュース記事を{max_chars}字以内で日本語で要約してください.\n\n"
            f"記事: {text}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        # 文字数指定はプロンプトで行い、max_tokens は大きめに設定
        return self._chat(messages, max_tokens=256, temperature=0.3)

    def generate_weekly_tweet(self, articles: List[Dict[str, str]], top_topics: List[str], start_date: str, end_date: str) -> str:
        """
        週次サマリー形式のツイート案を生成する。

        Args:
            articles: 週間の記事リスト
            top_topics: 注目トピックのタイトルリスト
            start_date: 期間開始日
            end_date: 期間終了日

        Returns:
            280 文字以内のツイート案。
        """
        system_prompt = (
            "あなたはバズるコンテンツを生み出すSNSマーケティングのエキスパートです。"
            "毎週フォローしたくなるような魅力的な週次レポートを作成します。"
        )
        
        topics_text = "\n".join([f"- {topic}" for topic in top_topics[:3]])
        
        user_prompt = (
            f"{start_date}〜{end_date}のDXニュース週次レポートを作成してください。\n\n"
            f"総記事数: {len(articles)}件\n\n"
            f"注目トピック:\n{topics_text}\n\n"
            "以下のポイントを意識してください：\n"
            "1. 「今週のDXニュース！」のようなキャッチーな出だし\n"
            "2. 注目トピックを分かりやすく紹介\n"
            "3. 「毎週見たい！」と思わせる表現\n"
            "4. 詳細はリンク先で確認できることを示唆\n"
            "5. ハッシュタグ: #DX週報 #AIニュース など\n\n"
            "280文字以内で作成してください。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self._chat(messages, max_tokens=200, temperature=0.8)
    
    def generate_daily_tweet(self, articles: List[Dict[str, str]], top_topics: List[str], date: str) -> str:
        """
        日次サマリー形式のツイート案を生成する。

        Args:
            articles: 日間の記事リスト
            top_topics: 注目トピックのタイトルリスト
            date: 対象日

        Returns:
            280 文字以内のツイート案。
        """
        system_prompt = (
            "あなたはバズるコンテンツを生み出すSNSマーケティングのエキスパートです。"
            "毎日フォロワーが楽しみにする魅力的な日次レポートを作成します。"
        )
        
        topics_text = "\n".join([f"- {topic}" for topic in top_topics[:2]])
        
        user_prompt = (
            f"{date}のDXニュース日次レポートを作成してください。\n\n"
            f"総記事数: {len(articles)}件\n\n"
            f"注目トピック:\n{topics_text}\n\n"
            "以下のポイントを意識してください：\n"
            "1. 「今日のDXニュース！」のようなキャッチーな出だし\n"
            "2. 注目トピックを分かりやすく紹介\n"
            "3. 「毎日チェック！」と思わせる表現\n"
            "4. 詳細はリンク先で確認できることを示唆\n"
            "5. ハッシュタグ: #DX日報 #AIニュース など\n\n"
            "280文字以内で作成してください。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self._chat(messages, max_tokens=200, temperature=0.8)
    
    def generate_tweet(self, title: str, summary: str) -> str:
        """
        記事情報から 280 文字以内の日本語ツイート案を生成する。

        Args:
            title: ニュースのタイトル。
            summary: 記事の短い要約。

        Returns:
            280 文字以内のツイート案。
        """
        system_prompt = (
            "あなたはバズるコンテンツを生み出すSNSマーケティングのエキスパートです。"
            "読者の知的好奇心を刺激し、思わずクリックしたくなるツイートを作成します。"
        )
        user_prompt = (
            "以下のニュースに基づいて、読者が思わず詳細を知りたくなるような魅力的なツイートを作成してください。\n\n"
            "以下のポイントを意識してください：\n"
            "1. 出だしでインパクトを与える\n"
            "2. 数字や具体的な事実を含める\n"
            "3. 読者にとってのメリットを明確に示す\n"
            "4. 驚きや新しい発見を強調\n"
            "5. エモーショナルな表現を適度に使用\n"
            "6. ハッシュタグは2～3個、トレンドを意識\n\n"
            "280文字以内で作成してください。\n\n"
            f"タイトル: {title}\n要約: {summary}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self._chat(messages, max_tokens=200, temperature=0.8)

    def select_featured_articles(
        self, 
        articles: List[Dict[str, str]], 
        summaries: Dict[str, str],
        categorized: Dict[str, List[Dict[str, str]]],
        count: int = 3
    ) -> List[Dict[str, str]]:
        """
        重要度と関心度に基づいて厳選した記事を選択する。
        
        Args:
            articles: 全記事リスト
            summaries: 記事の要約
            categorized: カテゴリ別記事
            count: 選択する記事数
            
        Returns:
            厳選された記事のリスト
        """
        # 各記事にスコアを付与
        scored_articles = []
        
        for article in articles:
            title = article.get("title", "")
            link = article.get("link", "")
            summary = summaries.get(link, "")
            
            # 重要度スコア計算
            importance_score = self._calculate_importance_score(title, summary)
            
            # 関心度スコア計算
            interest_score = self._calculate_interest_score(title, summary)
            
            # 総合スコア
            total_score = importance_score + interest_score
            
            scored_articles.append({
                **article,
                "importance_score": importance_score,
                "interest_score": interest_score,
                "total_score": total_score,
                "summary": summary
            })
        
        # スコア順にソートして上位を選択
        scored_articles.sort(key=lambda x: x["total_score"], reverse=True)
        return scored_articles[:count]
    
    def _calculate_importance_score(self, title: str, summary: str) -> float:
        """記事の重要度スコアを計算する"""
        text = f"{title} {summary}".lower()
        score = 0.0
        
        # 重要度の高いキーワード
        high_impact_keywords = [
            "breakthrough", "革新", "革命", "画期的", "大幅", "劇的",
            "新記録", "世界初", "業界初", "前例のない", "史上最大",
            "市場を変える", "ゲームチェンジャー", "パラダイムシフト"
        ]
        
        # 技術的重要度キーワード
        tech_importance = [
            "ai", "人工知能", "機械学習", "deep learning", "ディープラーニング",
            "自動化", "効率化", "生産性", "コスト削減", "売上向上",
            "セキュリティ", "プライバシー", "データ保護"
        ]
        
        # 企業・市場インパクト
        business_impact = [
            "企業", "市場", "業界", "経済", "投資", "資金調達",
            "上場", "買収", "合弁", "パートナーシップ", "戦略"
        ]
        
        for keyword in high_impact_keywords:
            if keyword in text:
                score += 3.0
                
        for keyword in tech_importance:
            if keyword in text:
                score += 2.0
                
        for keyword in business_impact:
            if keyword in text:
                score += 1.5
        
        return score
    
    def _calculate_interest_score(self, title: str, summary: str) -> float:
        """記事の関心度スコアを計算する"""
        text = f"{title} {summary}".lower()
        score = 0.0
        
        # 話題性キーワード
        trending_keywords = [
            "話題", "注目", "人気", "バズる", "トレンド", "流行",
            "ソーシャル", "sns", "twitter", "話題沸騰"
        ]
        
        # 実用性キーワード
        practical_keywords = [
            "活用", "利用", "使える", "便利", "簡単", "手軽",
            "導入", "実装", "実践", "応用", "活かす"
        ]
        
        # 未来性キーワード
        future_keywords = [
            "次世代", "将来", "未来", "展望", "予測", "期待",
            "可能性", "ポテンシャル", "発展", "成長"
        ]
        
        for keyword in trending_keywords:
            if keyword in text:
                score += 2.5
                
        for keyword in practical_keywords:
            if keyword in text:
                score += 2.0
                
        for keyword in future_keywords:
            if keyword in text:
                score += 1.5
        
        return score

    def generate_weekly_note_article(
        self, 
        articles: List[Dict[str, str]], 
        top_topics: List[Dict[str, str]], 
        start_date: str, 
        end_date: str,
        categorized: Dict[str, List[Dict[str, str]]] | None = None,
        summaries: Dict[str, str] | None = None,
        min_chars: int = 2000, 
        max_chars: int = 3000
    ) -> str:
        """
        週次サマリー形式のnote記事案を生成する。

        Args:
            articles: 週間の記事リスト
            top_topics: 注目トピックの詳細情報（後方互換性のため保持）
            start_date: 期間開始日
            end_date: 期間終了日
            categorized: カテゴリ別記事
            summaries: 記事の要約
            min_chars: 記事の最小文字数
            max_chars: 記事の最大文字数

        Returns:
            note 向けの記事本文（日本語）。
        """
        # 厳選された記事を選択
        if summaries and categorized:
            featured_articles = self.select_featured_articles(articles, summaries, categorized, count=3)
        else:
            # 後方互換性のため従来の方法を使用
            featured_articles = top_topics[:3] if top_topics else []
        
        system_prompt = (
            "あなたは読者が毎週楽しみにするテクノロジーライターです。"
            "週次DXニュースレポートを魅力的にまとめ、読者にとって価値ある情報を提供します。"
            "記事には必ず元記事のリンクを含めて、読者が詳細を確認できるようにしてください。"
        )
        
        # 厳選記事の詳細情報（リンク付き）
        featured_text = ""
        for i, article in enumerate(featured_articles, 1):
            title = article.get("title", "")
            link = article.get("link", "")
            summary = article.get("summary", "")
            featured_text += f"{i}. {title}\n   概要: {summary}\n   📰 記事詳細: {link}\n\n"
        
        # カテゴリ別記事一覧の作成（リンク付き）
        category_lists = ""
        if categorized:
            for category in ["最新技術動向", "導入・活用事例", "その他"]:
                articles_in_category = categorized.get(category, [])
                if articles_in_category:
                    category_lists += f"\n### {category} ({len(articles_in_category)}件)\n"
                    for article in articles_in_category:
                        title = article.get("title", "")
                        link = article.get("link", "")
                        category_lists += f"- [{title}]({link})\n"
        
        user_prompt = (
            f"{start_date}〜{end_date}の週次DXニュースレポートを作成してください。\n\n"
            f"今週の総記事数: {len(articles)}件\n\n"
            f"厳選された注目トピック（詳細説明が必要）:\n{featured_text}\n"
            f"その他のニュース一覧（カテゴリ別）:\n{category_lists}\n\n"
            "記事作成のポイント：\n"
            "1. 「今週のDXニュース！盛りだくさんの最新トピックをお届け！」のようなキャッチーな導入\n"
            "2. 総記事数と厳選した3つのトピックについて触れる\n"
            "3. 厳選された3つのトピックを詳しく解説（各トピックに見出しを付け、必ず元記事リンクを含める）\n"
            "4. 各トピックがなぜ重要か、読者にとってのメリットを明確に説明\n"
            "5. 記事の最後に「---」で区切り線を入れる\n"
            "6. その他のニュース一覧をカテゴリ別に表示（リンク付き）\n"
            "7. 「来週もお楽しみに！」で締めくくり、定期購読を促す\n"
            "8. noteでそのまま投稿できるよう、適切な見出し（##、###）とマークダウン形式を使用\n"
            "9. 各記事のリンクは「詳細はこちら → [記事タイトル](URL)」形式で表示\n\n"
            "構成：\n"
            "- 導入（今週のニュースの概要）\n"
            "- 厳選トピック1（詳細説明 + リンク）\n"
            "- 厳選トピック2（詳細説明 + リンク）\n"
            "- 厳選トピック3（詳細説明 + リンク）\n"
            "- 区切り線（---）\n"
            "- その他ニュース一覧（カテゴリ別、リンク付き）\n"
            "- 締めくくり\n\n"
            f"{min_chars}字から{max_chars}字の間で作成してください。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self._chat(messages, max_tokens=3000, temperature=0.7)
    
    def generate_note_article(self, title: str, summary: str, link: str = "", min_chars: int = 800, max_chars: int = 1200) -> str:
        """
        note 向けの記事案を生成する。指定した文字数範囲で日本語記事を作成する。

        Args:
            title: トピックのタイトル。
            summary: トピックの要約情報。
            link: 元記事のURL。
            min_chars: 記事の最小文字数。
            max_chars: 記事の最大文字数。

        Returns:
            note 向けの記事本文（日本語）。
        """
        system_prompt = (
            "あなたは読者を惹きつけるプロのテクノロジーライターです。"
            "読者が最後まで読みたくなる、価値あるコンテンツを作成します。"
            "記事には必ず元記事のリンクを含めて、読者が詳細を確認できるようにしてください。"
        )
        
        # リンク情報
        link_info = f"\n📰 元記事: {link}" if link else ""
        
        user_prompt = (
            "以下のニュースに基づいて、noteに投稿する魅力的な記事を作成してください。\n\n"
            "記事作成のポイント：\n"
            "1. キャッチーなタイトルと導入で読者の興味を引く\n"
            "2. 読者にとっての具体的なメリットや影響を明示\n"
            "3. 専門用語を避け、初心者でも理解できるように説明\n"
            "4. 具体的な例や活用シーンを交えて説明\n"
            "5. 読者のアクションを促す結論で締めくくる\n"
            "6. 適度に改行を入れて読みやすく\n"
            "7. noteでそのまま投稿できるよう、適切な見出し（##、###）とマークダウン形式を使用\n"
            "8. 記事の最後に「詳細はこちら → [記事タイトル](URL)」形式で元記事リンクを表示\n\n"
            "構成：\n"
            "- イントロ（興味を引く導入）\n"
            "- 本文（詳細説明、メリット、活用例）\n"
            "- 結論（まとめと今後の展望）\n"
            "- 元記事へのリンク\n\n"
            f"{min_chars}字から{max_chars}字の間で作成してください。\n\n"
            f"タイトル: {title}\n概要: {summary}{link_info}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self._chat(messages, max_tokens=1500, temperature=0.7)
    
    def generate_daily_note_article(
        self, 
        articles: List[Dict[str, str]], 
        top_topics: List[Dict[str, str]], 
        date: str,
        categorized: Dict[str, List[Dict[str, str]]] | None = None,
        summaries: Dict[str, str] | None = None,
        min_chars: int = 1000, 
        max_chars: int = 2000
    ) -> str:
        """
        日次サマリー形式のnote記事案を生成する。

        Args:
            articles: 日間の記事リスト
            top_topics: 注目トピックの詳細情報
            date: 対象日
            categorized: カテゴリ別記事
            summaries: 記事の要約
            min_chars: 記事の最小文字数
            max_chars: 記事の最大文字数

        Returns:
            note 向けの記事本文（日本語）。
        """
        system_prompt = (
            "あなたは読者が毎日楽しみにするテクノロジーライターです。"
            "日次DXニュースレポートを魅力的にまとめ、読者にとって価値ある情報を提供します。"
            "記事には必ず元記事のリンクを含めて、読者が詳細を確認できるようにしてください。"
        )
        
        # 注目記事の詳細情報（リンク付き）
        featured_text = ""
        for i, article in enumerate(top_topics[:2], 1):
            title = article.get("title", "")
            link = article.get("link", "")
            summary = article.get("summary", "")
            featured_text += f"{i}. {title}\n   概要: {summary}\n   📰 記事詳細: {link}\n\n"
        
        # カテゴリ別記事一覧の作成（リンク付き）
        category_lists = ""
        if categorized:
            for category in ["最新技術動向", "導入・活用事例", "その他"]:
                articles_in_category = categorized.get(category, [])
                if articles_in_category:
                    category_lists += f"\n### {category} ({len(articles_in_category)}件)\n"
                    for article in articles_in_category:
                        title = article.get("title", "")
                        link = article.get("link", "")
                        category_lists += f"- [{title}]({link})\n"
        
        user_prompt = (
            f"{date}の日次DXニュースレポートを作成してください。\n\n"
            f"今日の総記事数: {len(articles)}件\n\n"
            f"注目トピック（詳細説明が必要）:\n{featured_text}\n"
            f"その他のニュース一覧（カテゴリ別）:\n{category_lists}\n\n"
            "記事作成のポイント：\n"
            "1. 「今日のDXニュース！最新情報をお届け！」のようなキャッチーな導入\n"
            "2. 総記事数と注目トピックについて触れる\n"
            "3. 注目トピックを詳しく解説（各トピックに見出しを付け、必ず元記事リンクを含める）\n"
            "4. 各トピックがなぜ重要か、読者にとってのメリットを明確に説明\n"
            "5. 記事の最後に「---」で区切り線を入れる\n"
            "6. その他のニュース一覧をカテゴリ別に表示（リンク付き）\n"
            "7. 「明日もお楽しみに！」で締めくくり、継続購読を促す\n"
            "8. noteでそのまま投稿できるよう、適切な見出し（##、###）とマークダウン形式を使用\n"
            "9. 各記事のリンクは「詳細はこちら → [記事タイトル](URL)」形式で表示\n\n"
            "構成：\n"
            "- 導入（今日のニュースの概要）\n"
            "- 注目トピック1（詳細説明 + リンク）\n"
            "- 注目トピック2（詳細説明 + リンク）\n"
            "- 区切り線（---）\n"
            "- その他ニュース一覧（カテゴリ別、リンク付き）\n"
            "- 締めくくり\n\n"
            f"{min_chars}字から{max_chars}字の間で作成してください。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self._chat(messages, max_tokens=2000, temperature=0.7)

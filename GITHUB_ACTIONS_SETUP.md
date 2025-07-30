# GitHub Actions 自動実行セットアップガイド

## 概要

このガイドでは、GitHub Actionsを使用してDXニュース収集を自動化する方法を説明します。

## セットアップ手順

### 1. リポジトリの準備

```bash
# リポジトリをGitHubにプッシュ
git add .
git commit -m "Add GitHub Actions workflows"
git push origin main
```

### 2. GitHub Secrets の設定

GitHubリポジトリの設定から、以下のSecretsを追加してください：

**Settings > Secrets and variables > Actions > New repository secret**

#### 必須設定

| Secret名 | 説明 | 例 |
|---------|------|-----|
| `OPENAI_API_KEY` | OpenAI APIキー | `sk-...` |
| `RSS_FEEDS` | RSSフィードURL（カンマ区切り） | `https://example.com/feed1,https://example.com/feed2` |
| `KEYWORDS` | 検索キーワード（カンマ区切り） | `DX,AI,デジタル,自動化` |

#### オプション設定

| Secret名 | 説明 | 設定例 |
|---------|------|-------|
| `TEAM_WEBHOOK_URL` | Microsoft Teams Webhook URL | `https://outlook.office.com/webhook/...` |
| `TWITTER_BEARER_TOKEN` | X(Twitter) Bearer Token | `AAAA...` |
| `NOTE_TOKEN` | note APIトークン | `note_token_...` |
| `SMTP_SERVER` | メールサーバー | `smtp.gmail.com` |
| `SMTP_PORT` | SMTPポート | `587` |
| `SMTP_USERNAME` | メールユーザー名 | `your-email@gmail.com` |
| `SMTP_PASSWORD` | メールパスワード | `your-app-password` |
| `FROM_EMAIL` | 送信者メールアドレス | `your-email@gmail.com` |
| `EMAIL_RECIPIENTS` | 受信者リスト（カンマ区切り） | `user1@example.com,user2@example.com` |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot Channel Access Token | `LINE_TOKEN_...` |
| `LINE_USER_IDS` | LINE User ID（カンマ区切り） | `USER_ID_1,USER_ID_2` |

### 3. ワークフローの有効化

1. GitHubリポジトリの **Actions** タブに移動
2. ワークフローが表示されていることを確認
3. 必要に応じて **Enable workflow** をクリック

## 実行スケジュール

### 日次実行（Daily DX News Collection）
- **実行時刻**: 毎日朝8時（JST）
- **内容**: 
  - 前日のニュースを収集
  - 日次ツイート・note記事案を生成
  - Teams通知（設定時）
  - 生成ファイルをArtifactsに保存

### 週次実行（Weekly DX News Summary）
- **実行時刻**: 毎週日曜日夜10時（JST）
- **内容**:
  - 過去7日分の日次データを統合
  - 週間ツイート・note記事案を生成
  - 重複記事の除去
  - 週間サマリーをArtifactsに保存

## 手動実行

### 日次ニュース収集の手動実行

1. **Actions** タブ → **Daily DX News Collection**
2. **Run workflow** をクリック
3. オプション設定:
   - **SNSに実際に投稿するか**: `false`（テスト）/ `true`（本番投稿）

### 週間サマリーの手動実行

1. **Actions** タブ → **Weekly DX News Summary**
2. **Run workflow** をクリック
3. オプション設定:
   - **対象とする日数**: デフォルト `7`

## 生成ファイルのダウンロード

### Artifactsからのダウンロード

1. **Actions** タブ → 実行結果をクリック
2. **Artifacts** セクションからファイルをダウンロード
   - `daily-news-XXX`: 日次生成ファイル
   - `weekly-summary-XXX`: 週間生成ファイル

### ファイル構造

```
downloaded-artifacts/
├── tweets/
│   └── tweet_01.txt          # ツイート案
├── notes/
│   └── note_01_今日のDX....md  # note記事案（コピペ可能）
└── summary.json              # 実行結果サマリー
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. ワークフローが実行されない
- **確認点**:
  - GitHub Actionsが有効になっているか
  - 必須のSecretsが設定されているか
  - リポジトリにワークフローファイルがコミットされているか

#### 2. OpenAI APIエラー
- **確認点**:
  - `OPENAI_API_KEY` が正しく設定されているか
  - APIクォータが残っているか
  - APIキーに必要な権限があるか

#### 3. RSS取得エラー
- **確認点**:
  - `RSS_FEEDS` のURLが有効か
  - フィードが正常に配信されているか
  - ネットワーク接続に問題がないか

#### 4. 週間サマリーでデータがない
- **確認点**:
  - 過去7日間に日次実行が成功しているか
  - Artifactsが正常に保存されているか

### ログの確認方法

1. **Actions** タブ → 失敗した実行をクリック
2. 各ステップをクリックしてログを確認
3. エラーメッセージから原因を特定

### デバッグ方法

```bash
# ローカルでテスト実行
python main.py --run-now

# 週間生成のテスト
python weekly_generator.py --days 3
```

## セキュリティ注意事項

### Secretsの管理
- APIキーは絶対にコードにハードコーディングしない
- Secretsは必要最小限の権限で設定
- 定期的にAPIキーをローテーション

### リポジトリの設定
- プライベートリポジトリを使用することを推奨
- 必要に応じてブランチ保護ルールを設定

## 監視とメンテナンス

### 定期チェック項目
- [ ] 日次実行が正常に動作しているか
- [ ] 生成されるコンテンツの品質
- [ ] APIクォータの使用量
- [ ] エラーログの確認

### 月次メンテナンス
- [ ] 古いArtifactsの整理
- [ ] 設定の見直し
- [ ] パフォーマンスの確認

## カスタマイズ

### 実行時刻の変更

`.github/workflows/daily-news.yml` の cron 式を編集：

```yaml
# 現在: 毎日朝8時（JST）
- cron: '0 23 * * *'

# 例: 毎日朝6時（JST）に変更
- cron: '0 21 * * *'
```

### 対象日数の変更

週間サマリーの対象日数を変更する場合：

```yaml
# weekly-news.yml の default 値を変更
default: '5'  # 5日分に変更
```

## サポート

問題が発生した場合は、以下を確認してください：

1. GitHub Actionsのログ
2. Secretsの設定
3. 依存関係の更新
4. APIの制限・変更

詳細なログとエラー情報は、実行結果のArtifactsに含まれています。
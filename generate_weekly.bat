@echo off
REM 週間ニュース生成バッチスクリプト

echo 週間ニュースを生成しています...
python weekly_generator.py --days 7 --output-dir outputs

if %errorlevel% equ 0 (
    echo 週間ニュースの生成が完了しました！
    echo 出力フォルダをチェックしてください。
) else (
    echo エラーが発生しました。ログを確認してください。
)

pause
\# Cookie Tool 実験記録



---



\## 実験日: 2025-07-30

\### 対象サイト: N/A（初期準備）

\### 実施内容:

\- GitHub リポジトリ作成

\- cookie-tool プロジェクト初期化（`git init`, `.venv` 作成）

\- `README.md` テンプレート作成



\#### ✅ 観察結果:

\- ローカル環境構築完了

\- GitHub との push 成功



---



\## 実験日: 2025-08-01

\### 対象サイト: N/A（基盤整備）

\### 実施内容:

\- `extractor/`・`importer/` ディレクトリ作成

\- Selenium による Chrome 起動確認

\- `cookie\_extractor.py` の初期動作確認



\#### ✅ 観察結果:

\- Chrome の headless 起動も確認

\- コマンドラインからの Python 実行問題なし



---



\## 実験日: 2025-08-02

\### 対象サイト: https://www.google.com

\### 実施内容:

\- `cookie\_extractor.py` にて Google へアクセスし cookie を取得

\- `output/` ディレクトリへ JSON 保存確認



\#### ✅ 観察結果:

\- `output/cookies\_www.google.com.json` ファイル生成成功

\- cookie 情報は形式通り保存されていた



---



\## 実験日: 2025-08-03

\### 対象サイト: https://www.google.com

\### 実施内容:

\- `cookie\_importer.py` を作成し、前日の cookie を使用してインポートテスト



\#### ✅ 観察結果:

\- 再読み込み時に Cookie は適用された様子（エラーなし）

\- ただし、Google ログイン状態は保持されず（要再ログイン）



\#### 💬 考察:

\- `HttpOnly` や `Secure` 属性の cookie は `add\_cookie()` では反映されない可能性

\- 再読み込み後も cookie がセッションベースで期限切れになることがある



---



\## 実験日: 2025-08-04

\### 対象サイト: https://www.google.com

\### 実施内容:

\- `extractor`・`importer` 両ファイルにコマンドライン引数対応追加

\- 実験記録ディレクトリ `experiments/` 作成

\- 実験ログ `experiment\_log.md` 初版作成



\#### ✅ 観察結果:

\- `python extractor/cookie\_extractor.py https://www.google.com` にて cookie 抽出成功

\- `python importer/cookie\_importer.py https://www.google.com` にて cookie 適用成功（ログイン状態は保持されず）



\#### 💬 考察:

\- サイトによっては cookie の依存関係が複雑で、ログイン情報のみでのセッション維持は困難

\- 次回は Yahoo、Wikipedia 等への適用も検証予定



## 実験日: 2025-08-04

\### 対象サイト: https://www.google.com

\### 使用ファイル: output/cookies\_www.google.com.json



\#### 🔄 実験ステップ:

1\. extractor にて cookie を取得

2\. importer にて cookie を適用

3\. 同一ブラウザで再度アクセス



\#### ✅ 観察結果:

\- 🔹 Google ページ言語が「日本語」のまま保持

\- 🔸 ログイン状態は保持されず（ログインが必要なまま）



\#### 💬 考察:

\- 一部の cookie（ログイン関連）は `HttpOnly` や `Secure` 属性があり、手動でのセット不可

\- セッション cookie が Chrome のプロセスをまたいで無効になっている可能性

\- 今後の実験ではログイン後の cookie を含めて再検証予定


✅ Experiment Log — BBC Login Cookie Extraction & Import (2025-08-05)
Date: 2025-08-05
User Profile Used: user_bbc_2
Test Domain: https://www.bbc.co.uk/

🔧 Objective
To test whether user login cookies from BBC can be:

Successfully extracted from a Chrome profile where manual login was performed.

Reimported into a fresh browser session via Selenium and restore the login session.

🧪 Procedure
Step	Action
1	Launched Chrome manually using:
chrome.exe --user-data-dir=profiles/user_bbc_2
2	Visited https://www.bbc.co.uk/ and logged in manually
3	Ran:
python extractor/cookie_extractor.py https://www.bbc.co.uk/ user_bbc_2
→ Extracted cookies saved to: output/cookies_www.bbc.co.uk.json
4	Ran:
python importer/cookie_importer.py https://www.bbc.co.uk/ user_bbc_2
→ Cookies loaded into fresh Selenium session
5	Verified: User remained logged in without needing manual login again

✅ Result
Success: Login session was maintained after cookie reimport.

Saved File: output/cookies_www.bbc.co.uk.json

Profile Directory: profiles/user_bbc_2

📝 Notes
Initial Selenium errors were due to Chrome crashing (DevToolsActivePort file doesn't exist).
This was resolved by fully closing all Chrome instances before retrying.

Tested manually by inspecting the DOM to confirm login persistence.

🧩 Tools Used
cookie_extractor.py from extractor/

cookie_importer.py from importer/

Chrome Stable Version: C:\Program Files\Google\Chrome\Application\chrome.exe

Python 3.x + Selenium (venv)

🔄 Next Steps
 Add support for automatic headless login testing

 Test same flow with different domains (e.g., YouTube, Reddit)

 Create cookie diff/merge tool for comparing two sessions

 Log cookie content metadata (e.g., expiration, domain coverage)

これを experiment_log.md として保存・コミットしたい場合、以下を実行してください:

bash
Copy code
mkdir -p logs
echo "[PASTE ABOVE CONTENT HERE]" > logs/experiment_log.md

git add logs/experiment_log.md
git commit -m "Add experiment log: BBC cookie extraction & import success (2025-08-05)"
git push origin main



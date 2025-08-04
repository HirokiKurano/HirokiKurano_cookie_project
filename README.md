# Cookie Extractor Tool

A simple Selenium-based tool to extract cookies from websites.
Outputs cookies as JSON to the output/ folder.



\# 🍪 HirokiKurano Cookie Privacy Project



このプロジェクトは、\*\*WebブラウザやアプリからCookieを抽出・インポート・分析\*\*するためのツールセットを開発し、\*\*オンラインプライバシーの影響を検証\*\*することを目的としています。



---



\## 🗓 プロジェクトスケジュール（2025年 夏）



| 日付       | タスク内容                                                                 |

|------------|------------------------------------------------------------------------------|

| 24 Jun     | テーマの調査・技術的な下調べ（topic familiarity）                           |

| 2 Jul      | Cookie抽出ツールの開発（from browsers or apps）                             |

| 11 Jul     | Cookieインポートツールの開発                                                |

| 18 Jul     | ユーザープロファイルを作成し、Cookieの抽出・切り替えをテスト               |

| 25 Jul     | 特定のCookie（ログイン関連など）の精査・ブロック                             |

| 8 Aug      | 異なるユーザー・ブラウザ間でCookieを混合して実験                             |

| 15 Aug     | プライバシーへの影響を考察・可視化                                           |

| 5 Sep      | 最終レポートのドラフト提出                                                  |

| 12 Sep     | 提出期限（最終版）                                                           |



---



\## 🔧 現在の機能



\- \[x] Chromeから任意サイトのCookieを取得してJSON形式で保存

\- \[ ] Cookieを別ユーザーや別ブラウザへインポート

\- \[ ] Cookieを精査し、フィルタリング・ブロック

\- \[ ] 実験モジュールによるCookieの混合テスト

\- \[ ] プライバシーへの影響分析の可視化とレポート生成



---



\## 📦 セットアップ



```bash

git clone https://github.com/HirokiKurano/HirokiKurano\_cookie\_project.git

cd HirokiKurano\_cookie\_project

pip install -r requirements.txt

🚀 実行方法

bash

Copy code

python extractor/cookie\_extractor.py

取得されたCookieは output/ フォルダに保存されます。



📁 フォルダ構成

bash

Copy code

cookie-tool/

├── extractor/              # Cookie抽出スクリプト

│   └── cookie\_extractor.py

├── output/                 # 出力されたCookieファイル（.gitignore済）

├── requirements.txt        # 依存ライブラリ

├── .gitignore

└── README.md               # このドキュメント

📌 注意点

Chromeがローカルにインストールされている必要があります。



出力ファイルは .gitignore によりGitHubにはアップロードされません。



📚 ライセンス

MIT License © Hiroki Kurano



yaml

Copy code



---



\## ✅【STEP 2】保存と GitHub へのアップロード



メモ帳で保存したあと、以下のコマンドでコミット＆プッシュ：



```bash

git add README.md

git commit -m "Add README with project description"

git push

8月４日追記分

📌 Cookie Extractor & Importer for Chrome
このツールは、Google Chrome で使用されている Cookie を取得・保存し、後で再適用することができる Python ベースのユーティリティです。主に オンラインプライバシーの実験 を目的としています。

🛠 使用方法
1. Cookie 抽出
bash
Copy code
python extractor/cookie_extractor.py
抽出された Cookie は output/cookies_<domain>.json という形式で保存されます。

2. Cookie インポート
bash
Copy code
python importer/cookie_importer.py
保存された Cookie ファイルを自動で読み込み、Chrome に適用して該当サイトを開き直します。

🧪 実験目的と背景
Webサイトごとに異なる Cookie を切り替えて適用することで、ユーザープロファイルの違いをシミュレート

Cookie によるログイン状態や広告表示の変化を確認

プライバシー・トラッキング技術の挙動を検証

📂 ディレクトリ構成
lua
Copy code
cookie-tool/
│
├── extractor/
│   └── cookie_extractor.py
├── importer/
│   └── cookie_importer.py
├── output/
│   └── cookies_google.com.json
├── .gitignore
├── requirements.txt
└── README.md
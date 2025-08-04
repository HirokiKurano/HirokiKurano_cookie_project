\## 実験日: 2025-08-04

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




# importer/cookie_importer.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import time
import sys

# 対象URL（省略時は Google）
url = sys.argv[1] if len(sys.argv) > 1 else "https://www.google.com"
domain = url.split("//")[-1].split("/")[0]
cookie_file = f"output/cookies_{domain}.json"

# Chrome起動設定
options = Options()
options.add_experimental_option("detach", True)  # ブラウザを自動で閉じない
driver = webdriver.Chrome(options=options)

print(f"[INFO] Chrome 起動 & {url} にアクセス中...")
driver.get(url)
time.sleep(3)

# Cookie読み込み
try:
    with open(cookie_file, "r", encoding="utf-8") as f:
        cookies = json.load(f)
except FileNotFoundError:
    print(f"[❌ エラー] Cookie ファイルが見つかりません: {cookie_file}")
    driver.quit()
    sys.exit(1)

# Cookieをセット
driver.delete_all_cookies()
for cookie in cookies:
    try:
        if 'sameSite' in cookie:
            del cookie['sameSite']
        driver.add_cookie(cookie)
    except Exception as e:
        print(f"[WARN] Cookie 無視: {cookie.get('name')} - {e}")

# 再アクセスして Cookie 状態を確認
print("[INFO] Cookie 適用後に再読み込みします...")
driver.get(url)
time.sleep(5)

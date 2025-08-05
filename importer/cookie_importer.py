# importer/cookie_importer.py

import json, os, time, sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

if len(sys.argv) < 3:
    print("使用法: python importer/cookie_importer.py <URL> <プロファイル名>")
    sys.exit(1)

url = sys.argv[1]
profile_name = sys.argv[2]
profile_path = os.path.abspath(f"profiles/{profile_name}")
domain = url.split("//")[-1].split("/")[0]
cookie_file = f"output/cookies_{domain}.json"

options = Options()
options.add_argument(f"--user-data-dir={profile_path}")
options.add_experimental_option("detach", True)

driver = webdriver.Chrome(options=options)
print(f"[INFO] Chrome 起動 & {url} にアクセス中...")
driver.get(url)
time.sleep(3)

if not os.path.exists(cookie_file):
    print(f"[❌ エラー] Cookie ファイルが存在しません: {cookie_file}")
    sys.exit(1)

with open(cookie_file, "r", encoding="utf-8") as f:
    cookies = json.load(f)

driver.delete_all_cookies()
for cookie in cookies:
    try:
        driver.add_cookie(cookie)
    except Exception as e:
        print(f"[WARN] Cookie 無視: {cookie.get('name')} - {e}")

print("[INFO] Cookie 適用後に再読み込みします...")
driver.get(url)

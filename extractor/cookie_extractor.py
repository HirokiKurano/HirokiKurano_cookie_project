# extractor/cookie_extractor.py

import json, os, sys, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

if len(sys.argv) < 3:
    print("使用法: python extractor/cookie_extractor.py <URL> <プロファイル名>")
    sys.exit(1)

url = sys.argv[1]
profile_name = sys.argv[2]
profile_path = os.path.abspath(f"profiles/{profile_name}")
domain = url.split("//")[-1].split("/")[0]
cookie_file = f"output/cookies_{domain}.json"

options = Options()
options.add_argument(f"--user-data-dir={profile_path}")
options.add_experimental_option("detach", True)

print("[INFO] Chrome 起動中...")
driver = webdriver.Chrome(options=options)
driver.get(url)
print(f"[INFO] {url} にアクセス中...")
time.sleep(5)

print("[INFO] Cookie を取得中...")
cookies = driver.get_cookies()

os.makedirs("output", exist_ok=True)
with open(cookie_file, "w", encoding="utf-8") as f:
    json.dump(cookies, f, indent=2, ensure_ascii=False)

print(f"[✅ 完了] Cookie を保存しました → {cookie_file}")
driver.quit()

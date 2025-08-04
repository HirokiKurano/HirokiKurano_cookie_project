# extractor/cookie_extractor.py

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import json, os, time, sys

def extract_cookies(url, output_file=None):
    options = webdriver.ChromeOptions()
    # 表示モードのままでOK（headlessではない）

    try:
        print("[INFO] Chrome 起動中...")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        print(f"[INFO] {url} にアクセス中...")
        driver.get(url)
        time.sleep(10)

        print("[INFO] Cookie を取得中...")
        cookies = driver.get_cookies()

        os.makedirs("output", exist_ok=True)
        domain = url.split("//")[-1].split("/")[0]
        output_file = output_file or f"cookies_{domain}.json"
        output_path = f"output/{output_file}"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=4)

        print(f"[✅ 完了] Cookie を保存しました → {output_path}")

    except Exception as e:
        print("[❌ エラー] 例外が発生しました:", str(e))

    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    # コマンドライン引数からURLを取得（なければGoogle）
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.google.com"
    extract_cookies(url)

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import json, os, time

def extract_cookies(url, output_file="cookies.json"):
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  ← 表示モードのままでOK

    try:
        print("[INFO] Chrome 起動中...")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        print(f"[INFO] {url} にアクセス中...")
        driver.get(url)
        time.sleep(10)

        print("[INFO] Cookie を取得中...")
        cookies = driver.get_cookies()

        os.makedirs("output", exist_ok=True)
        output_path = f"output/{output_file}"
        with open(output_path, "w") as f:
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
    extract_cookies("https://www.google.com", "cookies_google.com.json")

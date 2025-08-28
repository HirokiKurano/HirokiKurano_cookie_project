import json, os, sys, time, argparse, shutil
from urllib.parse import urlsplit
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions

CDP_BROWSERS = {"chrome", "edge", "brave", "chromium"}

def host_from_url(url: str) -> str:
    host = urlsplit(url).netloc
    return host.split(":")[0]

def normalize_from_cdp(cookie):
    return {
        "name": cookie.get("name"),
        "value": cookie.get("value"),
        "domain": cookie.get("domain"),
        "path": cookie.get("path", "/"),
        "secure": cookie.get("secure", False),
        "httpOnly": cookie.get("httpOnly", False),
        "sameSite": cookie.get("sameSite"),
        "expiry": int(cookie["expires"]) if cookie.get("expires") else None,
    }

def compute_profile_dir(profile_name: str, browser: str) -> str:
    legacy = os.path.abspath(f"profiles/{profile_name}")
    scoped = os.path.abspath(f"profiles/{browser}_{profile_name}")
    # 既存との互換を優先。なければブラウザ別ディレクトリを使う
    return legacy if os.path.exists(legacy) else scoped

def make_driver(browser: str, profile_dir: str, headless: bool, detach: bool):
    os.makedirs(profile_dir, exist_ok=True)
    if browser in {"chrome", "brave", "chromium"}:
        opts = ChromeOptions()
        opts.add_argument(f"--user-data-dir={profile_dir}")
        opts.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
        opts.add_argument("--log-level=3")
        if headless: opts.add_argument("--headless=new")
        if detach: opts.add_experimental_option("detach", True)
        # Brave の場合はバイナリ推定（見つからなければそのまま Chrome を利用）
        if browser == "brave":
            for p in [
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"
            ]:
                if os.path.exists(p):
                    opts.binary_location = p
                    break
        return webdriver.Chrome(options=opts)

    if browser == "edge":
        opts = EdgeOptions()
        opts.add_argument(f"--user-data-dir={profile_dir}")
        opts.add_argument("--log-level=3")
        if headless: opts.add_argument("--headless=new")
        # Edge は detach 相当のオプションがないので無視
        return webdriver.Edge(options=opts)

    if browser == "firefox":
        opts = FirefoxOptions()
        if headless: opts.add_argument("-headless")
        # プロファイル永続化は必須でないので指定なし（必要なら Gecko 用プロフィール運用に変更可）
        return webdriver.Firefox(options=opts)

    raise SystemExit(f"[ABORT] unsupported browser: {browser}")

def parse_args():
    parser = argparse.ArgumentParser(
        description="Cookie Extractor (Selenium or CDP, multi-browser)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("url", help="Target URL (e.g., https://www.bbc.com/)")
    parser.add_argument("profile_name", help="Profile name (stored under profiles/)")
    parser.add_argument("--browser", choices=["chrome","edge","brave","chromium","firefox"], default="chrome")
    parser.add_argument("--wait", type=int, default=5, help="Seconds to wait after page load")
    parser.add_argument("--detach", action="store_true", help="Keep the browser window open after execution")
    parser.add_argument("--mode", choices=["selenium", "cdp"], default="cdp",
                        help="Selenium API (no HttpOnly) or CDP (HttpOnly supported)")
    parser.add_argument("--run-dir", default=None, help="Directory to save outputs (e.g., runs/...)")
    return parser.parse_args()

def main():
    if os.getenv("COOKIE_LAB_TESTMODE") != "1":
        print("[ABORT] TESTMODE not set. Set COOKIE_LAB_TESTMODE=1 to run in test environment.")
        sys.exit(1)

    args = parse_args()
    url = args.url
    headless = os.getenv("HEADLESS") == "1"

    # Firefox は CDP 非対応なので自動フォールバック
    if args.mode == "cdp" and args.browser not in CDP_BROWSERS:
        print("[WARN] CDP is not supported on this browser. Falling back to Selenium mode.")
        args.mode = "selenium"

    profile_dir = compute_profile_dir(args.profile_name, args.browser)
    print("[INFO] Launching", args.browser, "...")
    driver = make_driver(args.browser, profile_dir, headless=headless, detach=args.detach)

    try:
        if args.mode == "cdp" and args.browser in CDP_BROWSERS:
            driver.execute_cdp_cmd("Network.enable", {})

        print(f"[INFO] Accessing {url} ...")
        driver.get(url)
        time.sleep(args.wait)

        final_url = driver.current_url
        domain = host_from_url(final_url)

        out_base = args.run_dir or "output"
        os.makedirs(out_base, exist_ok=True)
        cookie_file = os.path.join(out_base, f"cookies_{domain}.json")

        if args.mode == "cdp" and args.browser in CDP_BROWSERS:
            print("[INFO] Retrieving cookies via CDP (includes HttpOnly)...")
            all_cookies = driver.execute_cdp_cmd("Network.getAllCookies", {})["cookies"]
            cookies = [normalize_from_cdp(c) for c in all_cookies]
        else:
            print("[INFO] Retrieving cookies via Selenium (no HttpOnly)...")
            cookies = driver.get_cookies()

        payload = {
            "meta": {
                "browser": args.browser,
                "profile": args.profile_name,
                "mode": args.mode,
                "extracted_at": int(time.time()),
                "requested_url": url,
                "final_url": final_url,
                "final_domain": domain
            },
            "cookies": cookies
        }
        with open(cookie_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        print(f"[COMPLETED] Cookies saved -> {cookie_file}")

    finally:
        if not args.detach:
            driver.quit()

if __name__ == "__main__":
    main()

import json, os, sys, time, argparse
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
        # Brave binary hint
        if browser == "brave":
            for p in [
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
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
        return webdriver.Edge(options=opts)

    if browser == "firefox":
        opts = FirefoxOptions()
        if headless: opts.add_argument("-headless")
        return webdriver.Firefox(options=opts)

    raise SystemExit(f"[ABORT] unsupported browser: {browser}")

def get_storage(driver, storage_type: str):
    """
    storage_type: 'localStorage' or 'sessionStorage'
    取得失敗時は {} を返す
    """
    try:
        script = """
        const type = arguments[0];
        try {
          const store = window[type];
          const out = {};
          for (let i = 0; i < store.length; i++) {
            const k = store.key(i);
            out[k] = store.getItem(k);
          }
          return { ok: true, data: out };
        } catch (e) {
          return { ok: false, error: String(e) };
        }
        """
        res = driver.execute_script(script, storage_type)
        if res and res.get("ok"):
            return res.get("data") or {}
        else:
            print(f"[WARN] {storage_type} read failed: {res.get('error') if res else 'unknown'}")
            return {}
    except Exception as e:
        print(f"[WARN] {storage_type} read exception: {e}")
        return {}

def parse_args():
    parser = argparse.ArgumentParser(
        description="Cookie Extractor (Selenium or CDP, multi-browser)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("url", help="Target URL (e.g., https://example.com/)")
    parser.add_argument("profile_name", help="Profile name (stored under profiles/)")
    parser.add_argument("--browser", choices=["chrome","edge","brave","chromium","firefox"], default="chrome")
    parser.add_argument("--wait", type=int, default=5, help="Seconds to wait after page load")
    parser.add_argument("--detach", action="store_true", help="Keep the browser window open after execution")
    parser.add_argument("--mode", choices=["selenium", "cdp"], default="cdp",
                        help="Selenium API (no HttpOnly) or CDP (HttpOnly supported)")
    parser.add_argument("--run-dir", default=None, help="Directory to save outputs (e.g., runs/...)")
    parser.add_argument("--with-storage", action="store_true",
                        help="Also dump localStorage & sessionStorage for the final origin")
    return parser.parse_args()

def main():
    if os.getenv("COOKIE_LAB_TESTMODE") != "1":
        print("[ABORT] TESTMODE not set. Set COOKIE_LAB_TESTMODE=1 to run in test environment.")
        sys.exit(1)

    args = parse_args()
    url = args.url
    headless = os.getenv("HEADLESS") == "1"

    # Firefox CDP fallback
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

        # Cookies
        if args.mode == "cdp" and args.browser in CDP_BROWSERS:
            print("[INFO] Retrieving cookies via CDP (includes HttpOnly)...")
            all_cookies = driver.execute_cdp_cmd("Network.getAllCookies", {})["cookies"]
            cookies = [normalize_from_cdp(c) for c in all_cookies]
        else:
            print("[INFO] Retrieving cookies via Selenium (no HttpOnly)...")
            cookies = driver.get_cookies()

        # Storage (optional)
        local_storage, session_storage = {}, {}
        if args.with_storage:
            print("[INFO] Reading localStorage / sessionStorage for", domain, "...")
            local_storage = get_storage(driver, "localStorage")
            session_storage = get_storage(driver, "sessionStorage")
            print(f"[INFO] Storage now: localStorage={len(local_storage)}, sessionStorage={len(session_storage)}")

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
            "cookies": cookies,
            "localStorage": local_storage,
            "sessionStorage": session_storage
        }

        with open(cookie_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        print(f"[COMPLETED] Saved -> {cookie_file}")

    finally:
        if not args.detach:
            driver.quit()

if __name__ == "__main__":
    main()
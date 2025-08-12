import json, os, sys, time, argparse
from urllib.parse import urlsplit
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def parse_args():
    parser = argparse.ArgumentParser(
        description="Cookie Extractor (supports Selenium or Chrome DevTools Protocol)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("url", help="Target URL (e.g., https://www.bbc.com/)")
    parser.add_argument("profile_name", help="Chrome profile name (profiles/<name>)")
    parser.add_argument("--wait", type=int, default=5, help="Seconds to wait after page load")
    parser.add_argument("--detach", action="store_true", help="Keep the browser window open after execution")
    parser.add_argument("--mode", choices=["selenium", "cdp"], default="cdp",
                        help="Extraction mode: Selenium API (no HttpOnly) or CDP (HttpOnly supported)")
    return parser.parse_args()

def host_from_url(url: str) -> str:
    """Extract hostname without port from a URL."""
    host = urlsplit(url).netloc
    return host.split(":")[0]

def normalize_from_cdp(cookie):
    """
    Convert CDP cookie dict to Selenium-style format.
    This allows storing them in a common JSON format for both modes.
    """
    return {
        "name": cookie.get("name"),
        "value": cookie.get("value"),
        "domain": cookie.get("domain"),
        "path": cookie.get("path", "/"),
        "secure": cookie.get("secure", False),
        "httpOnly": cookie.get("httpOnly", False),
        "sameSite": cookie.get("sameSite"),  # May be "Strict", "Lax", "None", or None
        "expiry": int(cookie["expires"]) if cookie.get("expires") else None,
    }

def main():
    args = parse_args()
    url = args.url
    profile_path = os.path.abspath(f"profiles/{args.profile_name}")

    # Set Chrome options to use the specified user profile
    options = Options()
    options.add_argument(f"--user-data-dir={profile_path}")
    if args.detach:
        options.add_experimental_option("detach", True)

    print("[INFO] Launching Chrome...")
    driver = webdriver.Chrome(options=options)
    try:
        if args.mode == "cdp":
            driver.execute_cdp_cmd("Network.enable", {})

        print(f"[INFO] Accessing {url} ...")
        driver.get(url)
        time.sleep(args.wait)

        # Determine the final domain (after redirects)
        final_url = driver.current_url
        domain = host_from_url(final_url)

        os.makedirs("output", exist_ok=True)
        cookie_file = f"output/cookies_{domain}.json"

        # Extract cookies using the chosen mode
        if args.mode == "cdp":
            print("[INFO] Retrieving cookies via CDP (includes HttpOnly)...")
            all_cookies = driver.execute_cdp_cmd("Network.getAllCookies", {})["cookies"]
            cookies = [normalize_from_cdp(c) for c in all_cookies]
        else:
            print("[INFO] Retrieving cookies via Selenium (no HttpOnly)...")
            cookies = driver.get_cookies()

        with open(cookie_file, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)

        print(f"[COMPLETED] Cookies saved → {cookie_file}")

    finally:
        if not args.detach:
            driver.quit()

if __name__ == "__main__":
    main()

# extractor/cookie_extractor.py

import json, os, sys, time, argparse
from urllib.parse import urlsplit
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def parse_args():
    p = argparse.ArgumentParser(
        description="Cookie Extractor (test profiles only)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    p.add_argument("url", help="Target URL (e.g., https://www.bbc.com/)")
    p.add_argument("profile_name", help="Chrome profile name (profiles/<name>)")
    p.add_argument("--wait", type=int, default=5, help="Seconds to wait after page load")
    p.add_argument("--detach", action="store_true", help="Keep the browser window open after execution")
    return p.parse_args()

def host_from_url(u: str) -> str:
    host = urlsplit(u).netloc
    # Example: "example.com:443" -> "example.com"
    return host.split(":")[0]

def main():
    args = parse_args()

    url = args.url
    profile_name = args.profile_name
    profile_path = os.path.abspath(f"profiles/{profile_name}")

    options = Options()
    options.add_argument(f"--user-data-dir={profile_path}")
    if args.detach:
        options.add_experimental_option("detach", True)

    print("[INFO] Launching Chrome...")
    driver = webdriver.Chrome(options=options)
    try:
        print(f"[INFO] Accessing {url} ...")
        driver.get(url)
        time.sleep(args.wait)  # Can be replaced with WebDriverWait if needed

        # Considering redirects: determine the domain name from the final URL
        final_url = driver.current_url
        domain = host_from_url(final_url)
        os.makedirs("output", exist_ok=True)
        cookie_file = f"output/cookies_{domain}.json"

        print("[INFO] Retrieving cookies...")
        cookies = driver.get_cookies()

        with open(cookie_file, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)

        print(f"[ Completed] Cookies saved → {cookie_file}")
    finally:
        # Use --detach to keep the browser window open (do not quit when detached)
        if not args.detach:
            driver.quit()

if __name__ == "__main__":
    main()

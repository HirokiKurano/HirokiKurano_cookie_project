import json, os, time, sys, re, argparse
from urllib.parse import urlsplit
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions

CDP_BROWSERS = {"chrome", "edge", "brave", "chromium"}

# ---------- utilities ----------
def compile_patterns(patterns):
    if not patterns:
        return []
    if isinstance(patterns, str):
        patterns = [patterns]
    import re as _re
    return [_re.compile(p, _re.IGNORECASE) for p in patterns]

def cookie_key(cookie):
    return f"{cookie.get('domain','')}/{cookie.get('path','')}/{cookie.get('name','')}"

def is_match(regex_list, text):
    return any(r.search(text) for r in regex_list)

def load_filters(filters_path):
    if not filters_path or not os.path.exists(filters_path):
        return [], [], []
    with open(filters_path, "r", encoding="utf-8") as ff:
        cfg = json.load(ff)
    return (
        compile_patterns(cfg.get("allow")),
        compile_patterns(cfg.get("block")),
        compile_patterns(cfg.get("block_domain")),
    )

def merge_cli_filters(allow_re, block_re, block_domain_re, args):
    allow_re += compile_patterns(args.allow)
    block_re += compile_patterns(args.block)
    block_domain_re += compile_patterns(args.block_domain)
    return allow_re, block_re, block_domain_re

def filter_cookies(cookies, allow_re, block_re, block_domain_re, verbose=True):
    if not (allow_re or block_re or block_domain_re):
        return cookies
    filtered = []
    for c in cookies:
        key = cookie_key(c)
        dom = c.get("domain", "")
        if is_match(block_domain_re, dom):
            if verbose: print(f"[FILTER] block_domain: {dom} -> skip {c.get('name')}")
            continue
        if allow_re and not is_match(allow_re, key):
            if verbose: print(f"[FILTER] not in allow: {key} -> skip {c.get('name')}")
            continue
        if is_match(block_re, key):
            if verbose: print(f"[FILTER] block: {key} -> skip {c.get('name')}")
            continue
        filtered.append(c)
    return filtered

def sanitize_cookie_for_cdp(c):
    out = {
        "name": c["name"],
        "value": c.get("value", ""),
        "domain": c.get("domain"),
        "path": c.get("path") or "/",
        "secure": bool(c.get("secure", False)),
        "httpOnly": bool(c.get("httpOnly", False)),
    }
    if c.get("sameSite") in ("Lax", "Strict", "None"):
        out["sameSite"] = c["sameSite"]
    if c.get("expiry") is not None:
        try:
            out["expires"] = float(c["expiry"])
        except Exception:
            pass
    return out

def host_from_url(url: str) -> str:
    host = urlsplit(url).netloc
    return host.split(":")[0]

def etld1(host: str) -> str:
    """超簡易 eTLD+1 っぽい抽出（bbc.co.uk 等の第二階層TLDに対応）"""
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in {"co", "com", "org", "gov", "ac", "net"}:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host

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
        return webdriver.Edge(options=opts)

    if browser == "firefox":
        opts = FirefoxOptions()
        if headless: opts.add_argument("-headless")
        return webdriver.Firefox(options=opts)

    raise SystemExit(f"[ABORT] unsupported browser: {browser}")

# ---------- args ----------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Cookie Importer with Filtering (Selenium or CDP, multi-browser)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("url", help="Target URL (should match extraction domain)")
    parser.add_argument("profile_name", help="Profile name (stored under profiles/)")
    parser.add_argument("--browser", choices=["chrome","edge","brave","chromium","firefox"], default="chrome")
    parser.add_argument("--filters", default="filters.json", help="Path to filter settings JSON")
    parser.add_argument("--allow", action="append", default=[], help="Allow regex for 'domain/path/name'")
    parser.add_argument("--block", action="append", default=[], help="Block regex for 'domain/path/name'")
    parser.add_argument("--block-domain", action="append", default=[], help="Block regex for domain")
    parser.add_argument("--dry-run", action="store_true", help="Do not actually apply cookies")
    parser.add_argument("--quiet", action="store_true", help="Suppress detailed logs")
    parser.add_argument("--wait", type=int, default=3, help="Seconds to wait after initial page load")
    parser.add_argument("--mode", choices=["selenium", "cdp"], default="cdp",
                        help="Import mode: Selenium API or CDP (HttpOnly supported)")
    parser.add_argument("--pre-clear", nargs="*", default=["cookies","localStorage","sessionStorage"],
                        help="What to clear before import")
    parser.add_argument("--run-dir", default=None, help="Directory to write artifacts")
    parser.add_argument("--screenshot", action="store_true", help="Capture screenshot after import & reload")
    parser.add_argument("--detach", action="store_true", help="Keep the browser window open after execution")
    return parser.parse_args()

# ---------- main ----------
def main():
    if os.getenv("COOKIE_LAB_TESTMODE") != "1":
        print("[ABORT] TESTMODE not set. Set COOKIE_LAB_TESTMODE=1 to run in test environment.")
        sys.exit(1)

    args = parse_args()
    url = args.url
    headless = os.getenv("HEADLESS") == "1"

    if args.mode == "cdp" and args.browser not in CDP_BROWSERS:
        print("[WARN] CDP is not supported on this browser. Falling back to Selenium mode.")
        args.mode = "selenium"

    profile_dir = compute_profile_dir(args.profile_name, args.browser)

    target_domain = host_from_url(url)
    base_dir = args.run_dir or "output"
    os.makedirs(base_dir, exist_ok=True)
    cookie_file = os.path.join(base_dir, f"cookies_{target_domain}.json")

    # ===== ここから：Not Found 時だけ「自動解決」する軽微パッチ =====
    if not os.path.exists(cookie_file):
        # まず run-dir 内を優先的に探索
        search_dirs = [base_dir]
        if "output" not in search_dirs:
            search_dirs.append("output")

        candidates = []
        for d in search_dirs:
            if os.path.exists(d):
                for p in os.listdir(d):
                    if p.startswith("cookies_") and p.endswith(".json"):
                        candidates.append(os.path.join(d, p))

        # スコア方式で最適と思われるファイルを選ぶ
        target_host = host_from_url(url)          # 例: www.bbc.com
        target_etld1 = etld1(target_host)         # 例: bbc.com
        chosen = None

        for cpath in candidates:
            try:
                with open(cpath, "r", encoding="utf-8") as f:
                    payload_try = json.load(f)
                meta = payload_try.get("meta", {}) if isinstance(payload_try, dict) else {}
                final_dom = meta.get("final_domain") or ""
                score = 0
                if final_dom == target_host:
                    score = 3  # 完全一致
                elif final_dom and etld1(final_dom) == target_etld1:
                    score = 2  # eTLD+1 一致（bbc.com / bbc.co.uk など）
                elif final_dom and final_dom in url:
                    score = 1  # URLに含まれる
                if score > 0 and (chosen is None or score > chosen[0]):
                    chosen = (score, cpath)
            except Exception:
                # 壊れたJSONなどはスキップ
                pass

        if chosen:
            cookie_file = chosen[1]
            print(f"[INFO] Cookie file auto-selected -> {cookie_file}")
        else:
            # 最後の単純置換フォールバック（.bbc.com → .bbc.co.uk）
            alt = cookie_file.replace(".bbc.com", ".bbc.co.uk")
            if os.path.exists(alt):
                cookie_file = alt
                print(f"[INFO] Cookie file fallback (.com→.co.uk) -> {cookie_file}")
            else:
                hint = " / ".join(candidates[:5]) if candidates else "(none)"
                print(f"[ERROR] Cookie file not found: {cookie_file}")
                print(f"[HINT] Candidates: {hint}")
                sys.exit(1)
    # ===== パッチここまで =====

    driver = make_driver(args.browser, profile_dir, headless=headless, detach=args.detach)
    print(f"[INFO] Launching {args.browser} & accessing {url} ...")

    if args.mode == "cdp" and args.browser in CDP_BROWSERS:
        driver.execute_cdp_cmd("Network.enable", {})

    driver.get(url)
    time.sleep(args.wait)

    # pre-clear via CDP (Chromium 系のみ)
    if args.mode == "cdp" and args.browser in CDP_BROWSERS:
        if "cookies" in args.pre_clear:
            driver.execute_cdp_cmd("Network.clearBrowserCookies", {})
        if "localStorage" in args.pre_clear or "sessionStorage" in args.pre_clear:
            origin = f"{url.split('//')[0]}//{host_from_url(url)}"
            storage_types = []
            if "localStorage" in args.pre_clear: storage_types.append("local_storage")
            if "sessionStorage" in args.pre_clear: storage_types.append("session_storage")
            if storage_types:
                driver.execute_cdp_cmd("Storage.clearDataForOrigin", {
                    "origin": origin,
                    "storageTypes": ",".join(storage_types)
                })

    # Load cookies (meta or plain)
    with open(cookie_file, "r", encoding="utf-8") as f:
        payload = json.load(f)
    cookies = payload["cookies"] if isinstance(payload, dict) and "cookies" in payload else payload

    # filtering
    allow_re, block_re, block_domain_re = load_filters(args.filters)
    allow_re, block_re, block_domain_re = merge_cli_filters(allow_re, block_re, block_domain_re, args)
    before = len(cookies)
    cookies = filter_cookies(cookies, allow_re, block_re, block_domain_re, verbose=(not args.quiet))
    after = len(cookies)
    print(f"[INFO] Filters applied: {before} -> {after} cookies")

    if args.dry_run:
        print("[DRY-RUN] No cookies applied. Exiting.")
        driver.quit()
        return

    # apply
    if args.mode == "cdp" and args.browser in CDP_BROWSERS:
        payload2 = {"cookies": [sanitize_cookie_for_cdp(c) for c in cookies]}
        if payload2["cookies"]:
            driver.execute_cdp_cmd("Network.setCookies", payload2)
        applied = len(payload2["cookies"])
        skipped = 0
    else:
        driver.delete_all_cookies()
        applied = skipped = 0
        for c in cookies:
            try:
                d = {k: v for k, v in c.items()
                     if k in {"name","value","path","domain","secure","httpOnly","expiry","sameSite"}}
                if "expiry" in d and d["expiry"] is not None:
                    try: d["expiry"] = int(d["expiry"])
                    except: d.pop("expiry", None)
                if not d.get("path"): d["path"] = "/"
                driver.add_cookie(d)
                applied += 1
            except Exception as e:
                skipped += 1
                if not args.quiet:
                    print(f"[WARN] Cookie ignored: {c.get('name')} - {e}")

    print(f"[INFO] Cookie application complete: applied={applied}, skipped={skipped}")
    print("[INFO] Reloading page after applying cookies...")
    driver.get(url)
    time.sleep(2)

    # artifacts
    if args.screenshot:
        ss_path = os.path.join(base_dir, f"screenshot_after_{target_domain}.png")
        driver.save_screenshot(ss_path)
        print(f"[ARTIFACT] Screenshot saved -> {ss_path}")
    if args.mode == "cdp" and args.browser in CDP_BROWSERS:
        after_c = driver.execute_cdp_cmd("Network.getAllCookies", {})["cookies"]
        with open(os.path.join(base_dir, f"cookies_after_{target_domain}.json"), "w", encoding="utf-8") as f:
            json.dump(after_c, f, indent=2, ensure_ascii=False)

    if not args.detach:
        driver.quit()

if __name__ == "__main__":
    main()

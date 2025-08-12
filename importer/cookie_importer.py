import json, os, time, sys, re, argparse
from urllib.parse import urlsplit
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ---------------------------
# Utility functions
# ---------------------------

def compile_patterns(patterns):
    """Compile regex patterns (case-insensitive) from string or list."""
    if not patterns:
        return []
    if isinstance(patterns, str):
        patterns = [patterns]
    return [re.compile(p, re.IGNORECASE) for p in patterns]

def cookie_key(cookie):
    """Return a unique key for a cookie in 'domain/path/name' format."""
    return f"{cookie.get('domain','')}/{cookie.get('path','')}/{cookie.get('name','')}"

def is_match(regex_list, text):
    """Check if any regex in the list matches the given text."""
    return any(r.search(text) for r in regex_list)

def load_filters(filters_path):
    """Load allow/block patterns from a JSON filter config file."""
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
    """Merge CLI-provided patterns with filter file patterns."""
    allow_re += compile_patterns(args.allow)
    block_re += compile_patterns(args.block)
    block_domain_re += compile_patterns(args.block_domain)
    return allow_re, block_re, block_domain_re

def filter_cookies(cookies, allow_re, block_re, block_domain_re, verbose=True):
    """Filter cookies according to allow/block rules."""
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
    """Prepare cookie dict for CDP's Network.setCookies API."""
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
    """Extract hostname without port."""
    host = urlsplit(url).netloc
    return host.split(":")[0]

# ---------------------------
# CLI parsing
# ---------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Cookie Importer with Filtering (supports Selenium or Chrome DevTools Protocol)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("url", help="Target URL (should match extraction domain)")
    parser.add_argument("profile_name", help="Chrome profile name (profiles/<name>)")
    parser.add_argument("--filters", default="filters.json", help="Path to filter settings JSON")
    parser.add_argument("--allow", action="append", default=[], help="Allow regex for 'domain/path/name'")
    parser.add_argument("--block", action="append", default=[], help="Block regex for 'domain/path/name'")
    parser.add_argument("--block-domain", action="append", default=[], help="Block regex for domain")
    parser.add_argument("--dry-run", action="store_true", help="Do not actually apply cookies")
    parser.add_argument("--quiet", action="store_true", help="Suppress detailed logs")
    parser.add_argument("--wait", type=int, default=3, help="Seconds to wait after initial page load")
    parser.add_argument("--mode", choices=["selenium", "cdp"], default="cdp",
                        help="Import mode: Selenium API or CDP (HttpOnly supported)")
    return parser.parse_args()

# ---------------------------
# Main logic
# ---------------------------

def main():
    args = parse_args()
    url = args.url
    profile_path = os.path.abspath(f"profiles/{args.profile_name}")

    target_domain = host_from_url(url)
    cookie_file = f"output/cookies_{target_domain}.json"

    # Check cookie file existence
    if not os.path.exists(cookie_file):
        candidates = [p for p in os.listdir("output") if p.startswith("cookies_") and p.endswith(".json")] if os.path.exists("output") else []
        hint = " / ".join(candidates[:5]) if candidates else "(none)"
        print(f"[ERROR] Cookie file not found: {cookie_file}")
        print(f"[HINT] Candidates in output/: {hint}")
        sys.exit(1)

    options = Options()
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_experimental_option("detach", True)

    driver = webdriver.Chrome(options=options)
    print(f"[INFO] Launching Chrome & accessing {url} ...")

    if args.mode == "cdp":
        driver.execute_cdp_cmd("Network.enable", {})

    driver.get(url)
    time.sleep(args.wait)

    # Load cookies from file
    with open(cookie_file, "r", encoding="utf-8") as f:
        cookies = json.load(f)

    # Apply filters
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

    # Apply cookies depending on mode
    if args.mode == "cdp":
        payload = {"cookies": [sanitize_cookie_for_cdp(c) for c in cookies]}
        driver.execute_cdp_cmd("Network.setCookies", payload)
        applied = len(payload["cookies"])
        skipped = 0
    else:
        driver.delete_all_cookies()
        applied = skipped = 0
        for c in cookies:
            try:
                d = {k: v for k, v in c.items() if k in {"name","value","path","domain","secure","httpOnly","expiry","sameSite"}}
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

if __name__ == "__main__":
    main()

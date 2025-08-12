# importer/cookie_importer.py
# update12/08/2025

import json, os, time, sys, re, argparse
from urllib.parse import urlsplit
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def compile_patterns(patterns):
    if not patterns:
        return []
    if isinstance(patterns, str):
        patterns = [patterns]
    return [re.compile(p, re.IGNORECASE) for p in patterns]

def cookie_key(c):
    # Matching key: "domain/path/name"
    return f"{c.get('domain','')}/{c.get('path','')}/{c.get('name','')}"

def is_match(regex_list, text):
    return any(r.search(text) for r in regex_list)

def load_filters(filters_path):
    if not filters_path or not os.path.exists(filters_path):
        return [], [], []
    with open(filters_path, "r", encoding="utf-8") as ff:
        cfg = json.load(ff)
    allow_re = compile_patterns(cfg.get("allow"))
    block_re = compile_patterns(cfg.get("block"))
    block_domain_re = compile_patterns(cfg.get("block_domain"))
    return allow_re, block_re, block_domain_re

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

def sanitize_cookie(c):
    """
    Format the cookie so that Selenium.add_cookie can accept it
    - Remove unnecessary keys
    - Ensure expiry is an int
    """
    allowed = {"name", "value", "path", "domain", "secure", "httpOnly", "expiry", "sameSite"}
    d = {k: v for k, v in c.items() if k in allowed}

    if "expiry" in d and d["expiry"] is not None:
        try:
            d["expiry"] = int(d["expiry"])
        except Exception:
            d.pop("expiry", None)

    # If sameSite causes errors depending on the environment, uncomment the line below
    # d.pop("sameSite", None)

    if "path" not in d or not d["path"]:
        d["path"] = "/"

    if not d.get("name") or d.get("value") is None:
        raise ValueError("invalid cookie: missing name or value")

    return d

def host_from_url(u: str) -> str:
    host = urlsplit(u).netloc
    return host.split(":")[0]

def parse_args():
    parser = argparse.ArgumentParser(
        description="Cookie Importer with Filtering (test profiles only)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("url", help="Target URL (recommended: same domain as extraction)")
    parser.add_argument("profile_name", help="Chrome profile name (profiles/<name>)")
    parser.add_argument("--filters", default="filters.json",
                        help="Filter settings file (allow/block/block_domain)")
    parser.add_argument("--allow", action="append", default=[],
                        help="Allow (regex for 'domain/path/name')")
    parser.add_argument("--block", action="append", default=[],
                        help="Block (same format as above)")
    parser.add_argument("--block-domain", action="append", default=[],
                        help="Block domains (regex)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Do not execute add_cookie, only display results")
    parser.add_argument("--quiet", action="store_true", help="Suppress detailed logs")
    parser.add_argument("--wait", type=int, default=3, help="Seconds to wait after initial access")
    return parser.parse_args()

def main():
    args = parse_args()

    url = args.url
    profile_name = args.profile_name
    profile_path = os.path.abspath(f"profiles/{profile_name}")

    target_domain = host_from_url(url)
    cookie_file = f"output/cookies_{target_domain}.json"
    if not os.path.exists(cookie_file):
        candidates = [p for p in os.listdir("output") if p.startswith("cookies_") and p.endswith(".json")]
        hint = " / ".join(candidates[:5]) if candidates else "(none)"
        print(f"[ERROR] Cookie file not found: {cookie_file}")
        print(f"[HINT] Candidates in output/: {hint}")
        sys.exit(1)

    options = Options()
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_experimental_option("detach", True)

    driver = webdriver.Chrome(options=options)
    print(f"[INFO] Launching Chrome & accessing {url} ...")
    driver.get(url)
    time.sleep(args.wait)

    with open(cookie_file, "r", encoding="utf-8") as f:
        cookies = json.load(f)

    allow_re, block_re, block_domain_re = load_filters(args.filters)
    allow_re, block_re, block_domain_re = merge_cli_filters(allow_re, block_re, block_domain_re, args)
    before = len(cookies)
    cookies = filter_cookies(cookies, allow_re, block_re, block_domain_re, verbose=(not args.quiet))
    after = len(cookies)
    print(f"[INFO] Filters applied: {before} -> {after} cookies")

    if args.dry_run:
        print("[DRY-RUN] Skipping add_cookie execution. Exiting.")
        driver.quit()
        return

    driver.delete_all_cookies()
    applied, skipped = 0, 0
    for c in cookies:
        try:
            driver.add_cookie(sanitize_cookie(c))
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
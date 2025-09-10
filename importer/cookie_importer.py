import json, os, sys, time, argparse
from urllib.parse import urlsplit
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions

CDP_BROWSERS = {"chrome", "edge", "brave", "chromium"}

# ---------- utilities ----------
def host_from_url(url: str) -> str:
    host = urlsplit(url).netloc
    return host.split(":")[0]

def origin_from_url(url: str) -> str:
    u = urlsplit(url)
    scheme = u.scheme or "https"
    host = u.netloc
    return f"{scheme}://{host}"

def etld1(host: str) -> str:
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
        # Brave browser binary location (if installed in default paths)
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

def add_preload_storage_script(driver, local_storage: dict, session_storage: dict):
    """
    Inject before navigation. At the earliest timing (document start),
    set localStorage / sessionStorage.
    """
    # Do nothing if both storages are empty
    if not (local_storage or session_storage):
        return None

    import json as _json
    ls_json = _json.dumps(local_storage or {}, ensure_ascii=False)
    ss_json = _json.dumps(session_storage or {}, ensure_ascii=False)

    script = f"""
    (function() {{
      try {{
        const __LS__ = {ls_json};
        const __SS__ = {ss_json};
        // Clear storages first (may duplicate with pre-clear but safer)
        try {{ window.localStorage.clear(); }} catch (e) {{}}
        try {{ window.sessionStorage.clear(); }} catch (e) {{}}

        // Restore values
        try {{
          for (const [k,v] of Object.entries(__LS__)) {{
            try {{ window.localStorage.setItem(k, v); }} catch (e) {{}}
          }}
        }} catch (e) {{}}

        try {{
          for (const [k,v] of Object.entries(__SS__)) {{
            try {{ window.sessionStorage.setItem(k, v); }} catch (e) {{}}
          }}
        }} catch (e) {{}}
      }} catch (e) {{}}
    }})();
    """
    try:
        return driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": script})
    except Exception as e:
        print("[WARN] preload storage script install failed:", e)
        return None

# ---------- args ----------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Cookie Importer (apply-before-nav) + Storage restore at document start (CDP preferred)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("url", help="Target URL")
    parser.add_argument("profile_name", help="Profile name (stored under profiles/)")
    parser.add_argument("--browser", choices=["chrome","edge","brave","chromium","firefox"], default="chrome")
    parser.add_argument("--wait", type=int, default=3, help="Seconds to wait after final page load")
    parser.add_argument("--mode", choices=["selenium", "cdp"], default="cdp",
                        help="Import mode: Selenium API or CDP (HttpOnly supported)")
    parser.add_argument("--pre-clear", nargs="*", default=["cookies","localStorage","sessionStorage"],
                        help="What to clear before import (cookies, localStorage, sessionStorage)")
    parser.add_argument("--run-dir", default=None, help="Directory to read/write artifacts")
    parser.add_argument("--screenshot", action="store_true", help="Capture screenshot after import")
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

    # CDP support check
    if args.mode == "cdp" and args.browser not in CDP_BROWSERS:
        print("[WARN] CDP is not supported on this browser. Falling back to Selenium mode.")
        args.mode = "selenium"

    profile_dir = compute_profile_dir(args.profile_name, args.browser)
    target_domain = host_from_url(url)
    target_origin = origin_from_url(url)
    base_dir = args.run_dir or "output"
    os.makedirs(base_dir, exist_ok=True)
    cookie_file = os.path.join(base_dir, f"cookies_{target_domain}.json")

    # Cookie file selection (auto-select if exact match not found)
    if not os.path.exists(cookie_file):
        search_dirs = [base_dir] + (["output"] if base_dir != "output" else [])
        candidates = []
        for d in search_dirs:
            if os.path.exists(d):
                for p in os.listdir(d):
                    if p.startswith("cookies_") and p.endswith(".json"):
                        candidates.append(os.path.join(d, p))
        chosen = None
        tgt_etld = etld1(target_domain)
        for cpath in candidates:
            try:
                with open(cpath, "r", encoding="utf-8") as f:
                    pl = json.load(f)
                meta = pl.get("meta", {}) if isinstance(pl, dict) else {}
                final_dom = meta.get("final_domain") or ""
                score = 0
                if final_dom == target_domain: score = 3
                elif final_dom and etld1(final_dom) == tgt_etld: score = 2
                elif final_dom and final_dom in url: score = 1
                if score and (not chosen or score > chosen[0]): chosen = (score, cpath)
            except Exception:
                pass
        if chosen:
            cookie_file = chosen[1]
            print(f"[INFO] Cookie file auto-selected -> {cookie_file}")
        else:
            print(f"[ERROR] Cookie file not found: {cookie_file}")
            print(f"[HINT] Candidates: {' / '.join(candidates[:5]) if candidates else '(none)'}")
            sys.exit(1)

    # Launch browser (first at about:blank)
    driver = make_driver(args.browser, profile_dir, headless=headless, detach=args.detach)
    print(f"[INFO] Launching {args.browser} at about:blank ...")
    driver.get("about:blank")

    # Enable CDP features
    if args.mode == "cdp" and args.browser in CDP_BROWSERS:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd("Page.enable", {})

    # Load JSON file
    with open(cookie_file, "r", encoding="utf-8") as f:
        payload = json.load(f)
    cookies = payload.get("cookies", payload if isinstance(payload, list) else [])
    local_storage = payload.get("localStorage", {})
    session_storage = payload.get("sessionStorage", {})

    # --- Pre-clear executed *before* navigation ---
    if "cookies" in args.pre_clear:
        try:
            if args.mode == "cdp" and args.browser in CDP_BROWSERS:
                driver.execute_cdp_cmd("Network.clearBrowserCookies", {})
            else:
                driver.delete_all_cookies()
        except Exception as e:
            print("[WARN] clear cookies:", e)

    if ("localStorage" in args.pre_clear) or ("sessionStorage" in args.pre_clear):
        try:
            if args.mode == "cdp" and args.browser in CDP_BROWSERS:
                driver.execute_cdp_cmd("Storage.clearDataForOrigin", {
                    "origin": target_origin,
                    "storageTypes": ",".join(
                        [s for s, t in (("local_storage","localStorage" in args.pre_clear),
                                        ("session_storage","sessionStorage" in args.pre_clear)) if t]
                    )
                })
            # In Selenium mode, no origin exists before navigation,
            # so JS-based clearing will be handled later
        except Exception as e:
            print("[WARN] clear storage:", e)

    # --- Apply cookies *before* navigation (CDP can set across domains) ---
    applied = skipped = 0
    if args.mode == "cdp" and args.browser in CDP_BROWSERS:
        payload2 = {"cookies": [sanitize_cookie_for_cdp(c) for c in cookies]}
        try:
            if payload2["cookies"]:
                driver.execute_cdp_cmd("Network.setCookies", payload2)
                applied = len(payload2["cookies"])
        except Exception as e:
            print("[WARN] CDP setCookies failed:", e)
    else:
        # In Selenium mode, add_cookie before navigation is limited,
        # so cookies will be applied later after reaching origin
        pass

    # --- Restore storage at *document start* (CDP: Page.addScriptToEvaluateOnNewDocument) ---
    preload_id = None
    if args.mode == "cdp" and args.browser in CDP_BROWSERS:
        preload_id = add_preload_storage_script(driver, local_storage, session_storage)

    # Now navigate to the target URL for the first time
    print(f"[INFO] Navigating to {url} with pre-applied state ...")
    driver.get(url)

    # Selenium fallback: apply after reaching origin (not perfect)
    if args.mode != "cdp" or (args.browser not in CDP_BROWSERS):
        # Apply as many cookies as possible
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
                print(f"[WARN] Cookie ignored: {c.get('name')} - {e}")
        # Restore storage afterward (requires JS, happens after first render)
        try:
            driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
        except Exception:
            pass
        try:
            # localStorage
            if local_storage:
                driver.execute_script("""
                  const items = arguments[0] || {};
                  for (const [k,v] of Object.entries(items)) { try { localStorage.setItem(k, v); } catch(e){} }
                """, local_storage)
            # sessionStorage
            if session_storage:
                driver.execute_script("""
                  const items = arguments[0] || {};
                  for (const [k,v] of Object.entries(items)) { try { sessionStorage.setItem(k, v); } catch(e){} }
                """, session_storage)
        except Exception as e:
            print("[WARN] storage restore (selenium) failed:", e)
        # Reload the page to apply restored state
        driver.get(url)

    # Final wait
    time.sleep(max(0, args.wait))

    print(f"[INFO] Cookie application complete: applied={applied}, skipped={skipped}")

    if args.screenshot:
        ss_path = os.path.join(base_dir, f"screenshot_after_{target_domain}.png")
        try:
            driver.save_screenshot(ss_path)
            print(f"[ARTIFACT] Screenshot saved -> {ss_path}")
        except Exception as e:
            print("[WARN] screenshot failed:", e)

    # Post-verification (CDP only)
    if args.mode == "cdp" and args.browser in CDP_BROWSERS:
        try:
            after_c = driver.execute_cdp_cmd("Network.getAllCookies", {})["cookies"]
            with open(os.path.join(base_dir, f"cookies_after_{target_domain}.json"), "w", encoding="utf-8") as f:
                json.dump(after_c, f, indent=2, ensure_ascii=False)
            # Unregister preload script after use (optional)
            if preload_id and "identifier" in preload_id:
                try:
                    driver.execute_cdp_cmd("Page.removeScriptToEvaluateOnNewDocument",
                                           {"identifier": preload_id["identifier"]})
                except Exception:
                    pass
        except Exception as e:
            print("[WARN] post-read cookies failed:", e)

    if not args.detach:
        driver.quit()

if __name__ == "__main__":
    main()

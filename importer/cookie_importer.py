# importer/cookie_importer.py

import json, os, time, sys, re, argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def compile_patterns(patterns):
    if not patterns:
        return []
    # リスト or 文字列（"a|b|c"）どちらでもOK
    if isinstance(patterns, str):
        patterns = [patterns]
    return [re.compile(p, re.IGNORECASE) for p in patterns]

def cookie_key(cookie):
    # マッチ用キー: "domain/path/name"
    return f"{cookie.get('domain','')}/{cookie.get('path','')}/{cookie.get('name','')}"

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
    # 追加CLIフィルタをマージ
    allow_re += compile_patterns(args.allow)
    block_re += compile_patterns(args.block)
    block_domain_re += compile_patterns(args.block_domain)
    return allow_re, block_re, block_domain_re

def filter_cookies(cookies, allow_re, block_re, block_domain_re, verbose=True):
    if not (allow_re or block_re or block_domain_re):
        # フィルタ未指定ならそのまま返す
        return cookies

    filtered = []
    for c in cookies:
        key = cookie_key(c)
        dom = c.get("domain", "")

        # ドメイン単位のブロック
        if is_match(block_domain_re, dom):
            if verbose:
                print(f"[FILTER] block_domain: {dom} -> skip {c.get('name')}")
            continue

        # 許可リストがある場合、マッチしたものだけ通す
        if allow_re and not is_match(allow_re, key):
            if verbose:
                print(f"[FILTER] not in allow: {key} -> skip {c.get('name')}")
            continue

        # ブロックリストに該当したら除外
        if is_match(block_re, key):
            if verbose:
                print(f"[FILTER] block: {key} -> skip {c.get('name')}")
            continue

        filtered.append(c)
    return filtered

def parse_args():
    parser = argparse.ArgumentParser(
        description="Cookie Importer with Filtering",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("url", help="アクセス先URL")
    parser.add_argument("profile_name", help="Chromeプロファイル名（profiles/<name>）")
    parser.add_argument("--filters", default="filters.json",
                        help="フィルタ設定ファイル（allow/block/block_domain）")
    # 追加の一時フィルタ（正規表現）。複数指定可 or 'a|b|c' 形式も可
    parser.add_argument("--allow", action="append", default=[],
                        help="許可する cookie（'domain/path/name' に対する正規表現）")
    parser.add_argument("--block", action="append", default=[],
                        help="ブロックする cookie（同上）")
    parser.add_argument("--block-domain", action="append", default=[],
                        help="ブロックするドメイン（正規表現）")
    parser.add_argument("--dry-run", action="store_true",
                        help="実際に add_cookie せず、フィルタ結果だけ表示")
    parser.add_argument("--quiet", action="store_true",
                        help="詳細ログを抑制")
    return parser.parse_args()

def main():
    args = parse_args()

    url = args.url
    profile_name = args.profile_name
    profile_path = os.path.abspath(f"profiles/{profile_name}")
    domain = url.split("//")[-1].split("/")[0]
    cookie_file = f"output/cookies_{domain}.json"

    # Chrome 起動設定
    options = Options()
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_experimental_option("detach", True)

    driver = webdriver.Chrome(options=options)
    print(f"[INFO] Chrome 起動 & {url} にアクセス中...")
    driver.get(url)
    time.sleep(3)

    # Cookieファイル存在確認
    if not os.path.exists(cookie_file):
        print(f"[❌ エラー] Cookie ファイルが存在しません: {cookie_file}")
        sys.exit(1)

    # Cookie読み込み
    with open(cookie_file, "r", encoding="utf-8") as f:
        cookies = json.load(f)

    # フィルタ設定の読み込み + CLI上書き/追加
    allow_re, block_re, block_domain_re = load_filters(args.filters)
    allow_re, block_re, block_domain_re = merge_cli_filters(
        allow_re, block_re, block_domain_re, args
    )

    # フィルタ適用
    before = len(cookies)
    cookies = filter_cookies(cookies, allow_re, block_re, block_domain_re, verbose=(not args.quiet))
    after = len(cookies)
    print(f"[INFO] フィルタ適用: {before} -> {after} 件")

    # ドライランの場合はここで終了
    if args.dry_run:
        print("[DRY-RUN] add_cookie は実行しません。終了します。")
        driver.quit()
        return

    # 既存Cookieをクリアしてから適用
    driver.delete_all_cookies()
    skipped = 0
    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
        except Exception as e:
            skipped += 1
            if not args.quiet:
                print(f"[WARN] Cookie 無視: {cookie.get('name')} - {e}")

    print(f"[INFO] Cookie 適用後に再読み込みします... (skip: {skipped})")
    driver.get(url)

if __name__ == "__main__":
    main()

# tools/make_all_except_auth.py
import json, sys, os

if len(sys.argv) < 3:
    print("Usage: py -3 tools\\make_all_except_auth.py <in.json> <out.json>")
    raise SystemExit(1)

src = sys.argv[1]
dst = sys.argv[2]

with open(src, "r", encoding="utf-8") as f:
    data = json.load(f)

# Exclude authentication-related cookies only (add more here if needed)
DENY = {"reddit_session", "token_v2", "csrf_token"}

kept = [c for c in data.get("cookies", []) if c.get("name") not in DENY]
data["cookies"] = kept

os.makedirs(os.path.dirname(dst), exist_ok=True)
with open(dst, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"kept {len(kept)} cookies -> {dst}")




HirokiKurano Cookie Privacy Project

This project develops a **Python-based toolset for extracting, importing, and managing cookies** from web browsers,  
with the aim of **testing cookie behavior and evaluating its impact on online privacy** in a controlled environment.

No real personal cookies or private data are used in this project.**  
All experiments are conducted exclusively on **test accounts and isolated local browser profiles** created by the researcher.

---

Project Schedule (Summer 2025)

| Date       | Task |
|------------|------|
| 24 Jun     | Topic research & technical background study |
| 2 Jul      | Develop cookie extraction tool (via Chrome DevTools Protocol) |
| 11 Jul     | Develop cookie import tool |
| 18 Jul     | Test extraction & switching between test browser profiles |
| 25 Jul     | Inspect and block specific cookies (e.g., login-related) |
| 8 Aug      | Cross-profile cookie mixing experiments |
| 15 Aug     | Privacy impact analysis & visualization |
| 5 Sep      | Draft submission of final report |
| 12 Sep     | Final submission |


---

Setup

git clone https://github.com/HirokiKurano/HirokiKurano_cookie_project.git
cd HirokiKurano_cookie_project
pip install -r requirements.txt


Usage
1. Extract Cookies

python extractor/cookie_extractor.py
Extracted cookies are saved in the format:
output/cookies_<domain>.json
※ All cookies are from test accounts only.

2. Import Cookies

python importer/cookie_importer.py
Reads a saved cookie file and applies it to a test browser profile.

Experiment Background & Purpose
Switch cookies between different test browser profiles to observe behavioral changes.

Identify login state changes or advertisement personalization caused by cookies.

Understand tracking mechanisms in a safe, controlled environment without privacy risks.

Cookie Filtering (Optional)
importer/cookie_importer.py can block or allow specific cookies (via regular expressions) using filters.json or CLI options.

filters <path>: Load filters.json
allow: Allowlist (only cookies matching domain/path/name are applied)
block: Blocklist (cookies matching these patterns are excluded)
block-domain: Block cookies based on domain
dry-run: Show filtering results without applying changes
quiet: Suppress detailed logs

Directory Structure


cookie-tool/
├── extractor/              # Cookie extraction scripts
│   └── cookie_extractor.py
├── importer/               # Cookie import scripts
│   └── cookie_importer.py
├── output/                 # Extracted cookie files (.gitignored)
├── requirements.txt        # Dependencies
├── .gitignore
└── README.md

Notes
Requires Google Chrome installed locally.

All tests are performed on local test accounts and browser profiles.

No personal or third-party cookies are handled.

License
MIT License © Hiroki Kurano
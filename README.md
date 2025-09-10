# HirokiKurano Cookie Project

This work designs a toolset in Python, for scraping, importing and storage of cookies and browser storage with the goal of testing of cookie behaviour and evaluation of the resulting user experience for **authentication**, **consent**, and **personalization** in the light of GDPR.

> **Note:** These experiments occur exclusively in **test accounts** and **local browser profiles**.  
> No cookies are set containing personal and/or third-party data.

---

## Features

### Extractor
- Retrieves cookies from supported browsers (**Chrome, Edge, Brave, Chromium, Firefox**).  
  *Note: for this project only Chrome was utilised.*
- Chrome DevTools Protocol (**CDP**) enables full capture including **HttpOnly** cookies.
- Fallback to **Selenium** when CDP is not available.
- Optional storage of **localStorage** and **sessionStorage** (`--with-storage`).
- Saves output in organized **JSON** with metadata.

### Importer
- Reads JSON already extracted and applies cookies/storage into a new browsing session.
- **CDP mode:** apply cookies before navigating and restore storage at document start.
- **Selenium mode:** inject cookies after page first load, then reload.
- Supports **pre-clear** of cookies and storage to start from a clean state.
- Optional **screenshot** capture for verification.

### Filtering & Variants
Individual JSON files can be modified to run on subsets of data:
- **Consent-only** (e.g., `ckns_policy`, `eu_cookie`)
- **Login-only** (e.g., `reddit_session`)
- **All-except-auth** (retain ads/personalization cookies, clear authentication)

### Reproducibility & Safety
- Cross-`runas` shell execution on Windows for profile isolation.
- Requires `COOKIE_LAB_TESTMODE=1` for safe use.
- Outputs are versioned JSON artefacts:
  - `cookies_<domain>.json`
  - `cookies_after_<domain>.json`

---

## Directory Structure

```text
cookie-tool/
├── extractor/              # Cookie extraction scripts
│   └── cookie_extractor.py
├── importer/               # Cookie import scripts
│   └── cookie_importer.py
├── tools/                  # Additional utilities
│   └── make_all_except_auth.py
├── output*/                # Run-specific output (JSON, screenshots) [gitignored]
├── requirements.txt        # Python dependencies
├── .gitignore
└── README.md

### Ethical Considerations

- No real users: all accounts are test accounts created by the researcher.
- No password storage: authentication is replicated using cookies only, never stored passwords.
- Transparency: all JSON outputs are explicit, reproducible, and local-only.
- Safety flag: requires COOKIE_LAB_TESTMODE=1 for execution.

### License
MIT License © Hiroki Kurano, 2025
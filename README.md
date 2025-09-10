HirokiKurano Cookie Project 

This work designs a toolset in Python, for scraping, importing and storage of cookies and browser storage with the goal of testing of cookie behaviour and evaluation of the resulting user experience for authentication, consent and personalization in the light of GDPR. 

Note that these experiments occur exclusively in test accounts and local browser profiles. 

No cookies are set containing personal and/or third-party data. 

 

Features 

Extractor 

Retrieves cookies from supported browsers (Chrome, Edge, Brave, Chromium, Firefox). 
 Note: for this part of project only Chrome was utilised. 

Chrome DevTools Protocol (CDP) is the way to go for full capture including HttpOnly cookies. 

Fallback to Selenium when CDP is not available. 

Optional storage of localStorage and sessionStorage (--with-storage). 

Saves output in organized JSON with metadata. 

Importer 

Reads out JSON already extracted and applies cookies/storage into a new browsing session. 

CDP mode: only apply cookies before navigating and restore after document start. 

Selenium Mode: inject cookies after page first load and then reload. 

And support the pre-clear of cookies and storage to make the state clear. 

Optional screenshot capture for verification. 

Filtering & Variants 

Individual files in the JSON can be modified to run on subsets of data: 

Consent-only (e.g., ckns_policy, eu_cookie) 

Login-only (e.g., reddit_session) 

All-except-auth (retains ads/personalization cookies, clear authentication) 

Reproducibility & Safety 

Cross-runas shell execution on Windows for profile isolation. 

Needs COOKIE_LAB_TESTMODE=1 to not use blindly on real accounts. 

Outputs are versioned JSON artifacts: 

cookies_<domain>.json 

cookies_after_<domain>.json 

 

Installation 

git clone https://github.com/HirokiKurano/HirokiKurano_cookie_project.git 
cd HirokiKurano_cookie_project 
pip install -r requirements.txt 
 

 

Usage 

Extract Cookies 

python extractor/cookie_extractor.py \ 
  --url https://www.bbc.co.uk/ \ 
  --profile user1 \ 
  --browser chrome \ 
  --mode cdp \ 
  --with-storage \ 
  --run-dir outputUser1 
 

Saves results to outputUser1/cookies_<domain>.json. 

Includes cookies and optional storage with metadata (browser, profile, timestamp, final domain). 

Import Cookies 

python importer/cookie_importer.py \ 
  --url https://www.bbc.co.uk/ \ 
  --profile user2 \ 
  --browser chrome \ 
  --mode cdp \ 
  --run-dir outputUser1 \ 
  --screenshot 
 

Reads cookies from cookies_<domain>.json and applies them into User2’s session. 

Produces verification JSON (cookies_after_<domain>.json) and optional screenshot. 

 

Directory Structure 

cookie-tool/ 
├── extractor/              # Cookie extraction scripts 
│   └── cookie_extractor.py 
├── importer/               # Cookie import scripts 
│   └── cookie_importer.py 
├── output*/                # Run-specific output (JSON, screenshots) [gitignored] 
├── requirements.txt        # Python dependencies 
├── .gitignore 
└── README.md 
 

 

Ethical Considerations 

No actual users constitute the data: all the users were test accounts set up by the researcher. 

No password storage: authentication is replicated using only distributing cookies, never through stored password. 

Transparancy: all JSON outputs are exlicit and repproductible, and are local results only. 

Safety flag: requires COOKIE_LAB_TESTMODE=1 to execution. 

 

License 

MIT License © Hiroki Kurano, 2025 

 
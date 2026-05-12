# # Sports Betting QA – Automation Framework
# import betting
# import pytest
#
# import tests
#
# # End-to-end UI tests (Selenium + Pytest) and API contract tests (requests + Pytest)
# # for the **Single Bet Placement** feature of the Sports Betting QA application.
#
#
#
# ## Project Structure
#
#
# betting-qa/
# ├── conftest.py                         # Shared fixtures: driver, api_session, reset
# ├── pages/
# │   ├── __init__.py
# │   ├── base_page.py                    # WebDriver wait/action helpers (BasePage)
# │   └── betting_page.py                 # Full Page Object for the betting UI
# ├── tests/
# │   ├── __init__.py
# │   ├── ui/
# │   │   ├── __init__.py
# │   │   └── test_bet_placement.py       # Automated Test 1 – E2E UI
# │   └── api/
# │       ├── __init__.py
# │       └── test_place_bet_api.py       # Automated Test 2 – API validation
# ├── docs/
# │   ├── test_plan.md                    # Part A – 6 prioritised test scenarios
# │   ├── bug_report.md                   # Part A – Execution results + 3 bug reports
# │   └── strategy.md                     # Part C – Automation rationale + recommendations
# ├── reports/                            # HTML report generated at runtime (git-ignored)
# ├── .gitignore
# ├── pytest.ini
# └── requirements.txt
# ```
#
# ---
#
# ## Prerequisites
#
# | Tool | Version |
# |---|---|
# | Python | 3.11 + |
# | Google Chrome | Latest stable |
# | ChromeDriver | Auto-managed by webdriver-manager |
#
# ---
#
# ## Setup
#
# ```bash
# # 1. Clone
# git clone <your-repo-url>
# cd betting-qa
#
# # 2. Virtual environment
# python -m venv .venv
# source .venv/bin/activate        # Windows: .venv\Scripts\activate
#
# # 3. Install dependencies
# pip install -r requirements.txt
# repr(``)
#
# ---
#
# ## Running Tests
#
# ```bash
# # All tests
# pytest
#
# # API only  (no browser, ~5 s)
# pytest tests/api/ -v
#
# # UI only
# pytest tests/ui/ -v
#
# # Custom user / base URL
# USER_ID=your-id APP_BASE_URL=https://qae-assignment-tau.vercel.app pytest
# ```
#
# Open `reports/test_report.html` in a browser after any run.
#
# ---
# #
# # ## Configuration
# #
# # Set via environment variables (defaults in `conftest.py`):
# #
# # | Variable | Default | Purpose |
# # |---|---|---|
# # | `APP_BASE_URL` | `https://qae-assignment-tau.vercel.app` | Application base URL |
# # | `USER_ID` | `candidate-K9vTb3Hd6Z` | `x-user-id` header value |
# #
#
#
# ## Stack Choices
#
# # | Tool | Reason |
# # |---|---|
# # | **Pytest** | Powerful fixture scoping, parametrize, markers |
# # | **Selenium 4** | Required; headless Chrome with `--headless=new` |
# # | **webdriver-manager** | Auto-downloads matching ChromeDriver |
# # | **requests** | Lightweight, expressive API testing |
# # | **pytest-html** | Zero-config HTML report |
# # | **Page Object Model** | Locators in one file; tests stay readable |
# # | **Explicit waits only** | `implicitly_wait(0)` prevents hidden race conditions |
#
#
#
# ## Known Issues
#
# # | Bug | Impact on tests |
# # |---|---|
# # | **BUG-001** – Min stake EUR 1.00 vs EUR 1.01 spec conflict | Tests assert EUR 1.00 accepted (3 sources agree); adjust if implementation enforces 1.01 |
# # | **BUG-002** – reset-balance response may differ from persisted state | `reset` fixture skips (not fails) if values diverge |
# # | **BUG-003** – Payout floating-point artefacts | Payout assertions use `pytest.approx(abs=0.01)` |

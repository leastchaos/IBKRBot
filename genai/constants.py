# constants.py
from enum import Enum
import os

# --- Application-Wide Constants ---
DATABASE_PATH = os.path.join(os.getcwd(), "genai", "database", "research_queue.db")
GEMINI_URL = "https://gemini.google.com/app"

# --- Worker Settings ---
MONITORING_INTERVAL_SECONDS = 10
JOB_TIMEOUT_SECONDS = 2700  # 45 minutes
MAX_RETRIES = 2
TELEGRAM_USER_PREFIX = "telegram:"

# --- NEW: Google API Constants ---
# The scopes define the level of access the script requests.
GDRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]

# Paths for Google API credentials.
CREDENTIALS_DIR = os.path.join(os.getcwd(), "credentials")

# --- CSS Selectors ---
PROMPT_TEXTAREA_CSS = ".ql-editor[contenteditable='true']"
DEEP_RESEARCH_BUTTON_XPATH = "//button[contains(., 'Deep Research')]"
START_RESEARCH_BUTTON_XPATH = "//button[contains(., 'Start research')]"
SHARE_EXPORT_BUTTON_XPATH = "//button[contains(., 'Export')]"
EXPORT_TO_DOCS_BUTTON_XPATH = "//button[contains(., 'Export to Docs')]"
RESPONSE_CONTENT_CSS = "div.response-content"
GENERATING_INDICATOR_CSS = "progress.mat-mdc-linear-progress"
TOOLS_BUTTON_XPATH = "//span[normalize-space()='Tools']"


# --- NEW: Selectors for attaching Google Drive files ---
# NOTE: These are placeholder selectors. You will need to inspect the Gemini
# web UI to find the correct values for these if they stop working.
ADD_FILE_BUTTON_XPATH = "//button[@aria-label='Open upload file menu']"
ADD_FROM_DRIVE_BUTTON_XPATH = "//button[@data-test-id='uploader-drive-button']"
DRIVE_URL_INPUT_CSS = "input[aria-label='Search in Drive or paste URL']"
INSERT_BUTTON_XPATH = "//button[contains(@aria-label, 'Insert') and not(@disabled)]"
PICKER_IFRAME_XPATH = "//iframe[contains(@src, 'docs.google.com/picker/v2/home')]"
# --- NEW: Share Dialog Selectors ---
SHARE_BUTTON_XPATH = "//button[descendant::mat-icon[@fonticon='share']]"
CREATE_PUBLIC_LINK_BUTTON_XPATH = "//button[contains(., 'Create public link')]"
PUBLIC_URL_INPUT_XPATH = "//input[contains(@value, 'gemini.google.com/share/')]"
CLOSE_SHARE_DIALOG_BUTTON_XPATH = "//button[contains(., 'Done')]"

class TaskType(str, Enum):
    """Defines the valid types of tasks the worker can process."""

    COMPANY_DEEP_DIVE = "company_deep_dive"
    TACTICAL_REVIEW = "tactical_review"
    UNDERVALUED_SCREENER = "undervalued_screener"
    PORTFOLIO_REVIEW = "portfolio_review"
    SHORT_COMPANY_DEEP_DIVE = "short_company_deep_dive"
    BUY_THE_DIP = "buy_the_dip"
    COVERED_CALL_REVIEW = "covered_call_strategy_review"
    BUY_RANGE_CHECK = "buy_range_check"
    EXTRACT_TICKERS = "extract_tickers"
    OTB_COVERED_CALL_REVIEW = "otb_covered_call_strategy_review"
    RISK_REVIEW = "risk_review"

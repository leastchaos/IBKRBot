from enum import Enum
import os

from genai.helpers.prompt_text import (
    PORTFOLIO_REVIEW_PROMPT,
    SCANNER_PROMPT,
    DEEPDIVE_PROMPT,
    SHORT_DEEPDIVE_PROMPT,
    TACTICAL_PROMPT,
    BUY_THE_DIP_DEEPDIVE_PROMPT,
)

# --- Application-Wide Constants ---
DATABASE_PATH = os.path.join(os.getcwd(), "genai", "database", "research_queue.db")
GEMINI_URL = "https://gemini.google.com/app"

# --- Worker Settings ---
MAX_ACTIVE_RESEARCH_JOBS = 2
MONITORING_INTERVAL_SECONDS = 15
MAX_RETRIES = 3
TELEGRAM_USER_PREFIX = "telegram:"
JOB_TIMEOUT_SECONDS = 60 * 60  # 30 minutes

# --- NEW: Google API Constants ---
# The scopes define the level of access the script requests.
GDRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]

# Paths for Google API credentials.
CREDENTIALS_DIR = os.path.join(os.getcwd(), "credentials")
GDRIVE_TOKEN_PATH = os.path.join(CREDENTIALS_DIR, "token.json")
GDRIVE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_DIR, "genai_cred.json")

# --- CSS Selectors ---
PROMPT_TEXTAREA_CSS = ".ql-editor[contenteditable='true']"
DEEP_RESEARCH_BUTTON_XPATH = "//button[contains(., 'Deep Research')]"
START_RESEARCH_BUTTON_XPATH = "//button[contains(., 'Start research')]"
SHARE_EXPORT_BUTTON_XPATH = "//button[contains(., 'Export')]"
EXPORT_TO_DOCS_BUTTON_XPATH = "//button[contains(., 'Export to Docs')]"
RESPONSE_CONTENT_CSS = "div.response-content"
GENERATING_INDICATOR_CSS = "progress.mat-mdc-linear-progress"

# --- Error Recovery ---
RECOVERABLE_ERROR_PHRASE = (
    "I encountered an error doing what you asked. Could you try again?"
)
SOMETHING_WENT_WRONG_RESPONSE = (
    "Sorry, something went wrong. Please try your request again."
)

# --- NEW: Selectors for attaching Google Drive files ---
# NOTE: These are placeholder selectors. You will need to inspect the Gemini
# web UI to find the correct values for these if they stop working.
ADD_FILE_BUTTON_XPATH = "//button[@aria-label='Open upload file menu']"
ADD_FROM_DRIVE_BUTTON_XPATH = "//button[@data-test-id='uploader-drive-button']"
DRIVE_URL_INPUT_CSS = "input[aria-label='Search in Drive or paste URL']"
INSERT_BUTTON_XPATH = "//button[contains(@aria-label, 'Insert') and not(@disabled)]"
PICKER_IFRAME_XPATH = "//iframe[contains(@src, 'docs.google.com/picker/v2/home')]"


class TaskType(str, Enum):
    """Defines the valid types of tasks the worker can process."""

    COMPANY_DEEP_DIVE = "company_deep_dive"
    DAILY_MONITOR = "daily_monitor"
    UNDERVALUED_SCREENER = "undervalued_screener"
    PORTFOLIO_REVIEW = "portfolio_review"
    SHORT_COMPANY_DEEP_DIVE = "short_company_deep_dive"
    BUY_THE_DIP = "buy_the_dip"


TASK_PROMPT_MAP = {
    TaskType.COMPANY_DEEP_DIVE: DEEPDIVE_PROMPT,
    TaskType.DAILY_MONITOR: TACTICAL_PROMPT,
    TaskType.UNDERVALUED_SCREENER: SCANNER_PROMPT,
    TaskType.PORTFOLIO_REVIEW: PORTFOLIO_REVIEW_PROMPT,
    TaskType.SHORT_COMPANY_DEEP_DIVE: SHORT_DEEPDIVE_PROMPT,
    TaskType.BUY_THE_DIP: BUY_THE_DIP_DEEPDIVE_PROMPT,
}

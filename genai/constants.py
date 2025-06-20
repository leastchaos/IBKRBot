import os

# --- Application-Wide Constants ---
DATABASE_PATH = os.path.join(os.getcwd(), 'genai', 'database', 'research_queue.db')
GEMINI_URL = "https://gemini.google.com/app"

# --- Worker Settings ---
MAX_ACTIVE_RESEARCH_JOBS = 2
MONITORING_INTERVAL_SECONDS = 15
MAX_RETRIES = 3

# --- NEW: Google API Constants ---
# The scopes define the level of access the script requests.
GDRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]

# Paths for Google API credentials.
CREDENTIALS_DIR = os.path.join(os.getcwd(), "credentials")
GDRIVE_TOKEN_PATH = os.path.join(CREDENTIALS_DIR, "token.json")
GDRIVE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_DIR, "credentials.json")

# --- CSS Selectors ---
PROMPT_TEXTAREA_CSS = ".ql-editor[contenteditable='true']"
DEEP_RESEARCH_BUTTON_XPATH = "//button[contains(., 'Deep Research')]"
START_RESEARCH_BUTTON_XPATH = "//button[contains(., 'Start research')]"
SHARE_EXPORT_BUTTON_XPATH = "//button[contains(., 'Export')]"
EXPORT_TO_DOCS_BUTTON_XPATH = "//button[contains(., 'Export to Docs')]"
RESPONSE_CONTENT_CSS = "div.response-content"
GENERATING_INDICATOR_CSS = "progress.mat-mdc-linear-progress"
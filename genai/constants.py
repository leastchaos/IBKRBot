import os

# --- Application Constants ---

# The single source of truth for the database path, relative to the project root.
DATABASE_PATH = os.path.join(os.getcwd(), 'genai', 'database', 'research_queue.db')

# You can also move other constants here if you like
GEMINI_URL = "https://gemini.google.com/app"
MAX_ACTIVE_RESEARCH_JOBS = 2
MONITORING_INTERVAL_SECONDS = 15
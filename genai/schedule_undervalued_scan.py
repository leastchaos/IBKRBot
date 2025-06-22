import sqlite3
import logging
import os
from genai.helpers.logging_config import setup_logging
from genai.constants import DATABASE_PATH, TaskType

def queue_undervalued_screener_task():
    """Adds a single 'undervalued_screener' task to the queue for the worker to handle."""
    setup_logging()
    logging.info("--- Queuing the Undervalued Company Screener Task ---")
    
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            # The worker will see this task and know to run the discovery prompts.
            # No company_name is needed for this task type.
            cursor.execute(
                "INSERT INTO tasks (task_type, requested_by) VALUES (?, ?)",
                (TaskType.UNDERVALUED_SCREENER, "undervalued_screener_script"),
            )
            conn.commit()
        logging.info("✅ Successfully queued the 'undervalued_screener' task.")
    except sqlite3.Error as e:
        logging.error(f"Database error during screener task scheduling: {e}")

if __name__ == "__main__":
    queue_undervalued_screener_task()
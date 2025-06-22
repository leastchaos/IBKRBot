import sqlite3
import logging
import os

from genai.helpers.logging_config import setup_logging
from genai.constants import DATABASE_PATH, TaskType

def queue_daily_companies_from_db():
    """
    Fetches the list of companies from the daily_monitoring_list table
    and adds them to the main tasks queue with the 'daily_monitor' type.
    """
    setup_logging()
    logging.info("Starting daily task scheduler...")
    
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            
            logging.info("Fetching companies from the daily monitoring list...")
            cursor.execute("SELECT company_name FROM daily_monitoring_list")
            companies_to_monitor = [row[0] for row in cursor.fetchall()]

            if not companies_to_monitor:
                logging.info("No companies in the daily monitoring list. Nothing to queue.")
                return

            logging.info(f"Found {len(companies_to_monitor)} companies to queue for daily monitoring.")
            queued_count = 0
            for company in companies_to_monitor:
                if company != "NYSE:BABA":
                    continue
                # --- CHANGE: Set the task_type to 'daily_monitor' ---
                cursor.execute(
                    "INSERT INTO tasks (company_name, requested_by, task_type) VALUES (?, ?, ?)",
                    (company, 'daily_monitor_script', TaskType.DAILY_MONITOR)
                )
                logging.info(f"Queued daily monitoring task for: {company}")
                queued_count += 1
            
            conn.commit()
            logging.info(f"Successfully queued {queued_count} daily monitoring tasks.")
            
    except sqlite3.Error as e:
        logging.error(f"Database error during daily task scheduling: {e}")

if __name__ == "__main__":
    queue_daily_companies_from_db()
import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DATABASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(DATABASE_DIR, 'research_queue.db')

def create_database():
    os.makedirs(DATABASE_DIR, exist_ok=True)
    logging.info(f"Connecting to database at: {DATABASE_PATH}")
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        create_tasks_table_query = """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            task_type TEXT NOT NULL DEFAULT 'company_deep_dive',
            status TEXT NOT NULL DEFAULT 'queued',
            requested_by TEXT,
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            report_url TEXT,
            summary TEXT,
            error_message TEXT
        );
        """
        logging.info("Ensuring 'tasks' table exists...")
        cursor.execute(create_tasks_table_query)
        
        create_daily_list_table_query = """
        CREATE TABLE IF NOT EXISTS daily_monitoring_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL UNIQUE,
            added_by TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        logging.info("Ensuring 'daily_monitoring_list' table exists...")
        cursor.execute(create_daily_list_table_query)
        
        conn.commit()
        conn.close()
        logging.info("Database and tables setup completed successfully.")
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")

if __name__ == "__main__":
    create_database()
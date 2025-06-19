import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'research_queue.db')

def add_retry_count_column():
    """Adds the 'retry_count' column to the tasks table if it doesn't exist."""
    logging.info(f"Connecting to database at: {DATABASE_PATH}")
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Check if the column already exists to make the script safely re-runnable
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'retry_count' not in columns:
            logging.info("Adding 'retry_count' column to 'tasks' table...")
            # We add it with a default of 0.
            cursor.execute("ALTER TABLE tasks ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0")
            conn.commit()
            logging.info("Column 'retry_count' added successfully.")
        else:
            logging.info("Column 'retry_count' already exists.")
            
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")

if __name__ == "__main__":
    add_retry_count_column()
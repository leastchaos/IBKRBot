import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'research_queue.db')

def add_target_chat_id_column():
    """Adds the 'target_chat_id' column to the tasks table if it doesn't exist."""
    logging.info(f"Connecting to database at: {DATABASE_PATH}")
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Check if the column already exists
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'target_chat_id' not in columns:
            logging.info("Adding 'target_chat_id' column to 'tasks' table...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN target_chat_id TEXT") # Can be NULL
            conn.commit()
            logging.info("Column 'target_chat_id' added successfully.")
        else:
            logging.info("Column 'target_chat_id' already exists.")
            
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")

if __name__ == "__main__":
    add_target_chat_id_column()
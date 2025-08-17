# genai/database/api.py
import logging
import os
import sqlite3

from genai.constants import DATABASE_PATH, MAX_RETRIES, TaskType


def _connect() -> sqlite3.Connection:
    """Creates and returns a new database connection."""
    # This ensures the database path is consistent
    return sqlite3.connect(DATABASE_PATH)


def handle_task_failure(task_id: int, error_message: str):
    """
    Handles a failed task by checking its retry count and deciding whether to
    re-queue it or mark it as a permanent error.
    """
    with _connect() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT retry_count FROM tasks WHERE id = ?", (task_id,))
            result = cursor.fetchone()
            if not result:
                logging.error(f"Could not find task ID {task_id} to handle failure.")
                return

            current_retries = result[0]

            if current_retries < MAX_RETRIES:
                new_retry_count = current_retries + 1
                logging.warning(
                    f"Task {task_id} failed. Retrying (attempt {new_retry_count}/{MAX_RETRIES}). "
                    f"Error: {error_message}"
                )
                cursor.execute(
                    "UPDATE tasks SET status = 'queued', retry_count = ? WHERE id = ?",
                    (new_retry_count, task_id),
                )
            else:
                logging.error(
                    f"Task {task_id} has failed after {MAX_RETRIES} retries. Marking as permanent error."
                )
                # Use the dedicated update function for consistency
                update_task_status(task_id, "error", error_message)

            conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Database error during failure handling for task {task_id}: {e}")


def get_latest_report_info(company_name: str) -> tuple[str, str] | None:
    """Fetches the report_url and timestamp from the most recent completed deep dive."""
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT report_url, requested_at FROM tasks
            WHERE company_name = ?
            AND task_type = ?
            AND status = 'completed'
            AND report_url IS NOT NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (company_name, TaskType.COMPANY_DEEP_DIVE.value), # Use .value for enums in queries
        )
        return cursor.fetchone()


def get_next_queued_task() -> tuple[int, str, str, str] | None:
    """Fetches the next available task from the queue."""
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, company_name, task_type, requested_by FROM tasks WHERE status = 'queued' ORDER BY requested_at ASC LIMIT 1"
        )
        return cursor.fetchone()


def update_task_status(task_id: int, status: str, error_msg: str | None = None) -> None:
    """Updates the status and optionally the error message of a task."""
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tasks SET status = ?, error_message = ? WHERE id = ?",
            (status, error_msg, task_id),
        )
        conn.commit()


def update_task_result(task_id: int, report_url: str, summary: str) -> None:
    """Updates the final results (URL and summary) for a completed task."""
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tasks SET report_url = ?, summary = ? WHERE id = ?",
            (report_url, summary, task_id),
        )
        conn.commit()


def add_tasks_from_screener(company_list: list[str], screener_task_id: int) -> None:
    """Adds a batch of new deep dive tasks discovered by a screener task."""
    tasks_to_add = []
    for company in company_list:
        if ":" not in company:
            logging.warning(f"Skipping invalid company format from screener: {company}")
            continue
        tasks_to_add.append(
            (company.strip(), f"screener_task_{screener_task_id}", TaskType.COMPANY_DEEP_DIVE.value)
        )

    with _connect() as conn:
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO tasks (company_name, requested_by, task_type) VALUES (?, ?, ?)",
            tasks_to_add,
        )
        conn.commit()


def update_task_type(task_id: int, new_task_type: TaskType) -> None:
    """Updates the task_type of a specific task."""
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tasks SET task_type = ? WHERE id = ?", (new_task_type.value, task_id)
        )
        conn.commit()


def queue_task(
    task_type: TaskType,
    requested_by: str,
    company_name: str | None = None,
) -> int | None:
    """
    Adds a new task to the queue in the database.

    Args:
        task_type: The type of task to queue (from the TaskType enum).
        requested_by: A string identifying who or what requested the task.
        company_name: The company ticker, if applicable for the task type.

    Returns:
        The ID of the newly created task, or None on failure.
    """
    logging.info(
        f"Queuing new task. Type: {task_type.value}, Company: {company_name or 'N/A'}, Requested by: {requested_by}"
    )
    try:
        with _connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (company_name, requested_by, task_type) VALUES (?, ?, ?)",
                (company_name, requested_by, task_type.value),
            )
            conn.commit()
            logging.info(f"Successfully queued task. Task ID: {cursor.lastrowid}")
            return cursor.lastrowid
    except sqlite3.Error as e:
        logging.error(
            f"Database error while queuing task for {company_name}: {e}",
            exc_info=True,
        )
        return None


def add_to_daily_monitoring_list(company_name: str, requested_by: str) -> bool:
    """Adds a company to the daily monitoring list, ignoring duplicates."""
    try:
        with _connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO daily_monitoring_list (company_name, added_by) VALUES (?, ?)",
                (company_name, requested_by),
            )
            conn.commit()
            # cursor.rowcount will be 1 if a row was inserted, 0 if it was ignored.
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Database error adding '{company_name}' to daily list: {e}")
        return False

def remove_from_daily_monitoring_list(company_name: str) -> bool:
    """Removes a company from the daily monitoring list."""
    try:
        with _connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM daily_monitoring_list WHERE company_name = ?", (company_name,)
            )
            conn.commit()
            # cursor.rowcount will be > 0 if a row was deleted.
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Database error removing '{company_name}' from daily list: {e}")
        return False

def get_daily_monitoring_list() -> list[str]:
    """Returns a sorted list of all companies on the daily monitoring list."""
    try:
        with _connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT company_name FROM daily_monitoring_list ORDER BY company_name ASC")
            return [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Database error listing daily companies: {e}")
        return []
    
def trigger_daily_monitor_task() -> list[str]:
    """Queues a new daily monitor task."""
    logging.info("Triggering daily monitor task...")
    companies_monitored = []
    try:
        with _connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT company_name FROM daily_monitoring_list")
            companies = cursor.fetchall()
        if not companies:
            logging.warning("No companies found in the daily monitoring list.")
            return []
        for company in companies:
            logging.info(f"Queuing daily monitor task for {company[0]}")
            task_id = queue_task(
                task_type=TaskType.TACTICAL_REVIEW,  # Assuming TACTICAL_REVIEW is the correct type for daily monitoring
                requested_by="daily_monitor_trigger",
                company_name=company[0]
            )
            if task_id:
                logging.info(f"Successfully queued daily monitor task for {company[0]} with ID {task_id}")
                companies_monitored.append(company[0])
            else:
                logging.error(f"Failed to queue daily monitor task for {company[0]}")
    except sqlite3.Error as e:
        logging.error(f"Database error triggering daily monitor task: {e}")
    return companies_monitored
    
if __name__ == "__main__":
    # This is just for testing the database setup
    logging.basicConfig(level=logging.INFO)
    trigger_daily_monitor_task()
    logging.info("Database setup complete.")
import logging
import sqlite3

from genai.constants import DATABASE_PATH, MAX_RETRIES, TaskType


def _connect() -> sqlite3.Connection:
    """Creates and returns a new database connection."""
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
                update_task_status(task_id, "error", error_message)

            conn.commit()

        except sqlite3.Error as e:
            logging.error(f"Database error during failure handling for task {task_id}: {e}")


def get_latest_report_info( company_name: str
) -> tuple[str, str] | None:
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
            (company_name, TaskType.COMPANY_DEEP_DIVE),
        )
        result = cursor.fetchone()
        if not result:
            logging.warning(
                f"No previous completed deep dive with a report URL found for {company_name}."
            )
            return None
        return result


def get_next_queued_task() -> tuple[int, str, str, str] | None:
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, company_name, task_type, requested_by FROM tasks WHERE status = 'queued' ORDER BY requested_at ASC LIMIT 1"
        )
        return cursor.fetchone()


def update_task_status(
    task_id: int, status: str, error_msg: str | None = None
) -> None:
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
    with _connect() as conn:
        cursor = conn.cursor()
        for company in company_list:
            if ":" not in company:
                logging.warning(f"Skipping invalid company format from screener: {company}")
                continue
            cursor.execute(
                "INSERT INTO tasks (company_name, requested_by, task_type) VALUES (?, ?, ?)",
                (company.strip(), f"screener_task_{screener_task_id}", "company_deep_dive"),
            )
        conn.commit()

def claim_next_queued_task() -> tuple[int, str, str, str] | None:
    """Atomically finds the next queued task and updates its status to 'processing'."""
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, company_name, task_type, requested_by FROM tasks WHERE status = 'queued' ORDER BY requested_at ASC LIMIT 1"
        )
        task = cursor.fetchone()
        if task:
            task_id = task[0]
            cursor.execute("UPDATE tasks SET status = 'processing' WHERE id = ?", (task_id,))
            conn.commit()
            return task
        return None

def update_task_type(task_id: int, new_task_type: str) -> None:
    """Updates the task_type of a specific task."""
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tasks SET task_type = ? WHERE id = ?", (new_task_type, task_id)
        )
        conn.commit()
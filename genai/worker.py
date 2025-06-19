import logging
import sqlite3
import time
from typing import Any

# --- UPDATED IMPORT BLOCK ---
from genai.helpers.config import Settings, get_settings
from genai.helpers.google_api_helpers import get_drive_service
from genai.constants import DATABASE_PATH
from genai.helpers.prompt_text import PROMPT_TEXT, PROMPT_TEXT_2, PROMPT_TEXT_3
from genai.helpers.logging_config import setup_logging
from genai.workflow import (
    initialize_driver,
    navigate_to_url,
    perform_deep_research,
    process_completed_job,  # <-- Now imported
    ResearchJob,  # <-- TypedDict now imported
)

# --- END UPDATED IMPORT BLOCK ---

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from genai.helpers.prompt_text import PROMPT_TEXT, PROMPT_TEXT_2
from genai.workflow import get_response, enter_prompt_and_submit
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# --- Constants ---
MAX_ACTIVE_RESEARCH_JOBS = 2
MONITORING_INTERVAL_SECONDS = 15
MAX_RETRIES = 3


# --- Database Helper Functions (Unchanged) ---
def handle_task_failure(conn: sqlite3.Connection, task_id: int, error_message: str):
    """
    Handles a failed task by checking its retry count and deciding whether to
    re-queue it or mark it as a permanent error.
    """
    cursor = conn.cursor()
    try:
        # First, get the current retry count for the task
        cursor.execute("SELECT retry_count FROM tasks WHERE id = ?", (task_id,))
        result = cursor.fetchone()
        if not result:
            logging.error(f"Could not find task ID {task_id} to handle failure.")
            return

        current_retries = result[0]
        
        if current_retries < MAX_RETRIES:
            # Increment retry count and set status back to 'queued'
            new_retry_count = current_retries + 1
            logging.warning(
                f"Task {task_id} failed. Retrying (attempt {new_retry_count}/{MAX_RETRIES}). "
                f"Error: {error_message}"
            )
            cursor.execute(
                "UPDATE tasks SET status = 'queued', retry_count = ? WHERE id = ?",
                (new_retry_count, task_id)
            )
        else:
            # Max retries reached, mark as a permanent error
            logging.error(
                f"Task {task_id} has failed after {MAX_RETRIES} retries. Marking as permanent error."
            )
            update_task_status(conn, task_id, "error", error_message)
        
        conn.commit()

    except sqlite3.Error as e:
        logging.error(f"Database error during failure handling for task {task_id}: {e}")

def get_next_queued_task(conn: sqlite3.Connection) -> tuple[int, str, str] | None:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, company_name, task_type FROM tasks WHERE status = 'queued' ORDER BY requested_at ASC LIMIT 1"
    )
    return cursor.fetchone()


def update_task_status(
    conn: sqlite3.Connection, task_id: int, status: str, error_msg: str | None = None
) -> None:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tasks SET status = ?, error_message = ? WHERE id = ?",
        (status, error_msg, task_id),
    )
    conn.commit()


def update_task_result(
    conn: sqlite3.Connection, task_id: int, report_url: str, summary: str
) -> None:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tasks SET report_url = ?, summary = ? WHERE id = ?",
        (report_url, summary, task_id),
    )
    conn.commit()


def handle_screener_task(
    driver: WebDriver, task_id: int, conn: sqlite3.Connection
) -> None:
    """
    Performs the discovery workflow: runs prompts 1 & 2, then queues up new tasks.
    This is called by the main worker loop.
    """

    logging.info(f"Handling screener task ID: {task_id}")
    try:
        navigate_to_url(driver, "https://gemini.google.com/app")
        perform_deep_research(driver, PROMPT_TEXT)
        WebDriverWait(driver, 1200).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Export')]"))
        )

        responses_before = len(
            driver.find_elements(By.CSS_SELECTOR, ".response-content")
        )
        enter_prompt_and_submit(driver, PROMPT_TEXT_2)
        company_list = get_response(driver, responses_before, is_csv=True)

        if not isinstance(company_list, list):
            raise ValueError("Screener did not return a valid company list.")

        logging.info(
            f"Screener discovered {len(company_list)} companies. Queuing them for deep dive..."
        )
        cursor = conn.cursor()
        for company in company_list:
            cursor.execute(
                "INSERT INTO tasks (company_name, requested_by, task_type) VALUES (?, ?, ?)",
                (company.strip(), f"screener_task_{task_id}", "company_deep_dive"),
            )
        conn.commit()
        update_task_status(conn, task_id, "completed")
    except Exception as e:
        logging.error(f"Error handling screener task {task_id}.", exc_info=True)
        update_task_status(conn, task_id, "error", str(e))


def handle_deep_dive_task(
    driver: WebDriver,
    task_id: int,
    company_name: str,
    active_jobs: dict[int, ResearchJob],
) -> None:
    """
    Launches a deep dive research task in a new tab and adds it to the active job pool.
    This is called by the main worker loop.
    """
    logging.info(f"Launching deep dive for task ID: {task_id}, Company: {company_name}")
    driver.switch_to.new_window("tab")
    new_handle: str = driver.current_window_handle

    active_jobs[task_id] = {
        "task_id": task_id,
        "handle": new_handle,
        "company_name": company_name,
        "status": "processing",
        "started_at": time.time(),
    }

    navigate_to_url(driver, "https://gemini.google.com/app")
    prompt = f"{PROMPT_TEXT_3} {company_name}."
    perform_deep_research(driver, prompt)


# --- Main Worker Logic ---
def main() -> None:
    """The main worker loop that processes tasks from the queue based on their type."""
    setup_logging()
    config: Settings = get_settings()
    service: Any = get_drive_service()
    driver: WebDriver | None = None
    active_jobs: dict[int, ResearchJob] = {}

    try:
        driver = initialize_driver(
            config.chrome.user_data_dir,
            config.chrome.profile_directory,
            config.chrome.chrome_driver_path,
            config.chrome.download_dir,
        )
        original_tab: str = driver.current_window_handle
        logging.info("Unified Worker started. Monitoring task queue...")

        while True:
            completed_task_ids: list[int] = []
            for task_id, job in list(active_jobs.items()):
                try:
                    driver.switch_to.window(job["handle"])
                    if driver.find_elements(
                        By.XPATH, "//button[contains(., 'Export')]"
                    ):

                        # The call to the imported function
                        final_status, results = process_completed_job(
                            driver, job, config, service
                        )

                        with sqlite3.connect(DATABASE_PATH) as conn:
                            update_task_status(
                                conn,
                                task_id,
                                final_status,
                                results.get("error_message"),
                            )
                            if final_status == "completed":
                                update_task_result(
                                    conn,
                                    task_id,
                                    results.get("report_url", ""),
                                    results.get("summary", ""),
                                )
                            else:
                                # --- CHANGE: Call the new failure handler ---
                                error_msg = results.get("error_message", "Processing failed.")
                                handle_task_failure(conn, task_id, error_msg)
                        completed_task_ids.append(task_id)

                except Exception:
                    logging.error(
                        f"Error checking active job for task ID {task_id}. Marking as errored.",
                        exc_info=True,
                    )
                    with sqlite3.connect(DATABASE_PATH) as conn:
                        update_task_status(
                            conn, task_id, "error", "Worker failed to check job status."
                        )
                    completed_task_ids.append(task_id)

            # Clean up finished jobs
            for task_id in completed_task_ids:
                if task_id in active_jobs:
                    handle = active_jobs.pop(task_id)["handle"]
                    logging.info(f"Task {task_id} processing finished. Closing tab.")
                    try:
                        driver.switch_to.window(handle)
                        driver.close()
                    except Exception as e:
                        logging.warning(
                            f"Could not close window for task {task_id}: {e}"
                        )
                    finally:
                        driver.switch_to.window(original_tab)

            # Fetch and dispatch new tasks
            with sqlite3.connect(DATABASE_PATH) as conn:
                if len(active_jobs) < MAX_ACTIVE_RESEARCH_JOBS:
                    task = get_next_queued_task(conn)
                    if task:
                        task_id, company_name, task_type = task
                        update_task_status(conn, task_id, "processing")

                        if task_type == "undervalued_screener":
                            driver.switch_to.window(original_tab)
                            handle_screener_task(driver, task_id, conn)

                        elif task_type == "company_deep_dive":
                            handle_deep_dive_task(
                                driver, task_id, company_name, active_jobs
                            )
                            driver.switch_to.window(original_tab)

            logging.info(
                f"Monitoring... {len(active_jobs)} active deep dives. Sleeping for {MONITORING_INTERVAL_SECONDS}s."
            )
            time.sleep(MONITORING_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logging.info("Shutdown signal received.")
    except Exception:
        logging.critical(
            "A critical error occurred in the worker's main loop.", exc_info=True
        )
    finally:
        if driver:
            logging.info("Closing WebDriver.")
            driver.quit()
        logging.info("Worker process terminated.")


if __name__ == "__main__":
    main()

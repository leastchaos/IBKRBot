import logging
import sqlite3
import time
from typing import Any

# --- UPDATED IMPORT BLOCK ---
from genai.helpers.config import Settings, get_settings
from genai.helpers.google_api_helpers import get_drive_service
from genai.constants import (
    DATABASE_PATH,
    RESPONSE_CONTENT_CSS,
    SHARE_EXPORT_BUTTON_XPATH,
    TASK_PROMPT_MAP,
)
from genai.helpers.prompt_text import (
    PROMPT_TEXT,
    PROMPT_TEXT_2,
)
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
                (new_retry_count, task_id),
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


def get_next_queued_task(conn: sqlite3.Connection) -> tuple[int, str, str, str] | None:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, company_name, task_type, requested_by FROM tasks WHERE status = 'queued' ORDER BY requested_at ASC LIMIT 1"
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
            EC.element_to_be_clickable((By.XPATH, SHARE_EXPORT_BUTTON_XPATH))
        )

        responses_before = len(
            driver.find_elements(By.CSS_SELECTOR, RESPONSE_CONTENT_CSS)
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


def launch_research_task(
    driver: WebDriver,
    task_id: int,
    company_name: str,
    requested_by: str | None,
    prompt_template: str,
    task_type: str,
) -> ResearchJob | None:
    """
    Launches a research task in a new tab using a specified prompt.
    """
    logging.info(f"Launching research for task ID: {task_id}, Company: {company_name}")
    driver.switch_to.new_window("tab")
    new_handle: str = driver.current_window_handle
    navigate_to_url(driver)
    # Use the provided prompt template
    prompt = f"{prompt_template} {company_name}."
    success = perform_deep_research(driver, prompt)
    if not success:
        logging.error(f"Failed to launch research for task ID: {task_id}")
        try:
            driver.switch_to.window(new_handle)
            driver.close()
        except Exception as e:
            logging.warning(f"Could not close window for failed task {task_id}: {e}")
        return None
    new_job_details: ResearchJob = {
        "task_id": task_id,
        "handle": new_handle,
        "company_name": company_name,
        "status": "processing",
        "started_at": time.time(),
        "requested_by": requested_by,
        "task_type": task_type,
    }
    return new_job_details


# --- Decomposed Main Loop Functions ---


def check_and_process_active_jobs(
    driver: WebDriver,
    active_jobs: dict[int, ResearchJob],
    config: Settings,
    service: Any,
) -> list[int]:
    """Checks all active jobs, processes any that are complete, and returns their IDs."""
    completed_task_ids: list[int] = []
    for task_id, job in list(active_jobs.items()):
        try:
            driver.switch_to.window(job["handle"])
            if not driver.find_elements(By.XPATH, SHARE_EXPORT_BUTTON_XPATH):
                continue  # Guard clause: If not complete, skip to the next job.

            final_status, results = process_completed_job(driver, job, config, service)

            with sqlite3.connect(DATABASE_PATH) as conn:
                if final_status == "completed":
                    update_task_status(conn, task_id, "completed")
                    update_task_result(
                        conn,
                        task_id,
                        results.get("report_url", ""),
                        results.get("summary", ""),
                    )
                else:  # final_status is 'error'
                    error_msg = results.get("error_message", "Post-processing failed.")
                    handle_task_failure(conn, task_id, error_msg)

            completed_task_ids.append(task_id)

        except Exception as e:
            error_str = (
                f"Worker failed while checking job status: {e.__class__.__name__}"
            )
            logging.error(
                f"Error checking active job for task ID {task_id}. {error_str}",
                exc_info=True,
            )
            with sqlite3.connect(DATABASE_PATH) as conn:
                handle_task_failure(conn, task_id, error_str)
            completed_task_ids.append(task_id)

    return completed_task_ids


def cleanup_finished_jobs(
    driver: WebDriver,
    active_jobs: dict[int, ResearchJob],
    completed_ids: list[int],
    original_tab: str,
) -> None:
    """Removes completed jobs from the active pool and closes their browser tabs."""
    for task_id in completed_ids:
        if task_id not in active_jobs:
            continue

        handle = active_jobs.pop(task_id)["handle"]
        logging.info(f"Task {task_id} processing finished. Closing tab.")
        try:
            driver.switch_to.window(handle)
            driver.close()
        except Exception as e:
            logging.warning(f"Could not close window for task {task_id}: {e}")
        finally:
            driver.switch_to.window(original_tab)


def dispatch_new_task(driver: WebDriver, num_active_jobs: int) -> ResearchJob | None:
    """Checks for queued tasks and dispatches them if slots are available."""
    if num_active_jobs >= MAX_ACTIVE_RESEARCH_JOBS:
        return  # Guard clause: Exit if no slots are free.

    with sqlite3.connect(DATABASE_PATH) as conn:
        task = get_next_queued_task(conn)
        if not task:
            return None

        task_id, company_name, task_type, requested_by = task
        update_task_status(conn, task_id, "processing")

        try:
            if task_type == "undervalued_screener":
                handle_screener_task(driver, task_id, conn)
                return None
            prompt_template = TASK_PROMPT_MAP.get(task_type)
            if not prompt_template:
                error_msg = f"No prompt template found for task type '{task_type}'."
                logging.error(f"Skipping task {task_id}. {error_msg}")
                # Mark as a permanent error since it's a configuration issue
                update_task_status(conn, task_id, "error", error_msg)
                return None

            logging.info(
                f"Dispatching task {task_id} ({task_type}) with selected prompt."
            )
            new_job = launch_research_task(
                driver, task_id, company_name, requested_by, prompt_template, task_type
            )
            if not new_job:
                handle_task_failure(
                    conn, task_id, "Failed to launch research in browser."
                )
                return None

            return new_job

        except Exception as e:
            # This will catch failures from launch_research_task or handle_screener_task
            logging.error(f"Failed to dispatch task {task_id}.", exc_info=True)
            handle_task_failure(
                conn, task_id, f"Failed during dispatch: {e.__class__.__name__}"
            )


# --- Simplified main() Function ---


def main() -> None:
    """The main worker loop that orchestrates all tasks."""
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
            # The main loop is now extremely simple and readable.
            completed_ids = check_and_process_active_jobs(
                driver, active_jobs, config, service
            )

            if completed_ids:
                cleanup_finished_jobs(driver, active_jobs, completed_ids, original_tab)
            driver.switch_to.window(original_tab)
            new_job = dispatch_new_task(driver, len(active_jobs))
            if new_job:
                active_jobs[new_job["task_id"]] = new_job
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

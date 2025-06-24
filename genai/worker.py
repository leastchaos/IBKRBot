import logging
import sqlite3
import time
from typing import Any
from datetime import datetime, timedelta

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from genai.constants import (
    DATABASE_PATH,
    MAX_ACTIVE_RESEARCH_JOBS,
    MAX_RETRIES,
    MONITORING_INTERVAL_SECONDS,
    RESPONSE_CONTENT_CSS,
    SHARE_EXPORT_BUTTON_XPATH,
    TASK_PROMPT_MAP,
    TaskType,
)
from genai.helpers.config import Settings, get_settings
from genai.helpers.google_api_helpers import get_drive_service
from genai.helpers.helpers import save_debug_screenshot
from genai.helpers.logging_config import setup_logging
from genai.helpers.prompt_text import PROMPT_TEXT_2
from genai.workflow import (
    ResearchJob,
    enter_prompt_and_submit,
    get_response,
    initialize_driver,
    navigate_to_url,
    perform_daily_monitor_research,
    perform_deep_research,
    process_completed_job,
)


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


def get_latest_report_info(
    conn: sqlite3.Connection, company_name: str
) -> tuple[str, str] | None:
    """Fetches the report_url and timestamp from the most recent completed deep dive."""
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


def process_completed_screener(
    driver: WebDriver, job: ResearchJob
) -> tuple[str, dict]:
    """
    Processes a completed screener job by extracting company names and queuing new tasks.
    """
    task_id = job["task_id"]
    logging.info(f"✅ Screener task {task_id} is COMPLETE. Extracting companies...")

    try:
        responses_before = len(
            driver.find_elements(By.CSS_SELECTOR, RESPONSE_CONTENT_CSS)
        )
        enter_prompt_and_submit(driver, PROMPT_TEXT_2)
        # Use a shorter timeout for this simple extraction
        company_list = get_response(driver, responses_before, is_csv=True, timeout=120)

        if not company_list or not isinstance(company_list, list):
            raise ValueError("Screener did not return a valid company list.")

        logging.info(
            f"Screener discovered {len(company_list)} companies. Queuing them for deep dive..."
        )
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            for company in company_list:
                # Ensure we only queue valid-looking tasks
                if ":" not in company:
                    logging.warning(
                        f"Skipping invalid company format from screener: {company}"
                    )
                    continue
                cursor.execute(
                    "INSERT INTO tasks (company_name, requested_by, task_type) VALUES (?, ?, ?)",
                    (company.strip(), f"screener_task_{task_id}", "company_deep_dive"),
                )
            conn.commit()

        return "completed", {}  # Return empty dict as there are no "results" like a URL

    except Exception:
        logging.error(
            f"❌ Error during post-processing for screener task {task_id}.",
            exc_info=True,
        )
        return "error", {
            "error_message": "Failed to extract or queue companies from screener."
        }


def launch_research_task(
    driver: WebDriver,
    task_id: int,
    company_name: str | None,
    requested_by: str | None,
    task_type: str,
) -> ResearchJob | None:
    """
    Launches a research task in a new tab using a specified prompt.
    """
    logging.info(
        f"Launching research for task ID: {task_id}, Type: {task_type}, Company: {company_name or 'N/A'}"
    )
    driver.switch_to.new_window("tab")
    new_handle: str = driver.current_window_handle

    try:
        navigate_to_url(driver)

        prompt_template = TASK_PROMPT_MAP.get(task_type)
        if not prompt_template:
            raise ValueError(f"No prompt template for task type '{task_type}'")

        success = False
        if task_type == TaskType.DAILY_MONITOR:
            if not company_name:
                raise ValueError("Daily monitor task requires a company name.")

            report_url = None
            with sqlite3.connect(DATABASE_PATH) as conn:
                report_info = get_latest_report_info(conn, company_name)

            if report_info:
                url, timestamp_str = report_info
                # SQLite timestamp format is 'YYYY-MM-DD HH:MM:SS'
                report_datetime = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                if datetime.now() - report_datetime <= timedelta(days=7):
                    report_url = url
                else:
                    logging.warning(
                        f"Previous report for {company_name} is older than 7 days (from {timestamp_str}). "
                        f"It will be regenerated via a full deep dive."
                    )

            if report_url:
                # We have a recent report, proceed as normal daily monitor
                success = perform_daily_monitor_research(
                    driver, prompt_template, report_url
                )
            else:
                # No report, or report is stale. Fall back to a full deep dive.
                # THIS IS THE CRITICAL FIX: We must update the task's type in the database
                # so that the generated report is correctly categorized as a deep dive.
                logging.warning(
                    f"Task {task_id} is falling back to a deep dive. Updating task type in DB."
                )
                with sqlite3.connect(DATABASE_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE tasks SET task_type = ? WHERE id = ?",
                        (TaskType.COMPANY_DEEP_DIVE, task_id),
                    )
                    conn.commit()
                # Also update the local variable to ensure the rest of the logic uses the new type.
                task_type = TaskType.COMPANY_DEEP_DIVE

                if not report_info:  # Only log this if there was no report at all
                    logging.warning(
                        f"No previous report URL for {company_name} (task {task_id}). "
                        f"Falling back to a full deep dive analysis."
                    )
                # Use the deep dive prompt instead
                deep_dive_prompt_template = TASK_PROMPT_MAP.get(task_type)
                if not deep_dive_prompt_template:
                    raise ValueError(
                        f"No prompt template for fallback task type '{TaskType.COMPANY_DEEP_DIVE}'"
                    )
                prompt = f"{deep_dive_prompt_template} {company_name}."
                success = perform_deep_research(driver, prompt)

        elif task_type == TaskType.UNDERVALUED_SCREENER:
            prompt = prompt_template
            success = perform_deep_research(driver, prompt)

        elif task_type == TaskType.COMPANY_DEEP_DIVE:
            prompt = f"{prompt_template} {company_name}."
            success = perform_deep_research(driver, prompt)

        else:
            raise ValueError(f"Unhandled task type '{task_type}'")

        if not success:
            raise RuntimeError("Research initiation workflow returned False.")

        new_job_details: ResearchJob = {
            "task_id": task_id,
            "handle": new_handle,
            "company_name": company_name or "Screener",  # Use a placeholder
            "status": "processing",
            "started_at": time.time(),
            "requested_by": requested_by,
            "task_type": task_type,
        }
        return new_job_details

    except Exception as e:
        logging.error(f"Failed to launch research for task ID {task_id}: {e}", exc_info=True)
        save_debug_screenshot(driver, f"launch_task_error_{task_id}")
        try:
            driver.switch_to.window(new_handle)
            driver.close()
            logging.info(f"Successfully closed tab for failed task {task_id}.")
        except Exception as e:
            logging.warning(f"Could not close window for failed task {task_id}: {e}")
        return None


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

            # --- NEW: Route to the correct processing function based on task type ---
            if job.get("task_type") == TaskType.UNDERVALUED_SCREENER:
                final_status, results = process_completed_screener(driver, job)
            else:
                final_status, results = process_completed_job(
                    driver, job, config, service
                )

            with sqlite3.connect(DATABASE_PATH) as conn:
                if final_status == "completed":
                    update_task_status(conn, task_id, "completed")
                    # Only update results if they exist (screener returns an empty dict)
                    if results.get("report_url"):
                        update_task_result(
                            conn, task_id, results["report_url"], results["summary"]
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
            save_debug_screenshot(driver, f"check_job_error_{task_id}")
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
            # REFACTORED: All tasks are now dispatched through the same logic.
            # For screener tasks, company_name will be None, which is fine.
            # The prompt for the screener is self-contained.
            if task_type not in TASK_PROMPT_MAP:
                error_msg = f"No prompt template found for task type '{task_type}'."
                logging.error(f"Skipping task {task_id}. {error_msg}")
                # Mark as a permanent error since it's a configuration issue
                update_task_status(conn, task_id, "error", error_msg)
                return None

            logging.info(
                f"Dispatching task {task_id} ({task_type}) with selected prompt."
            )
            new_job = launch_research_task(
                driver, task_id, company_name, requested_by, task_type
            )
            if not new_job:
                handle_task_failure(
                    conn, task_id, "Failed to launch research in browser."
                )
                return None

            return new_job

        except Exception as e:
            # This will catch failures from launch_research_task
            logging.error(f"Failed to dispatch task {task_id}.", exc_info=True)
            handle_task_failure(
                conn, task_id, f"Failed during dispatch: {e.__class__.__name__}"
            )
            return None


# --- Simplified main() Function ---


def main(headless: bool = True) -> None:
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
            headless=headless,
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
            logging.debug(
                f"Monitoring... {len(active_jobs)} active jobs. Sleeping for {MONITORING_INTERVAL_SECONDS}s."
            )
            time.sleep(MONITORING_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logging.info("Shutdown signal received.")
    except Exception:
        logging.critical(
            "A critical error occurred in the worker's main loop.", exc_info=True
        )
        if driver:
            save_debug_screenshot(driver, "worker_main_critical_error")
    finally:
        if driver:
            logging.info("Closing WebDriver.")
            driver.quit()
        logging.info("Worker process terminated.")


if __name__ == "__main__":
    main(headless=True)

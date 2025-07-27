import logging
import random
import sqlite3
import time
from datetime import datetime, timedelta

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import NoSuchWindowException
from genai.constants import (
    DATABASE_PATH,
    JOB_TIMEOUT_SECONDS,
    MAX_RETRIES,
    MONITORING_INTERVAL_SECONDS,
    RESPONSE_CONTENT_CSS,
    SHARE_EXPORT_BUTTON_XPATH,
    TASK_PROMPT_MAP,
    RECOVERABLE_ERROR_PHRASE,
    SOMETHING_WENT_WRONG_RESPONSE,
    TaskType,
)
from genai.helpers.config import Settings, get_settings
from genai.helpers.helpers import save_debug_screenshot
from genai.helpers.logging_config import setup_logging
from genai.helpers.prompt_text import EXTRACT_TICKERS_PROMPT
from genai.workflow import (
    ResearchJob,
    enter_prompt_and_submit,
    get_response,
    initialize_driver,
    navigate_to_url,
    perform_daily_monitor_research,
    perform_deep_research,
    perform_portfolio_review,
    process_completed_job,
)


def handle_task_failure(conn: sqlite3.Connection, task_id: int, error_message: str):
    """
    Handles a failed task by checking its retry count and deciding whether to
    re-queue it or mark it as a permanent error.
    """
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


def process_completed_screener(driver: WebDriver, job: ResearchJob) -> tuple[str, dict]:
    """
    Processes a completed screener job by extracting company names and queuing new tasks.
    """
    task_id = job["task_id"]
    logging.info(f"✅ Screener task {task_id} is COMPLETE. Extracting companies...")

    try:
        responses_before = len(
            driver.find_elements(By.CSS_SELECTOR, RESPONSE_CONTENT_CSS)
        )
        enter_prompt_and_submit(driver, EXTRACT_TICKERS_PROMPT)
        company_list = get_response(driver, responses_before, is_csv=True, timeout=120)

        if not company_list or not isinstance(company_list, list):
            raise ValueError("Screener did not return a valid company list.")

        logging.info(
            f"Screener discovered {len(company_list)} companies. Queuing them for deep dive..."
        )
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            for company in company_list:
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

        return "completed", {}

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
    account_name: str,
    config: Settings,
) -> ResearchJob | None:
    """
    Launches a research task in a new tab using a specified prompt.
    """
    logging.info(
        f"Launching research on account '{account_name}' for task ID: {task_id}, Type: {task_type}, Company: {company_name or 'N/A'}"
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
                report_datetime = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                if datetime.now() - report_datetime <= timedelta(days=7):
                    report_url = url
                else:
                    logging.warning(
                        f"Previous report for {company_name} is older than 7 days (from {timestamp_str}). "
                        f"It will be regenerated via a full deep dive."
                    )

            if report_url:
                success = perform_daily_monitor_research(
                    driver, prompt_template, report_url
                )
            else:
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
                task_type = TaskType.COMPANY_DEEP_DIVE

                if not report_info:
                    logging.warning(
                        f"No previous report URL for {company_name} (task {task_id}). "
                        f"Falling back to a full deep dive analysis."
                    )

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

        elif task_type in [
            TaskType.COMPANY_DEEP_DIVE,
            TaskType.SHORT_COMPANY_DEEP_DIVE,
            TaskType.BUY_THE_DIP,
        ]:
            prompt = f"{prompt_template} {company_name}."
            success = perform_deep_research(driver, prompt)

        elif task_type == TaskType.PORTFOLIO_REVIEW:
            success = perform_portfolio_review(
                driver, prompt_template, config.drive.portfolio_sheet_url
            )
        else:
            raise ValueError(f"Unhandled task type '{task_type}'")

        if not success:
            raise RuntimeError("Research initiation workflow returned False.")

        new_job_details: ResearchJob = {
            "task_id": task_id,
            "handle": new_handle,
            "company_name": company_name or "Not Required",
            "status": "processing",
            "started_at": time.time(),
            "requested_by": requested_by,
            "task_type": task_type,
            "error_recovery_attempted": False,
            "account_name": account_name,
        }
        return new_job_details

    except Exception as e:
        logging.error(
            f"Failed to launch research for task ID {task_id}: {e}", exc_info=True
        )
        save_debug_screenshot(driver, f"launch_task_error_{task_id}")
        try:
            driver.switch_to.window(new_handle)
            driver.close()
            logging.info(f"Successfully closed tab for failed task {task_id}.")
        except Exception as e:
            logging.warning(f"Could not close window for failed task {task_id}: {e}")
        return None


def check_and_process_active_jobs(
    driver_pool: dict[str, WebDriver],
    active_jobs: dict[int, ResearchJob],
    config: Settings,
) -> tuple[list[int], set[str]]:
    """Checks all active jobs, processes any that are complete, and returns their IDs."""
    completed_task_ids: list[int] = []
    crashed_accounts: set[str] = set()
    for task_id, job in list(active_jobs.items()):
        account_name = job["account_name"]
        if account_name in crashed_accounts:
            with sqlite3.connect(DATABASE_PATH) as conn:
                handle_task_failure(conn, task_id, "Browser session crashed")
            completed_task_ids.append(task_id)
            continue
        try:

            driver = driver_pool[account_name]
            driver.switch_to.window(job["handle"])

            if not driver.find_elements(By.XPATH, SHARE_EXPORT_BUTTON_XPATH):
                if time.time() - job["started_at"] > JOB_TIMEOUT_SECONDS:
                    logging.warning(
                        f"Task {task_id} for '{job['company_name']}' has timed out after "
                        f"{JOB_TIMEOUT_SECONDS / 60:.0f} minutes. Marking as failed."
                    )
                    with sqlite3.connect(DATABASE_PATH) as conn:
                        handle_task_failure(conn, task_id, "Job timed out")
                    completed_task_ids.append(task_id)
                    continue

                if not job.get("error_recovery_attempted"):
                    try:
                        all_responses = driver.find_elements(
                            By.CSS_SELECTOR, RESPONSE_CONTENT_CSS
                        )
                        if (
                            all_responses
                            and (
                                RECOVERABLE_ERROR_PHRASE
                                or SOMETHING_WENT_WRONG_RESPONSE
                            )
                            in all_responses[-1].text
                        ):
                            logging.warning(
                                f"Recoverable error found for task {task_id}. "
                                "Attempting to continue research..."
                            )
                            job["error_recovery_attempted"] = True
                            enter_prompt_and_submit(driver, "continue research")

                    except Exception as e:
                        logging.warning(
                            f"Could not check for recoverable error on task {task_id}: {e}"
                        )

                continue

            logging.info(
                f"Export button found for task {task_id}. Starting post-processing..."
            )
            final_status, results = ("error", {})
            if job.get("task_type") == TaskType.UNDERVALUED_SCREENER:
                final_status, results = process_completed_screener(driver, job)
            else:
                final_status, results = process_completed_job(driver, job, config)

            with sqlite3.connect(DATABASE_PATH) as conn:
                if final_status == "completed":
                    update_task_status(conn, task_id, "completed")
                    if results.get("report_url"):
                        update_task_result(
                            conn, task_id, results["report_url"], results["summary"]
                        )
                else:
                    error_msg = results.get("error_message", "Post-processing failed.")
                    handle_task_failure(conn, task_id, error_msg)

            completed_task_ids.append(task_id)
        except NoSuchWindowException:
            logging.warning(
                f"Browser window for task {task_id} has been closed. Marking as failed."
            )
            with sqlite3.connect(DATABASE_PATH) as conn:
                handle_task_failure(conn, task_id, "Browser window closed")
            completed_task_ids.append(task_id)
            crashed_accounts.add(account_name)
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

    return completed_task_ids, crashed_accounts


def cleanup_finished_jobs(
    driver_pool: dict[str, WebDriver],
    active_jobs: dict[int, ResearchJob],
    completed_ids: list[int],
    account_job_counts: dict[str, int],
    original_tabs: dict[str, str],
) -> None:
    """Removes completed jobs from the active pool and closes their browser tabs."""
    for task_id in completed_ids:
        if task_id not in active_jobs:
            continue

        job = active_jobs.pop(task_id)
        account_name = job["account_name"]
        handle = job["handle"]

        if account_name in account_job_counts:
            account_job_counts[account_name] -= 1
            if account_job_counts[account_name] < 0:
                account_job_counts[account_name] = 0

        logging.info(
            f"Task {task_id} finished. Account '{account_name}' now running {account_job_counts.get(account_name, 0)} jobs. Closing tab."
        )
        try:
            driver = driver_pool[account_name]
            original_tab = original_tabs[account_name]
            driver.switch_to.window(handle)
            driver.close()
            driver.switch_to.window(original_tab)
        except Exception as e:
            logging.warning(
                f"Could not close window for task {task_id} on account '{account_name}': {e}"
            )


def dispatch_new_task(
    driver_pool: dict[str, WebDriver],
    account_job_counts: dict[str, int],
    config: Settings,
) -> ResearchJob | None:
    """Checks for queued tasks and dispatches them if slots are available."""
    account_to_use = None
    shuffled_accounts = random.sample(
        config.chrome.accounts, k=len(config.chrome.accounts)
    )

    for account in shuffled_accounts:
        current_jobs = account_job_counts.get(account.name, 0)
        if current_jobs < account.max_concurrent_jobs:
            account_to_use = account.name
            break

    if account_to_use is None:
        return None

    with sqlite3.connect(DATABASE_PATH) as conn:
        task = get_next_queued_task(conn)
        if not task:
            return None

        account_job_counts[account_to_use] += 1
        task_id, company_name, task_type, requested_by = task
        update_task_status(conn, task_id, "processing")
        driver = driver_pool[account_to_use]

        try:
            if task_type not in TASK_PROMPT_MAP:
                error_msg = f"No prompt template found for task type '{task_type}'."
                logging.error(f"Skipping task {task_id}. {error_msg}")
                update_task_status(conn, task_id, "error", error_msg)
                account_job_counts[account_to_use] -= 1
                return None

            logging.info(
                f"Dispatching task {task_id} ({task_type}) to account '{account_to_use}'"
            )

            new_job = launch_research_task(
                driver,
                task_id,
                company_name,
                requested_by,
                task_type,
                account_to_use,
                config,
            )
            if not new_job:
                handle_task_failure(
                    conn, task_id, "Failed to launch research in browser."
                )
                account_job_counts[account_to_use] -= 1
                return None

            return new_job

        except Exception as e:
            logging.error(f"Failed to dispatch task {task_id}.", exc_info=True)
            handle_task_failure(
                conn, task_id, f"Failed during dispatch: {e.__class__.__name__}"
            )
            account_job_counts[account_to_use] -= 1
            return None


def main(headless: bool = True) -> None:
    """The main worker loop that orchestrates all tasks."""
    setup_logging()
    config: Settings = get_settings()
    driver_pool: dict[str, WebDriver] = {}
    original_tabs: dict[str, str] = {}
    active_jobs: dict[int, ResearchJob] = {}
    account_job_counts: dict[str, int] = {}

    try:
        if not config.chrome.accounts:
            logging.error("No accounts configured in settings. Exiting worker.")
            return

        while True:
            for account in config.chrome.accounts:
                if account.name in driver_pool:
                    continue
                logging.info(
                    f"Initializing or Restarting WebDriver for persistent profile: '{account.profile_directory}'..."
                )
                try:
                    driver = initialize_driver(
                        user_data_dir=account.user_data_dir,
                        profile_directory=account.profile_directory,
                        webdriver_path=config.chrome.chrome_driver_path,
                        download_dir=config.chrome.download_dir,
                        headless=headless,
                    )
                    driver_pool[account.name] = driver
                    original_tabs[account.name] = driver.current_window_handle
                    account_job_counts[account.name] = 0
                except Exception as e:
                    logging.error(
                        f"Failed to initialize WebDriver for account '{account.name}': {e}",
                        exc_info=True,
                    )
                    continue

            logging.info(
                f"Unified Worker started with {len(driver_pool)} accounts. Monitoring task queue..."
            )

            completed_ids, crashed_accounts = check_and_process_active_jobs(
                driver_pool, active_jobs, config
            )
            if crashed_accounts:
                logging.warning(
                    f"Detected crashed accounts: {', '.join(crashed_accounts)}. "
                    "Attempting to reinitialize WebDrivers for these accounts."
                )
                for account_name in crashed_accounts:
                    if account_name in driver_pool:
                        driver_pool[account_name].quit()
                        del driver_pool[account_name]
                        del original_tabs[account_name]
                        del account_job_counts[account_name]
            if completed_ids:
                cleanup_finished_jobs(
                    driver_pool,
                    active_jobs,
                    completed_ids,
                    account_job_counts,
                    original_tabs,
                )

            new_job = dispatch_new_task(driver_pool, account_job_counts, config)
            if new_job:
                active_jobs[new_job["task_id"]] = new_job

            job_counts_str = ", ".join(
                [f"{name}: {count}" for name, count in account_job_counts.items()]
            )
            logging.debug(
                f"Monitoring... {len(active_jobs)} active jobs. ({job_counts_str}). Sleeping for {MONITORING_INTERVAL_SECONDS}s."
            )
            time.sleep(MONITORING_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logging.info("Shutdown signal received.")
    except Exception:
        logging.critical(
            "A critical error occurred in the worker's main loop.", exc_info=True
        )
        if driver_pool:
            for account_name, driver in driver_pool.items():
                save_debug_screenshot(
                    driver, f"worker_main_critical_error_{account_name}"
                )
        logging.error(
            "Worker encountered a critical error. Please check the logs for details."
        )
    finally:
        if driver_pool:
            for account_name, driver in driver_pool.items():
                logging.info(f"Closing WebDriver for account '{account_name}'.")
                driver.quit()
        logging.info("Worker process terminated.")


if __name__ == "__main__":
    main(headless=True)

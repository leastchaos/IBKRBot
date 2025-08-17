# genai/worker.py
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict

from selenium.common.exceptions import (NoSuchWindowException,
                                        WebDriverException)

from genai import post_processing, workflows
from genai.browser_actions import Browser
from genai.constants import (GEMINI_URL, JOB_TIMEOUT_SECONDS, MONITORING_INTERVAL_SECONDS,
                           TaskType)
from genai.database import api as db
from genai.common.config import Settings, get_settings
from genai.common.utils import get_prompt
from genai.models import ResearchJob, WorkerState


# --- Worker Core Functions ---

def _ensure_drivers_are_running(state: WorkerState, headless: bool):
    """Ensures a WebDriver instance is running for each configured account."""
    for account in state.config.chrome.accounts:
        driver_crashed = False
        if account.name in state.browser_pool:
            try:
                _ = state.browser_pool[account.name].driver.current_window_handle
            except (NoSuchWindowException, WebDriverException):
                logging.warning(f"Driver for account '{account.name}' appears to have crashed.")
                driver_crashed = True

            if driver_crashed:
                state.account_job_counts[account.name] = 0
                del state.browser_pool[account.name]
                if account.name in state.original_tabs:
                    del state.original_tabs[account.name]

        if account.name not in state.browser_pool:
            try:
                browser_instance = Browser.initialize(
                    user_data_dir=account.user_data_dir,
                    profile_directory=account.profile_directory,
                    headless=headless,
                    webdriver_path=state.config.chrome.chrome_driver_path,
                    download_dir=state.config.chrome.download_dir,
                )
                state.browser_pool[account.name] = browser_instance
                state.original_tabs[account.name] = browser_instance.driver.current_window_handle
            except Exception as e:
                logging.error(f"Failed to initialize browser for {account.name}: {e}")

def _dispatch_new_task(state: WorkerState):
    """Checks for a queued task and dispatches it if a slot is available."""
    available_account = next(
        (
            acc
            for acc in state.config.chrome.accounts
            if state.account_job_counts.get(acc.name, 0) < acc.max_concurrent_jobs
        ),
        None,
    )
    if not available_account or available_account.name not in state.browser_pool:
        return

    task_data = db.get_next_queued_task()
    if not task_data:
        return

    task_id, company_name, task_type_str, requested_by = task_data
    task_type = TaskType(task_type_str)
    browser = state.browser_pool[available_account.name]

    logging.info(f"Dispatching task {task_id} ({task_type.value}) to account '{available_account.name}'")
    db.update_task_status(task_id, "processing")
    state.account_job_counts[available_account.name] += 1
    
    browser.driver.switch_to.new_window("tab")
    new_handle = browser.driver.current_window_handle
    
    browser.navigate_to_url(GEMINI_URL)
    
    prompt = get_prompt(task_type.value)
    if not prompt or task_type not in [TaskType.COMPANY_DEEP_DIVE, TaskType.SHORT_COMPANY_DEEP_DIVE, TaskType.BUY_THE_DIP]:
        logging.error(f"Prompt for task type '{task_type.value}' not found.")
        db.handle_task_failure(task_id, "Prompt not found")
        return

    success = False
    
    if task_type in [TaskType.COMPANY_DEEP_DIVE, TaskType.SHORT_COMPANY_DEEP_DIVE, TaskType.BUY_THE_DIP]:
        success = workflows.perform_deep_research(browser, f"{prompt} {company_name}")
    elif task_type == TaskType.UNDERVALUED_SCREENER:
         success = workflows.perform_deep_research(browser, prompt)
    elif task_type == TaskType.PORTFOLIO_REVIEW:
        success = workflows.perform_portfolio_review(browser, prompt, state.config.drive.portfolio_sheet_url)
    else:
        logging.warning(f"No workflow defined for task type: {task_type.value}")

    if success:
        new_job = ResearchJob(
            task_id=task_id,
            handle=new_handle,
            company_name=company_name or task_type.value,
            task_type=task_type,
            account_name=available_account.name,
            requested_by=requested_by,
            started_at=time.time(),
        )
        state.active_jobs[task_id] = new_job
    else:
        db.handle_task_failure(task_id, "Failed to launch research in browser.")
        state.account_job_counts[available_account.name] -= 1
        browser.driver.close()
        browser.driver.switch_to.window(state.original_tabs[available_account.name])

def _check_and_process_completed_jobs(state: WorkerState):
    """Checks active jobs, processes them if complete, and handles timeouts."""
    completed_task_ids = set()
    for task_id, job in list(state.active_jobs.items()):
        account_name = job.account_name
        browser = state.browser_pool.get(account_name)

        if not browser:
            db.handle_task_failure(task_id, "Browser session for this account has crashed.")
            completed_task_ids.add(task_id)
            continue

        try:
            browser.driver.switch_to.window(job.handle)
            
            if browser.is_job_complete():
                logging.info(f"Task {task_id} is complete. Starting post-processing.")
                
                if job.task_type == TaskType.UNDERVALUED_SCREENER:
                    status, results = post_processing.run_post_processing_for_screener(browser, job)
                else:
                    status, results = post_processing.run_post_processing_for_standard_job(browser, job, state.config)
                
                if status == "completed":
                    db.update_task_result(task_id, results.get("report_url", ""), results.get("summary", ""))
                else:
                    db.handle_task_failure(task_id, results.get("error_message", "Post-processing failed."))
                
                completed_task_ids.add(task_id)

            elif time.time() - job.started_at > JOB_TIMEOUT_SECONDS:
                logging.warning(f"Task {task_id} for '{job.company_name}' has timed out.")
                db.handle_task_failure(task_id, "Job timed out")
                completed_task_ids.add(task_id)

        except NoSuchWindowException:
            logging.error(f"Window for job {task_id} not found. Assuming it crashed.")
            db.handle_task_failure(task_id, "Browser window disappeared.")
            completed_task_ids.add(task_id)
        except Exception as e:
            logging.error(f"An unexpected error occurred while checking job {task_id}: {e}", exc_info=True)
            db.handle_task_failure(task_id, f"Worker error: {e.__class__.__name__}")
            completed_task_ids.add(task_id)

    # --- Cleanup completed jobs ---
    for task_id in completed_task_ids:
        if task_id in state.active_jobs:
            job = state.active_jobs.pop(task_id)
            account_name = job.account_name
            browser = state.browser_pool.get(account_name)
            
            state.account_job_counts[account_name] = max(0, state.account_job_counts[account_name] - 1)
            
            if browser:
                try:
                    browser.driver.switch_to.window(job.handle)
                    browser.driver.close()
                    browser.driver.switch_to.window(state.original_tabs[account_name])
                except (NoSuchWindowException, KeyError):
                    logging.warning(f"Could not close tab for job {task_id}, it may have already been closed.")

def _shutdown(state: WorkerState):
    """Gracefully shuts down all browser instances."""
    logging.info("Shutting down all webdrivers.")
    for browser in state.browser_pool.values():
        if browser.driver:
            browser.driver.quit()

def main(headless: bool = True):
    """The main entry point and loop for the worker."""
    from genai.common.logging_setup import setup_logging
    
    setup_logging()
    config = get_settings()
    worker_state = WorkerState(config=config)

    try:
        while True:
            _ensure_drivers_are_running(worker_state, headless)
            _check_and_process_completed_jobs(worker_state)
            _dispatch_new_task(worker_state)

            job_counts_str = ", ".join([f"{name}: {count}" for name, count in worker_state.account_job_counts.items()])
            logging.info(f"Monitoring... {len(worker_state.active_jobs)} active jobs. ({job_counts_str})")
            time.sleep(MONITORING_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logging.info("Shutdown signal received.")
    finally:
        _shutdown(worker_state)

if __name__ == "__main__":
    main(headless=False)
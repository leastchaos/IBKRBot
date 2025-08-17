# genai/post_processing.py
import logging
from datetime import datetime
from typing import TypedDict, Any

from genai.browser_actions import Browser
from genai.database.api import queue_task, add_tasks_from_screener
from genai.common.config import Settings, DriveSettings
from genai.helpers.google_api_helpers import (
    get_doc_id_from_url,
    get_google_doc_content,
    get_drive_service,
    rename_google_doc,
    move_file_to_folder,
    share_google_doc_publicly,
)
from genai.common.utils import get_prompt
from genai.helpers.notifications import send_report_to_telegram
from genai.constants import TaskType
from genai.models import ResearchJob, ProcessingResult

def _extract_summary(report_text: str) -> str:
    """Parses the full report text to extract the executive summary."""
    summary_marker_start = "//-- EXECUTIVE SUMMARY START --//"
    summary_marker_end = "//-- EXECUTIVE SUMMARY END --//"
    
    try:
        # Extract the text after the start marker
        summary = report_text.split(summary_marker_start)[1]
        # Extract the text before the end marker
        summary = summary.split(summary_marker_end)[0].strip()
        
        # Truncate if necessary for Telegram's message limit
        if len(summary) > 4000:
            summary = summary[:4000] + "..."
        return summary
    except IndexError:
        logging.warning("Could not find executive summary markers. Using default message.")
        return "Executive summary could not be automatically extracted from the report."

def _manage_drive_file(service: Any, doc_id: str, company_name: str, task_type: str, drive_config: DriveSettings):
    """Renames, moves, and shares the Google Doc."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        new_doc_title = f"{timestamp}_{company_name}_{task_type}"
        
        rename_google_doc(service, doc_id, new_doc_title)
        if drive_config and drive_config.folder_id:
            move_file_to_folder(service, doc_id, drive_config.folder_id)
        share_google_doc_publicly(service, doc_id)
    except Exception:
        logging.error(f"An error occurred while managing Google Drive file {doc_id}.", exc_info=True)


def _perform_buy_range_check(browser: Browser, prompt: str) -> bool:
    """Performs a follow-up prompt to check if the stock is in the buy range."""
    logging.info("Performing buy-range check...")
    
    # --- SIMPLIFIED LOGIC ---
    response = browser.enter_prompt_and_get_response(prompt, timeout=120)
    
    if response and "YES" in response.upper():
        return True
    
    return False


def run_post_processing_for_standard_job(browser: Browser, job: ResearchJob, config: Settings) -> tuple[str, ProcessingResult]:
    """Orchestrates all post-processing for a standard research job."""
    task_type = job.task_type
    company_name = job.company_name
    account_name = job.account_name

    drive_service = get_drive_service(account_name)
    if not drive_service:
        return "error", {"error_message": "Failed to authenticate with Google Drive."}

    doc_url = browser.export_and_get_doc_url()
    if not doc_url:
        return "error", {"error_message": "Failed to export report to Google Docs."}

    doc_id = get_doc_id_from_url(doc_url)
    if not doc_id:
        return "error", {"error_message": f"Could not parse Doc ID from URL: {doc_url}"}

    full_report_text = get_google_doc_content(drive_service, doc_id)
    if not full_report_text:
        return "error", {"error_message": f"Failed to fetch content from Google Doc (ID: {doc_id})."}

    summary_text = _extract_summary(full_report_text)
    _manage_drive_file(drive_service, doc_id, company_name, task_type, config.drive)

    # Simplified from original for brevity, assuming share_chat_and_get_public_url is in Browser class
    # public_url = browser.share_chat_and_get_public_url() 

    send_report_to_telegram(
        company_name=company_name,
        summary_text=summary_text,
        doc_url=doc_url,
        config=config.telegram,
        task_type=task_type,
        target_chat_id=job.requested_by, # Simplified for now
        gemini_url=browser.driver.current_url,
        gemini_account_name=account_name
    )

    final_results: ProcessingResult = {"report_url": doc_url, "summary": summary_text}
    
    if task_type == TaskType.COMPANY_DEEP_DIVE:
        buy_range_prompt = get_prompt(TaskType.BUY_RANGE_CHECK)
        if not buy_range_prompt:
            logging.error("Buy range check prompt not found in configuration.")
            return "error", {"error_message": "Buy range check prompt is missing from configuration."}
        if _perform_buy_range_check(browser, buy_range_prompt):
            # Call the new generic function with the specific follow-up type
            queue_task(
                task_type=TaskType.DAILY_MONITOR,
                company_name=company_name,
                requested_by=f"follow_up_from_task_{job.task_id}"
            )
    return "completed", final_results


def run_post_processing_for_screener(browser: Browser, job: ResearchJob) -> tuple[str, ProcessingResult]:
    """Processes a completed screener job by extracting tickers and queuing new tasks."""
    logging.info(f"Screener task {job.task_id} complete. Extracting tickers...")
    try:
        extract_tickers_prompt = get_prompt(TaskType.EXTRACT_TICKERS)
        if not extract_tickers_prompt:
             raise ValueError("Could not load EXTRACT_TICKERS_PROMPT.")

        # --- SIMPLIFIED LOGIC ---
        company_list_raw = browser.enter_prompt_and_get_response(extract_tickers_prompt, timeout=300)
        
        if not company_list_raw:
             raise ValueError("Screener did not return a valid company list text.")

        company_list = [item.strip() for item in company_list_raw.split(',') if item.strip()]

        logging.info(f"Screener discovered {len(company_list)} companies. Queuing for deep dive...")
        add_tasks_from_screener(company_list, job.task_id)

        return "completed", {}
    except Exception as e:
        logging.error(f"Error post-processing screener task {job.task_id}: {e}", exc_info=True)
        return "error", {"error_message": "Failed to extract or queue companies from screener."}
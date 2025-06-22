import logging
import sqlite3
import time
import os
import json
import re
from datetime import datetime
from typing import TypedDict, Any

# Third-party imports
import pyperclip
import requests
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

# Internal project imports
from genai.helpers.config import DriveSettings, Settings
from genai.helpers.google_api_helpers import (
    get_doc_id_from_url,
    move_file_to_folder,
    share_google_doc_publicly,
)
from genai.helpers.notifications import send_report_to_telegram
from genai.helpers.prompt_text import PROMPT_BUY_RANGE_CHECK, PROMPT_TEXT_4
from genai.constants import (
    DATABASE_PATH,
    GEMINI_URL,
    PROMPT_TEXTAREA_CSS,
    DEEP_RESEARCH_BUTTON_XPATH,
    START_RESEARCH_BUTTON_XPATH,
    SHARE_EXPORT_BUTTON_XPATH,
    EXPORT_TO_DOCS_BUTTON_XPATH,
    RESPONSE_CONTENT_CSS,
    GENERATING_INDICATOR_CSS,
    TaskType,
)


# --- Type Definitions for Workflows ---
class ResearchJob(TypedDict):
    """A dictionary representing the state of a single active research job."""

    task_id: int
    handle: str
    company_name: str
    status: str
    started_at: float
    requested_by: str | None  # <-- ADD THIS FIELD
    task_type: str


class ProcessingResult(TypedDict, total=False):
    """A dictionary for the results of post-processing a completed job."""

    report_url: str
    summary: str
    error_message: str


# --- Core Selenium and Browser Interaction Functions ---


def initialize_driver(
    user_data_dir: str,
    profile_directory: str,
    webdriver_path: str | None,
    download_dir: str,
) -> WebDriver:
    """Initializes and returns a Selenium WebDriver instance for Chrome."""
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    chrome_options.add_argument(f"--profile-directory={profile_directory}")
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    service = None
    if webdriver_path:
        service = Service(executable_path=webdriver_path)

    driver = webdriver.Chrome(service=service, options=chrome_options)
    logging.info("WebDriver initialized.")
    return driver


def navigate_to_url(driver: WebDriver, url: str = GEMINI_URL) -> None:
    """Navigates to the specified URL and waits for the page to load."""
    logging.info(f"Navigating to {url}...")
    driver.get(url)
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, PROMPT_TEXTAREA_CSS))
        )
        logging.info("Page loaded.")
    except TimeoutException:
        logging.exception("Timeout waiting for page to load initial elements.")
        raise


def enter_text(driver: WebDriver, prompt: str) -> None:
    """Enters text into the prompt textarea instantly using JavaScript."""
    logging.info("Injecting prompt text directly via JavaScript...")
    try:
        prompt_textarea = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".ql-editor[contenteditable='true']"))
        )
        js_script = """
            var element = arguments[0];
            var text = arguments[1];
            element.textContent = text;
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
        """
        driver.execute_script(js_script, prompt_textarea, prompt)
        time.sleep(1)
        logging.info("Text entered successfully using JavaScript.")
    except Exception:
        # --- NEW: Add diagnostics on failure ---
        logging.error("Failed to find or interact with prompt textarea.", exc_info=True)
        # Save a screenshot to see what the page looks like
        screenshot_path = f"error_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        driver.save_screenshot(screenshot_path)
        logging.info(f"Saved error screenshot to: {screenshot_path}")
        
        # Save the page source to check for changed selectors or pop-ups
        html_path = f"error_page_source_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        logging.info(f"Saved page HTML to: {html_path}")
        # --- END NEW ---
        raise # Re-raise the exception to be caught by the calling function


def enter_prompt_and_submit(driver: WebDriver, prompt: str) -> None:
    """Enters the prompt in the prompt textarea and submits with RETURN."""
    enter_text(driver, prompt)
    time.sleep(1)
    try:
        prompt_textarea = driver.find_element(By.CSS_SELECTOR, PROMPT_TEXTAREA_CSS)
        prompt_textarea.send_keys(Keys.RETURN)
        logging.info("Prompt submitted.")
    except StaleElementReferenceException:
        logging.info(
            "Prompt textarea became stale or had an issue. Re-finding and submitting."
        )
        time.sleep(1)
        prompt_textarea = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, PROMPT_TEXTAREA_CSS))
        )
        prompt_textarea.send_keys(Keys.RETURN)
        logging.info("Prompt submitted after re-finding.")


def perform_deep_research(driver: WebDriver, prompt: str) -> None:
    """Handles the full workflow for initiating a Deep Research task."""
    try:
        logging.info("Locating and clicking Deep Research button...")
        try:
            WebDriverWait(driver, 60).until(
                EC.element_to_be_clickable((By.XPATH, DEEP_RESEARCH_BUTTON_XPATH))
            ).click()
        except StaleElementReferenceException:
            logging.info(
                "Deep Research button became stale. Re-finding and clicking."
            )
            time.sleep(1)
            driver.find_element(By.XPATH, DEEP_RESEARCH_BUTTON_XPATH).click()

        logging.info("Deep Research button clicked. Entering prompt...")
        time.sleep(1)
        enter_prompt_and_submit(driver, prompt)

        logging.info(
            "Prompt text entered. Locating and clicking Start Research button..."
        )
        try:
            WebDriverWait(driver, 120).until(
                EC.element_to_be_clickable((By.XPATH, START_RESEARCH_BUTTON_XPATH))
            ).click()
        except StaleElementReferenceException:
            logging.info(
                "Start Research button became stale. Re-finding and clicking."
            )
            time.sleep(1)
            driver.find_element(By.XPATH, START_RESEARCH_BUTTON_XPATH).click()
        logging.info("Deep Research initiated.")
        return True
    except Exception:
        logging.error(
            "An error occurred during Deep Research initiation.", exc_info=True
        )
        return False


def get_response(
    driver: WebDriver, responses_before_prompt: int, is_csv: bool = False, timeout: int = 900
) -> list[str] | str | None:
    """Waits for and returns the latest AI response, either as a list or a string."""
    try:
        logging.info(
            f"Waiting for new response (currently {responses_before_prompt} on page)..."
        )
        WebDriverWait(driver, timeout).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, RESPONSE_CONTENT_CSS))
            > responses_before_prompt
        )
        latest_response_element = driver.find_elements(
            By.CSS_SELECTOR, RESPONSE_CONTENT_CSS
        )[-1]

        logging.info("Waiting for response to finish generating...")
        WebDriverWait(latest_response_element, timeout).until(
            EC.invisibility_of_element_located(
                (By.CSS_SELECTOR, GENERATING_INDICATOR_CSS)
            )
        )
        logging.info("Response finished generating.")
        time.sleep(1)

        raw_text = latest_response_element.text

        if not raw_text:
            return None

        if is_csv:
            return [item.strip() for item in raw_text.split(",") if item.strip()]

        return raw_text
    except Exception:
        logging.error("An error occurred in get_response.", exc_info=True)
        return None


def export_and_get_doc_url(driver: WebDriver, current_tab_handle: str) -> str | None:
    """Exports the report to Google Docs and returns the new document's URL."""
    logging.info("Exporting report to Google Docs...")
    try:
        initial_handles = set(driver.window_handles)
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, SHARE_EXPORT_BUTTON_XPATH))
        ).click()
        time.sleep(1)
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, EXPORT_TO_DOCS_BUTTON_XPATH))
        ).click()

        new_handle = WebDriverWait(driver, 30).until(
            lambda d: next(iter(set(d.window_handles) - initial_handles), None)
        )
        driver.switch_to.window(new_handle)

        WebDriverWait(driver, 60).until_not(EC.url_to_be("about:blank"))
        doc_url = driver.current_url

        logging.info(f"Successfully exported. Doc URL: {doc_url}")
        driver.close()
        driver.switch_to.window(current_tab_handle)
        return doc_url
    except Exception:
        logging.error("An error occurred during report export.", exc_info=True)
        driver.switch_to.window(current_tab_handle)
        return None


def download_google_doc_as_pdf(
    doc_url: str, download_folder: str, company_name: str
) -> str | None:
    """Downloads a Google Doc as a PDF using a direct export link."""
    logging.info(f"Downloading Google Doc as PDF for {company_name}...")
    try:
        pdf_export_url = doc_url.replace("/edit", "/export?format=pdf")
        response = requests.get(pdf_export_url, stream=True, timeout=60)
        response.raise_for_status()

        safe_company_name = "".join(
            c for c in company_name if c.isalnum() or c in (" ", "_")
        ).rstrip()
        file_path = os.path.join(
            download_folder,
            f"{safe_company_name}_Report_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf",
        )

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logging.info(f"Successfully downloaded report to: {file_path}")
        return file_path
    except requests.exceptions.RequestException:
        logging.error("Failed to download file from Google Docs.", exc_info=True)
        return None


# --- High-Level Orchestration Workflow & Helpers ---


def _manage_google_drive_file(
    service: Any, doc_id: str | None, drive_config: DriveSettings
):
    """Private helper to handle all Google Drive API interactions for a file."""
    if not doc_id or not service or not drive_config:
        logging.warning(
            "Missing doc_id, drive_service, or drive_config. Skipping Drive actions."
        )
        return

    try:
        if drive_config.folder_id:
            move_file_to_folder(service, doc_id, drive_config.folder_id)
        share_google_doc_publicly(service, doc_id)
    except Exception:
        logging.error(f"An unexpected error occurred while managing Google Drive file {doc_id}.", exc_info=True)


def _send_final_notification(
    doc_url: str,
    summary_text: str,
    company_name: str,
    config: Settings,
    target_chat_id: str | None,
):
    """Private helper to handle sending the final notification to Telegram."""
    if not config.telegram:
        logging.warning("Telegram not configured. Skipping notification.")
        return

    # The logic is now just a single function call.
    send_report_to_telegram(
        company_name=company_name,
        summary_text=summary_text,
        doc_url=doc_url,
        config=config.telegram,
        target_chat_id=target_chat_id
    )

def _queue_follow_up_task(company_name: str, original_task_id: int):
    """Queues a new daily monitor task as a follow-up."""
    logging.info(f"Queuing follow-up DAILY_MONITOR task for {company_name}.")
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (company_name, requested_by, task_type) VALUES (?, ?, ?)",
                (company_name, f"follow_up_from_task_{original_task_id}", TaskType.DAILY_MONITOR)
            )
            conn.commit()
        logging.info(f"Successfully queued follow-up task for {company_name}.")
    except sqlite3.Error:
        logging.error(f"Database error while queuing follow-up task for {company_name}.", exc_info=True)
def process_completed_job(
    driver: WebDriver, job: ResearchJob, config: Settings, service: Any
) -> tuple[str, ProcessingResult]:
    """
    Processes a completed job by orchestrating summary, export, and notification steps.
    """
    company_name = job["company_name"]
    logging.info(
        f"✅ Research for '{company_name}' is COMPLETE. Starting post-processing workflow..."
    )

    try:
        res_before_summary = len(
            driver.find_elements(By.CSS_SELECTOR, RESPONSE_CONTENT_CSS)
        )
        enter_prompt_and_submit(driver, PROMPT_TEXT_4)
        summary_text = get_response(driver, res_before_summary, is_csv=False)

        doc_url = export_and_get_doc_url(driver, job["handle"])

        if not doc_url or not isinstance(summary_text, str):
            raise ValueError(
                "Failed to get a valid Doc URL or Summary string from Gemini."
            )
        # --- NEW: Parse the target_chat_id from the job data ---
        target_chat_id = None
        requested_by = job.get("requested_by")
        if requested_by and requested_by.startswith("telegram:"):
            try:
                # Extracts the ID part from "telegram:12345"
                target_chat_id = requested_by.split(":", 1)[1]
            except IndexError:
                logging.warning(
                    f"Could not parse chat ID from requested_by field: {requested_by}"
                )
        # --- END NEW ---
        _manage_google_drive_file(service, get_doc_id_from_url(doc_url), config.drive)
        _send_final_notification(
            doc_url, summary_text, company_name, config, target_chat_id
        )

        final_results: ProcessingResult = {
            "report_url": doc_url,
            "summary": summary_text,
        }
        if job.get("task_type") == TaskType.COMPANY_DEEP_DIVE:
            logging.info(f"Performing buy-range check for {company_name}...")
            res_before_check = len(driver.find_elements(By.CSS_SELECTOR, RESPONSE_CONTENT_CSS))
            enter_prompt_and_submit(driver, PROMPT_BUY_RANGE_CHECK)
            # Use a shorter timeout for this simple check
            check_response = get_response(driver, res_before_check)

            if check_response and "YES" in check_response.upper():
                logging.info(f"'{company_name}' is in buy range. Queuing follow-up task.")
                _queue_follow_up_task(company_name, job["task_id"])
            else:
                logging.info(f"'{company_name}' is not in buy range or check failed. No follow-up task queued.")
        return "completed", final_results

    except Exception:
        logging.error(
            f"❌ Error during post-processing for '{company_name}'.", exc_info=True
        )
        final_results: ProcessingResult = {
            "error_message": "An error occurred during post-processing."
        }
        return "error", final_results


if __name__ == "__main__":
    from genai.helpers.config import get_settings
    from genai.helpers.google_api_helpers import get_drive_service
    from genai.helpers.logging_config import setup_logging

    setup_logging()
    config = get_settings()
    service = get_drive_service()
    driver = None

    driver = initialize_driver(
        config.chrome.user_data_dir,
        config.chrome.profile_directory,
        config.chrome.chrome_driver_path,
        config.chrome.download_dir,
    )
    driver.get("https://gemini.google.com/app/a95bfed43b54ef04")
    input("Press Enter to continue...")
    process_completed_job(driver, {
        "task_id": 1,
        "handle": driver.current_window_handle,
        "company_name": "Example Company",
        "status": "processing",
        "started_at": time.time(),
        "requested_by": "telegram:123456789"
    }, config, service)
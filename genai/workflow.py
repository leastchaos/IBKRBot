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
    rename_google_doc,
    share_google_doc_publicly,
)
from genai.helpers.notifications import send_report_to_telegram
from genai.helpers.prompt_text import PROMPT_BUY_RANGE_CHECK, PROMPT_TEXT_4
from genai.helpers.helpers import save_debug_screenshot
from genai.constants import (
    DATABASE_PATH,
    GEMINI_URL,
    INSERT_BUTTON_XPATH,
    PICKER_IFRAME_XPATH,
    PROMPT_TEXTAREA_CSS,
    DEEP_RESEARCH_BUTTON_XPATH,
    START_RESEARCH_BUTTON_XPATH,
    SHARE_EXPORT_BUTTON_XPATH,
    EXPORT_TO_DOCS_BUTTON_XPATH,
    RESPONSE_CONTENT_CSS,
    GENERATING_INDICATOR_CSS,
    ADD_FILE_BUTTON_XPATH,
    ADD_FROM_DRIVE_BUTTON_XPATH,
    DRIVE_URL_INPUT_CSS,
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
    headless:bool = True,
) -> WebDriver:
    """Initializes and returns a Selenium WebDriver instance for Chrome."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
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
        save_debug_screenshot(driver, "navigate_to_url_timeout")
        raise


def enter_text(driver: WebDriver, prompt: str) -> None:
    """Enters text into the prompt textarea instantly using JavaScript."""
    logging.info("Injecting prompt text directly via JavaScript...")
    try:
        prompt_textarea = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".ql-editor[contenteditable='true']")
            )
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
        save_debug_screenshot(driver, "enter_text_error")

        # Save the page source to check for changed selectors or pop-ups
        html_path = f"error_page_source_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logging.info(f"Saved page HTML to: {html_path}")
        # --- END NEW ---
        raise  # Re-raise the exception to be caught by the calling function


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
            logging.info("Deep Research button became stale. Re-finding and clicking.")
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
            logging.info("Start Research button became stale. Re-finding and clicking.")
            time.sleep(1)
            driver.find_element(By.XPATH, START_RESEARCH_BUTTON_XPATH).click()
        logging.info("Deep Research initiated.")
        return True
    except Exception:
        logging.error(
            "An error occurred during Deep Research initiation.", exc_info=True
        )
        save_debug_screenshot(driver, "deep_research_error")
        return False


def perform_daily_monitor_research(
    driver: WebDriver, prompt: str, report_url: str
) -> bool:
    """
    Handles the workflow for a daily monitor task by first attaching a
    Google Doc via URL and then submitting the prompt.
    """
    try:
        logging.info(f"Starting daily monitor workflow. Attaching doc: {report_url}")
        # 1. Click the Deep Research button
        try:
            WebDriverWait(driver, 60).until(
                EC.element_to_be_clickable((By.XPATH, DEEP_RESEARCH_BUTTON_XPATH))
            ).click()
        except StaleElementReferenceException:
            logging.info("Deep Research button became stale. Re-finding and clicking.")
            time.sleep(1)
            driver.find_element(By.XPATH, DEEP_RESEARCH_BUTTON_XPATH).click()
        time.sleep(1)

        # 2. Click the "+" button
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, ADD_FILE_BUTTON_XPATH))
        ).click()
        logging.info("Clicked 'Attach files' button.")
        time.sleep(1)

        # 3. Click the "Add from Google Drive" option
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, ADD_FROM_DRIVE_BUTTON_XPATH))
        ).click()
        logging.info("Clicked 'Add from Google Drive' option.")
        time.sleep(2)  # Allow time for the next modal/input to appear


        # 4. Switch to the google picker iframe then Enter the URL into the input field
        picker_iframe = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, PICKER_IFRAME_XPATH))
        )
        
        driver.switch_to.frame(picker_iframe)
        logging.info("Switched to Google Picker iframe.")
        url_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, DRIVE_URL_INPUT_CSS))
        )
        url_input.send_keys(report_url)
        logging.info("Pasted Google Doc URL into input field.")
        time.sleep(1)
        url_input.send_keys(Keys.RETURN)
        logging.info("Submitted Google Doc URL.")
        # 6. select the file and click "Insert"
        doc_id = get_doc_id_from_url(report_url)
        if not doc_id:
            raise ValueError(f"Could not extract document ID from URL: {report_url}")

        file_selector_xpath = f"//div[@role='option' and @data-id='{doc_id}']"
        logging.info(f"Waiting for file element with selector: {file_selector_xpath}")
        file_element = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, file_selector_xpath))
        )
        file_element.click()
        logging.info(f"Selected file with doc ID: {doc_id}")
        time.sleep(1)

        # Using a more robust XPath selector that targets the aria-label.
        
        logging.info(f"Waiting for the 'Insert' button ({INSERT_BUTTON_XPATH})...")
        insert_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, INSERT_BUTTON_XPATH))
        )
        insert_button.click()
        logging.info("Clicked 'Insert' button.")
        driver.switch_to.default_content()
        logging.info("Switched back to default content.")
        time.sleep(1)

        # 6. Now, submit the actual prompt for analysis
        enter_prompt_and_submit(driver, prompt)
        logging.info("Daily monitor prompt submitted for analysis.")
        time.sleep(1)
        try:
            WebDriverWait(driver, 120).until(
                EC.element_to_be_clickable((By.XPATH, START_RESEARCH_BUTTON_XPATH))
            ).click()
        except StaleElementReferenceException:
            logging.info("Start Research button became stale. Re-finding and clicking.")
            time.sleep(1)
            driver.find_element(By.XPATH, START_RESEARCH_BUTTON_XPATH).click()
        logging.info("Deep Research initiated.")
        return True

    except Exception:
        logging.error(
            "An error occurred during the daily monitor research workflow.",
            exc_info=True,
        )
        save_debug_screenshot(driver, "daily_monitor_error")
        return False


def get_response(
    driver: WebDriver,
    responses_before_prompt: int,
    is_csv: bool = False,
    timeout: int = 900,
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
        logging.info("Initial response generation indicator has disappeared.")

        # --- NEW: Wait for the text content to stabilize ---
        stabilization_timeout = 30  # Max seconds to wait for text to stop changing
        stabilization_interval = 2  # Seconds between checks
        start_time = time.time()
        last_text = ""

        while time.time() - start_time < stabilization_timeout:
            try:
                current_text = latest_response_element.text
                if current_text == last_text and current_text:
                    logging.info("✅ Response text has stabilized.")
                    break
                last_text = current_text
                logging.debug(
                    f"Response text not yet stable. Waiting {stabilization_interval}s..."
                )
                time.sleep(stabilization_interval)
            except StaleElementReferenceException:
                logging.warning("Response element became stale, re-finding...")
                latest_response_element = driver.find_elements(
                    By.CSS_SELECTOR, RESPONSE_CONTENT_CSS
                )[-1]
                continue  # Retry the loop immediately
        else:
            logging.warning(
                f"Response text did not stabilize within {stabilization_timeout}s. Using last captured content."
            )

        if not last_text:
            return None

        return [item.strip() for item in last_text.split(",") if item.strip()] if is_csv else last_text
    except Exception:
        logging.error("An error occurred in get_response.", exc_info=True)
        save_debug_screenshot(driver, "get_response_error")
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
        save_debug_screenshot(driver, "export_doc_error")
        driver.switch_to.window(current_tab_handle)
        return None


# --- High-Level Orchestration Workflow & Helpers ---


def _manage_google_drive_file(
    service: Any,
    doc_id: str | None,
    drive_config: DriveSettings,
    new_title: str | None = None,
):
    """Private helper to handle all Google Drive API interactions for a file."""
    if not doc_id or not service:
        logging.warning("Missing doc_id or drive_service. Skipping Drive actions.")
        return

    try:
        if new_title:
            rename_google_doc(service, doc_id, new_title)
        if drive_config and drive_config.folder_id:
            move_file_to_folder(service, doc_id, drive_config.folder_id)
        share_google_doc_publicly(service, doc_id)
    except Exception:
        logging.error(
            f"An unexpected error occurred while managing Google Drive file {doc_id}.",
            exc_info=True,
        )


def _send_final_notification(
    doc_url: str,
    summary_text: str,
    company_name: str,
    config: Settings,
    task_type: str,
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
        task_type=task_type,
        target_chat_id=target_chat_id,
    )


def _queue_follow_up_task(company_name: str, original_task_id: int):
    """Queues a new daily monitor task as a follow-up."""
    logging.info(f"Queuing follow-up DAILY_MONITOR task for {company_name}.")
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (company_name, requested_by, task_type) VALUES (?, ?, ?)",
                (
                    company_name,
                    f"follow_up_from_task_{original_task_id}",
                    TaskType.DAILY_MONITOR,
                ),
            )
            conn.commit()
        logging.info(f"Successfully queued follow-up task for {company_name}.")
    except sqlite3.Error:
        logging.error(
            f"Database error while queuing follow-up task for {company_name}.",
            exc_info=True,
        )


def process_completed_job(
    driver: WebDriver, job: ResearchJob, config: Settings, service: Any
) -> tuple[str, ProcessingResult]:
    """
    Processes a completed job by orchestrating summary, export, and notification steps.
    """
    task_type = job["task_type"]
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
        logging.info(f"Summary: {summary_text}")

        doc_url = export_and_get_doc_url(driver, job["handle"])

        if not doc_url or not isinstance(summary_text, str):
            raise ValueError(
                "Failed to get a valid Doc URL or Summary string from Gemini."
            )

        doc_id = get_doc_id_from_url(doc_url)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        new_doc_title = f"{timestamp}_{company_name}_{task_type}"

        # --- Parse the target_chat_id from the job data ---
        target_chat_id = None
        requested_by = job.get("requested_by")
        if requested_by and requested_by.startswith("telegram:"):
            try:
                target_chat_id = requested_by.split(":", 1)[1]
            except IndexError:
                logging.warning(
                    f"Could not parse chat ID from requested_by field: {requested_by}"
                )
        _manage_google_drive_file(service, doc_id, config.drive, new_doc_title)
        _send_final_notification(
            doc_url, summary_text, company_name, config, task_type, target_chat_id
        )

        final_results: ProcessingResult = {
            "report_url": doc_url,
            "summary": summary_text,
        }
        if task_type == TaskType.COMPANY_DEEP_DIVE:
            logging.info(f"Performing buy-range check for {company_name}...")
            res_before_check = len(
                driver.find_elements(By.CSS_SELECTOR, RESPONSE_CONTENT_CSS)
            )
            enter_prompt_and_submit(driver, PROMPT_BUY_RANGE_CHECK)
            # Use a shorter timeout for this simple check
            check_response = get_response(driver, res_before_check)

            if check_response and "YES" in check_response.upper():
                logging.info(
                    f"'{company_name}' is in buy range. Queuing follow-up task."
                )
                _queue_follow_up_task(company_name, job["task_id"])
            else:
                logging.info(
                    f"'{company_name}' is not in buy range or check failed. No follow-up task queued."
                )
        return "completed", final_results

    except Exception:
        logging.error(
            f"❌ Error during post-processing for '{company_name}'.", exc_info=True
        )
        save_debug_screenshot(driver, f"post_processing_error_{company_name}")
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
    driver.get("https://gemini.google.com/app")
    input("Press Enter to continue...")
    perform_daily_monitor_research(driver, "test", "https://docs.google.com/document/d/1hpSthpQ3_Rn23LwA8a730N0oO2QD1lTce6QJ4mzkGug/edit?tab=t.0" \
    "")
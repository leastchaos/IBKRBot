import logging
import sqlite3
import time
from datetime import datetime
from typing import TypedDict, Any

# Third-party imports
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
from genai.helpers.prompt_text import PROMPT_BUY_RANGE_CHECK, FOLLOWUP_DEEPDIVE_PROMPT
from genai.helpers.helpers import save_debug_screenshot
from genai.constants import (
    CLOSE_SHARE_DIALOG_BUTTON_XPATH,
    CREATE_PUBLIC_LINK_BUTTON_XPATH,
    DATABASE_PATH,
    GEMINI_URL,
    INSERT_BUTTON_XPATH,
    PICKER_IFRAME_XPATH,
    PROMPT_TEXTAREA_CSS,
    DEEP_RESEARCH_BUTTON_XPATH,
    PUBLIC_URL_INPUT_XPATH,
    SHARE_BUTTON_XPATH,
    START_RESEARCH_BUTTON_XPATH,
    SHARE_EXPORT_BUTTON_XPATH,
    EXPORT_TO_DOCS_BUTTON_XPATH,
    RESPONSE_CONTENT_CSS,
    GENERATING_INDICATOR_CSS,
    ADD_FILE_BUTTON_XPATH,
    ADD_FROM_DRIVE_BUTTON_XPATH,
    DRIVE_URL_INPUT_CSS,
    TELEGRAM_USER_PREFIX,
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
    requested_by: str | None
    error_recovery_attempted: bool
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
    headless: bool = True,
) -> WebDriver:
    """Initializes and returns a Selenium WebDriver instance for Chrome."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--window-size=1920,1080")
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
    try:
        prompt_textarea = driver.find_element(By.CSS_SELECTOR, PROMPT_TEXTAREA_CSS)
        prompt_textarea.send_keys(Keys.RETURN)
        logging.info("Prompt submitted.")
    except StaleElementReferenceException:
        logging.info(
            "Prompt textarea became stale or had an issue. Re-finding and submitting."
        )
        prompt_textarea = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, PROMPT_TEXTAREA_CSS))
        )
        prompt_textarea.send_keys(Keys.RETURN)
        logging.info("Prompt submitted after re-finding.")


def _click_deep_research_button(driver: WebDriver):
    """Waits for and clicks the 'Deep Research' button, handling stale elements."""
    logging.info("Locating and clicking Deep Research button...")
    try:
        WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, DEEP_RESEARCH_BUTTON_XPATH))
        ).click()
    except StaleElementReferenceException:
        logging.info("Deep Research button became stale. Re-finding and clicking.")
        driver.find_element(By.XPATH, DEEP_RESEARCH_BUTTON_XPATH).click()
    logging.info("Deep Research button clicked.")


def _click_start_research_button(driver: WebDriver):
    """Waits for and clicks the 'Start Research' button, handling stale elements."""
    logging.info("Locating and clicking Start Research button...")
    try:
        WebDriverWait(driver, 120).until(
            EC.element_to_be_clickable((By.XPATH, START_RESEARCH_BUTTON_XPATH))
        ).click()
    except StaleElementReferenceException:
        logging.info("Start Research button became stale. Re-finding and clicking.")
        driver.find_element(By.XPATH, START_RESEARCH_BUTTON_XPATH).click()
    logging.info("Start Research button clicked.")


def perform_deep_research(driver: WebDriver, prompt: str) -> bool:
    """Handles the full workflow for initiating a Deep Research task."""
    try:
        _click_deep_research_button(driver)
        enter_prompt_and_submit(driver, prompt)
        _click_start_research_button(driver)
        logging.info("Deep Research initiated.")
        return True
    except Exception:
        logging.error(
            "An error occurred during Deep Research initiation.", exc_info=True
        )
        save_debug_screenshot(driver, "deep_research_error")
        return False


def _attach_drive_file(driver: WebDriver, report_url: str) -> None:
    """Handles the UI interaction to attach a Google Drive file by URL."""
    # 1. Click the "+" button to open the upload menu
    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, ADD_FILE_BUTTON_XPATH))
    ).click()
    logging.info("Clicked 'Attach files' button.")

    # 2. Click the "Add from Google Drive" option
    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, ADD_FROM_DRIVE_BUTTON_XPATH))
    ).click()
    logging.info("Clicked 'Add from Google Drive' option.")

    # 3. Switch to the Google Picker iframe
    picker_iframe = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, PICKER_IFRAME_XPATH))
    )
    driver.switch_to.frame(picker_iframe)
    logging.info("Switched to Google Picker iframe.")

    # 4. Enter the URL and select the file
    url_input = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, DRIVE_URL_INPUT_CSS))
    )
    url_input.send_keys(report_url)
    logging.info("Pasted Google Doc URL into input field.")
    url_input.send_keys(Keys.RETURN)
    logging.info("Submitted Google Doc URL.")

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

    # 5. Click the "Insert" button
    logging.info(f"Waiting for the 'Insert' button ({INSERT_BUTTON_XPATH})...")
    insert_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, INSERT_BUTTON_XPATH))
    )
    insert_button.click()
    logging.info("Clicked 'Insert' button.")

    # 6. Switch back to the main content
    driver.switch_to.default_content()
    logging.info("Switched back to default content.")


def perform_daily_monitor_research(
    driver: WebDriver, prompt: str, report_url: str
) -> bool:
    """
    Handles the workflow for a daily monitor task by first attaching a
    Google Doc via URL and then submitting the prompt.
    """
    try:
        logging.info(f"Starting daily monitor workflow. Attaching doc: {report_url}")
        _click_deep_research_button(driver)
        _attach_drive_file(driver, report_url)
        enter_prompt_and_submit(driver, prompt)
        logging.info("Daily monitor prompt submitted for analysis.")
        # 4. Click the final "Start Research" button
        _click_start_research_button(driver)
        logging.info("Daily monitor research initiated.")
        return True

    except Exception:
        logging.error(
            "An error occurred during the daily monitor research workflow.",
            exc_info=True,
        )
        save_debug_screenshot(driver, "daily_monitor_error")
        return False


def perform_portfolio_review(driver: WebDriver, prompt: str, sheet_url: str) -> bool:
    try:
        logging.info("Starting portfolio review workflow.")
        _click_deep_research_button(driver)
        _attach_drive_file(driver, sheet_url)
        enter_prompt_and_submit(driver, prompt)
        _click_start_research_button(driver)
        logging.info("Portfolio review prompt submitted for analysis.")
        return True

    except Exception:
        logging.error(
            "An error occurred during the portfolio review workflow.", exc_info=True
        )
        save_debug_screenshot(driver, "portfolio_review_error")
        return False


def get_response(
    driver: WebDriver,
    responses_before_prompt: int,
    is_csv: bool = False,
    timeout: int = 900,
) -> list[str] | str | None:
    """
    Waits for and returns the latest AI response.

    This function is designed to be robust against partially loaded or streaming
    responses. It performs three stages of waiting:
    1. Waits for a new response container to be added to the DOM.
    2. Waits for the "generating..." progress bar to disappear.
    3. Waits for the text content of the response to stabilize, ensuring the
       full response has been streamed and rendered.

    Args:
        driver: The Selenium WebDriver instance.
        responses_before_prompt: The number of response elements on the page
            before the current prompt was submitted.
        is_csv: If True, the response text will be split by commas into a list.
        timeout: The maximum time in seconds to wait for the response.

    Returns:
        The response text as a string or list of strings, or None on failure.
    """
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

        return (
            [item.strip() for item in last_text.split(",") if item.strip()]
            if is_csv
            else last_text
        )
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
    gemini_chat_url: str,
    gemini_public_url: str | None = None,
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
        gemini_url=gemini_chat_url,
        gemini_public_url=gemini_public_url,
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
def share_chat_and_get_public_url(driver: WebDriver) -> str | None:
    """
    Shares the current Gemini conversation and returns the public URL.

    Handles clicking the 'Share & Export' button, then 'Create public link',
    extracting the URL from the input field, and closing the dialog.

    Args:
        driver: The Selenium WebDriver instance.

    Returns:
        The public URL as a string, or None if an error occurs.
    """
    logging.info("Sharing conversation to get public link...")
    try:
        # 1. Click the main 'Share & Export' button to open the dialog
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, SHARE_BUTTON_XPATH))
        ).click()
        logging.info("Clicked 'Share & Export' button.")

        # 2. Click 'Create public link'
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, CREATE_PUBLIC_LINK_BUTTON_XPATH))
        ).click()
        logging.info("Clicked 'Create public link'.")

        # 3. Wait for the input with the URL and get its 'value' attribute
        public_url_input = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, PUBLIC_URL_INPUT_XPATH))
        )
        public_url = public_url_input.get_attribute("value")
        logging.info(f"✅ Successfully retrieved public URL: {public_url}")

        # 4. Close the share dialog
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, CLOSE_SHARE_DIALOG_BUTTON_XPATH))
        ).click()
        logging.info("Closed the share dialog.")

        return public_url

    except Exception:
        logging.error(
            "An error occurred while sharing the chat.", exc_info=True
        )
        save_debug_screenshot(driver, "share_chat_error")
        # Fallback: try to press Escape to close any open dialogs
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            logging.warning("Sent ESCAPE key to close lingering share dialog.")
        except Exception as e:
            logging.warning(f"Could not send ESCAPE key as a fallback: {e}")
        return None

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
        enter_prompt_and_submit(driver, FOLLOWUP_DEEPDIVE_PROMPT)
        summary_text = get_response(driver, res_before_summary, is_csv=False)
        gemini_chat_url = driver.current_url
        logging.info(f"Gemini chat URL: {gemini_chat_url}")

        doc_url = export_and_get_doc_url(driver, job["handle"])

        if not summary_text or not isinstance(summary_text, str):
            logging.warning(
                f"Failed to retrieve a valid summary for {company_name}. Using a default message."
            )
            summary_text = "Failed to provide summary."
        logging.info(f"Summary: {summary_text}")

        if not doc_url:
            raise ValueError(
                "Failed to get a valid Doc URL from Gemini. Cannot proceed."
            )

        doc_id = get_doc_id_from_url(doc_url)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        new_doc_title = f"{timestamp}_{company_name}_{task_type}"

        # --- Parse the target_chat_id from the job data ---
        target_chat_id = None
        requested_by = job.get("requested_by")
        if requested_by and requested_by.startswith(TELEGRAM_USER_PREFIX):
            try:
                target_chat_id = requested_by.split(":", 1)[1]
            except IndexError:
                logging.warning(
                    f"Could not parse chat ID from requested_by field: {requested_by}"
                )
        _manage_google_drive_file(service, doc_id, config.drive, new_doc_title)
        _send_final_notification(
            doc_url,
            summary_text,
            company_name,
            config,
            task_type,
            target_chat_id,
            gemini_chat_url,
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
            # Use a shorter timeout for this simple YES/NO check
            check_response = get_response(driver, res_before_check, timeout=900)

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
        headless=False,  # Set to False for debugging
    )
    driver.get("https://gemini.google.com/app")
    input("Press Enter to continue...")
    # perform_daily_monitor_research(
    #     driver,
    #     "test",
    #     "https://docs.google.com/document/d/1hpSthpQ3_Rn23LwA8a730N0oO2QD1lTce6QJ4mzkGug/edit?tab=t.0"
    #     "",
    # )
    print(share_chat_and_get_public_url(driver))
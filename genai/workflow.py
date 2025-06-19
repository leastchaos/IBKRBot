from datetime import datetime
import logging
import sys
import time
import os
import json
import pyperclip
import requests
from typing import TypedDict, List, Any

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    NoSuchWindowException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.keys import Keys

from genai.helpers.config import Settings, get_settings
from genai.helpers.google_api_helpers import (
    get_doc_id_from_url,
    get_drive_service,
    move_file_to_folder,
    share_google_doc_publicly,
)
from genai.helpers.helpers import retry_on_exception
from genai.helpers.logging_config import setup_logging
from genai.helpers.notifications import send_report_to_telegram
from genai.helpers.prompt_text import (
    PROMPT_TEXT,
    PROMPT_TEXT_2,
    PROMPT_TEXT_3,
    PROMPT_TEXT_4,
)


# --- Constants ---
GEMINI_URL = "https://gemini.google.com/app"
MONITORING_INTERVAL_SECONDS = 15
MAX_ACTIVE_RESEARCH_JOBS = 2  # New constant for the Gemini limitation


# --- Element Locators ---
PROMPT_TEXTAREA_CSS = ".ql-editor[contenteditable='true']"
DEEP_RESEARCH_BUTTON_XPATH = "//button[contains(., 'Deep Research')]"
START_RESEARCH_BUTTON_XPATH = "//button[contains(., 'Start research')]"
SHARE_EXPORT_BUTTON_XPATH = "//button[contains(., 'Export')]"
EXPORT_TO_DOCS_BUTTON_XPATH = "//button[contains(., 'Export to Docs')]"
RESPONSE_CONTENT_CSS = "div.response-content"
GENERATING_INDICATOR_CSS = "progress.mat-mdc-linear-progress"


# --- Type Definitions for State Management ---
class ResearchJob(TypedDict):
    """A dictionary representing the state of a single research job."""

    task_id: int
    handle: str
    company_name: str
    status: str
    started_at: float


class ProcessingResult(TypedDict, total=False):
    """A dictionary for the results of post-processing a completed job."""

    report_url: str
    summary: str
    error_message: str


def initialize_driver(
    user_data_dir: str, profile_directory: str, webdriver_path: str, download_dir: str
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
    if webdriver_path:
        service = Service(executable_path=webdriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        driver = webdriver.Chrome(options=chrome_options)
    logging.info("WebDriver initialized.")
    return driver


def navigate_to_url(driver: WebDriver, url: str):
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


def enter_text_without_submitting(driver: WebDriver, prompt: str):
    """Enters text into the prompt textarea WITHOUT submitting."""
    logging.info("Copying prompt to clipboard and pasting...")
    pyperclip.copy(prompt)
    prompt_textarea = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, PROMPT_TEXTAREA_CSS))
    )
    prompt_textarea.clear()
    prompt_textarea.send_keys(Keys.CONTROL, "v")
    time.sleep(1)
    logging.info("Text entered.")


@retry_on_exception
def enter_prompt_and_submit(driver: WebDriver, prompt: str):
    """Enters the prompt and submits it."""
    enter_text_without_submitting(driver, prompt)
    try:
        prompt_textarea = driver.find_element(By.CSS_SELECTOR, PROMPT_TEXTAREA_CSS)
        prompt_textarea.send_keys(Keys.RETURN)
        logging.info("Prompt submitted.")
    except StaleElementReferenceException:
        logging.info("Prompt textarea became stale. Re-finding and submitting.")
        prompt_textarea = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, PROMPT_TEXTAREA_CSS))
        )
        prompt_textarea.send_keys(Keys.RETURN)
        logging.info("Prompt submitted after re-finding.")


@retry_on_exception
def click_start_research(driver: WebDriver):
    """Clicks the Start Research button."""
    try:
        WebDriverWait(driver, 300).until(
            EC.element_to_be_clickable((By.XPATH, START_RESEARCH_BUTTON_XPATH))
        ).click()
        logging.info("Start Research button clicked.")
    except StaleElementReferenceException:
        logging.info("Start Research button became stale. Re-finding and clicking...")
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, START_RESEARCH_BUTTON_XPATH))
        ).click()
        logging.info("Start Research button clicked after re-finding.")


@retry_on_exception
def perform_deep_research(driver: WebDriver, prompt: str):
    """Initiates the Deep Research workflow with a given prompt."""
    try:
        logging.info("Locating and clicking Deep Research button...")
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, DEEP_RESEARCH_BUTTON_XPATH))
        ).click()
        time.sleep(1)
        enter_prompt_and_submit(driver, prompt)
        logging.info(
            "Prompt text entered. Locating and clicking Start Research button..."
        )
        click_start_research(driver)
        logging.info("Deep Research initiated.")
    except Exception as e:
        logging.exception(f"An error occurred during Deep Research initiation: {e}")
        driver.save_screenshot("debug_deep_research_error.png")
        raise


@retry_on_exception
def get_response(
    driver: WebDriver, responses_before_prompt: int, is_csv: bool = False
) -> list[str] | str | None:
    """Waits for and returns the latest AI response."""
    try:
        logging.info(
            f"Waiting for new response (currently {responses_before_prompt} on page)..."
        )
        # Wait for a new response element to appear
        WebDriverWait(driver, 900).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, RESPONSE_CONTENT_CSS))
            > responses_before_prompt
        )
        latest_response_element = driver.find_elements(
            By.CSS_SELECTOR, RESPONSE_CONTENT_CSS
        )[-1]

        logging.info("Waiting for response to finish generating...")
        # Then wait for the progress bar within that response to disappear
        WebDriverWait(latest_response_element, 900).until(
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
    except Exception as e:
        logging.exception(f"An error occurred in get_response: {e}")
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

        # Wait for the new tab to open and get its handle
        new_handle = WebDriverWait(driver, 30).until(
            lambda d: next(iter(set(d.window_handles) - initial_handles), None)
        )
        driver.switch_to.window(new_handle)

        # Wait for the URL to be the final Google Doc URL
        WebDriverWait(driver, 60).until_not(EC.url_to_be("about:blank"))
        doc_url = driver.current_url

        logging.info(f"Successfully exported. Doc URL: {doc_url}")
        driver.close()
        driver.switch_to.window(current_tab_handle)
        return doc_url
    except Exception as e:
        logging.exception(f"An error occurred during report export: {e}")
        driver.switch_to.window(current_tab_handle)
        return None


def download_google_doc_as_pdf(
    doc_url: str, download_folder: str, company_name: str
) -> str | None:
    """Downloads a Google Doc as a PDF using a direct export link."""
    logging.info(f"Downloading Google Doc as PDF for {company_name}...")
    try:
        base_url = doc_url.split("/edit")[0]

        # Append the correct export format
        pdf_export_url = f"{base_url}/export?format=pdf"
        response = requests.get(pdf_export_url, stream=True, timeout=60)
        response.raise_for_status()
        company_name = company_name.replace(":", "_")
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
    except requests.exceptions.RequestException as e:
        logging.exception(f"Failed to download file from Google Docs: {e}")
        return None


# --- New Logical Workflow Functions ---


def get_initial_company_list(driver: WebDriver) -> List[str]:
    """Performs the initial research to get the list of companies."""
    navigate_to_url(driver, GEMINI_URL)
    perform_deep_research(driver, PROMPT_TEXT)
    WebDriverWait(driver, 1200).until(
        EC.element_to_be_clickable((By.XPATH, SHARE_EXPORT_BUTTON_XPATH))
    )
    logging.info("Initial research complete. Asking for company list...")

    responses_before = len(driver.find_elements(By.CSS_SELECTOR, RESPONSE_CONTENT_CSS))
    enter_prompt_and_submit(driver, PROMPT_TEXT_2)
    company_list = get_response(driver, responses_before, is_csv=True)

    if not company_list or not isinstance(company_list, list):
        logging.error("Could not retrieve a valid company list. Exiting.")
        return []
    return company_list


def launch_research_job(driver: WebDriver, company_name: str) -> ResearchJob:
    """Opens a new tab for a single company and starts the research."""
    logging.info(f"\nInitiating research for: {company_name}")
    driver.switch_to.new_window("tab")
    new_handle = driver.current_window_handle
    navigate_to_url(driver, GEMINI_URL)
    company_prompt = f"{PROMPT_TEXT_3} {company_name}."
    perform_deep_research(driver, company_prompt)
    return {
        "handle": new_handle,
        "company_name": company_name,
        "status": "active",  # Mark as active immediately
        "started_at": time.time(),
    }


def process_completed_job(driver: WebDriver, job: ResearchJob, config: Settings, service: Any) -> tuple[str, ProcessingResult]:
    """
    Processes a single completed deep dive research job from start to finish.
    This is a high-level workflow that orchestrates multiple smaller steps.

    Args:
        driver: The Selenium WebDriver instance, focused on the completed tab.
        job: The ResearchJob dictionary containing info about the task.
        config: The main Settings object.
        service: The authenticated Google Drive API service object.

    Returns:
        A tuple containing the final status ('completed' or 'error') and a
        dictionary with the results.
    """
    company_name = job['company_name']
    pdf_path: str | None = None
    
    try:
        logging.info(f"✅ Research for '{company_name}' is COMPLETE. Starting post-processing workflow...")
        
        # 1. Get AI Summary: Asks Gemini for a formatted summary string.
        res_before_summary = len(driver.find_elements(By.CSS_SELECTOR, ".response-content"))
        enter_prompt_and_submit(driver, PROMPT_TEXT_4)
        summary_text = get_response(driver, res_before_summary, is_csv=False)
        logging.info(f"Summary for '{company_name}': {summary_text}")

        # 2. Export to Google Docs: Gets the URL of the full report.
        doc_url = export_and_get_doc_url(driver, job["handle"])
        
        if not doc_url or not isinstance(summary_text, str):
            raise ValueError("Failed to get a valid Doc URL or Summary string from Gemini.")

        # 3. Manage Google Drive File: Sets permissions and moves the file using the API.
        doc_id = get_doc_id_from_url(doc_url)
        if doc_id and config.drive:
            if config.drive.folder_id:
                move_file_to_folder(service, doc_id, config.drive.folder_id)
            share_google_doc_publicly(service, doc_id)
        
        # 4. Download PDF Version: Downloads a local copy of the report for sending.
        if config.chrome and config.chrome.download_dir:
            pdf_path = download_google_doc_as_pdf(doc_url, config.chrome.download_dir, company_name)
            if not pdf_path:
                raise ValueError("Failed to download the report as a PDF.")
        else:
             logging.warning("Download directory not configured. Skipping PDF download.")

        # 5. Send Telegram Notification: Sends the summary and attaches the PDF file.
        if pdf_path and config.telegram:
            send_report_to_telegram(
                company_name=company_name,
                summary_text=summary_text,
                file_path=pdf_path,
                doc_url=doc_url,
                config=config.telegram
            )

        final_results: ProcessingResult = {"report_url": doc_url, "summary": summary_text}
        return "completed", final_results

    except Exception as e:
        logging.error(f"❌ Error during post-processing for '{company_name}'.", exc_info=True)
        final_results: ProcessingResult = {"error_message": str(e)}
        return "error", final_results
    
    finally:
        # 6. Cleanup: Always deletes the local PDF file to save space.
        if pdf_path and os.path.exists(pdf_path):
            logging.info(f"Cleaning up downloaded file: {pdf_path}")
            os.remove(pdf_path)


def monitor_and_process_jobs(
    driver: WebDriver,
    companies: list[str],
    config: Settings,
    service,
    original_tab_handle: str,
):
    """Monitors all pending jobs and processes them upon completion, adhering to MAX_ACTIVE_RESEARCH_JOBS."""
    logging.info(
        "\n--- Research initiated. Now monitoring and launching new tasks. ---"
    )

    active_jobs: dict[str, ResearchJob] = {}
    pending_companies = list(companies)  # Create a mutable copy

    # Initial launch of MAX_ACTIVE_RESEARCH_JOBS
    for _ in range(min(MAX_ACTIVE_RESEARCH_JOBS, len(pending_companies))):
        if pending_companies:
            company_to_launch = pending_companies.pop(0)
            job = launch_research_job(driver, company_to_launch)
            active_jobs[job["handle"]] = job
            driver.switch_to.window(
                original_tab_handle
            )  # Switch back to main tab after launching

    while active_jobs or pending_companies:
        logging.info(
            f"\n-- Active tasks: {len(active_jobs)}. Pending in queue: {len(pending_companies)}. --"
        )

        jobs_to_remove = []
        for handle, job in list(active_jobs.items()):
            try:
                driver.switch_to.window(handle)
                # Check if the "Export" button is present, indicating completion
                if driver.find_elements(By.XPATH, SHARE_EXPORT_BUTTON_XPATH):
                    new_status = process_completed_job(driver, job, config, service)
                    active_jobs[handle]["status"] = new_status
                    jobs_to_remove.append(handle)
                else:
                    logging.info(
                        f"⏳ Research for '{job['company_name']}' is still in progress..."
                    )
            except (NoSuchWindowException, StaleElementReferenceException) as e:
                logging.warning(
                    f"⚠️ Window for '{job['company_name']}' not found or stale. Marking as error. Details: {e}"
                )
                active_jobs[handle]["status"] = "error"
                jobs_to_remove.append(handle)

        for handle in jobs_to_remove:
            logging.info(
                f"Task for '{active_jobs[handle]['company_name']}' completed or errored. Closing tab."
            )
            try:
                driver.switch_to.window(handle)
                driver.close()
            except NoSuchWindowException:
                logging.warning(
                    f"Window for {active_jobs[handle]['company_name']} already closed."
                )
            del active_jobs[handle]

        # Launch new jobs if slots are available and there are pending companies
        while len(active_jobs) < MAX_ACTIVE_RESEARCH_JOBS and pending_companies:
            company_to_launch = pending_companies.pop(0)
            job = launch_research_job(driver, company_to_launch)
            active_jobs[job["handle"]] = job
            driver.switch_to.window(
                original_tab_handle
            )  # Switch back to main tab after launching

        if active_jobs or pending_companies:  # Only sleep if there's still work to do
            time.sleep(MONITORING_INTERVAL_SECONDS)

    logging.info("\n🎉 All research tasks have been processed!")


@retry_on_exception
def get_last_response(driver: WebDriver) -> str:
    """Retrieves the last response from the page."""
    logging.info("Retrieving last response...")

    return driver.find_elements(By.CSS_SELECTOR, RESPONSE_CONTENT_CSS)[-1].text


def main():
    """Main function to orchestrate the Gemini Deep Research automation."""
    setup_logging()
    config = get_settings()
    service = get_drive_service()
    driver = None

    try:
        driver = initialize_driver(
            config.chrome.user_data_dir,
            config.chrome.profile_directory,
            config.chrome.chrome_driver_path,
            config.chrome.download_dir,
        )
        original_tab = driver.current_window_handle

        company_list = get_initial_company_list(driver)
        if not company_list:
            return

        monitor_and_process_jobs(driver, company_list, config, service, original_tab)

    except Exception as e:
        logging.exception(f"\nAn unexpected error occurred in main: {e}")
        if driver:
            driver.save_screenshot("debug_main_error.png")
    finally:
        if driver:
            logging.info("\nProcess finished. Browser will close in 60 seconds...")
            time.sleep(60)
            driver.quit()
            logging.info("WebDriver closed.")


if __name__ == "__main__":
    TEST = False
    if TEST:
        setup_logging()
        config = get_settings()
        service = get_drive_service()
        driver = None

        try:
            driver = initialize_driver(
                config.chrome.user_data_dir,
                config.chrome.profile_directory,
                config.chrome.chrome_driver_path,
                config.chrome.download_dir,
            )
            driver.get("https://gemini.google.com/app/a95bfed43b54ef04")
            input("Press Enter to continue...")
            summary = get_last_response(driver)
            logging.info(f"Summary: {summary}")
            doc_path = r"C:\Python Projects\IBKRBot\debug_main_error.png"
            send_report_to_telegram(
                "Example Company",
                summary,
                r"C:\Python Projects\IBKRBot\debug_main_error.png",
                "www.google.com",
                config.telegram.token,
                config.telegram.chat_id,
            )

        except Exception as e:
            logging.exception(f"\nAn unexpected error occurred in main: {e}")
            if driver:
                driver.save_screenshot("debug_main_error.png")
        finally:
            if driver:
                logging.info("\nProcess finished. Browser will close in 60 seconds...")
                time.sleep(60)
                driver.quit()
                logging.info("WebDriver closed.")

    else:
        main()

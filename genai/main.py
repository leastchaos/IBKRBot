from datetime import datetime
import logging
import sys
import time
import os
import json
import pyperclip
import requests
from typing import TypedDict, List

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

from genai.config import Settings, get_settings
from genai.google_api_helpers import (
    get_doc_id_from_url,
    get_drive_service,
    move_file_to_folder,
    share_google_doc_publicly,
)
from genai.helpers import retry_on_exception
from genai.logging_config import setup_logging
from genai.notifications import send_report_to_telegram
from genai.prompt_text import PROMPT_TEXT, PROMPT_TEXT_2, PROMPT_TEXT_3, PROMPT_TEXT_4


# --- Constants ---
GEMINI_URL = "https://gemini.google.com/app"
MONITORING_INTERVAL_SECONDS = 15

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

    handle: str
    company_name: str
    status: str  # "pending", "completed", "processed", "error"


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
        try:
            WebDriverWait(driver, 300).until(
                EC.element_to_be_clickable((By.XPATH, START_RESEARCH_BUTTON_XPATH))
            ).click()  # diisable this to save research report during debugging
            logging.info("Start Research button clicked.")
        except StaleElementReferenceException:
            logging.info(
                "Start Research button became stale. Re-finding and clicking..."
            )
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, START_RESEARCH_BUTTON_XPATH))
            ).click()
            logging.info("Start Research button clicked after re-finding.")
        logging.info("Deep Research initiated.")
    except Exception as e:
        logging.exception(f"An error occurred during Deep Research initiation: {e}")
        driver.save_screenshot("debug_deep_research_error.png")
        raise


def get_response(
    driver: WebDriver, responses_before_prompt: int, is_csv: bool = False
) -> list[str] | str | None:
    """Waits for and returns the latest AI response."""
    try:
        logging.info(
            f"Waiting for new response (currently {responses_before_prompt} on page)..."
        )
        # Wait for a new response element to appear
        WebDriverWait(driver, 600).until(
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


def launch_research_jobs(
    driver: WebDriver, companies: list[str]
) -> dict[str, ResearchJob]:
    """Opens a new tab for each company and starts the research."""
    research_jobs = {}
    logging.info("\n--- Starting All Company-Specific Deep Research Tasks ---")
    for company in companies:
        company_name = company.strip()
        if not company_name:
            continue
        logging.info(f"\nInitiating research for: {company_name}")
        driver.switch_to.new_window("tab")
        new_handle = driver.current_window_handle
        research_jobs[new_handle] = {
            "handle": new_handle,
            "company_name": company_name,
            "status": "pending",
        }
        navigate_to_url(driver, GEMINI_URL)
        company_prompt = f"{PROMPT_TEXT_3} {company_name}."
        perform_deep_research(driver, company_prompt)
    return research_jobs


def process_completed_job(
    driver: WebDriver, job: ResearchJob, config: Settings, service
) -> str:
    """Processes a single completed research job: summarizes, exports, notifies."""
    try:
        logging.info(
            f"✅ Research for '{job['company_name']}' is COMPLETE. Processing..."
        )

        # 1. Get Summary
        res_before_summary = len(
            driver.find_elements(By.CSS_SELECTOR, RESPONSE_CONTENT_CSS)
        )
        enter_prompt_and_submit(driver, PROMPT_TEXT_4)
        summary_data = get_response(driver, res_before_summary, is_csv=False)
        logging.info(f"Summary for '{job['company_name']}': {summary_data}")
        # 2. Export and manage Google Doc
        doc_url = export_and_get_doc_url(driver, job["handle"])
        if not doc_url or not summary_data:
            logging.error(
                f"❌ Failed to get Doc URL or Summary for {job['company_name']}."
            )
            return "error"

        doc_id = get_doc_id_from_url(doc_url)
        move_file_to_folder(service, doc_id, config.folder_id)
        share_google_doc_publicly(service, doc_id)
        doc_path = download_google_doc_as_pdf(
            doc_url, config.download_dir, job["company_name"]
        )

        # 3. Send notification
        send_report_to_telegram(
            job["company_name"],
            summary_data,
            doc_path,
            doc_url,
            config.telegram_token,
            config.telegram_chat_id,
        )
        return "processed"
    except Exception as e:
        logging.exception(f"❌ Error processing job for '{job['company_name']}': {e}")
        return "error"


def monitor_and_process_jobs(
    driver: WebDriver, jobs: dict[str, ResearchJob], config: Settings, service
):
    """Monitors all pending jobs and processes them upon completion."""
    logging.info("\n--- All research initiated. Now monitoring for completion. ---")

    while any(job["status"] == "pending" for job in jobs.values()):
        pending_count = sum(1 for job in jobs.values() if job["status"] == "pending")
        logging.info(f"\n-- {pending_count} tasks pending. Checking status... --")

        for handle, job in list(jobs.items()):
            if job["status"] != "pending":
                continue

            try:
                driver.switch_to.window(handle)
                # Check if the "Export" button is present, indicating completion
                if driver.find_elements(By.XPATH, SHARE_EXPORT_BUTTON_XPATH):
                    new_status = process_completed_job(driver, job, config, service)
                    jobs[handle]["status"] = new_status
                else:
                    logging.info(
                        f"⏳ Research for '{job['company_name']}' is still in progress..."
                    )
            except (NoSuchWindowException, StaleElementReferenceException) as e:
                logging.warning(
                    f"⚠️ Window for '{job['company_name']}' not found or stale. Marking as error. Details: {e}"
                )
                jobs[handle]["status"] = "error"

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
            config.user_data_dir,
            config.profile_directory,
            config.chrome_driver_path,
            config.download_dir,
        )
        original_tab = driver.current_window_handle

        company_list = get_initial_company_list(driver)
        if not company_list:
            return

        research_jobs = launch_research_jobs(driver, company_list)
        driver.switch_to.window(original_tab)  # Switch back to the main tab

        monitor_and_process_jobs(driver, research_jobs, config, service)

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
                config.user_data_dir,
                config.profile_directory,
                config.chrome_driver_path,
                config.download_dir,
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
                config.telegram_token,
                config.telegram_chat_id,
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
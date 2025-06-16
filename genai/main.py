from datetime import datetime
import logging
import sys
import time
import os
import json
import pyperclip
import requests
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
from genai.logging_config import setup_logging
from genai.notifications import send_report_to_telegram
from genai.prompt_text import PROMPT_TEXT, PROMPT_TEXT_2, PROMPT_TEXT_3, PROMPT_TEXT_4

# --- User Configurable Variables ---
GEMINI_URL = "https://gemini.google.com/app"
# How many seconds to wait between checking the status of all tabs
MONITORING_INTERVAL_SECONDS = 15

# --- Element Locators (Examples - These may change with UI updates) ---
PROMPT_TEXTAREA_CSS = ".ql-editor[contenteditable='true']"
DEEP_RESEARCH_BUTTON_XPATH = "//button[contains(., 'Deep Research')]"
START_RESEARCH_BUTTON_XPATH = "//button[contains(., 'Start research')]"
SHARE_EXPORT_BUTTON_XPATH = "//button[contains(., 'Export')]"
EXPORT_TO_DOCS_BUTTON_XPATH = "//button[contains(., 'Export to Docs')]"
RESPONSE_CONTENT_CSS = "div.response-content"
GENERATING_INDICATOR_CSS = "progress.mat-mdc-linear-progress"

config = get_settings()


def initialize_driver(
    user_data_dir, profile_directory, webdriver_path, download_dir
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
    """Navigates to the specified URL."""
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
    """Enters text into the prompt textarea WITHOUT submitting with RETURN."""
    logging.info("Copying prompt to clipboard...")
    pyperclip.copy(prompt)
    logging.info("Locating prompt textarea...")
    prompt_textarea = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, PROMPT_TEXTAREA_CSS))
    )
    prompt_textarea.clear()
    prompt_textarea.send_keys(Keys.CONTROL, "v")
    time.sleep(1)
    logging.info("Text entered.")


def enter_prompt_and_submit(driver: WebDriver, prompt: str):
    """Enters the prompt in the prompt textarea and submits with RETURN."""
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
    """Corrected function to handle the Deep Research workflow."""
    try:
        logging.info("Locating and clicking Deep Research button...")
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, DEEP_RESEARCH_BUTTON_XPATH))
        ).click()
        time.sleep(1)
        enter_prompt_and_submit(driver, prompt)
        logging.info("Prompt text entered. Locating and clicking Start Research button...")
        # WebDriverWait(driver, 300).until(
        #     EC.element_to_be_clickable((By.XPATH, START_RESEARCH_BUTTON_XPATH))
        # ).click() # diisable this to save research report during debugging
        logging.info("Deep Research initiated.")
    except Exception as e:
        logging.exception(f"An error occurred during Deep Research initiation: {e}")
        driver.save_screenshot("debug_deep_research_error.png")
        raise


def get_response(
    driver: WebDriver, responses_before_prompt: int, is_json: bool = False
):
    """Waits for a new AI response and parses it as either JSON or a list."""
    try:
        logging.info(
            f"Waiting for new response (currently {responses_before_prompt} on page)..."
        )
        WebDriverWait(driver, 600).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, RESPONSE_CONTENT_CSS))
            > responses_before_prompt
        )
        latest_response_element = driver.find_elements(
            By.CSS_SELECTOR, RESPONSE_CONTENT_CSS
        )[-1]
        logging.info("Waiting for response to finish generating...")
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
        if is_json:
            json_text = raw_text.split("```json")[-1].split("```")[0].strip()
            return json.loads(json_text)
        else:
            return [item.strip() for item in raw_text.split(",") if item.strip()]
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
        time.sleep(5)
        new_handle = WebDriverWait(driver, 30).until(
            lambda d: next(iter(set(d.window_handles) - initial_handles), None)
        )
        driver.switch_to.window(new_handle)
        while driver.current_url == "about:blank":
            logging.info("Waiting for export to complete...")
            time.sleep(5)
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
        safe_company_name = "".join(
            c for c in company_name if c.isalnum() or c in (" ", "_")
        ).rstrip()
        file_path = os.path.join(download_folder, f"{safe_company_name} Report {datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logging.info(f"Successfully downloaded report to: {file_path}")
        return file_path
    except requests.exceptions.RequestException as e:
        logging.exception(f"Failed to download file from Google Docs: {e}")
        return None


def main():
    """Main function to orchestrate the Gemini Deep Research automation."""
    setup_logging()
    config = get_settings()
    service = get_drive_service()
    try:
        os.makedirs(config.download_dir, exist_ok=True)

        driver = initialize_driver(
            config.user_data_dir,
            config.profile_directory,
            config.chrome_driver_path,
            config.download_dir,
        )
        original_tab = driver.current_window_handle

        navigate_to_url(driver, GEMINI_URL)
        perform_deep_research(driver, PROMPT_TEXT)
        WebDriverWait(driver, 1200).until(
            EC.element_to_be_clickable((By.XPATH, SHARE_EXPORT_BUTTON_XPATH))
        )
        logging.info("Initial research complete. Asking for company list...")

        responses_before = len(
            driver.find_elements(By.CSS_SELECTOR, RESPONSE_CONTENT_CSS)
        )
        enter_prompt_and_submit(driver, PROMPT_TEXT_2)
        company_list = get_response(driver, responses_before, is_json=False)

        if not company_list:
            logging.error("Could not retrieve company list. Exiting.")
            return

        research_tabs = {}
        logging.info("\n--- Starting All Company-Specific Deep Research Tasks ---")
        for company in company_list:
            company_name = company.strip()
            if not company_name:
                continue
            logging.info(f"\nInitiating research for: {company_name}")
            driver.switch_to.new_window("tab")
            new_handle = driver.current_window_handle
            research_tabs[new_handle] = {"company": company_name, "status": "pending"}
            navigate_to_url(driver, GEMINI_URL)
            company_prompt = f"{PROMPT_TEXT_3} {company_name}."
            perform_deep_research(driver, company_prompt)

        driver.switch_to.window(original_tab)

        logging.info("\n--- All research initiated. Now monitoring for completion. ---")
        while True:
            pending_tabs = {
                h: d for h, d in research_tabs.items() if d["status"] == "pending"
            }
            if not pending_tabs:
                logging.info("\n🎉 All research tasks have been processed!")
                break

            logging.info(f"\n-- {len(pending_tabs)} tasks pending. Checking status... --")
            for handle, data in pending_tabs.items():
                pdf_path = None
                try:
                    driver.switch_to.window(handle)
                    if driver.find_elements(By.XPATH, SHARE_EXPORT_BUTTON_XPATH):
                        logging.info(
                            f"✅ Research for '{data['company']}' is COMPLETE. Starting processing..."
                        )
                        summary_data = None
                        res_before_summary = len(
                            driver.find_elements(
                                By.CSS_SELECTOR, RESPONSE_CONTENT_CSS
                            )
                        )
                        enter_prompt_and_submit(driver, PROMPT_TEXT_4)
                        summary_data = get_response(
                            driver, res_before_summary, is_json=False
                        )
                        doc_url = export_and_get_doc_url(driver, handle)
                        if doc_url:
                            doc_id = get_doc_id_from_url(doc_url)
                            move_file_to_folder(service, doc_id, config.folder_id)
                            share_google_doc_publicly(service, doc_id)
                            pdf_path = download_google_doc_as_pdf(
                                doc_url, config.download_dir, data["company"]
                            )
                        if pdf_path and summary_data:
                            send_report_to_telegram(
                                data["company"],
                                summary_data,
                                pdf_path,
                                config.telegram_token,
                                config.telegram_chat_id,
                            )
                            research_tabs[handle]["status"] = "processed"
                        else:
                            logging.error(
                                f"❌ Failed to process report for {data['company']}. Missing PDF or Summary."
                            )
                            research_tabs[handle]["status"] = "error"
                    else:
                        logging.info(
                            f"⏳ Research for '{data['company']}' is still in progress..."
                        )
                except (NoSuchWindowException, StaleElementReferenceException):
                    logging.exception(
                        f"⚠️ Window issue for '{data['company']}': {e}. Marking as errored."
                    )
                    research_tabs[handle]["status"] = "error"
            time.sleep(MONITORING_INTERVAL_SECONDS)

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

    main()

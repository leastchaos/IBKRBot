import sys
import time
import os
import json
import pyperclip
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from genai.config import get_settings
from genai.prompt_text import PROMPT_TEXT, PROMPT_TEXT_2

# PROMPT_TEXT = "Provide a detailed analysis of the impact of AI on the global shipping industry."
# PROMPT_TEXT_2 = "From the report above, extract the names of the top 5 shipping companies mentioned. Return them as a comma-separated list and nothing else."
# --- End Mock ---

# --- User Configurable Variables ---
GEMINI_URL = "https://gemini.google.com/app"

# --- Element Locators (Examples - These may change with UI updates) ---
PROMPT_TEXTAREA_CSS = ".ql-editor[contenteditable='true']"
DEEP_RESEARCH_BUTTON_XPATH = "//button[contains(., 'Deep Research')]"
START_RESEARCH_BUTTON_XPATH = "//button[contains(., 'Start research')]"
SHARE_EXPORT_BUTTON_XPATH = "//button[contains(., 'Export')]"
EXPORT_TO_DOCS_BUTTON_XPATH = "//button[contains(., 'Export to Docs')]"
# --- NEW LOCATORS ---
# IMPORTANT: Verify these selectors using your browser's developer tools.
RESPONSE_CONTENT_CSS = "div.response-content"
GENERATING_INDICATOR_CSS = (
    "progress.mat-mdc-linear-progress"  # Example for a progress bar
)

config = get_settings()


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
        "safeBrowse.enabled": False,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    if webdriver_path:
        service = Service(executable_path=webdriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        driver = webdriver.Chrome(options=chrome_options)
    print("WebDriver initialized.")
    return driver


def navigate_to_url(driver: WebDriver, url: str):
    """Navigates to the specified URL."""
    print(f"Navigating to {url}...")
    driver.get(url)
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, PROMPT_TEXTAREA_CSS))
        )
        print("Page loaded.")
    except TimeoutException:
        print("Timeout waiting for page to load initial elements.")
        raise


def enter_prompt(driver: WebDriver, prompt: str):
    """Enters the prompt in the prompt textarea and submits."""
    print("Copying prompt to clipboard...")
    pyperclip.copy(prompt)  # Copy the long text to the system clipboard
    print("Locating prompt textarea...")
    prompt_textarea = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, PROMPT_TEXTAREA_CSS))
    )
    print("Entering prompt...")
    prompt_textarea.clear()
    print("Pasting prompt from clipboard...")
    prompt_textarea.send_keys(Keys.CONTROL, "v")
    time.sleep(1)
    prompt_textarea.send_keys(Keys.RETURN)
    print("Prompt submitted.")


def perform_deep_research(driver: WebDriver, prompt: str):
    """Enters the prompt, enables Deep Research, and starts it."""
    try:
        print("Locating and clicking Deep Research button...")
        deep_research_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, DEEP_RESEARCH_BUTTON_XPATH))
        )
        deep_research_button.click()
        time.sleep(1)
        enter_prompt(driver, prompt)
        print("Prompt submitted with Deep Research enabled.")
        print("Locating and clicking Start Research button...")
        start_research_button = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, START_RESEARCH_BUTTON_XPATH))
        )
        start_research_button.click()
        print("Deep Research initiated.")
    except Exception as e:
        print(f"An error occurred during Deep Research initiation: {e}")
        driver.save_screenshot("debug_deep_research_error.png")
        raise


def export_report_to_docs(driver: WebDriver, timeout_seconds: int = 900):
    """Clicks the necessary buttons to export the report to Google Docs."""
    try:
        print(
            f"Waiting for research completion (max {timeout_seconds / 60} minutes)..."
        )
        share_export_button = WebDriverWait(driver, timeout_seconds).until(
            EC.element_to_be_clickable((By.XPATH, SHARE_EXPORT_BUTTON_XPATH))
        )
        print("Research completed. Export button available.")
        share_export_button.click()
        time.sleep(1)

        print("Locating and clicking Export to Google Docs button...")
        export_to_docs_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, EXPORT_TO_DOCS_BUTTON_XPATH))
        )
        export_to_docs_button.click()
        print("Export to Google Docs initiated.")
        time.sleep(5)
    except Exception as e:
        print(f"An error occurred during report export: {e}")
        driver.save_screenshot("debug_export_error.png")
        raise


def close_current_window(driver: WebDriver):
    """Closes the current browser window/tab."""
    print(f"Closing current window: {driver.title}...")
    driver.close()


def get_gemini_response(driver: WebDriver) -> list[str]:
    """
    Waits for the AI to finish responding, then retrieves the last response
    and parses it into a list of strings.
    """
    try:
        print("Waiting for Gemini to finish responding (this may take a moment)...")
        WebDriverWait(driver, 180).until(
            EC.invisibility_of_element_located(
                (By.CSS_SELECTOR, GENERATING_INDICATOR_CSS)
            )
        )
        print("Response finished generating.")
        time.sleep(1)

        print("Locating response elements...")
        response_elements = driver.find_elements(By.CSS_SELECTOR, RESPONSE_CONTENT_CSS)
        if not response_elements:
            print("Warning: No response elements were found on the page.")
            return []

        latest_response_text = response_elements[-1].text
        print(f"Extracted raw text: '{latest_response_text}'")

        if latest_response_text:
            parsed_list = [item.strip() for item in latest_response_text.split(",")]
            print(f"Successfully parsed list: {parsed_list}")
            return parsed_list
        else:
            print("Warning: The latest response element contained no text.")
            return []
    except TimeoutException:
        print(
            "TimeoutException: The response took too long to generate or the loading indicator was not found."
        )
        driver.save_screenshot("debug_get_response_timeout.png")
        raise
    except Exception as e:
        print(f"An unexpected error occurred in get_gemini_response: {e}")
        driver.save_screenshot("debug_get_response_error.png")
        raise


def main():
    """Main function to orchestrate the Gemini Deep Research automation."""
    driver: WebDriver | None = None
    print("Starting Gemini Deep Research Automation Script.")
    print(
        "IMPORTANT: Please ensure you are manually logged into gemini.google.com in Chrome."
    )
    try:
        print("Initializing Chrome driver...")
        config = get_settings()
        driver = initialize_driver(
            config.user_data_dir,
            config.profile_directory,
            config.chrome_driver_path,
            config.download_dir,
        )
        navigate_to_url(driver, GEMINI_URL)
        perform_deep_research(driver, PROMPT_TEXT)
        export_report_to_docs(driver)
        # if driver has more than one window, close the current one
        if len(driver.window_handles) > 1:
            close_current_window(driver)
        enter_prompt(driver, PROMPT_TEXT_2)
        company_list = get_gemini_response(driver)

        print("\n--- Process Completed ---")
        if company_list:
            print("Retrieved Company List:")
            for company in company_list:
                print(f"- {company}")
        else:
            print("Could not retrieve the company list.")

    except Exception as e:
        print(f"An unexpected error occurred in main: {e}")
    finally:
        if driver:
            print("Closing WebDriver in 20 seconds...")
            time.sleep(20)
            driver.quit()
            print("WebDriver closed.")


if __name__ == "__main__":
    main()

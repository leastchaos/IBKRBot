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
from selenium.common.exceptions import TimeoutException, NoSuchElementException, NoSuchWindowException
from selenium.webdriver.common.keys import Keys
from genai.config import get_settings
from genai.prompt_text import PROMPT_TEXT, PROMPT_TEXT_2

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
    pyperclip.copy(prompt) # Copy the long text to the system clipboard
    print("Locating prompt textarea...")
    prompt_textarea = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, PROMPT_TEXTAREA_CSS))
    )
    print("Entering prompt...")
    prompt_textarea.clear()
    print("Pasting prompt from clipboard...")
    prompt_textarea.send_keys(Keys.CONTROL, 'v')
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
        print(f"Waiting for research completion (max {timeout_seconds / 60} minutes)...")
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

def get_gemini_response(driver: WebDriver) -> list[str]:
    """
    Waits for the AI to finish responding, then retrieves the last response
    and parses it into a list of strings.
    """
    try:
        print("Waiting for Gemini to finish responding (this may take a moment)...")
        WebDriverWait(driver, 180).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, GENERATING_INDICATOR_CSS))
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
            parsed_list = [item.strip() for item in latest_response_text.split(',')]
            print(f"Successfully parsed list: {parsed_list}")
            return parsed_list
        else:
            print("Warning: The latest response element contained no text.")
            return []
    except TimeoutException:
        print("TimeoutException: The response took too long to generate or the loading indicator was not found.")
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
    print("IMPORTANT: Please ensure you are manually logged into gemini.google.com in Chrome.")
    try:
        config = get_settings()
        driver = initialize_driver(
            config.user_data_dir,
            config.profile_directory,
            config.chrome_driver_path,
            config.download_dir,
        )
        
        original_tab = driver.current_window_handle
        
        # 1. Perform initial research and get company list
        navigate_to_url(driver, GEMINI_URL)
        perform_deep_research(driver, PROMPT_TEXT)
        export_report_to_docs(driver)

        if len(driver.window_handles) > 1:
            for handle in driver.window_handles:
                if handle != original_tab:
                    driver.switch_to.window(handle)
                    driver.close()
            driver.switch_to.window(original_tab)

        enter_prompt(driver, PROMPT_TEXT_2)
        company_list = get_gemini_response(driver)

        if not company_list:
            print("Could not retrieve the company list. Exiting.")
            return

        print("\n--- Retrieved Company List ---")
        for company in company_list:
            print(f"- {company}")

        # 2. Initiate research for all companies in new tabs
        research_tabs = {}
        print("\n--- Starting All Company-Specific Deep Research Tasks ---")
        for company in company_list:
            company_name = company.strip()
            if not company_name:
                continue

            print(f"\nInitiating research for: {company_name}")
            driver.switch_to.new_window('tab')
            new_handle = driver.current_window_handle
            research_tabs[new_handle] = {'company': company_name, 'status': 'pending'}
            
            navigate_to_url(driver, GEMINI_URL)
            company_prompt = f"{PROMPT_TEXT} Focus the analysis specifically on {company_name}."
            perform_deep_research(driver, company_prompt)
        
        driver.switch_to.window(original_tab) # Switch back to the main tab

        # 3. Monitor all tabs until research is complete
        print("\n--- All research initiated. Now monitoring for completion. ---")
        while True:
            pending_count = 0
            for handle, data in research_tabs.items():
                if data['status'] == 'pending':
                    try:
                        driver.switch_to.window(handle)
                        # Check for completion by looking for the export button without waiting
                        export_button = driver.find_elements(By.XPATH, SHARE_EXPORT_BUTTON_XPATH)
                        if export_button:
                            print(f"✅ Research for '{data['company']}' is COMPLETE.")
                            research_tabs[handle]['status'] = 'completed'
                        else:
                            # If not complete, increment the pending counter
                            print(f"⏳ Research for '{data['company']}' is still in progress...")
                            pending_count += 1
                    except NoSuchWindowException:
                        print(f"⚠️ Window for '{data['company']}' was closed. Marking as errored.")
                        research_tabs[handle]['status'] = 'error'
                    except Exception as e:
                        print(f"An error occurred while checking '{data['company']}': {e}")
                        research_tabs[handle]['status'] = 'error'

            if pending_count == 0:
                print("\n🎉 All research tasks have successfully completed!")
                break
            else:
                print(f"\n-- {pending_count} tasks still pending. Re-checking in {MONITORING_INTERVAL_SECONDS} seconds. --")
                time.sleep(MONITORING_INTERVAL_SECONDS)


    except Exception as e:
        print(f"\nAn unexpected error occurred in main: {e}")
        if driver:
          driver.save_screenshot("debug_main_error.png")
    finally:
        if driver:
            print("\nProcess finished. Browser will close in 60 seconds...")
            time.sleep(60)
            driver.quit()
            print("WebDriver closed.")


if __name__ == "__main__":
    main()
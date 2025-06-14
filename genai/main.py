import time
import os
import json
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

# --- User Configurable Variables ---
GEMINI_URL = "https://gemini.google.com/app"  # Updated URL based on common usage
# --- Element Locators (Examples - These may change with UI updates) ---
# It's highly recommended to verify these selectors using browser developer tools.
PROMPT_TEXTAREA_CSS = (
    ".ql-editor[contenteditable='true']"  # Common for rich text editors
)
DEEP_RESEARCH_BUTTON_XPATH = "//button[contains(., 'Deep Research')]"
# Send button might be an icon, aria-label is often more stable
SEND_PROMPT_BUTTON_CSS = "button"  # Example, verify
START_RESEARCH_BUTTON_XPATH = "//button[contains(., 'Start research')]"
VIEW_REPORT_BUTTON_XPATH = "//button[contains(text(), 'View report')]"
# Share & Export button might have an icon or specific aria-label
SHARE_EXPORT_BUTTON_XPATH = "//button[contains(., 'Export')]"  # Example, verify
EXPORT_TO_DOCS_BUTTON_XPATH = (
    "//button[contains(., 'Export to Docs')]"  # Example, verify
)

config = get_settings()


def initialize_driver(
    user_data_dir: str,
    profile_directory: str,
    webdriver_path: str | None,
    download_dir: str,
):
    """Initializes and returns a Selenium WebDriver instance for Chrome."""
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    chrome_options.add_argument(f"--profile-directory={profile_directory}")
    # chrome_options.add_argument("--headless") # Uncomment for headless operation

    # Preferences for download behavior (general Selenium setting)
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    if webdriver_path:
        service = Service(executable_path=webdriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        # Selenium Manager should handle ChromeDriver if not specified and it's in PATH or downloadable
        driver = webdriver.Chrome(options=chrome_options)

    print("WebDriver initialized.")
    return driver


def navigate_to_url(driver: WebDriver, url: str):
    """Navigates to the Gemini URL."""
    print(f"Navigating to {url}...")
    driver.get(url)
    # Add a generic wait for page elements to start loading, e.g., for the chat input area
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, PROMPT_TEXTAREA_CSS))
        )
        print("Gemini page loaded.")
    except TimeoutException:
        print("Timeout waiting for Gemini page to load initial elements.")
        raise


def enter_prompt(driver: WebDriver, prompt: str):
    """Enters the prompt in the prompt textarea."""
    print("Locating prompt textarea...")
    prompt_textarea = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, PROMPT_TEXTAREA_CSS))
    )
    print("Entering prompt...")
    prompt_textarea.clear()
    prompt_textarea.send_keys(prompt)
    time.sleep(1)  # Small pause after typing
    print("Locating and clicking Send Prompt button...")
    # Press enter in the prompt_text area
    prompt_textarea.send_keys(Keys.RETURN)


def perform_deep_research(driver: WebDriver, prompt: str):
    """Enters the prompt, enables Deep Research, and starts it."""
    try:
        print("Locating and clicking Deep Research button...")
        deep_research_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, DEEP_RESEARCH_BUTTON_XPATH))
        )
        deep_research_button.click()
        time.sleep(1)  # Wait for UI to update after clicking Deep Research
        enter_prompt(driver, prompt)
        print("Prompt submitted with Deep Research enabled.")
        print("Locating and clicking Start Research button...")
        start_research_button = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, START_RESEARCH_BUTTON_XPATH))
        )
        start_research_button.click()
        print("Deep Research initiated.")

    except TimeoutException as e:
        print(f"TimeoutException during Deep Research initiation: {e}")
        driver.save_screenshot("debug_deep_research_timeout.png")
        raise
    except NoSuchElementException as e:
        print(f"NoSuchElementException during Deep Research initiation: {e}")
        driver.save_screenshot("debug_deep_research_notfound.png")
        raise
    except Exception as e:
        print(f"An unexpected error occurred during Deep Research initiation: {e}")
        driver.save_screenshot("debug_deep_research_error.png")
        raise


def wait_for_research_completion(driver: WebDriver):
    """Waits for the Deep Research to complete by looking for the 'View report' button."""
    # Deep Research can take a significant amount of time (5-15 minutes or more)
    # Adjust timeout accordingly. 900 seconds = 15 minutes.
    timeout_seconds = 1200
    print(
        f"Waiting for Deep Research completion (max {timeout_seconds / 60} minutes)..."
    )
    try:
        view_report_button = WebDriverWait(driver, timeout_seconds).until(
            EC.visibility_of_element_located((By.XPATH, EXPORT_TO_DOCS_BUTTON_XPATH))
        )
        print("Deep Research completed. 'View report' button is visible.")
        # Optional: click view report if needed before export, or if export is inside the report view
        # view_report_button.click()
        # time.sleep(3) # Wait for report view to load if clicked
    except TimeoutException:
        print(
            "Timeout waiting for Deep Research to complete or 'View report' button to appear."
        )
        driver.save_screenshot("debug_research_completion_timeout.png")
        raise


def export_report_to_docs(driver: WebDriver, timeout_seconds: int = 900):
    """Clicks the necessary buttons to export the report to Google Docs."""
    try:
        print("Locating and clicking Share & Export button...")
        share_export_button = WebDriverWait(driver, timeout_seconds).until(
            EC.element_to_be_clickable((By.XPATH, SHARE_EXPORT_BUTTON_XPATH))
        )
        share_export_button.click()
        time.sleep(1)  # Wait for export options to appear

        print("Locating and clicking Export to Google Docs button...")
        export_to_docs_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, EXPORT_TO_DOCS_BUTTON_XPATH))
        )
        export_to_docs_button.click()
        print(
            "Export to Google Docs initiated. A new document should be created in your Google Drive."
        )
        # The script does not handle the new tab or the Google Doc itself.
        # It assumes the action triggers the export and then proceeds.
        # Wait for a moment to allow the export process to be triggered.
        time.sleep(5)  # Allow time for the export action to be processed by Gemini

    except TimeoutException as e:
        print(f"TimeoutException during report export: {e}")
        driver.save_screenshot("debug_export_timeout.png")
        raise
    except NoSuchElementException as e:
        print(f"NoSuchElementException during report export: {e}")
        driver.save_screenshot("debug_export_notfound.png")
        raise
    except Exception as e:
        print(f"An unexpected error occurred during report export: {e}")
        driver.save_screenshot("debug_export_error.png")
        raise


def close_current_window(driver: WebDriver):
    """Closes the Google Docs window."""
    print(f"Closing {driver.title} window...")
    driver.close()


def get_gemini_response(driver: WebDriver) -> list[str]:
    """Retrieves the Gemini response for the comma-seperated list."""


def main():
    """Main function to orchestrate the Gemini Deep Research automation."""
    driver = None  # Initialize driver to None for the finally block
    # Reminder: User must be logged into Google/Gemini manually in Chrome before running.
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
        # wait_for_research_completion(driver)
        export_report_to_docs(driver)
        close_current_window(driver)
        enter_prompt(driver, PROMPT_TEXT_2)
        get_gemini_response(driver)

        print("Gemini Deep Research and Export to Docs process completed successfully.")

    except TimeoutException:
        print(
            "A timeout occurred during the automation process. Check logs and screenshots."
        )
    except NoSuchElementException:
        print(
            "An element was not found. The UI might have changed. Check logs and screenshots."
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if driver:
            print("Closing WebDriver.")
            # driver.quit() # Uncomment to close the browser automatically
            print(
                "Browser will remain open for inspection. Manually close it when done."
            )
            # Or keep it open for a few seconds then close:
            # time.sleep(30)
            # driver.quit()


if __name__ == "__main__":
    main()

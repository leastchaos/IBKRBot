# genai/browser_actions.py
import logging
import time
from datetime import datetime

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from genai.constants import (
    ADD_FILE_BUTTON_XPATH,
    ADD_FROM_DRIVE_BUTTON_XPATH,
    DEEP_RESEARCH_BUTTON_XPATH,
    DRIVE_URL_INPUT_CSS,
    EXPORT_TO_DOCS_BUTTON_XPATH,
    GENERATING_INDICATOR_CSS,
    INSERT_BUTTON_XPATH,
    PICKER_IFRAME_XPATH,
    PROMPT_TEXTAREA_CSS,
    RESPONSE_CONTENT_CSS,
    SHARE_EXPORT_BUTTON_XPATH,
    START_RESEARCH_BUTTON_XPATH,
    TOOLS_BUTTON_XPATH,
)
from genai.helpers.google_api_helpers import get_doc_id_from_url
from genai.common.utils import save_debug_screenshot
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


class Browser:
    """Encapsulates all Selenium browser interactions for the GenAI workflows."""

    def __init__(self, driver: WebDriver, default_timeout: int = 20):
        """
        Initializes the Browser wrapper with an existing WebDriver instance.
        This __init__ is now primarily for internal use by the class method.
        """
        self.driver = driver
        self.wait = WebDriverWait(self.driver, default_timeout)

    @classmethod
    def initialize(
        cls,
        user_data_dir: str,
        profile_directory: str,
        webdriver_path: str | None,
        download_dir: str,
        headless: bool = True,
    ) -> "Browser":
        """
        A factory method that creates a WebDriver instance and returns an initialized Browser object.
        """
        logging.info(f"Initializing driver for profile: {profile_directory}")
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--start-maximized")

        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        chrome_options.add_argument(f"--profile-directory={profile_directory}")

        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True,
        }
        chrome_options.add_experimental_option("prefs", prefs)

        service = Service(executable_path=webdriver_path) if webdriver_path else None
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logging.info("WebDriver initialized successfully.")
        # Return an instance of the class itself
        return cls(driver)

    def _click_element(self, by: str, value: str, timeout: int | None = None) -> None:
        """Robustly clicks an element, waiting for it and handling stale references."""
        wait = self.wait if timeout is None else WebDriverWait(self.driver, timeout)
        try:
            element = wait.until(EC.element_to_be_clickable((by, value)))
            element.click()
        except StaleElementReferenceException:
            logging.warning(f"Stale element reference for '{value}'. Retrying click.")
            time.sleep(1)
            element = wait.until(EC.element_to_be_clickable((by, value)))
            element.click()

    def navigate_to_url(self, url: str) -> None:
        """Navigates to the specified URL and waits for the page to load."""
        logging.info(f"Navigating to {url}...")
        self.driver.get(url)
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, PROMPT_TEXTAREA_CSS))
        )
        logging.info("Page loaded.")

    def enter_prompt_and_submit(self, prompt: str) -> None:
        """Enters the prompt in the textarea and submits it."""
        logging.info("Injecting prompt text directly via JavaScript...")
        try:
            prompt_textarea = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, PROMPT_TEXTAREA_CSS))
            )
            js_script = """
                var element = arguments[0];
                var text = arguments[1];
                element.textContent = text;
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
            """
            self.driver.execute_script(js_script, prompt_textarea, prompt)
            prompt_textarea.send_keys(Keys.RETURN)
            logging.info("Prompt submitted successfully.")
        except Exception:
            logging.error(
                "Failed to find or interact with prompt textarea.", exc_info=True
            )
            save_debug_screenshot(self.driver, "enter_prompt_error")
            raise

    def navigate_to_deep_research_prompt(self) -> None:
        """Orchestrates the clicks to get to the deep research interface."""
        logging.info("Navigating to the Deep Research prompt...")
        self._click_element(By.XPATH, TOOLS_BUTTON_XPATH)
        self._click_element(By.XPATH, DEEP_RESEARCH_BUTTON_XPATH, timeout=60)

    def click_start_research(self) -> None:
        """Waits for and clicks the 'Start Research' button."""
        logging.info("Locating and clicking Start Research button...")
        self._click_element(By.XPATH, START_RESEARCH_BUTTON_XPATH, timeout=300)

    def attach_drive_file(self, file_url: str) -> None:
        """Handles the UI interaction to attach a Google Drive file by URL."""
        logging.info(f"Attaching Google Drive file: {file_url}")
        self._click_element(By.XPATH, ADD_FILE_BUTTON_XPATH)
        self._click_element(By.XPATH, ADD_FROM_DRIVE_BUTTON_XPATH)

        # Switch to iframe
        picker_iframe = self.wait.until(
            EC.presence_of_element_located((By.XPATH, PICKER_IFRAME_XPATH))
        )
        self.driver.switch_to.frame(picker_iframe)
        logging.info("Switched to Google Picker iframe.")

        # Interact within iframe
        url_input = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, DRIVE_URL_INPUT_CSS))
        )
        url_input.send_keys(file_url)
        url_input.send_keys(Keys.RETURN)

        doc_id = get_doc_id_from_url(file_url)
        if not doc_id:
            raise ValueError(f"Could not extract document ID from URL: {file_url}")

        file_selector_xpath = f"//div[@role='option' and @data-id='{doc_id}']"
        self._click_element(By.XPATH, file_selector_xpath)
        self._click_element(By.XPATH, INSERT_BUTTON_XPATH)

        # Switch back to main content
        self.driver.switch_to.default_content()
        logging.info("File attached and switched back to default content.")

    def get_response_count(self) -> int:
        """Returns the current number of response elements on the page."""
        return len(self.driver.find_elements(By.CSS_SELECTOR, RESPONSE_CONTENT_CSS))

    def get_latest_response(
        self, responses_before: int, timeout: int = 900
    ) -> str | None:
        """Waits for and returns the latest AI response text after it stabilizes."""
        logging.info(
            f"Waiting for new response (currently {responses_before} on page)..."
        )
        try:
            self.wait.until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, RESPONSE_CONTENT_CSS))
                > responses_before
            )
            latest_response_element = self.driver.find_elements(
                By.CSS_SELECTOR, RESPONSE_CONTENT_CSS
            )[-1]

            logging.info("Waiting for response generation to finish...")
            WebDriverWait(latest_response_element, timeout).until(
                EC.invisibility_of_element_located(
                    (By.CSS_SELECTOR, GENERATING_INDICATOR_CSS)
                )
            )

            # Wait for text to stabilize
            last_text = ""
            start_time = time.time()
            while time.time() - start_time < 30:  # 30s stabilization timeout
                try:
                    current_text = latest_response_element.text
                    if current_text == last_text and current_text:
                        logging.info("✅ Response text has stabilized.")
                        return current_text
                    last_text = current_text
                    time.sleep(2)
                except StaleElementReferenceException:
                    logging.warning(
                        "Response element became stale while stabilizing, re-finding..."
                    )
                    latest_response_element = self.driver.find_elements(
                        By.CSS_SELECTOR, RESPONSE_CONTENT_CSS
                    )[-1]

            logging.warning(
                "Response text did not stabilize. Using last captured content."
            )
            return last_text
        except Exception:
            logging.error("An error occurred in get_latest_response.", exc_info=True)
            save_debug_screenshot(self.driver, "get_response_error")
            return None

    def export_and_get_doc_url(self) -> str | None:
        """Exports the report to Google Docs and returns the new document's URL."""
        logging.info("Exporting report to Google Docs...")
        try:
            initial_handles = set(self.driver.window_handles)
            current_handle = self.driver.current_window_handle

            self._click_element(By.XPATH, SHARE_EXPORT_BUTTON_XPATH)
            self._click_element(By.XPATH, EXPORT_TO_DOCS_BUTTON_XPATH)

            new_handle = WebDriverWait(self.driver, 30).until(
                lambda d: next(iter(set(d.window_handles) - initial_handles), None)
            )
            if not new_handle:
                logging.error("Failed to switch to new window after export.")
                return None
            self.driver.switch_to.window(new_handle)

            WebDriverWait(self.driver, 60).until_not(EC.url_to_be("about:blank"))
            doc_url = self.driver.current_url

            logging.info(f"Successfully exported. Doc URL: {doc_url}")
            self.driver.close()
            self.driver.switch_to.window(current_handle)
            return doc_url
        except Exception:
            logging.error("An error occurred during report export.", exc_info=True)
            save_debug_screenshot(self.driver, "export_doc_error")
            # Attempt to switch back to the original handle to prevent losing control
            if "current_handle" in locals():
                self.driver.switch_to.window(current_handle)
            return None

    def enter_prompt_and_get_response(
        self, prompt: str, timeout: int = 900
    ) -> str | None:
        """
        A high-level method that enters a prompt, submits it, and waits for the full response.

        Args:
            prompt: The text prompt to send.
            timeout: The maximum time to wait for a response.

        Returns:
            The text of the AI's response, or None on failure.
        """
        logging.info(f"Submitting prompt and waiting for response...")
        try:
            responses_before = self.get_response_count()
            self.enter_prompt_and_submit(prompt)
            response_text = self.get_latest_response(responses_before, timeout=timeout)
            return response_text
        except Exception:
            # The lower-level functions already log the details, so we just add context.
            logging.error(f"Failed to get a response for prompt: '{prompt[:50]}...'")
            return None

    def is_job_complete(self) -> bool:
        """
        Checks if the current page indicates that a research job is complete.
        This is determined by the presence of the 'Share & Export' button.
        """
        try:
            # Use a very short timeout to avoid waiting if the element isn't there.
            # We are just checking for presence, not waiting for it to appear.
            WebDriverWait(self.driver, 0.5).until(
                EC.presence_of_element_located((By.XPATH, SHARE_EXPORT_BUTTON_XPATH))
            )
            return True
        except TimeoutException:
            return False
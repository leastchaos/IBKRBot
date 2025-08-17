# genai/workflow.py
import logging

from genai.browser_actions import Browser
from genai.common.utils import save_debug_screenshot


def perform_deep_research(browser: Browser, prompt: str) -> bool:
    """
    Handles the full workflow for initiating a Deep Research task.

    Args:
        browser: An initialized Browser object wrapping the WebDriver.
        prompt: The research prompt to submit.

    Returns:
        True if the task was initiated successfully, False otherwise.
    """
    try:
        browser.navigate_to_deep_research_prompt()
        browser.enter_prompt_and_submit(prompt)
        browser.click_start_research()
        logging.info("Deep Research initiated successfully.")
        return True
    except Exception:
        logging.error("An error occurred during Deep Research initiation.", exc_info=True)
        save_debug_screenshot(browser.driver, "deep_research_error")
        return False


def perform_daily_monitor_research(browser: Browser, prompt: str, report_url: str) -> bool:
    """
    Handles the workflow for a daily monitor task.

    Args:
        browser: An initialized Browser object.
        prompt: The research prompt to submit.
        report_url: The URL of the Google Doc to attach as context.

    Returns:
        True if the task was initiated successfully, False otherwise.
    """
    try:
        logging.info(f"Starting daily monitor workflow. Attaching doc: {report_url}")
        browser.navigate_to_deep_research_prompt()
        browser.attach_drive_file(report_url)
        browser.enter_prompt_and_submit(prompt)
        browser.click_start_research()
        logging.info("Daily monitor research initiated successfully.")
        return True
    except Exception:
        logging.error("An error occurred during the daily monitor workflow.", exc_info=True)
        save_debug_screenshot(browser.driver, "daily_monitor_error")
        return False


def perform_portfolio_review(browser: Browser, prompt: str, sheet_url: str) -> bool:
    """
    Handles the workflow for a portfolio review task.

    Args:
        browser: An initialized Browser object.
        prompt: The research prompt to submit.
        sheet_url: The URL of the Google Sheet to attach for analysis.

    Returns:
        True if the task was initiated successfully, False otherwise.
    """
    try:
        logging.info("Starting portfolio review workflow.")
        # Note the different order of operations for this workflow
        browser.attach_drive_file(sheet_url)
        browser.navigate_to_deep_research_prompt()
        browser.enter_prompt_and_submit(prompt)
        browser.click_start_research()
        logging.info("Portfolio review initiated successfully.")
        return True
    except Exception:
        logging.error("An error occurred during the portfolio review workflow.", exc_info=True)
        save_debug_screenshot(browser.driver, "portfolio_review_error")
        return False

# Note: The 'process_completed_job' and other functions have been removed.
# They will be moved to a new 'post_processing.py' file in a later step.
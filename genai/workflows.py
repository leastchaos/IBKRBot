# genai/workflow.py
from datetime import datetime, timedelta
import logging
from typing import Callable

from genai.browser_actions import Browser
from genai.constants import TaskType
from genai.database.api import get_latest_report_info

# This is the registry


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
        logging.error(
            "An error occurred during Deep Research initiation.", exc_info=True
        )
        browser.save_debug_screenshot("deep_research_error")
        return False


def perform_tactical_research(
    browser: Browser, prompt: str, company_name: str
) -> bool:
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
        report_info = get_latest_report_info(company_name)
        if not report_info:
            logging.error(f"No report found for company '{company_name}'.")
            return False
        report_url, timestamp = report_info
        logging.info(f"Found latest report for '{company_name}': {report_url} at {timestamp}")
        if timestamp < (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"):
            logging.warning(
                f"Report for '{company_name}' is older than 7 days. Skipping daily monitor."
            )
            return False
        logging.info(f"Starting daily monitor workflow. Attaching doc: {report_url}")
        browser.navigate_to_deep_research_prompt()
        browser.attach_drive_file(report_url)
        browser.enter_prompt_and_submit(prompt)
        browser.click_start_research()
        logging.info("Daily monitor research initiated successfully.")
        return True
    except Exception:
        logging.error(
            "An error occurred during the daily monitor workflow.", exc_info=True
        )
        browser.save_debug_screenshot("daily_monitor_error")
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
        logging.error(
            "An error occurred during the portfolio review workflow.", exc_info=True
        )
        browser.save_debug_screenshot("portfolio_review_error")
        return False


# This is the registry
WORKFLOW_REGISTRY: dict[TaskType, Callable[..., bool]] = {
    TaskType.COMPANY_DEEP_DIVE: perform_deep_research,
    TaskType.SHORT_COMPANY_DEEP_DIVE: perform_deep_research,
    TaskType.BUY_THE_DIP: perform_deep_research,
    TaskType.TACTICAL_REVIEW: perform_tactical_research,  # Example: maybe it needs a different function
    TaskType.UNDERVALUED_SCREENER: perform_deep_research,
    TaskType.PORTFOLIO_REVIEW: perform_portfolio_review,
    TaskType.COVERED_CALL_REVIEW: perform_portfolio_review,
    TaskType.OTB_COVERED_CALL_REVIEW: perform_portfolio_review,
    TaskType.RISK_REVIEW: perform_portfolio_review,
}

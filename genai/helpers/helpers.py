from functools import wraps
import logging
import os
import re
from datetime import datetime
from typing import TYPE_CHECKING

from genai.constants import TaskType
from genai.helpers.config import load_prompts

# To prevent circular imports with type hints
if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver


def retry_on_exception(func):
    """
    A decorator that catches exceptions, logs them, and asks the user
    if they want to retry the failed function.
    """

    @wraps(func)  # Preserves the original function's name and docstring
    def wrapper(*args, **kwargs):
        while True:
            try:
                # Attempt to execute the function and return its result
                return func(*args, **kwargs)
            except Exception as e:
                # If any exception occurs, log it and prompt the user
                logging.exception(
                    f"An error occurred in function '{func.__name__}': {e}"
                )

                # Loop until a valid y/n answer is given
                while True:
                    retry_choice = (
                        input(f"Do you want to retry '{func.__name__}'? (y/n): ")
                        .lower()
                        .strip()
                    )
                    if retry_choice in ["y", "n"]:
                        break
                    print("Invalid input. Please enter 'y' or 'n'.")

                if retry_choice == "y":
                    logging.info(f"User chose to retry '{func.__name__}'...")
                    continue  # This continues the outer `while True` loop, retrying the function
                else:
                    logging.error(
                        f"User chose not to retry. Aborting the operation in '{func.__name__}'."
                    )
                    raise  # Re-raises the last exception, stopping the script flow

    return wrapper


def save_debug_screenshot(driver: "WebDriver", filename_prefix: str):
    """Saves a screenshot to the debug_ss directory with a timestamp."""
    try:
        # Create the directory if it doesn't exist
        debug_dir = os.path.join(os.getcwd(), "debug_ss")
        os.makedirs(debug_dir, exist_ok=True)

        # Generate a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Sanitize filename prefix to be safe for file systems
        safe_prefix = re.sub(r'[\\/*?:"<>|]', "", str(filename_prefix))
        screenshot_path = os.path.join(debug_dir, f"{timestamp}_{safe_prefix}.png")

        driver.save_screenshot(screenshot_path)
        logging.info(f"Saved debug screenshot to: {screenshot_path}")
    except Exception as e:
        # Log if screenshot fails, but don't crash the main exception handling
        logging.error(f"Failed to save debug screenshot: {e}", exc_info=True)


def get_prompt(task_type: str, date_format: str = "%Y-%m-%d") -> str | None:
    prompts = load_prompts()
    prompt_template = prompts.get(task_type)
    if prompt_template:
        if date_format:
            prompt_template = prompt_template.replace("[CURRENT_DATE]", datetime.now().strftime(date_format))
        return prompt_template
    return None
from functools import wraps
import logging


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

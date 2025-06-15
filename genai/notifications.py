import os
import requests
from typing import Dict, Any

from genai.config import get_settings


def send_report_to_telegram(
    company_name: str, summary_data: str, file_path: str, token: str, chat_id: str
) -> bool:
    """
    Sends a formatted summary caption and a document file to a Telegram group.

    Args:
        company_name: The name of the company for the report.
        summary_data: The summary data to be included in the caption.
        file_path: The local path to the document (e.g., PDF) to be sent.
        config: The configuration object containing Telegram settings.

    Returns:
        True if the message was sent successfully, False otherwise.
    """
    print(f"Preparing to send report and summary to Telegram for {company_name}...")
    if not all([token, chat_id]):
        print(
            "Error: Telegram bot token or chat ID is not configured. Skipping notification."
        )
        return False

    caption = (
        f"✅ **New Company Analysis: {company_name}**\n\n"
        f"{summary_data}\n\n"
        f"[View Full Report]({file_path})"
    )

    # --- Prepare the API request ---
    api_url = f"https://api.telegram.org/bot{token}/sendDocument"
    payload = {"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"}

    try:
        # Check if the file exists before trying to open it
        if not os.path.exists(file_path):
            print(f"Error: Document not found at path: {file_path}")
            return False

        # Open the file in binary read mode and send the request
        with open(file_path, "rb") as document:
            files = {"document": document}
            print(f"Uploading {os.path.basename(file_path)} to Telegram...")

            response = requests.post(api_url, data=payload, files=files, timeout=60)

            # Raise an exception for HTTP error codes (4xx or 5xx)
            response.raise_for_status()

        print("Telegram notification with document sent successfully.")
        return True

    except requests.exceptions.Timeout:
        print("Error: The request to Telegram timed out.")
        return False
    except requests.exceptions.RequestException as e:
        print(
            f"Error: Failed to send Telegram notification. An error occurred with the request: {e}"
        )
        return False
    except Exception as e:
        print(f"An unexpected error occurred during Telegram sending: {e}")
        return False


if __name__ == "__main__":
    config = get_settings()
    send_report_to_telegram(
        "Example Company",
        "Summary Data",
        r"C:\Python Projects\IBKRBot\debug_main_error.png",
        config.telegram_token,
        config.telegram_chat_id,
    )

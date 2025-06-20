import os
import requests
import logging

from genai.helpers.config import TelegramSettings


def _send_single_telegram_document(
    chat_id: str, caption: str, file_path: str, config: TelegramSettings
) -> bool:
    """Private helper to send a document to a single chat ID."""
    api_url = f"https://api.telegram.org/bot{config.token}/sendDocument"
    try:
        with open(file_path, "rb") as document:
            payload = {"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"}
            files = {"document": document}

            logging.info(f"Uploading report to chat ID: {chat_id}...")
            response = requests.post(api_url, data=payload, files=files, timeout=60)
            response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logging.error(
            f"Failed to send Telegram document to chat_id {chat_id}.", exc_info=True
        )
        return False


def send_report_to_telegram(
    company_name: str,
    summary_text: str,
    file_path: str,
    doc_url: str,
    config: TelegramSettings,
    target_chat_id: str | None = None,
) -> bool:
    """
    Sends a report to the default chat ID and an optional target chat ID, avoiding duplicates.
    """
    logging.info(f"Preparing to send report for {company_name}...")
    if not config or not config.token or not config.chat_id:
        logging.error(
            "Default Telegram configuration is missing. Cannot send notifications."
        )
        return False

    # --- Build the list of unique recipients ---
    # Using a set automatically handles deduplication.
    chat_ids_to_notify = set()

    # 1. Always add the default chat_id
    default_chat_id = config.chat_id
    chat_ids_to_notify.add(default_chat_id)

    # 2. Add the target chat_id if it exists and is different
    if target_chat_id:
        chat_ids_to_notify.add(target_chat_id)

    logging.info(f"Notification will be sent to chat IDs: {list(chat_ids_to_notify)}")

    # --- Construct the message caption (once) ---
    caption = (
        f"✅ **New Company Analysis: {company_name}**\n\n"
        f"{summary_text}\n\n"
        f"[View Full Report in Google Docs]({doc_url})"
    )

    if not os.path.exists(file_path):
        logging.error(f"Document not found at path: {file_path}. Cannot send.")
        return False

    # --- Loop and send to all unique recipients ---
    all_successful = True
    for chat_id in chat_ids_to_notify:
        if not _send_single_telegram_document(chat_id, caption, file_path, config):
            all_successful = False  # Track if any sends failed

    if all_successful:
        logging.info("All Telegram notifications sent successfully.")
    else:
        logging.warning("One or more Telegram notifications failed to send.")

    return all_successful


if __name__ == "__main__":
    from genai.helpers.config import get_settings
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    config = get_settings()
    caption = """['PFE Investment Analysis Summary\nRecommendation: BUY\nEntry Range: $23.00 - $26.00\nPrice Target (12-Month Exit): $38.00\nThesis in Brief:']"""
    send_report_to_telegram(
        "Example Company",
        caption,
        r"C:\Python Projects\IBKRBot\debug_main_error.png",
        "www.google.com",
        config.telegram,
        "123456789",
    )

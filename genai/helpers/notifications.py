# genai/helpers/notifications.py
import requests
import logging
from typing import Any

# --- Internal Project Imports ---
from genai.constants import TaskType
from genai.helpers.config import TelegramSettings


def send_report_to_telegram(
    company_name: str,
    summary_text: str,
    doc_url: str,
    config: TelegramSettings,
    task_type: str,
    target_chat_id: str | None = None,
    gemini_url: str = "https://gemini.google.com/app",
    gemini_public_url: str | None = None,
    gemini_account_name: str | None = None,
) -> bool:
    """
    Sends a text message with a summary and a link to a Google Doc to one or more chats.
    """
    logging.info(f"Preparing to send text notification for {company_name} (Type: {task_type})")
    if not config or not config.token:
        logging.error("Telegram token not configured. Cannot send notifications.")
        return False

    # --- Build the list of unique recipients ---
    chat_ids_to_notify = set()
    if config.chat_id:
        chat_ids_to_notify.add(config.chat_id)
    if target_chat_id:
        chat_ids_to_notify.add(target_chat_id)

    if not chat_ids_to_notify:
        logging.warning("No recipients found for Telegram notification.")
        return False

    logging.info(f"Notification will be sent to chat IDs: {list(chat_ids_to_notify)}")

    # --- Construct title based on task type ---
    if task_type == TaskType.COMPANY_DEEP_DIVE:
        title = f"✅ **New Deep-Dive Analysis: {company_name}**"
    elif task_type == TaskType.SHORT_COMPANY_DEEP_DIVE:
        title = f"📉 **New Short-Sell Analysis: {company_name}**"
    elif task_type == TaskType.DAILY_MONITOR:
        title = f"📈 **Daily Tactical Update: {company_name}**"
    else:
        title = f"ℹ️ **New Report: {company_name}**"

    # --- Construct the message text ---
    message_text = (
        f"{title}\n\n"
        f"{summary_text}\n\n"
        f"**Report:** [Google Doc]({doc_url})\n"
        f"**Gemini Chat:** [Continue the conversation]({gemini_url})"
    )
    if gemini_account_name:
        message_text += f"\n**Gemini Account:** {gemini_account_name}"
    if gemini_public_url:
        message_text += f"\n**Public Link:** [View Public Chat]({gemini_public_url})"

    # --- Loop and send to all unique recipients ---
    all_successful = True
    for chat_id in chat_ids_to_notify:
        payload = {
            "chat_id": chat_id,
            "text": message_text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        # Log the full payload at DEBUG level for detailed troubleshooting
        logging.debug(f"Full payload for chat_id {chat_id}: {payload}")
        api_url = f"https://api.telegram.org/bot{config.token}/sendMessage"

        try:
            response = requests.post(api_url, json=payload, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException:
            logging.error(
                f"Failed to send Telegram message to chat_id {chat_id}.", exc_info=True
            )
            all_successful = False
            continue
        except Exception:
            logging.error(
                f"An unexpected error occurred while sending Telegram message to chat_id {chat_id}.",
                exc_info=True,
            )
            all_successful = False
            continue

    if all_successful:
        logging.info("All Telegram notifications sent successfully.")

    return all_successful


if __name__ == "__main__":
    from genai.helpers.config import get_settings
    from genai.constants import TaskType

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    config = get_settings()
    caption = """['PFE Investment Analysis Summary\nRecommendation: BUY\nEntry Range: $23.00 - $26.00\nPrice Target (12-Month Exit): $38.00\nThesis in Brief:']"""
    send_report_to_telegram(
        company_name="Example Company",
        summary_text=caption,
        doc_url="www.google.com",
        config=config.telegram,
        task_type=TaskType.COMPANY_DEEP_DIVE,
        target_chat_id="123456789",
    )

# genai/helpers/notifications.py
import requests
import logging
from typing import Any

# --- Internal Project Imports ---
from genai.constants import TaskType
from genai.common.config import TelegramSettings
from telegram.helpers import escape_markdown

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
    retry_without_summary: bool = False,
) -> bool:
    """
    Sends a text message with a summary and a link to a Google Doc to one or more chats.
    """
    logging.info(f"Preparing to send text notification for {company_name} (Type: {task_type})")
    logging.info(f"Sending telegram notification with the following details:\n"
                 f"Company: {company_name}\n"
                 f"Summary: {summary_text}\n"
                 f"Doc URL: {doc_url}\n"
                 f"Task Type: {task_type}\n"
                 f"Target Chat ID: {target_chat_id}\n"
                 f"Gemini URL: {gemini_url}\n"
                 f"Gemini Public URL: {gemini_public_url}\n"
                 f"Gemini Account Name: {gemini_account_name}\n"
                 f"Retry Without Summary: {retry_without_summary}")
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

    # 1. Escape all text variables first
    escaped_company_name = escape_markdown(company_name, version=2)
    escaped_task_type = escape_markdown(task_type, version=2)
    escaped_admin_id = escape_markdown(config.admin_id, version=2)
    escaped_summary = escape_markdown(summary_text, version=2) if summary_text and not retry_without_summary else ""
    escaped_account_name = escape_markdown(gemini_account_name, version=2) if gemini_account_name else ""

    # 2. Build the message parts using f-strings for clarity
    #    Note: Use '\\' to create a literal backslash for escaping the colon.
    parts = [
        f"Company\\: {escaped_company_name}",
        f"Task Type\\: {escaped_task_type}",
        "",
        escaped_summary,
        "",
        f"Requested By\\: {escaped_admin_id}",
        f"Report\\: [View Report]({doc_url})",
        f"Gemini Chat\\: [Continue the conversation]({gemini_url})",
        f"Gemini Account\\: {escaped_account_name}",
    ]
    message_text = "\n".join(part for part in parts if part)
    # message_text = escape_markdown(message_text, version=2)
    # --- Loop and send to all unique recipients ---
    all_successful = True
    for chat_id in chat_ids_to_notify:
        payload = {
            "chat_id": chat_id,
            "text": message_text,
            "parse_mode": "MarkdownV2",
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
            if not retry_without_summary:
                # Retry without summary text if the first attempt fails
                logging.info("Retrying without summary text...")
                success = send_report_to_telegram(
                    company_name=company_name,
                    summary_text="",
                    doc_url=doc_url,
                    config=config,
                    task_type=task_type,    
                    target_chat_id=target_chat_id,  
                    gemini_url=gemini_url,
                    gemini_public_url=gemini_public_url,
                    gemini_account_name=gemini_account_name,
                    retry_without_summary=True,
                )
                if success:
                    logging.info(f"Successfully retried sending message to chat_id {chat_id} without summary.")
                    continue
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
    from genai.common.config import get_settings
    from genai.constants import TaskType

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    config = get_settings()
    caption = """['PFE Investment Analysis Summary\nRecommendation: BUY\nEntry Range: $23.00 - $26.00\nPrice Target (12-Month Exit): $38.00\nThesis in Brief:']"""
    send_report_to_telegram(
        company_name="Example Company",
        summary_text=caption,
        doc_url="https://docs.google.com/document/d/1_xGK_7arolWHVUb1sb8s_0YVW3vewfe_CGeXgZlzK90/edit?tab=t.0",
        config=config.telegram,
        task_type=TaskType.COMPANY_DEEP_DIVE,
        # target_chat_id="123456789",
    )

import logging
import sqlite3
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from genai.helpers.config import get_settings
from genai.helpers.logging_config import setup_logging

DATABASE_PATH = os.path.join(os.getcwd(), 'genai', 'database', 'research_queue.db')

# --- Bot Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "Hello! I am the Gemini Research Bot.\n"
        "To request a report, use the command: \n"
        "/research <EXCHANGE:TICKER>\n\n"
        "Example: /research NYSE:GME"
    )

async def research(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Queues a research request from a user."""
    try:
        # The first argument after the command is the company name
        company_name = context.args[0]
    except (IndexError, ValueError):
        await update.message.reply_text("Please provide a company ticker.\nExample: /research NYSE:GME")
        return

    user = update.effective_user
    requested_by = f"telegram:{user.id}"
    logging.info(f"Received research request for '{company_name}' from user '{user.username}' ({user.id})")

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (company_name, requested_by) VALUES (?, ?)",
                (company_name, requested_by)
            )
            conn.commit()
        logging.info(f"Successfully queued request for {company_name}.")
        await update.message.reply_text(
            f"✅ Your request for '{company_name}' has been added to the queue!\n"
            "I will send you the report once it is complete."
        )
    except sqlite3.Error as e:
        logging.error(f"Database error while queuing request for {company_name}: {e}")
        await update.message.reply_text("Sorry, there was an error processing your request. Please try again later.")

def main() -> None:
    """Starts the bot."""
    setup_logging()
    config = get_settings()

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(config.telegram_token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("research", research))

    logging.info("Telegram bot started and polling for messages...")
    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()
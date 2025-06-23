import logging
import sqlite3
import os

# --- Third-party Imports ---
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Internal Project Imports ---
from genai.helpers.config import get_settings
from genai.helpers.logging_config import setup_logging
from genai.constants import DATABASE_PATH, TaskType


# --- Bot Command Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message with instructions when the /start command is issued."""
    welcome_text = (
        "Hello! I am the Gemini Research Bot.\n\n"
        "**Ad-hoc Research:**\n"
        "Use `/research <EXCHANGE:TICKER>` to request a new analysis.\n"
        "Example: `/research NASDAQ:NVDA`\n"
        "**Manage Daily Monitoring List:**\n"
        "`/add <TICKER>` - Adds a company to the daily scan.\n"
        "`/remove <TICKER>` - Removes a company from the daily scan.\n"
        "`/listdaily` - Shows all companies in the daily scan list.\n\n"
        "**Admin Commands:**\n"
        "`/clearqueue` - Clears all uncompleted tasks."
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def research_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Queues a new 'company_deep_dive' task from a user request."""
    try:
        # Get the company ticker from the arguments, e.g., /research arav
        company_name = context.args[0].upper()
    except (IndexError, ValueError):
        await update.message.reply_text("Please provide a company ticker.\nExample: `/research NYSE:GME`")
        return

    user = update.effective_user
    requested_by = f"telegram:{user.id}"
    logging.info(f"Received research request for '{company_name}' from user '{user.username}' ({user.id})")

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (company_name, requested_by, task_type) VALUES (?, ?, ?)",
                (company_name, requested_by, TaskType.COMPANY_DEEP_DIVE)
            )
            conn.commit()
        logging.info(f"Successfully queued request for {company_name}.")
        await update.message.reply_text(f"✅ Your request for `{company_name}` has been added to the queue!", parse_mode='Markdown')
    except sqlite3.Error as e:
        logging.error(f"Database error while queuing request for {company_name}: {e}")
        await update.message.reply_text("Sorry, there was a database error. Please try again later.")

async def add_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adds a company to the persistent daily monitoring list in the database."""
    try:
        company_name = context.args[0].upper()
    except (IndexError, ValueError):
        await update.message.reply_text("Please provide a company ticker.\nExample: `/add NASDAQ:AAPL`")
        return
    
    requested_by = f"telegram:{update.effective_user.id}"
    
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            # INSERT OR IGNORE will do nothing if the company already exists, preventing duplicates.
            cursor.execute(
                "INSERT OR IGNORE INTO daily_monitoring_list (company_name, added_by) VALUES (?, ?)",
                (company_name, requested_by)
            )
            conn.commit()
            
            # cursor.rowcount will be 1 if a row was inserted, 0 otherwise.
            if cursor.rowcount > 0:
                logging.info(f"Added '{company_name}' to daily list by {requested_by}.")
                await update.message.reply_text(f"✅ `{company_name}` has been added to the daily monitoring list.", parse_mode='Markdown')
            else:
                await update.message.reply_text(f"🔹 `{company_name}` is already on the daily monitoring list.", parse_mode='Markdown')
    except sqlite3.Error as e:
        logging.error(f"Database error adding '{company_name}' to daily list: {e}")
        await update.message.reply_text("Sorry, there was a database error.")


async def remove_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Removes a company from the daily monitoring list."""
    try:
        company_name = context.args[0].upper()
    except (IndexError, ValueError):
        await update.message.reply_text("Please provide a company ticker.\nExample: `/remove NASDAQ:AAPL`")
        return

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM daily_monitoring_list WHERE company_name = ?", (company_name,))
            conn.commit()

            if cursor.rowcount > 0:
                logging.info(f"Removed '{company_name}' from daily list.")
                await update.message.reply_text(f"✅ `{company_name}` has been removed from the daily monitoring list.", parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❓ `{company_name}` was not found on the daily monitoring list.", parse_mode='Markdown')
    except sqlite3.Error as e:
        logging.error(f"Database error removing '{company_name}' from daily list: {e}")
        await update.message.reply_text("Sorry, there was a database error.")


async def list_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists all companies currently in the daily monitoring list."""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT company_name FROM daily_monitoring_list ORDER BY company_name ASC")
            rows = cursor.fetchall()

            if not rows:
                await update.message.reply_text("The daily monitoring list is currently empty. Use `/add <TICKER>` to add one.")
                return

            # Format the list for the reply message
            company_list = "\n".join([f"• `{row[0]}`" for row in rows])
            message = f"**Daily Monitoring List:**\n{company_list}"
            await update.message.reply_text(message, parse_mode='Markdown')
            
    except sqlite3.Error as e:
        logging.error(f"Database error listing daily companies: {e}")
        await update.message.reply_text("Sorry, there was a database error.")


async def clear_queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """(Admin-only) Clears all 'queued' and 'processing' tasks from the queue."""
    config = get_settings()
    # Ensure the configured chat_id is a string for comparison
    admin_id = str(config.telegram.admin_id)
    user_id = str(update.effective_user.id)

    if not admin_id or user_id != admin_id:
        logging.warning(f"Unauthorized attempt to use /clearqueue from user ID {user_id}.")
        await update.message.reply_text("⛔️ Sorry, this is an admin-only command.")
        return

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            # Clear tasks that are waiting or currently running
            cursor.execute("DELETE FROM tasks WHERE status IN ('queued', 'processing')")
            tasks_cleared = cursor.rowcount
            conn.commit()

            logging.info(f"Admin {user_id} cleared the task queue. {tasks_cleared} tasks removed.")
            await update.message.reply_text(f"✅ Queue cleared. {tasks_cleared} pending/processing tasks were removed.")

    except sqlite3.Error as e:
        logging.error(f"Database error during queue clearing: {e}", exc_info=True)
        await update.message.reply_text("Sorry, there was a database error while clearing the queue.")


def main() -> None:
    """Starts the bot and registers all command handlers."""
    setup_logging()
    config = get_settings()
    
    if not config.telegram:
        logging.critical("Telegram configuration not found in config.py. Bot cannot start.")
        return

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(config.telegram.token).build()

    # Register all command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("research", research_command))
    application.add_handler(CommandHandler("add", add_daily_command))
    application.add_handler(CommandHandler("remove", remove_daily_command))
    application.add_handler(CommandHandler("listdaily", list_daily_command))
    application.add_handler(CommandHandler("clearqueue", clear_queue_command))

    logging.info("Telegram bot started and polling for messages...")
    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
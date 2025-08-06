# telegram_bot.py
import logging
import sqlite3
import os

# --- Third-party Imports ---
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# --- Internal Project Imports ---
from genai.helpers.config import get_settings
from genai.helpers.logging_config import setup_logging
from genai.constants import DATABASE_PATH, TaskType

# --- Bot Helper Functions ---


def _is_admin(update: Update) -> bool:
    """Checks if the user issuing the command is the configured admin."""
    config = get_settings()
    # Ensure the configured admin_id is a string for comparison
    admin_id = str(config.telegram.admin_id)
    if not update.effective_user:
        logging.warning("No effective user found in the update. Cannot check admin status.")
        return False
    user_id = str(update.effective_user.id)

    if not admin_id or user_id != admin_id:
        logging.warning(
            f"Unauthorized command attempt from user ID {user_id} on command '{update.message.text}'."
        )
        return False
    return True


def _create_start_menu(update: Update) -> InlineKeyboardMarkup:
    """Creates the start menu keyboard, including admin buttons if applicable."""
    keyboard = [
        [InlineKeyboardButton("List Monitored Stocks", callback_data="list_daily")],
    ]

    if _is_admin(update):
        admin_keyboard = [
            [
                InlineKeyboardButton(
                    "Trigger Screener", callback_data="trigger_screener"
                ),
                InlineKeyboardButton("Trigger Daily", callback_data="trigger_daily"),
            ],
            [
                InlineKeyboardButton(
                    "Trigger Portfolio Review", callback_data="trigger_portfolio"
                ),
                InlineKeyboardButton(
                    "Trigger Covered Call Review", callback_data="trigger_covered_call"
                ),
            ],
            [
                InlineKeyboardButton(
                    "⚠️ Clear Unstarted Queue", callback_data="clear_unstarted_queue"
                ),
            ],
        ]
        keyboard.extend(admin_keyboard)

    return InlineKeyboardMarkup(keyboard)


async def _queue_task(update: Update, company_name: str, task_type: TaskType):
    """A helper function to queue a task in the database and notify the user."""
    user = update.effective_user
    requested_by = f"telegram:{user.id}"
    logging.info(
        f"Received task request for '{company_name}' (Type: {task_type.value}) from user '{user.username}' ({user.id})"
    )

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (company_name, requested_by, task_type) VALUES (?, ?, ?)",
                (company_name, requested_by, task_type.value),
            )
            conn.commit()

        if task_type == TaskType.COMPANY_DEEP_DIVE:
            task_type_friendly_name = "Deep-Dive"
        elif task_type == TaskType.SHORT_COMPANY_DEEP_DIVE:
            task_type_friendly_name = "Short-Sell Analysis"
        elif task_type == TaskType.BUY_THE_DIP:
            task_type_friendly_name = "Buy-The-Dip Analysis"
        else:  # This will catch DAILY_MONITOR
            task_type_friendly_name = "Tactical"

        logging.info(
            f"Successfully queued {task_type_friendly_name} for {company_name}."
        )
        await update.message.reply_text(
            f"✅ Your {task_type_friendly_name} request for `{company_name}` has been added to the queue!",
            parse_mode="Markdown",
        )
    except sqlite3.Error as e:
        logging.error(f"Database error while queuing request for {company_name}: {e}")
        await update.message.reply_text(
            "Sorry, there was a database error. Please try again later."
        )


# --- Bot Command Handlers ---


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message with instructions when the /start command is issued."""
    welcome_text = generate_welcome_text()

    reply_markup = _create_start_menu(update)
    await update.message.reply_text(
        welcome_text, parse_mode="Markdown", reply_markup=reply_markup
    )


def generate_welcome_text():
    welcome_text = (
        "Hello! I am the Gemini Research Bot.\n\n"
        "You can use the buttons below for common actions or type commands directly.\n\n"
        "**Commands that require a ticker:**\n"
        "`/research <TICKER>` - Full deep-dive analysis.\n"
        "`/short <TICKER>` - Short-sell deep-dive analysis.\n"
        "`/buythedip <TICKER>` - Contrarian 'Buy The Dip' analysis.\n"
        "`/tactical <TICKER>` - Tactical update.\n"
        "`/add <TICKER>` - Add to daily monitoring.\n"
        "`/remove <TICKER>` - Remove from daily monitoring."
    )

    return welcome_text


async def research_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Queues a new 'company_deep_dive' task from a user request."""
    try:
        # Get the company ticker from the arguments, e.g., /research arav
        company_name = context.args[0].upper()
    except (IndexError, ValueError):
        await update.message.reply_text(
            "Please provide a company ticker.\nExample: `/research NYSE:GME`"
        )
        return

    await _queue_task(update, company_name, TaskType.COMPANY_DEEP_DIVE)


async def short_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Queues a new 'short_company_deep_dive' task from a user request."""
    try:
        # Get the company ticker from the arguments, e.g., /short arav
        company_name = context.args[0].upper()
    except (IndexError, ValueError):
        await update.message.reply_text(
            "Please provide a company ticker.\nExample: `/short NYSE:GME`"
        )
        return

    await _queue_task(update, company_name, TaskType.SHORT_COMPANY_DEEP_DIVE)


async def buy_the_dip_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Queues a new 'buy_the_dip' task from a user request."""
    try:
        # Get the company ticker from the arguments, e.g., /buythedip arav
        company_name = context.args[0].upper()
    except (IndexError, ValueError):
        await update.message.reply_text(
            "Please provide a company ticker.\nExample: `/buythedip NYSE:GME`"
        )
        return

    await _queue_task(update, company_name, TaskType.BUY_THE_DIP)


async def tactical_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Queues a new 'daily_monitor' (tactical) task from a user request."""
    try:
        company_name = context.args[0].upper()
    except (IndexError, ValueError):
        await update.message.reply_text(
            "Please provide a company ticker.\nExample: `/tactical NYSE:GME`"
        )
        return

    await _queue_task(update, company_name, TaskType.DAILY_MONITOR)


async def add_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Adds a company to the persistent daily monitoring list in the database."""
    try:
        company_name = context.args[0].upper()
    except (IndexError, ValueError):
        logging.warning("No company ticker provided for /add command.")
        message_text = "Please provide a company ticker.\nExample: `/add NASDAQ:AAPL`"
        await update.message.reply_text(text=message_text)
        return

    requested_by = f"telegram:{update.effective_user.id}"

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            # INSERT OR IGNORE will do nothing if the company already exists, preventing duplicates.
            cursor.execute(
                "INSERT OR IGNORE INTO daily_monitoring_list (company_name, added_by) VALUES (?, ?)",
                (company_name, requested_by),
            )
            conn.commit()

            # cursor.rowcount will be 1 if a row was inserted, 0 otherwise.
            if cursor.rowcount > 0:
                logging.info(f"Added '{company_name}' to daily list by {requested_by}.")
                message_text = (
                    f"✅ `{company_name}` has been added to the daily monitoring list."
                )
                await update.message.reply_text(
                    text=message_text, parse_mode="Markdown"
                )
            else:
                logging.info(f"'{company_name}' already exists in daily list.")
                message_text = (
                    f"🔹 `{company_name}` is already on the daily monitoring list."
                )
                await update.message.reply_text(
                    text=message_text, parse_mode="Markdown"
                )
    except sqlite3.Error as e:
        logging.error(f"Database error adding '{company_name}' to daily list: {e}")
        message_text = "Sorry, there was a database error."
        await update.message.reply_text(text=message_text)

    return message_text


async def remove_daily_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> str:
    """Removes a company from the daily monitoring list."""
    try:
        company_name = context.args[0].upper()
    except (IndexError, ValueError):
        await update.message.reply_text(
            "Please provide a company ticker.\nExample: `/remove NASDAQ:AAPL`"
        )
        return "Please provide a company ticker.\nExample: `/remove NASDAQ:AAPL`"

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM daily_monitoring_list WHERE company_name = ?",
                (company_name,),
            )
            conn.commit()

            if cursor.rowcount > 0:
                logging.info(f"Removed '{company_name}' from daily list.")
                message_text = f"✅ `{company_name}` has been removed from the daily monitoring list."
                await update.message.reply_text(
                    text=message_text,
                    parse_mode="Markdown",
                )
            else:
                message_text = (
                    f"❓ `{company_name}` was not found on the daily monitoring list."
                )
                await update.message.reply_text(
                    text=message_text,
                    parse_mode="Markdown",
                )
    except sqlite3.Error as e:
        logging.error(f"Database error removing '{company_name}' from daily list: {e}")
        message_text = "Sorry, there was a database error."
        await update.message.reply_text(text=message_text)

    return message_text


async def list_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Lists all companies currently in the daily monitoring list."""
    message_text = ""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT company_name FROM daily_monitoring_list ORDER BY company_name ASC"
            )
            rows = cursor.fetchall()

            if not rows:
                message_text = "The daily monitoring list is currently empty. Use `/add <TICKER>` to add one."
            else:
                company_list = "\n".join([f"• `{row[0]}`" for row in rows])
                message_text = f"**Daily Monitoring List:**\n{company_list}"

    except sqlite3.Error as e:
        logging.error(f"Database error listing daily companies: {e}")
        message_text = "Sorry, there was a database error."

    # Reply or edit the message depending on how the command was triggered
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=message_text, parse_mode="Markdown"
        )
    elif update.message:
        await update.message.reply_text(text=message_text, parse_mode="Markdown")
    return message_text


async def clear_unstarted_queue_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> str:
    """(Admin-only) Clears all 'queued' (unstarted) tasks from the queue."""
    message_text = ""
    if not _is_admin(update):
        message_text = "⛔️ Sorry, this is an admin-only command."
    else:
        user_id = str(update.effective_user.id)
        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM tasks WHERE status IN ('queued')")
                tasks_cleared = cursor.rowcount
                conn.commit()

                logging.info(
                    f"Admin {user_id} cleared the task queue. {tasks_cleared} tasks removed."
                )
                message_text = (
                    f"✅ Queue cleared. {tasks_cleared} unstarted tasks were removed."
                )

        except sqlite3.Error as e:
            logging.error(f"Database error during queue clearing: {e}", exc_info=True)
            message_text = "Sorry, there was a database error while clearing the queue."

    if update.callback_query:
        await update.callback_query.edit_message_text(text=message_text)
    elif update.message:
        await update.message.reply_text(text=message_text)

    return message_text


async def trigger_portfolio_review_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> str:
    """(Admin-only) Queues a new 'portfolio_review' task from a user request."""
    message_text = ""
    if not _is_admin(update):
        message_text = "⛔️ Sorry, this is an admin-only command."
    else:
        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO tasks (task_type, requested_by) VALUES (?, ?)",
                    (
                        TaskType.PORTFOLIO_REVIEW,
                        f"telegram_admin:{update.effective_user.id}",
                    ),
                )
                conn.commit()
            logging.info(
                f"Admin {update.effective_user.id} manually triggered the 'portfolio_review' task."
            )
            message_text = "✅ The 'portfolio_review' task has been queued."
        except sqlite3.Error as e:
            logging.error(
                f"Database error during 'portfolio_review' task scheduling: {e}",
                exc_info=True,
            )
            message_text = "Sorry, there was a database error while queuing the 'portfolio_review' task."

    if update.callback_query:
        await update.callback_query.edit_message_text(text=message_text)
    elif update.message:
        await update.message.reply_text(text=message_text)

    return message_text

async def trigger_covered_call_review_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """(Admin-only) Triggers a covered call review."""
    message_text = ""
    if not _is_admin(update):
        message_text = "⛔️ Sorry, this is an admin-only command."
    else:
        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO tasks (task_type, requested_by) VALUES (?, ?)",
                    (
                        TaskType.COVERED_CALL_REVIEW,
                        f"telegram_admin:{update.effective_user.id}",
                    ),
                )
                conn.commit()
            logging.info(
                f"Admin {update.effective_user.id} manually triggered the 'covered call review' task."
            )
            message_text = "✅ The 'covered call review' task has been queued."
        except sqlite3.Error as e:
            logging.error(
                f"Database error during 'covered call review' task scheduling: {e}",
                exc_info=True,
            )
            message_text = "Sorry, there was a database error while queuing the 'covered call review' task."

    if update.callback_query:
        await update.callback_query.edit_message_text(text=message_text)
    elif update.message:
        await update.message.reply_text(text=message_text)

    return message_text


async def trigger_screener_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> str:
    """(Admin-only) Manually queues the undervalued screener task."""
    message_text = ""
    if not _is_admin(update):
        message_text = "⛔️ Sorry, this is an admin-only command."
    else:
        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO tasks (task_type, requested_by) VALUES (?, ?)",
                    (
                        TaskType.UNDERVALUED_SCREENER,
                        f"telegram_admin:{update.effective_user.id}",
                    ),
                )
                conn.commit()
            logging.info(
                f"Admin {update.effective_user.id} manually triggered the screener task."
            )
            message_text = "✅ Undervalued screener task has been queued."
        except sqlite3.Error as e:
            logging.error(
                f"Database error during manual screener scheduling: {e}",
                exc_info=True,
            )
            message_text = (
                "Sorry, there was a database error while queuing the screener."
            )

    if update.callback_query:
        await update.callback_query.edit_message_text(text=message_text)
    elif update.message:
        await update.message.reply_text(text=message_text)

    return message_text

async def trigger_daily_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> str:
    """(Admin-only) Manually queues monitoring tasks for all companies on the daily list."""
    message_text = ""
    if not _is_admin(update):
        message_text = "⛔️ Sorry, this is an admin-only command."
    else:
        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT company_name FROM daily_monitoring_list")
                companies_to_monitor = [row[0] for row in cursor.fetchall()]
                if not companies_to_monitor:
                    message_text = (
                        "The daily monitoring list is empty. Nothing to queue."
                    )
                else:
                    requested_by = f"telegram_admin:{update.effective_user.id}"
                    for company in companies_to_monitor:
                        cursor.execute(
                            "INSERT INTO tasks (company_name, requested_by, task_type) VALUES (?, ?, ?)",
                            (company, requested_by, TaskType.DAILY_MONITOR),
                        )
                    conn.commit()
                    logging.info(
                        f"Admin {update.effective_user.id} manually triggered {len(companies_to_monitor)} daily tasks."
                    )
                    message_text = f"✅ Successfully queued {len(companies_to_monitor)} daily monitoring tasks."
        except sqlite3.Error as e:
            logging.error(
                f"Database error during manual daily task scheduling: {e}",
                exc_info=True,
            )
            message_text = (
                "Sorry, there was a database error while queuing daily tasks."
            )

    if update.callback_query:
        await update.callback_query.edit_message_text(text=message_text)
    elif update.message:
        await update.message.reply_text(text=message_text)

    return message_text

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and runs the appropriate command."""
    query = update.callback_query
    # Acknowledge the button press to remove the "loading" state on the user's screen
    await query.answer()

    command = query.data

    # Route the callback data to the appropriate command function
    if command == "list_daily":
        current_message = await list_daily_command(update, context)
    elif command == "clear_unstarted_queue":
        current_message = await clear_unstarted_queue_command(update, context)
    elif command == "trigger_screener":
        current_message = await trigger_screener_command(update, context)
    elif command == "trigger_daily":
        current_message = await trigger_daily_command(update, context)
    elif command == "trigger_portfolio":
        current_message = await trigger_portfolio_review_command(update, context)
    elif command == "trigger_covered_call":
        current_message = await trigger_covered_call_review_command(update, context)
    else:
        # This can be used to update the message if the button is no longer valid
        await query.edit_message_text(text=f"Action '{command}' is not implemented.")
        current_message = f"Action '{command}' is not implemented."
    
    # create back the start menu after handling the button
    reply_markup = _create_start_menu(update)
    welcome_text = generate_welcome_text()
    if update.callback_query:
        message_text = f"{current_message}\n\n{welcome_text}" if current_message else welcome_text
        await update.callback_query.edit_message_text(
            text=message_text,
            reply_markup=reply_markup,
        )
    # If this was a message, reply to it with the same text
    elif update.message:
        await update.message.reply_text(
            text=generate_welcome_text(),
            reply_markup=reply_markup,
        )


def main() -> None:
    """Starts the bot and registers all command handlers."""
    setup_logging()
    config = get_settings()

    if not config.telegram:
        logging.critical(
            "Telegram configuration not found in config.py. Bot cannot start."
        )
        return

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(config.telegram.token).build()

    # Register all command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("research", research_command))
    application.add_handler(CommandHandler("short", short_command))
    application.add_handler(CommandHandler("buythedip", buy_the_dip_command))
    application.add_handler(CommandHandler("tactical", tactical_command))
    application.add_handler(CommandHandler("add", add_daily_command))
    application.add_handler(CommandHandler("remove", remove_daily_command))
    application.add_handler(CommandHandler("listdaily", list_daily_command))
    application.add_handler(CommandHandler("clearqueue", clear_unstarted_queue_command))
    application.add_handler(
        CommandHandler("triggerportfolio", trigger_portfolio_review_command)
    )
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("triggerscreener", trigger_screener_command))
    application.add_handler(CommandHandler("triggerdaily", trigger_daily_command))
    application.add_handler(CommandHandler("triggercoveredcall", trigger_covered_call_review_command))

    logging.info("Telegram bot started and polling for messages...")
    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()

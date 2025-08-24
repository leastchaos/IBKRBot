# genai/telegram_bot.py
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import filters as Filters
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler

# Use our new, refactored modules
from genai.common.config import get_settings
from genai.common.logging_setup import setup_logging
from genai.database import api as db
from genai.constants import TaskType

# --- Helper Functions ---


def _is_admin(update: Update) -> bool:
    """Checks if the user issuing the command is the configured admin."""
    config = get_settings()
    admin_id = str(config.telegram.admin_id)
    # Guard clause to ensure effective_user exists
    if not update.effective_user or not admin_id:
        return False
    return str(update.effective_user.id) == admin_id


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
                    "Trigger OTB Covered Call Review",
                    callback_data="trigger_otb_covered_call",
                ),
                InlineKeyboardButton(
                    "Trigger Risk Review", callback_data="trigger_risk_review"
                ),
            ],
            [
                InlineKeyboardButton(
                    "Delete All Completed Tasks", callback_data="delete_all_completed"
                ),
                InlineKeyboardButton(
                    "Delete All Unprocessed Tasks", callback_data="delete_all_unprocessed"
                ),
            ],
        ]
        keyboard.extend(admin_keyboard)

    return InlineKeyboardMarkup(keyboard)


def _generate_welcome_text() -> str:
    """Generates the main welcome/help text."""
    return (
        "Hello! I am the Gemini Research Bot.\n\n"
        "You can use the buttons below or type commands directly.\n\n"
        "**Commands that require a ticker:**\n"
        "`/research <TICKER>` - Full deep-dive analysis.\n"
        "`/short <TICKER>` - Short-sell deep-dive analysis.\n"
        "`/buythedip <TICKER>` - Contrarian 'Buy The Dip' analysis.\n"
        "`/tactical <TICKER>` - Tactical update.\n"
        "`/add <TICKER>` - Add to daily monitoring.\n"
        "`/remove <TICKER>` - Remove from daily monitoring."
    )


# --- Bot Command Handlers ---


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message with instructions when the /start command is issued."""
    # Guard clause: This command must come from a message.
    if not update.message:
        logging.error("Start command received without a message.")
        return
    reply_markup = _create_start_menu(update)
    await update.message.reply_text(
        _generate_welcome_text(), parse_mode="Markdown", reply_markup=reply_markup
    )


async def _handle_task_creation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    task_type: TaskType,
    friendly_name: str,
):
    """Generic helper to handle queuing tasks that require a company name."""
    # Guard clause: Must have a message and a user to proceed.
    logging.info(f"Received update: {update}")
    logging.info(f"Received context: {context.args}")
    if not update.message:
        logging.error("Update missing message.")
        return
    if not update.effective_user:
        logging.error("Update missing effective user.")
        return

    if not context.args:
        # Guard clause: Must have a ticker to proceed.
        logging.error("No ticker provided.")
        await update.message.reply_text(
            f"Please provide a ticker. Example: `/{task_type.value.split('_')[0]} NYSE:GME`",
            parse_mode="Markdown",
        )
        return
    logging.info(f"Queuing {task_type.value} task from Telegram user {update.effective_user.id}")
    company_name = context.args[0].upper()
    user = update.effective_user

    task_id = db.queue_task(
        task_type=task_type,
        requested_by=f"telegram:{user.id}",
        company_name=company_name,
    )

    if task_id:
        await update.message.reply_text(
            f"✅ Your {friendly_name} request for `{company_name}` has been queued!",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text("Sorry, there was a database error.")


async def trigger_daily_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles the /trigger_daily command to queue a daily monitor task."""
    # Guard clause: Must be an admin to trigger this task.
    query = update.callback_query
    user = update.effective_user
    if not query or not user:
        return

    if not _is_admin(update):
        await query.answer("⛔️ Admin access required.", show_alert=True)
        return

    task_ids = db.trigger_daily_monitor_task()
    if task_ids:
        await query.edit_message_text(
            text="✅ Daily monitor task has been queued for the latest companies."
        )
    else:
        await query.edit_message_text(text="❌ Sorry, a database error occurred.")


async def delete_all_unprocessed_tasks(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles the /delete_all_unprocessed command to clear all unprocessed tasks."""
    query = update.callback_query
    user = update.effective_user
    if not query or not user:
        return
    if not _is_admin(update):
        await query.answer("⛔️ Admin access required.", show_alert=True)
        return
    deleted_count = db.delete_all_unstarted_tasks()
    await query.edit_message_text(text=f"✅ Deleted {deleted_count} unprocessed tasks.")


async def research_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.info("Received /research command")
    await _handle_task_creation(
        update, context, TaskType.COMPANY_DEEP_DIVE, "Deep-Dive"
    )


async def short_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _handle_task_creation(
        update, context, TaskType.SHORT_COMPANY_DEEP_DIVE, "Short-Sell Analysis"
    )


async def buy_the_dip_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await _handle_task_creation(
        update, context, TaskType.BUY_THE_DIP, "Buy-The-Dip Analysis"
    )


async def tactical_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _handle_task_creation(update, context, TaskType.TACTICAL_REVIEW, "Tactical")


async def add_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    if not context.args:
        await update.message.reply_text(
            "Please provide a ticker. Example: `/add NASDAQ:AAPL`"
        )
        return

    company_name = context.args[0].upper()
    user_id = update.effective_user.id

    was_added = db.add_to_daily_monitoring_list(company_name, f"telegram:{user_id}")

    if was_added:
        await update.message.reply_text(
            f"✅ `{company_name}` has been added to the daily monitoring list.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"🔹 `{company_name}` is already on the list or a database error occurred.",
            parse_mode="Markdown",
        )


async def remove_daily_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.message:
        return
    if not context.args:
        await update.message.reply_text(
            "Please provide a ticker. Example: `/remove NASDAQ:AAPL`"
        )
        return

    company_name = context.args[0].upper()
    was_removed = db.remove_from_daily_monitoring_list(company_name)

    if was_removed:
        await update.message.reply_text(
            f"✅ `{company_name}` has been removed from the daily monitoring list.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"❓ `{company_name}` was not found on the list or a database error occurred.",
            parse_mode="Markdown",
        )


async def list_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    companies = db.get_daily_monitoring_list()

    if not companies:
        message_text = (
            "The daily monitoring list is empty. Use `/add <TICKER>` to add one."
        )
    else:
        company_list = "\n".join([f"• `{company}`" for company in companies])
        message_text = f"**Daily Monitoring List:**\n{company_list}"

    # Handle both button clicks and typed commands
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=message_text, parse_mode="Markdown"
        )
    elif update.message:
        await update.message.reply_text(text=message_text, parse_mode="Markdown")


# --- Admin Command Handlers ---


async def _handle_admin_task_creation(
    update: Update, task_type: TaskType, success_message: str
):
    """Generic helper for queuing admin tasks from buttons."""
    query = update.callback_query
    user = update.effective_user
    if not query or not user:
        return

    if not _is_admin(update):
        await query.answer("⛔️ Admin access required.", show_alert=True)
        return

    task_id = db.queue_task(
        task_type=task_type, requested_by=f"telegram_admin:{user.id}"
    )

    if task_id:
        await query.edit_message_text(text=success_message)
    else:
        await query.edit_message_text(text="❌ Sorry, a database error occurred.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and runs the appropriate command."""
    query = update.callback_query
    if not query:
        return

    await query.answer()
    command = query.data

    if command == "list_daily":
        await list_daily_command(update, context)
    elif command == "trigger_screener":
        await _handle_admin_task_creation(
            update,
            TaskType.UNDERVALUED_SCREENER,
            "✅ Undervalued screener task has been queued.",
        )
    elif command == "trigger_portfolio":
        await _handle_admin_task_creation(
            update,
            TaskType.PORTFOLIO_REVIEW,
            "✅ Portfolio review task has been queued.",
        )
    elif command == "trigger_covered_call":
        await _handle_admin_task_creation(
            update,
            TaskType.COVERED_CALL_REVIEW,
            "✅ Covered call review task has been queued.",
        )
    elif command == "trigger_otb_covered_call":
        await _handle_admin_task_creation(
            update,
            TaskType.OTB_COVERED_CALL_REVIEW,
            "✅ OTB covered call review task has been queued.",
        )
    elif command == "trigger_risk_review":
        await _handle_admin_task_creation(
            update,
            TaskType.RISK_REVIEW,
            "✅ Risk review task has been queued.",
        )
    elif command == "trigger_daily":
        await trigger_daily_command(update, context)
    elif command == "delete_all_unprocessed":
        await delete_all_unprocessed_tasks(update, context)
    else:
        await query.edit_message_text(
            text=f"Action '{command}' is not yet implemented."
        )


async def _queue_daily_reviews(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Queues the daily review tasks (screener, portfolio, covered calls)."""
    logging.info("Queueing daily scheduled review tasks...")
    db.queue_task(
        task_type=TaskType.PORTFOLIO_REVIEW, requested_by="system:daily_job"
    )
    db.queue_task(
        task_type=TaskType.UNDERVALUED_SCREENER, requested_by="system:daily_job"
    )
    db.queue_task(
        task_type=TaskType.COVERED_CALL_REVIEW, requested_by="system:daily_job"
    )
    db.queue_task(
        task_type=TaskType.RISK_REVIEW, requested_by="system:daily_job"
    )
    logging.info("Daily scheduled review tasks queued.")


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles unknown commands."""
    if not update.message:
        logging.error("Unknown command received without a message.")
        return
    await update.message.reply_text(
        "⛔️ Unknown command. Please try again.",
        parse_mode="Markdown",
    )

def main() -> None:
    """Starts the bot."""
    setup_logging()
    config = get_settings()

    if not config.telegram or not config.telegram.token:
        logging.critical("Telegram token not found in config. Bot cannot start.")
        return

    application = Application.builder().token(config.telegram.token).build()

    # --- Queue startup and daily tasks ---
    # Queue tasks on startup
    logging.info("Queueing startup tasks (Screener, Portfolio, Covered Call)...")
    db.queue_task(
        task_type=TaskType.PORTFOLIO_REVIEW, requested_by="system:startup"
    )
    db.queue_task(
        task_type=TaskType.UNDERVALUED_SCREENER, requested_by="system:startup"
    )
    db.queue_task(
        task_type=TaskType.COVERED_CALL_REVIEW, requested_by="system:startup"
    )
    db.queue_task(task_type=TaskType.RISK_REVIEW, requested_by="system:startup")
    logging.info("...startup tasks queued.")

    # Schedule daily tasks
    if application.job_queue:
        import datetime

        # Schedule to run at 08:00 UTC every day
        application.job_queue.run_daily(
            _queue_daily_reviews, time=datetime.time(hour=8, minute=0)
        )
        logging.info("Scheduled daily review tasks for 08:00 UTC.")

    # Register all handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("research", research_command))
    application.add_handler(CommandHandler("short", short_command))
    application.add_handler(CommandHandler("buythedip", buy_the_dip_command))
    application.add_handler(CommandHandler("tactical", tactical_command))
    application.add_handler(CommandHandler("add", add_daily_command))
    application.add_handler(CommandHandler("remove", remove_daily_command))
    application.add_handler(CommandHandler("listdaily", list_daily_command))
    
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(Filters.COMMAND,unknown_command))

    logging.info("Telegram bot started...")
    application.run_polling()


if __name__ == "__main__":
    main()

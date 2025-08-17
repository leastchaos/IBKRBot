# --- Configuration ---
"""
A modular Telegram bot that monitors an IBKR Google Sheet using a custom utility module.
This script is designed to work with pandas DataFrames returned from sheet_utils.
"""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Any
import logging
import gspread
import pandas as pd
import telegram

# Import your custom utility functions
from portfolio import sheet

# --- Configuration ---
TELEGRAM_BOT_TOKEN: str = '8250069875:AAFHMc4JNLTVBolVauVUoceGg3q5gDjoYhQ'
TELEGRAM_CHAT_ID: str = '-1002769245528'
GOOGLE_SHEET_DOCUMENT_NAME: str = 'IBKR Data'
BALANCE_SHEET_NAME: str = 'IBKRBalance'
POSITIONS_SHEET_NAME: str = 'IBKRPositions'
PNL_SWING_THRESHOLD: int = 1000
ENABLE_DAILY_SUMMARY: bool = True
DAILY_SUMMARY_TIME: str = "21:00"  # 24-hour format

# --- Type Aliases ---
type SheetRow = dict[str, Any]
type State = dict[str, Any]

# --- Core Functions (Telegram sending and state management remain the same) ---

async def send_telegram_message(message: str) -> None:
    """Sends a formatted message to the configured Telegram chat."""
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='Markdown')

def load_state(file_path: str = 'previous_data.json') -> State:
    """Loads the last known state from a file, or returns a default."""
    if not os.path.exists(file_path):
        return {'balances': {}, 'positions': {}, 'daily_summary_sent': False}
    with open(file_path, 'r') as f:
        return json.load(f)

def save_state(state: State, file_path: str = 'previous_data.json') -> None:
    """Saves the current state to a file."""
    with open(file_path, 'w') as f:
        json.dump(state, f, indent=4)

# --- Logic-Specific Sub-Functions (These now expect dictionaries converted from DataFrames) ---

async def _handle_daily_summary(state: State) -> None:
    """Checks if it's time to send the daily summary and sends it."""
    if not ENABLE_DAILY_SUMMARY:
        return

    now = datetime.now()
    if now.strftime("%H:%M") < DAILY_SUMMARY_TIME:
        state['daily_summary_sent'] = False
        return
    
    if now.strftime("%H:%M") < DAILY_SUMMARY_TIME or state.get('daily_summary_sent', False):
        return

    balance_df = sheet.get_sheet_data(GOOGLE_SHEET_DOCUMENT_NAME, BALANCE_SHEET_NAME)
    if balance_df.empty:
        logging.warning("Balance DataFrame is empty. Cannot send daily summary.")
        return

    positions_df = sheet.get_sheet_data(GOOGLE_SHEET_DOCUMENT_NAME, POSITIONS_SHEET_NAME)
    if positions_df.empty:
        logging.warning("Positions DataFrame is empty. Cannot send daily summary.")
        return

    summary = balance_df.iloc[0] # Get the first row of the DataFrame
    message = (
        f"--- *Daily Account Summary* ---\n\n"
        f"Net Liquidation: `{summary.get('NetLiquidation', 'N/A')}`\n"
        f"Total Unrealized P&L: `{summary.get('UnrealizedPnL', 'N/A')}`\n"
        f"Today's Realized P&L: `{summary.get('RealizedPnL', 'N/A')}`\n"
        f"Open Positions: `{len(positions_df)}`"
    )
    await send_telegram_message(message)
    state['daily_summary_sent'] = True
    print(f"Sent daily summary at {now.strftime('%Y-%m-%d %H:%M:%S')}")


async def _process_balance_updates(current_balances: dict[str, SheetRow], previous_balances: dict[str, SheetRow]) -> None:
    """Compares current and previous balances and sends notifications for changes."""
    for acc, details in current_balances.items():
        prev_liq = previous_balances.get(acc, {}).get('NetLiquidation')
        if str(details.get('NetLiquidation')) != str(prev_liq):
            await send_telegram_message(f"💰 *Balance Update for {acc}*\nNew Net Liquidation: `{details.get('NetLiquidation')}`")

async def _process_position_updates(current_positions: dict[str, SheetRow], state: State) -> None:
    """Orchestrates checks for new, closed, and modified positions."""
    current_balances = state.get('balances', {})
    previous_positions = state.get('positions', {})
    previous_balances = state.get('previous_balances', {})

    for key, pos in previous_positions.items():
        if key not in current_positions:
            pnl_change = float(current_balances.get(pos['Account'], {}).get('RealizedPnL', 0)) - float(previous_balances.get(pos['Account'], {}).get('RealizedPnL', 0))
            await send_telegram_message(f"✅ *Position Closed: {pos['Symbol']}*\nChange in daily Realized P&L: `{pnl_change:,.2f}`")

    for key, pos in current_positions.items():
        if key not in previous_positions:
            await send_telegram_message(f"📈 *New Position: {pos['Symbol']}*\n   Quantity: `{pos['Position']}` | MV: `{pos['MarketValue']}`")
            continue

        prev_pos = previous_positions[key]
        if str(pos['Position']) != str(prev_pos['Position']):
            await send_telegram_message(f"🔄 *Position Adjusted: {pos['Symbol']}*\nQuantity changed from `{prev_pos['Position']}` to `{pos['Position']}`.")
        
        pnl_swing = abs(float(pos.get('UnrealizedPnL', 0)) - float(prev_pos.get('UnrealizedPnL', 0)))
        if pnl_swing >= PNL_SWING_THRESHOLD:
            await send_telegram_message(f"⚠️ *Large P&L Swing: {pos['Symbol']}*\nUnrealized P&L changed by `{pnl_swing:,.2f}`.")


# --- Main Application Loop ---
def _create_position_key(row: SheetRow) -> str:
    """
    Creates a unique key for a position. For options, it includes
    expiry, strike, and right to ensure uniqueness.
    """
    # Base key for all security types
    key = f"{row.get('Account')}-{row.get('Symbol')}-{row.get('SecType')}"

    # Add extra details only if the security is an option
    if row.get('SecType') == 'OPT':
        expiry = row.get('Expiry', '')
        strike = row.get('Strike', 0.0)
        right = row.get('Right', '')
        key += f"-{expiry}-{strike}-{right}"
    
    return key
async def monitor_google_sheet() -> None:
    """The main function to coordinate the monitoring loop."""
    print("Bot starting with custom sheet utilities...")
    
    while True:
        try:
            state = load_state()
            
            # Daily summary now uses its own data fetching via your utils
            await _handle_daily_summary(state)

            # --- Data Fetching using your utility function ---
            balance_df = sheet.get_sheet_data(GOOGLE_SHEET_DOCUMENT_NAME, BALANCE_SHEET_NAME, evaluate_formulas=True)
            if balance_df.empty:
                print("Balance DataFrame is empty. Retrying in 1 minute.")
            positions_df = sheet.get_sheet_data(GOOGLE_SHEET_DOCUMENT_NAME, POSITIONS_SHEET_NAME, evaluate_formulas=True)
            if positions_df.empty:
                print("Positions DataFrame is empty. Retrying in 1 minute.")
                time.sleep(60)
                continue

            # --- Convert DataFrames to Dictionaries for processing ---
            # This is the key adaptation step. The processing functions work with dicts.
            current_balances = balance_df.set_index('Account').to_dict('index')
            
            positions_df['key'] = positions_df['Account'].astype(str) + '-' + positions_df['ConId'].astype(str)
            current_positions = positions_df.set_index('key').to_dict('index')

            # Store previous balances from the last valid state for accurate P&L calculation
            state['previous_balances'] = state.get('balances', {})

            # --- Process Data ---
            await _process_balance_updates(current_balances, state.get('balances', {}))
            await _process_position_updates(current_positions, state)

            # --- Update State ---
            state['balances'] = current_balances
            state['positions'] = current_positions
            save_state(state)

        except NotImplementedError as e:
            print(f"An unexpected error occurred in main loop: {e}")

        print(f"Check complete. Waiting for 5 minutes...")
        time.sleep(300)

if __name__ == '__main__':
    # Make sure to configure your logging if sheet_utils uses it
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(monitor_google_sheet())
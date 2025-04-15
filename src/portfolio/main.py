import logging
import time
import keyboard  # New dependency for key detection
from tqdm import tqdm  # New dependency for progress bar
from ib_async import IB
from data_processing import process_positions_data
from ib_client import fetch_positions, fetch_balance
from sheet import get_sheet_data, set_sheet_data
from logger_config import setup_logger

logger = logging.getLogger()


def connect_to_ib() -> IB:
    ib = IB()
    ib.connect("127.0.0.1", 7496, clientId=1)
    return ib

def update_data(
    ib: IB,
    workbook_name: str,
    position_sheet: str,
    balance_sheet: str,
    scenario_sheet: str,
) -> None:
    try:
        if not ib.isConnected():
            connect_to_ib()
        positions_df = fetch_positions(ib) # this switches to ib.reqMarketDataType(4)
        balance_df = fetch_balance(ib)
        scenario_df = get_sheet_data(workbook_name, scenario_sheet)
        positions_df = process_positions_data(positions_df, scenario_df)

        set_sheet_data(workbook_name, position_sheet, positions_df)
        set_sheet_data(workbook_name, balance_sheet, balance_df)
    except Exception as e:
        logger.exception(f"An error occurred: {e}")

    logger.info("Data update completed.")

def wait_for_next_update(wait_time: int) -> None:
    logger.info(
        "Update completed. Waiting 5 minutes (press 's' to skip wait)..."
    )
    for _ in tqdm(range(wait_time, 0, -1), desc="Next refresh", unit="s", ncols=80):

        if keyboard.is_pressed("s"):  # Check for 's' key press
            logger.info("Manual refresh triggered!")
            break
        time.sleep(1)


def main(
    workbook_name="Portfolio Tracking",
    position_sheet="IBKRPositions",
    balance_sheet="IBKRBalances",
    scenario_sheet="ScenarioPrice",
) -> None:
    setup_logger()
    ib = IB()
    ib.connect("127.0.0.1", 7496, clientId=1)

    try:
        while True:
            update_data(
                ib,
                workbook_name,
                position_sheet,
                balance_sheet,
                scenario_sheet,
            )
            wait_for_next_update(300)

    except KeyboardInterrupt:
        logger.info("Exiting program...")
    finally:
        ib.disconnect()


if __name__ == "__main__":
    main()

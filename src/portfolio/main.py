from ib_async import IB
from data_processing import process_positions_data
from ib_client import fetch_positions, fetch_balance
from sheet import get_sheet_data, set_sheet_data
from logger_config import setup_logger

# Initialize the logger
logger = setup_logger()


# Main function
def main(
    workbook_name="Portfolio Tracking",
    position_sheet="IBKRPositions",
    balance_sheet="IBKRBalances",
    worst_case_scenario_sheet="Worst Case Scenario",
) -> None:
    logger.info("Starting the main function...")

    # Configure TWS connection
    ib = IB()
    logger.info("Connecting to TWS...")
    ib.connect("127.0.0.1", 7496, clientId=1)  # Default TWS API port is 7497
    positions_df = fetch_positions(ib)
    balance_df = fetch_balance(ib)
    ib.disconnect()

    worst_case_df = get_sheet_data(workbook_name, worst_case_scenario_sheet)
    positions_df = process_positions_data(positions_df, worst_case_df)

    set_sheet_data(workbook_name, position_sheet, positions_df)
    set_sheet_data(workbook_name, balance_sheet, balance_df)

    logger.info("Main function completed successfully.")


if __name__ == "__main__":
    main()

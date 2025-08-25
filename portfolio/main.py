import logging
import random
import time
import keyboard
from tqdm import tqdm
from ib_async import IB
from portfolio.portfolio_manager import PortfolioManager
from portfolio.logger_config import setup_logger

logger = logging.getLogger()


def connect_to_ib(host="127.0.0.1", port=7496, clientId=None) -> IB:
    """Connects to TWS with a specific client ID."""
    ib = IB()
    if clientId is None:
        clientId = random.randint(100, 999)
    ib.connect(host, port, clientId=clientId, readonly=True)
    return ib


def wait_for_next_update(wait_time: int) -> None:
    logger.info(
        f"Update completed. Waiting {wait_time} seconds (press 's' to skip wait)..."
    )
    for _ in tqdm(range(wait_time, 0, -1), desc="Next refresh", unit="s", ncols=80):
        if keyboard.is_pressed("s"):
            logger.info("Manual refresh triggered!")
            break
        time.sleep(1)


def main(
    host="127.0.0.1",
    port=7496,
    workbook_name="Portfolio Tracking",
    positions_sheet="IBKRPositions",
    contracts_sheet="IBKRContracts",
    market_data_sheet="IBKRMarketData",
    combined_sheet="Portfolio_CombinedView",
    balance_sheet="IBKRBalances",
    scenario_sheet="ScenarioPrice",
) -> None:
    setup_logger()
    # Create two separate clients with unique IDs
    ib_client = connect_to_ib(host, port, clientId=101)

    portfolio_manager = PortfolioManager(
        ib_client=ib_client,
        workbook_name=workbook_name,
        positions_sheet=positions_sheet,
        contracts_sheet=contracts_sheet,
        market_data_sheet=market_data_sheet,
        combined_sheet=combined_sheet,
        balance_sheet=balance_sheet,
        scenario_sheet=scenario_sheet,
    )

    while True:
        try:
            if not ib_client.isConnected():
                logger.info(f"IB connection lost for client {ib_client.client.clientId}. Reconnecting...")
                ib_client.disconnect()
                ib_client = connect_to_ib(host, port, clientId=random.randint(10000,99999))
                portfolio_manager.ib_client = ib_client

            portfolio_manager.update_portfolio_data()
            wait_for_next_update(300)

        except KeyboardInterrupt:
            logger.info("Exiting program...")
            break
        except Exception as e:
            logger.exception(f"An error occurred in the main loop: {e}", exc_info=True)
            logger.info("Retrying in 5 minutes...")
            wait_for_next_update(300)
            
    ib_client.disconnect()


if __name__ == "__main__":
    main()
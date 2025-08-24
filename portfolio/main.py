import logging
import random
import time
import keyboard
from tqdm import tqdm
from ib_async import IB
from portfolio.portfolio_manager import PortfolioManager
from portfolio.logger_config import setup_logger

logger = logging.getLogger()


def connect_to_ib(host="127.0.0.1", port=7496) -> IB:
    ib = IB()
    ib.connect(host, port, clientId=random.randint(1, 1000), readonly=True)
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
    position_sheet="IBKRPositions",
    balance_sheet="IBKRBalances",
    scenario_sheet="ScenarioPrice",
) -> None:
    setup_logger()
    ib = connect_to_ib(host, port)

    portfolio_manager = PortfolioManager(
        ib_client=ib,
        workbook_name=workbook_name,
        position_sheet=position_sheet,
        balance_sheet=balance_sheet,
        scenario_sheet=scenario_sheet,
    )

    while True:
        try:
            if not ib.isConnected():
                logger.info("IB connection lost. Reconnecting...")
                ib = connect_to_ib(host, port)
                portfolio_manager.ib_client = ib

            portfolio_manager.update_portfolio_data()
            wait_for_next_update(300)

        except KeyboardInterrupt:
            logger.info("Exiting program...")
            break
        except Exception as e:
            logger.exception(f"An error occurred in the main loop: {e}", exc_info=True)
            logger.info("Retrying in 5 minutes...")
            wait_for_next_update(300)
    ib.disconnect()


if __name__ == "__main__":
    main()
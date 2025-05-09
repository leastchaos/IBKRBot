import asyncio
from decimal import Decimal
import logging

from ib_async import Stock
from src.models.models import Action, OCAType, Rights
from src.strategy.mass_buy_options_async.config import TradingConfig
from src.strategy.mass_buy_options_async.trade_executor import mass_trade_oca_option
from src.core.ib_connector import (
    async_connect_to_ibkr,
    connect_to_ibkr,
    get_stock_ticker,
)
from src.utils.helpers import get_ibkr_account
from src.utils.logger_config import setup_logger

# Configuration
TRADE_CONFIG = TradingConfig(
    action=Action.SELL,
    right=Rights.PUT,
    min_dte=200,
    max_dte=400,
    min_strike=Decimal("160"),
    max_strike=Decimal("200"),
    size=Decimal("1"),
    manual_min_tick=Decimal("0.01"),
    min_update_size=Decimal("0.05"),
    min_distance=Decimal("0.1"),
    volatility=0.5,
    aggressive=True,
    skip_too_far_away=False,
    oca_type=OCAType.REDUCE_WITH_NO_BLOCK,
    min_ask_price=Decimal("0"),
    max_bid_price=Decimal("100"),
)

if __name__ == "__main__":
    # Connect to IBKR
    setup_logger()

    async def main():
        ib = await async_connect_to_ibkr(
            "127.0.0.1", 7496, 222, readonly=True, account=""
        )
        exec_ib = await async_connect_to_ibkr(
            "127.0.0.1",
            7496,
            333,
            readonly=True,
            account=get_ibkr_account("mass_buy_options"),
        )

        # Qualify stock contract
        stock = Stock(
            symbol="BABA",
            exchange="SMART",
            currency="USD",
        )
        # Run strategy
        await mass_trade_oca_option(ib, exec_ib, stock, TRADE_CONFIG)


    asyncio.run(main())

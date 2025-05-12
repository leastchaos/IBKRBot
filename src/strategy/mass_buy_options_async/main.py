import asyncio
from decimal import Decimal
import logging

from ib_async import Stock
from src.models.models import Action, OCAType, Rights
from src.strategy.mass_buy_options_async.config import TradingConfig
from src.strategy.mass_buy_options_async.trade_executor import mass_trade_oca_option
from src.core.ib_connector import async_connect_to_ibkr
from src.utils.helpers import get_ibkr_account
from src.utils.logger_config import setup_logger

# Configuration
TRADE_CONFIG = TradingConfig(
    action=Action.SELL,
    right=Rights.PUT,
    min_dte=200,
    max_dte=300,
    min_strike=Decimal("180"),
    max_strike=Decimal("200"),
    size=Decimal("1"),
    manual_min_tick=Decimal("0.01"),
    min_update_size=Decimal("0.05"),
    min_distance=Decimal("0.1"),
    volatility=0.6,
    aggressive=True,
    skip_too_far_away=False,
    oca_type=OCAType.REDUCE_WITH_NO_BLOCK,
    min_ask_price=Decimal("0"),
    max_bid_price=Decimal("100"),
    default_stock_price=Decimal("100"),
)

if __name__ == "__main__":
    # Connect to IBKR
    setup_logger()

    async def main():
        ib = await async_connect_to_ibkr(
            "127.0.0.1", 7496, 444, readonly=True, account=""
        )

        ib.reqMarketDataType(4)
        await asyncio.sleep(1)
        exec_ib = await async_connect_to_ibkr(
            "127.0.0.1",
            7496,
            333,
            readonly=False,
            account=get_ibkr_account("mass_buy_options"),
        )

        # Qualify stock contract
        stock = Stock(
            symbol="9988",
            exchange="",
            currency="HKD",
        )
        # Run strategy
        await mass_trade_oca_option(ib, exec_ib, stock, TRADE_CONFIG)

    asyncio.run(main())

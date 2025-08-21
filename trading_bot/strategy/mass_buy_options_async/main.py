import asyncio
from decimal import Decimal
import logging

from ib_async import Stock
from trading_bot.models.models import Action, OCAType, Rights
from trading_bot.strategy.mass_buy_options_async.config import TradingConfig
from trading_bot.strategy.mass_buy_options_async.trade_executor import mass_trade_oca_option
from trading_bot.core.ib_connector import async_connect_to_ibkr
from trading_bot.utils.helpers import get_ibkr_account
from trading_bot.utils.logger_config import setup_logger

# Configuration
TRADE_CONFIG = TradingConfig(
    action=Action.BUY,
    right=Rights.PUT,
    min_dte=300,
    max_dte=380,
    min_strike=Decimal("95"),
    max_strike=Decimal("105"),
    size=Decimal("1"),
    manual_min_tick=Decimal("0.01"),
    min_update_size=Decimal("0.1"),
    min_distance=Decimal("0.5"),
    volatility=0.37,
    aggressive=True,
    skip_too_far_away=False,
    oca_type=OCAType.REDUCE_WITH_NO_BLOCK,
    min_ask_price=Decimal("0"),
    max_bid_price=Decimal("20"),
    default_stock_price=None,
    loop_interval=0.1,
    min_underlying_price=None,
    max_underlying_price=None,
)
# Qualify stock contract
stock = Stock(
    symbol="9988",
    exchange="",
    currency="HKD",
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


        # Run strategy
        await mass_trade_oca_option(ib, exec_ib, stock, TRADE_CONFIG)
        ib.portfolio()

    asyncio.run(main())


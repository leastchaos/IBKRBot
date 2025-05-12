from decimal import Decimal
import logging
from ib_async import Ticker, IB, Trade
from math import isnan
from src.utils.helpers import get_price_at_depth
from src.core.order_management import round_to_tick
from src.models.models import Action
from src.strategy.mass_buy_options_async.config import TradingConfig
import asyncio

logger = logging.getLogger()
DEPTH_PRICE_SEMAPHORE = asyncio.Semaphore(2)


async def get_depth_price(
    ib: IB, option_ticker: Ticker, depth: int, timeout: int
) -> tuple[Decimal, Decimal]:
    """Get bid/ask prices at specified market depth."""
    async with DEPTH_PRICE_SEMAPHORE:
        depth_bid = (
            Decimal(str(option_ticker.bid))
            if option_ticker.bid and not isnan(option_ticker.bid)
            else Decimal(option_ticker.minTick)
        )
        depth_ask = (
            Decimal(str(option_ticker.ask))
            if option_ticker.ask and not isnan(option_ticker.ask)
            else Decimal(option_ticker.contract.strike)
        )

        if depth > 1:
            ib.reqMktDepth(option_ticker.contract, numRows=5, isSmartDepth=True)
            for _ in range(timeout):
                if option_ticker.domBids and option_ticker.domAsks:
                    break
                await asyncio.sleep(1)
            if option_ticker.domBids:
                depth_bid = get_price_at_depth(option_ticker.domBids, depth)
            if option_ticker.domAsks:
                depth_ask = get_price_at_depth(option_ticker.domAsks, depth)
            ib.cancelMktDepth(option_ticker.contract, isSmartDepth=True)
        return depth_bid, depth_ask


def get_stock_price(stock_ticker: Ticker, config: TradingConfig) -> float:
    market_price = stock_ticker.marketPrice()
    if isnan(market_price):
        logger.warning("Market price is NaN")
        if config.default_stock_price:
            logger.warning(f"Using default stock price: {config.default_stock_price}")
            return config.default_stock_price
    return market_price


async def determine_price(
    ib: IB,
    stock_ticker: Ticker,
    option_ticker: Ticker,
    config: TradingConfig,
    order: Trade | None = None,
) -> Decimal:
    """Determine optimal price for an order based on market data and strategy."""
    """Determine the price to place the order."""
    tick_size = Decimal(str(option_ticker.minTick))
    if config.manual_min_tick:
        tick_size = config.manual_min_tick
    own_quantity = 0
    action = config.action
    if config.depth > 0:
        if order:
            own_quantity = order.order.totalQuantity - order.filled()
    depth_bid, depth_ask = await get_depth_price(
        ib, option_ticker, config.depth + own_quantity, config.determine_price_timeout
    )
    market_price = get_stock_price(stock_ticker, config)
    if isnan(market_price):
        logger.warning("Market price is NaN, returning -1")
        return Decimal("-1")
    option_calculation = await ib.calculateOptionPriceAsync(
        option_ticker.contract, config.volatility, market_price
    )
    if not option_calculation:
        logger.warning("Option calculation failed")
        return Decimal("-1")
    calculated_price = Decimal(str(option_calculation.optPrice))
    if action == Action.BUY:
        max_price = Decimal(str(option_ticker.ask)) - config.min_distance
        logger.info(
            f"Calculated price: {calculated_price}, max_price: {max_price}, "
            f"depth_bid: {depth_bid}"
        )
        price = min(depth_bid, max_price, calculated_price, config.max_bid_price)
        logger.debug(f"price: {price}")

    if action == Action.SELL:
        min_price = Decimal(str(option_ticker.bid)) + config.min_distance
        logger.info(
            f"Calculated price: {calculated_price}, min_price: {min_price}, "
            f"depth_ask: {depth_ask}"
        )
        if depth_ask < Decimal("0"):
            logger.debug("No depth found")
            return Decimal("-1")
        price = max(depth_ask, min_price, calculated_price, config.min_ask_price)
        logger.debug(f"price: {price}")

    if price < Decimal("0"):
        return Decimal("-1")
    if config.aggressive:
        price += tick_size if action == Action.BUY else -tick_size
    rounded_price = round_to_tick(price, tick_size)
    logger.debug(
        f"rounded_price: {rounded_price} tick_size: {tick_size} price: {price}"
    )
    return rounded_price


if __name__ == "__main__":
    from src.core.ib_connector import (
        async_connect_to_ibkr,
        async_get_stock_ticker,
        async_get_option_ticker,
    )
    from src.utils.logger_config import setup_logger
    from ib_async import LimitOrder
    from src.models.models import Action, Rights, OCAType
    import asyncio

    setup_logger()
    config = TradingConfig(
        action=Action.BUY,
        right=Rights.CALL,
        min_dte=200,
        max_dte=300,
        min_strike=Decimal("190"),
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
    order = LimitOrder(
        action=config.action,
        totalQuantity=float(config.size),
        lmtPrice=100.0,
        tif="GTC",
        outsideRth=True,
        ocaGroup=config.oca_group,
        ocaType=config.oca_type.value,
    )

    async def main():
        ib = await async_connect_to_ibkr(
            "127.0.0.1", 7496, 666, readonly=True, account=""
        )
        ib.reqMarketDataType(4)
        stock_async = await async_get_stock_ticker(ib, "TSLA", "SMART", "USD", 10)
        option_async = await async_get_option_ticker(
            ib,
            "TSLA",
            "20250620",
            Decimal("100"),
            "C",
            "SMART",
            "",
            "USD",
            1,
        )

        await asyncio.sleep(1)
        print("market price")
        print(stock_async.marketPrice())
        limit_price = await determine_price(ib, stock_async, option_async, config)

        print(limit_price)

    asyncio.run(main())

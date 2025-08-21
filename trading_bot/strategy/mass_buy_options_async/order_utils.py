from decimal import Decimal
from math import isnan
from ib_async import Trade, IB, Ticker
from trading_bot.utils.helpers import option_display
import logging
from trading_bot.strategy.mass_buy_options_async.config import TradingConfig
from trading_bot.strategy.mass_buy_options_async.price_utils import (
    determine_price,
    get_stock_price,
)
from trading_bot.models.models import Action

logger = logging.getLogger()


async def manage_open_order(
    ib: IB,
    exec_ib: IB,
    trade: Trade,
    stock_ticker: Ticker,
    option_ticker: Ticker,
    config: TradingConfig,
) -> None:
    """Update order price if deviation exceeds threshold."""
    price = await determine_price(
        ib=ib,
        stock_ticker=stock_ticker,
        option_ticker=option_ticker,
        config=config,
        order=trade,
    )
    lmt_price = Decimal(str(trade.order.lmtPrice))
    if price <= Decimal("0"):
        logger.warning(
            f"Order {option_display(trade.contract)} has no limit price. Skipping update."
        )
        return
    if price == lmt_price:
        logger.info(
            f"Order {option_display(trade.contract)} limit price is already {price}. Skipping update."
        )
        return
    if (
        not config.aggressive
        and (price - lmt_price).copy_abs() < config.min_update_size
    ):
        logger.info(
            f"Not updating {option_display(trade.contract)} price from {trade.order.lmtPrice} to {price} (aggressive)"
        )
        return
    if (lmt_price - price).copy_abs() >= config.min_update_size:
        logger.info(
            f"Updating {option_display(trade.contract)} price from {trade.order.lmtPrice} to {price}"
        )
        trade.order.lmtPrice = price
        exec_ib.placeOrder(trade.contract, trade.order)
        return
    # if aggressive only shift when order is not in best bid when difference is less than min_update_size
    if trade.order.action == Action.BUY.value and lmt_price - price > Decimal("0"):
        logger.info(
            f"Not updating {option_display(trade.contract)} price from {trade.order.lmtPrice} to {price} (aggressive)"
        )
        return
    if trade.order.action == Action.SELL.value and price - lmt_price > Decimal("0"):
        logger.info(
            f"Not updating {option_display(trade.contract)} price from {trade.order.lmtPrice} to {price} (aggressive)"
        )
        return

    logger.info(
        f"Updating {option_display(trade.contract)} price from {trade.order.lmtPrice} to {price} (aggressive)"
    )
    trade.order.lmtPrice = price
    exec_ib.placeOrder(trade.contract, trade.order)


async def check_if_price_too_far(
    ib: IB, option_ticker: Ticker, config: TradingConfig, stock_price: Decimal
) -> bool:
    """Check if current price deviates too far from calculated value."""
    if not config.skip_too_far_away:
        return False
    if isnan(stock_price):
        logger.warning("Stock price is NaN, skipping check if price is too far away")
        return False
    option_price = await ib.calculateOptionPriceAsync(
        option_ticker.contract, float(config.volatility), float(stock_price)
    )
    if config.action == Action.BUY:
        bid_price = Decimal(
            str(
                (
                    option_ticker.bid
                    if not isnan(option_ticker.bid) and option_ticker.bid > Decimal("0")
                    else option_price.optPrice
                )
            )
        )
        if bid_price > Decimal("1.05") * config.max_bid_price:
            logger.info(
                f"Current bid price {bid_price} too far above max_buy_price {config.max_bid_price}"
            )
            return True
    if config.action == Action.SELL:
        ask_price = Decimal(
            str(
                option_ticker.ask
                if not isnan(option_ticker.ask) and option_ticker.ask > Decimal("0")
                else option_price.optPrice
            )
        )
        if ask_price < Decimal("0.95") * config.min_ask_price:
            logger.info(
                f"Current ask price {ask_price} too far below min_sell_price {config.min_ask_price}"
            )
            return True
    return False


if __name__ == "__main__":
    import asyncio
    from trading_bot.utils.logger_config import setup_logger

    setup_logger()
    from trading_bot.strategy.mass_buy_options_async.config import TradingConfig
    from trading_bot.core.ib_connector import (
        async_connect_to_ibkr,
        async_get_stock_ticker,
        async_get_option_ticker,
    )

    config = TradingConfig.generate_test_config()

    async def main():
        ib = await async_connect_to_ibkr(
            "127.0.0.1", 7496, 666, readonly=True, account=""
        )
        ib.reqMarketDataType(4)
        stock_ticker = await async_get_stock_ticker(ib, "TSLA", "SMART", "USD", 10)
        option_ticker = await async_get_option_ticker(
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
        stock_price = get_stock_price(stock_ticker, config)
        print(await check_if_price_too_far(ib, option_ticker, config, stock_price))

    asyncio.run(main())

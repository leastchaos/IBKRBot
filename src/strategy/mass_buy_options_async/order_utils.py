from decimal import Decimal
from math import isnan
from ib_async import Trade, IB, Ticker
from src.utils.helpers import option_display
import logging
from src.strategy.mass_buy_options_async.config import TradingConfig
from src.strategy.mass_buy_options_async.price_utils import determine_price
from src.models.models import Action

logger = logging.getLogger()


async def manage_open_order(
    ib: IB,
    exec_ib: IB,
    order: Trade,
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
        order=order,
    )
    lmt_price = Decimal(str(order.order.lmtPrice))
    if price <= Decimal("0"):
        logger.warning(
            f"Order {option_display(order.contract)} has no limit price. Skipping update."
        )
        return
    if price == lmt_price:
        return
    if (
        not config.aggressive
        and (price - lmt_price).copy_abs() < config.min_update_size
    ):
        return
    if (lmt_price - price).copy_abs() >= config.min_update_size:
        logger.info(
            f"Updating {option_display(order.contract)} price from {order.order.lmtPrice} to {price}"
        )
        order.order.lmtPrice = price
        exec_ib.placeOrder(order.contract, order.order)
        return
    # if aggressive only shift when order is not in best bid when difference is less than min_update_size
    if order.order.action == Action.BUY.value and lmt_price - price > Decimal("0"):
        logger.info(
            f"Not updating {option_display(order.contract)} price from {order.order.lmtPrice} to {price} (aggressive)"
        )
        return
    if order.order.action == Action.SELL.value and price - lmt_price > Decimal("0"):
        logger.info(
            f"Not updating {option_display(order.contract)} price from {order.order.lmtPrice} to {price} (aggressive)"
        )
        return

    logger.info(
        f"Updating {option_display(order.contract)} price from {order.order.lmtPrice} to {price} (aggressive)"
    )
    order.order.lmtPrice = price
    exec_ib.placeOrder(order.contract, order.order)


async def check_if_price_too_far(
    ib: IB, option_ticker: Ticker, config: TradingConfig, stock_price: Decimal
) -> bool:
    """Check if current price deviates too far from calculated value."""
    if not config.skip_too_far_away:
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


if __name__
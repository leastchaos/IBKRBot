from decimal import Decimal
from enum import Enum
import logging
import random
from ib_async import IB, Contract, LimitOrder, Option, Stock, Ticker, Trade

from src.core.order_management import execute_oca_orders, round_to_tick
from src.core.ib_connector import (
    get_current_position,
    get_option_ticker,
    get_option_ticker_depth_from_contract,
    get_option_ticker_from_contract,
    get_options,
    wait_for_subscription,
)
from src.models.models import Action, OCAOrder, OCAType, Rights
from src.utils.helpers import option_display, get_price_at_depth

logger = logging.getLogger()


def determine_price(
    ib: IB,
    stock_ticker: Ticker,
    option_ticker: Ticker,
    action: Action,
    min_distance: Decimal,
    depth: int,
    aggressive: bool,
    volatility: float,
    order: Trade | None = None,
    timeout: int = 5,
) -> Decimal:
    """Determine the price to place the order."""
    tick_size = Decimal(str(option_ticker.minTick))
    own_quantity = 0
    if depth > 0:
        if order:
            own_quantity = order.order.totalQuantity - order.filled()
    depth_bid, depth_ask = get_depth_price(
        ib, option_ticker, depth + own_quantity, timeout
    )
    calculated_price = Decimal(
        str(
            ib.calculateOptionPrice(
                option_ticker.contract, volatility, stock_ticker.marketPrice()
            ).optPrice
        )
    )
    if action == Action.BUY or action == Action.BUY.value:
        max_price = Decimal(str(option_ticker.ask)) - min_distance
        logger.info(
            f"Calculated price: {calculated_price}, max_price: {max_price}, "
            f"depth_bid: {depth_bid}"
        )
        price = min(depth_bid, max_price, calculated_price)
        logger.info(f"price: {price}")

    if action == Action.SELL or action == Action.SELL.value:
        min_price = Decimal(str(option_ticker.bid)) + min_distance
        logger.info(
            f"Calculated price: {calculated_price}, min_price: {min_price}, "
            f"depth_ask: {depth_ask}"
        )
        if depth_ask < Decimal("0"):
            logger.info("No depth found")
            return Decimal("-1")
        price = max(depth_ask, min_price, calculated_price)
        logger.info(f" price: {price}")

    rounded_price = round_to_tick(price, tick_size)
    if rounded_price < Decimal("0"):
        return Decimal("-1")
    if aggressive:
        rounded_price += tick_size if action == Action.BUY else -tick_size
        logger.info(f"Rounded price: {rounded_price}")
    return rounded_price


def get_depth_price(
    ib: IB, option_ticker: Ticker, depth: int, timeout: int
) -> tuple[Decimal, Decimal]:
    depth_bid = Decimal(str(option_ticker.minTick))
    depth_ask = Decimal(str(option_ticker.contract.strike))
    if option_ticker.bid:
        depth_bid = Decimal(str(option_ticker.bid))
    if option_ticker.ask:
        depth_ask = Decimal(str(option_ticker.ask))
    if depth > 1:
        ib.reqMktDepth(option_ticker.contract, numRows=5, isSmartDepth=True)
        for _ in range(timeout):
            if option_ticker.domBids and option_ticker.domAsks:
                break
            ib.sleep(1)
        if option_ticker.domBids:
            depth_bid = get_price_at_depth(option_ticker.domBids, depth)
        if option_ticker.domAsks:
            depth_ask = get_price_at_depth(option_ticker.domAsks, depth)
        ib.cancelMktDepth(option_ticker.contract, isSmartDepth=True)
    return depth_bid, depth_ask


def manage_open_order(
    ib: IB,
    exec_ib: IB,
    order: Trade,
    stock_ticker: Ticker,
    option_ticker: Ticker,
    min_distance: Decimal,
    depth: int,
    min_update_size: Decimal,
    volatility: float,
    aggressive: bool,
) -> None:
    """Manage the open order."""
    price = determine_price(
        ib=ib,
        stock_ticker=stock_ticker,
        option_ticker=option_ticker,
        action=order.order.action,
        min_distance=min_distance,
        depth=depth,
        order=order,
        volatility=volatility,
        aggressive=aggressive,
    )
    lmt_price = Decimal(str(order.order.lmtPrice))
    if price <= Decimal("0"):
        logger.warning(
            f"Order {option_display(order.contract)} has no limit price. Skipping update."
        )
        return
    if (lmt_price - price).copy_abs() >= min_update_size:
        logger.info(
            f"Updating {option_display(order.contract)} price from {order.order.lmtPrice} to {price}"
        )
        order.order.lmtPrice = price
        exec_ib.placeOrder(order.contract, order.order)


def mass_trade_oca_option(
    ib: IB,
    stock: Stock,
    action: Action,
    right: Rights,
    min_dte: int,
    max_dte: int,
    min_strike: Decimal,
    max_strike: Decimal,
    size: Decimal,
    min_distance: Decimal,
    oca_group: str,
    oca_type: OCAType,
    prevent_short_positions: bool,
    depth: int,
    min_update_size: Decimal,
    loop_interval: int,
    volatility: float,
    aggresive: bool,
    exec_ib: IB | None = None,  # in order to use data from account with subscriptions
) -> None:
    """Mass trade option contracts."""
    if exec_ib is None:
        exec_ib = ib
    options = get_options(ib, stock, [right], min_dte, max_dte, min_strike, max_strike)
    oca_orders = []
    stock_ticker = get_stock_ticker(ib, stock.symbol, stock.exchange, stock.currency)
    options_tickers = {
        option.conId: get_option_ticker_from_contract(
            ib, option, 0, include_depth=False
        )
        for option in options
    }
    for option in options:
        option_size = size
        option_ticker = options_tickers[option.conId]
        wait_for_subscription(ib, option_ticker, 1)
        price = determine_price(
            ib=ib,
            stock_ticker=stock_ticker,
            option_ticker=option_ticker,
            action=action,
            min_distance=min_distance,
            depth=depth,
            volatility=volatility,
            aggressive=aggresive,
        )
        if price < Decimal("0"):
            price = (
                Decimal(str(option_ticker.contract.strike))
                if action == Action.SELL
                else option_ticker.minTick
            )
            logger.warning(
                f"Unable to determine price for {option_display(option)}. Using strike price or min tick."
            )

        if prevent_short_positions and action == Action.SELL:
            current_pos = get_current_position(exec_ib, option_ticker.contract)
            logger.info(f"Current position for {option_display(option)}: {current_pos}")
            if current_pos <= 0:
                logger.info(
                    f"Skipping {option_display(option)} because current position is {current_pos}"
                )
                continue
            option_size = min(option_size, current_pos)

        order = LimitOrder(
            action=action.value,
            totalQuantity=float(option_size),
            lmtPrice=price,
            outsideRth=True,
            ocaGroup=oca_group,
            ocaType=oca_type.value,
            tif="Day",
            account=exec_ib.account, # custom attribute
        )
        oca_order = OCAOrder(contract=option, order=order)
        logger.info(
            f"Placing {oca_order.order.action} order: {oca_order.order.totalQuantity} @ {oca_order.order.lmtPrice}"
        )
        oca_orders.append(oca_order)

    orders = execute_oca_orders(exec_ib, oca_orders)
    for oca_order, open_order in orders.items():
        logger.info(
            f"Placed {oca_order.order.action} order: {oca_order.order.totalQuantity} @ {oca_order.order.lmtPrice}"
        )
    # Manage open_order

    while True:
        for open_order in orders.values():
            if open_order.isDone():
                logger.info(f"Order {open_order.order.action} is done")
                return
            ticker = options_tickers[open_order.contract.conId]
            manage_open_order(
                ib=ib,
                exec_ib=exec_ib,
                order=open_order,
                stock_ticker=stock_ticker,
                option_ticker=ticker,
                min_distance=min_distance,
                depth=depth,
                min_update_size=min_update_size,
                volatility=volatility,
                aggressive=aggresive,
            )

        # Wait for 5 seconds before checking again
        ib.sleep(loop_interval)


if __name__ == "__main__":
    from src.utils.logger_config import setup_logger
    from src.core.ib_connector import connect_to_ibkr, get_stock_ticker
    from datetime import datetime

    setup_logger()

    # exec_ib = connect_to_ibkr("127.0.0.1", 7497, 222, readonly=True, account="")
    exec_ib = connect_to_ibkr("127.0.0.1", 7496, 10, readonly=False, account="")
    ib = connect_to_ibkr("127.0.0.1", 7496, 222, readonly=True, account="")
    ib.reqMarketDataType(1)
    stock = Stock("9988", "", "HKD")
    stock = ib.qualifyContracts(stock)[0]
    mass_trade_oca_option(
        ib=ib,
        stock=stock,
        action=Action.SELL,
        right=Rights.PUT,
        min_dte=100,
        max_dte=365,
        min_strike=Decimal("140"),
        max_strike=Decimal("160"),
        size=Decimal("1"),
        min_distance=Decimal("0.5"),
        oca_group=f"Mass Trade {datetime.now().strftime('%Y%m%d %H:%M:%S')}",
        oca_type=OCAType.REDUCE_WITH_NO_BLOCK,
        prevent_short_positions=False,
        depth=5,
        loop_interval=5,
        aggresive=True,
        volatility=0.45,
        min_update_size=Decimal("0.01"),
        exec_ib=exec_ib,
    )

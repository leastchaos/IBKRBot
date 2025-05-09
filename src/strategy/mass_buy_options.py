from decimal import Decimal
import logging
from math import isnan
from ib_async import IB, LimitOrder, Stock, Ticker, Trade

from src.core.order_management import execute_oca_orders, round_to_tick
from src.core.ib_connector import (
    get_current_position,
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
    action: Action | str,
    min_distance: Decimal,
    depth: int,
    aggressive: bool,
    volatility: float,
    min_ask_price: Decimal,
    max_bid_price: Decimal,
    manual_min_tick: Decimal | None = None,
    order: Trade | None = None,
    timeout: int = 5,
) -> Decimal:
    """Determine the price to place the order."""
    tick_size = Decimal(str(option_ticker.minTick))
    if manual_min_tick:
        tick_size = manual_min_tick
    own_quantity = 0
    # convert str to Action if action is a string
    if isinstance(action, str):
        action = Action(action)
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
    if action == Action.BUY:
        max_price = Decimal(str(option_ticker.ask)) - min_distance
        logger.info(
            f"Calculated price: {calculated_price}, max_price: {max_price}, "
            f"depth_bid: {depth_bid}"
        )
        price = min(depth_bid, max_price, calculated_price, max_bid_price)
        logger.debug(f"price: {price}")

    if action == Action.SELL:
        min_price = Decimal(str(option_ticker.bid)) + min_distance
        logger.info(
            f"Calculated price: {calculated_price}, min_price: {min_price}, "
            f"depth_ask: {depth_ask}"
        )
        if depth_ask < Decimal("0"):
            logger.debug("No depth found")
            return Decimal("-1")
        price = max(depth_ask, min_price, calculated_price, min_ask_price)
        logger.debug(f"price: {price}")

    if price < Decimal("0"):
        return Decimal("-1")
    if aggressive:
        price += tick_size if action == Action.BUY else -tick_size
    rounded_price = round_to_tick(price, tick_size)
    logger.debug(f"rounded_price: {rounded_price} tick_size: {tick_size} price: {price}")
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
    if isnan(depth_bid):
        print(f"min tick: {option_ticker.minTick}")
        depth_bid = Decimal(str(option_ticker.minTick))
    if isnan(depth_ask):
        print(f"min tick: {option_ticker.minTick}")
        depth_ask = Decimal(str(option_ticker.contract.strike))
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
    min_ask_price: Decimal,
    max_ask_price: Decimal,
    manual_min_tick: Decimal | None,
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
        min_ask_price=min_ask_price,
        max_bid_price=max_ask_price,
        aggressive=aggressive,
        manual_min_tick=manual_min_tick,
    )
    lmt_price = Decimal(str(order.order.lmtPrice))
    if price <= Decimal("0"):
        logger.warning(
            f"Order {option_display(order.contract)} has no limit price. Skipping update."
        )
        return
    if price == lmt_price:
        return
    if not aggressive and (price - lmt_price).copy_abs() < min_update_size:
        return
    if (lmt_price - price).copy_abs() >= min_update_size:
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


def check_if_price_too_far(
    action: Action,
    option_ticker: Ticker,
    min_ask_price: Decimal,
    max_bid_price: Decimal,
    volatility: Decimal,
    stock_price: Decimal,
    skip_too_far_away: bool,
) -> bool:
    if not skip_too_far_away:
        return False
    if action == Action.BUY:
        bid_price = Decimal(
            str(
                (
                    option_ticker.bid
                    if not isnan(option_ticker.bid) and option_ticker.bid > Decimal("0")
                    else ib.calculateOptionPrice(
                        option_ticker.contract, float(volatility), float(stock_price)
                    ).optPrice
                )
            )
        )
        if bid_price > Decimal("1.05") * max_bid_price:
            logger.info(
                f"Current bid price {bid_price} too far above max_buy_price {max_bid_price}"
            )
            return True
    if action == Action.SELL:
        ask_price = Decimal(
            str(
                option_ticker.ask
                if not isnan(option_ticker.ask) and option_ticker.ask > Decimal("0")
                else ib.calculateOptionPrice(
                    option_ticker.contract, float(volatility), float(stock_price)
                ).optPrice
            )
        )
        if ask_price < Decimal("0.95") * min_ask_price:
            logger.info(
                f"Current ask price {ask_price} too far below min_sell_price {min_ask_price}"
            )
            return True
    return False


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
    close_positions_only: bool,
    depth: int,
    min_update_size: Decimal,
    loop_interval: int,
    volatility: float,
    aggresive: bool,
    skip_too_far_away: bool,
    min_ask_price: Decimal,
    max_bid_price: Decimal,
    manual_min_tick: Decimal | None,
    exec_ib: IB | None = None,  # in order to use data from account with subscriptions
) -> None:
    """Mass trade option contracts."""
    if exec_ib is None:
        exec_ib = ib
    if oca_type == OCAType.MANUAL:
        oca_group = ""
    options = get_options(ib, stock, [right], min_dte, max_dte, min_strike, max_strike)
    oca_orders: list[OCAOrder] = []
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

        if close_positions_only:
            current_pos = get_current_position(exec_ib, option_ticker.contract)
            logger.info(f"Current position for {option_display(option)}: {current_pos}")
            if action == Action.SELL:
                if current_pos <= 0:
                    logger.info(
                        f"Skipping {option_display(option)} because current position is {current_pos}"
                    )
                    continue
                option_size = min(option_size, current_pos)
            if action == Action.BUY:
                if current_pos >= 0:
                    logger.info(
                        f"Skipping {option_display(option)} because current position is {current_pos}"
                    )
                    continue
                option_size = min(option_size, -current_pos)
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
            manual_min_tick=manual_min_tick,
            min_ask_price=min_ask_price,
            max_bid_price=max_bid_price,
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
        # skip if current bid price is too far above max_buy_price to be triggered
        if check_if_price_too_far(
            action=action,
            option_ticker=option_ticker,
            min_ask_price=min_ask_price,
            max_bid_price=max_bid_price,
            volatility=volatility,
            stock_price=stock_ticker.marketPrice(),
            skip_too_far_away=skip_too_far_away,
        ):
            continue
        order = LimitOrder(
            action=action.value,
            totalQuantity=float(option_size),
            lmtPrice=price,
            outsideRth=True,
            ocaGroup=oca_group,
            ocaType=oca_type.value,
            tif="Day",
            account=exec_ib.account,  # custom attribute
            transmit=False,
        )
        order = exec_ib.placeOrder(option, order)
        order.order.transmit = True
        oca_order = OCAOrder(contract=option, trade=order.order)
        logger.info(
            f"Placing {action.value} order: {oca_order.trade.totalQuantity} @ {oca_order.trade.lmtPrice}"
        )
        oca_orders.append(oca_order)
    try:
        input("Check orders and press enter to continue...")
    except KeyboardInterrupt:
        for open_order in oca_orders:
            exec_ib.cancelOrder(open_order.trade)
            logger.info(
                f"Canceled {open_order.trade.action} order @ {open_order.trade.lmtPrice}"
            )
        ib.sleep(1)
        return

    orders = execute_oca_orders(exec_ib, oca_orders)

    for oca_order, open_order in orders.items():
        logger.info(
            f"Placed {oca_order.trade.action} order: {oca_order.trade.totalQuantity} @ {oca_order.trade.lmtPrice}"
        )
    # Manage open_order
    try:
        while True:
            for open_order in orders.values():
                if open_order.isDone():
                    logger.info(f"Order {open_order.order.action} is done")
                    for order in orders.values():
                        exec_ib.cancelOrder(order.order)
                        logger.info(
                            f"Canceled {order.order.action} order @ {order.order.lmtPrice}"
                        )
                    logger.info("All orders canceled.")
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
                    manual_min_tick=manual_min_tick,
                    min_ask_price=min_ask_price,
                    max_ask_price=max_bid_price,
                )

            # Wait for 5 seconds before checking again
            ib.sleep(loop_interval)

    finally:
        # cancel all orders
        for open_order in orders.values():

            exec_ib.cancelOrder(open_order.order)
            logger.info(
                f"Canceled {open_order.order.action} order @ {open_order.order.lmtPrice}"
            )

        logger.info("All orders canceled.")


if __name__ == "__main__":
    from src.utils.logger_config import setup_logger
    from src.utils.helpers import get_ibkr_account
    from src.core.ib_connector import connect_to_ibkr, get_stock_ticker
    from datetime import datetime

    setup_logger()
    account = get_ibkr_account("mass_buy_options")
    # exec_ib = connect_to_ibkr("127.0.0.1", 7497, 222, readonly=True, account="")
    exec_ib = connect_to_ibkr("127.0.0.1", 7496, 333, readonly=False, account=account)
    ib = connect_to_ibkr("127.0.0.1", 7496, 222, readonly=True, account="")
    ib.reqMarketDataType(1)
    stock = Stock("9988", "", "HKD")
    stock = ib.qualifyContracts(stock)[0]
    mass_trade_oca_option(
        ib=ib,
        stock=stock,
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
        min_ask_price=Decimal("40"),
        max_bid_price=Decimal("5"),
        oca_group=f"Mass Trade {datetime.now().strftime('%Y%m%d %H:%M:%S')}",
        oca_type=OCAType.REDUCE_WITH_NO_BLOCK,
        close_positions_only=False,
        depth=5,
        loop_interval=5,
        aggresive=True,
        skip_too_far_away=False,
        volatility=0.45,
        exec_ib=exec_ib,

    )

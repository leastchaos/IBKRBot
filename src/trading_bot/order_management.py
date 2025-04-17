from ib_async import IB, Contract, LimitOrder, Stock, Trade
import numpy as np
import logging

logger = logging.getLogger()


def manage_orders(
    ib: IB,
    contract: Stock,
    buy_prices: list[float],
    sell_prices: list[float],
    buy_sizes: list[float],
    sell_sizes: list[float],
    step_size: float,
    precision: int,
) -> None:
    """Manage buy and sell orders."""
    # Cancel out-of-range orders
    cancel_out_of_range_orders(ib, contract, buy_prices, sell_prices, step_size, precision)

    # Fetch existing open orders
    buy_orders, sell_orders = {}, {}
    for order in ib.reqAllOpenOrders():
        if order.contract.conId == contract.conId:
            (buy_orders if order.order.action == "BUY" else sell_orders)[
                order.order.lmtPrice
            ] = order

    # Process buy orders
    process_orders(
        ib=ib,
        contract=contract,
        action="BUY",
        prices=buy_prices,
        sizes=buy_sizes,
        existing_orders=buy_orders,
    )

    # Process sell orders
    process_orders(
        ib=ib,
        contract=contract,
        action="SELL",
        prices=sell_prices,
        sizes=sell_sizes,
        existing_orders=sell_orders,
    )


def cancel_out_of_range_orders(
    ib: IB,
    contract: Contract,
    buy_prices: list[float],
    sell_prices: list[float],
    step_size: float,
    precision: int,
) -> None:
    """Cancel out-of-range orders."""
    valid_prices = np.arange(
        min(buy_prices) - step_size, max(sell_prices) + step_size, step_size
    )
    valid_prices = [round(p, precision) for p in valid_prices]
    for order in ib.reqAllOpenOrders():
        if order.contract.conId == contract.conId:
            price = order.order.lmtPrice
            if price not in valid_prices:
                logger.info(
                    f"Cancelling out-of-range {order.order.action} order @ {price}"
                )
                ib.cancelOrder(order.order)


def process_orders(
    ib: IB,
    contract: Contract,
    action: str,
    prices: list[float],
    sizes: list[float],
    existing_orders: dict[float, Trade],
) -> None:
    """Process buy/sell orders."""
    for price, size in zip(prices, sizes):
        if size <= 0:
            continue
        if price in existing_orders:
            existing_order = existing_orders[price]
            if existing_order.order.totalQuantity == size:
                logger.debug(f"Order exists: {action} {size} @ {price}")
                continue
            ib.cancelOrder(existing_order.order)
            logger.info(f"Cancelled {action} @ {price}")
        order = LimitOrder(
            action=action,
            totalQuantity=size,
            lmtPrice=price,
            tif="GTC",  # Good-Till-Cancelled
            outsideRth=True,  # Allow trading outside regular trading hours
        )
        ib.placeOrder(contract, order)
        logger.info(f"Placed {action} GTC order: {size} @ {price}")


def place_limit_order(
    ib: IB, stock_ticker: Stock, action: str, size: float, price: float
) -> Trade:
    """
    Place a limit order with the given parameters.
    """
    order = LimitOrder(
        action=action,
        totalQuantity=size,
        lmtPrice=price,
        tif="GTC",  # Good-Till-Cancelled
        outsideRth=True,  # Allow trading outside regular trading hours
    )
    trade = ib.placeOrder(stock_ticker.contract, order)
    logger.info(f"Placed {action} GTC order: {size} @ {price}")
    return trade


def wait_for_order_execution(ib: IB, trade: Trade, timeout=60) -> bool:
    """
    Wait for the order to execute fully within the specified timeout.
    Returns True if the order is fully executed, False otherwise.
    """
    for _ in range(timeout):
        ib.sleep(1)
        if trade.isDone():
            return True
    return False


def execute_catch_up_trade(
    ib: IB,
    stock_ticker: Stock,
    last_traded_price: float,
    current_price: float,
    active_levels: int,
    step_size: float,
    position_per_level: float,
    timeout=60,
):
    """
    Execute the trading logic based on the price difference between last traded price and current price.
    """
    if (
        last_traded_price
        and abs(current_price - last_traded_price) > active_levels * step_size
    ):
        # Calculate the number of levels and size
        size = abs(last_traded_price - current_price) // step_size * position_per_level
        action = "BUY" if last_traded_price > current_price else "SELL"
        price = (
            current_price + step_size if action == "BUY" else current_price - step_size
        )

        # Place the initial order
        while size > position_per_level:
            trade = place_limit_order(ib, stock_ticker, action, size, price)
            if wait_for_order_execution(ib, trade, timeout):
                logger.info(f"Order executed: {trade.order.action} {trade.order.totalQuantity} @ {trade.order.lmtPrice}")
                break
            logger.warning(
                f"Order failed to execute fully: {trade.order.action} {trade.order.totalQuantity} @ {trade.order.lmtPrice}"
            )
            ib.cancelOrder(trade.order)
            logger.info(
                f"Cancelled order: {trade.order.action} {trade.order.totalQuantity} @ {trade.order.lmtPrice}"
            )
            # Handle any remaining quantity
            size -= trade.filled() + position_per_level
            price = price + step_size if action == "BUY" else price - step_size
            
from ib_async import IB, Contract, LimitOrder, Stock, Trade
import numpy as np
import logging
from decimal import Decimal, getcontext

logger = logging.getLogger()


def manage_orders(
    ib: IB,
    contract: Stock,
    buy_prices: list[Decimal],
    sell_prices: list[Decimal],
    buy_sizes: list[Decimal],
    sell_sizes: list[Decimal],
    step_size: Decimal,
) -> None:
    """Manage buy and sell orders using Decimal."""
    # Cancel out-of-range orders
    cancel_out_of_range_orders(ib, contract, buy_prices, sell_prices, step_size)

    # Fetch existing open orders
    buy_orders, sell_orders = {}, {}
    for order in ib.reqAllOpenOrders():
        if order.contract.conId == contract.conId:
            (buy_orders if order.order.action == "BUY" else sell_orders)[
                Decimal(str(order.order.lmtPrice))
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
    buy_prices: list[Decimal],
    sell_prices: list[Decimal],
    step_size: Decimal,
) -> None:
    """Cancel out-of-range orders using Decimal."""
    # Generate valid price range using Decimal arithmetic
    min_price = min(buy_prices)
    max_price = max(sell_prices)
    valid_prices = [
        min_price + i * step_size
        for i in range(int((max_price - min_price) / step_size) + 1)
    ]

    # Cancel out-of-range orders
    for order in ib.reqAllOpenOrders():
        if order.contract.conId == contract.conId:
            price = Decimal(str(order.order.lmtPrice))
            if price not in valid_prices:
                logger.info(
                    f"Cancelling out-of-range {order.order.action} order @ {price}"
                )
                ib.cancelOrder(order.order)


def process_orders(
    ib: IB,
    contract: Contract,
    action: str,
    prices: list[Decimal],
    sizes: list[Decimal],
    existing_orders: dict[Decimal, Trade],
) -> None:
    """Process buy/sell orders using Decimal."""
    for price, size in zip(prices, sizes):
        if size <= Decimal(0):
            continue
        if price in existing_orders:
            existing_order = existing_orders[price]
            if Decimal(str(existing_order.order.totalQuantity)) == size:
                logger.debug(f"Order exists: {action} {size} @ {price}")
                continue
            ib.cancelOrder(existing_order.order)
            logger.info(f"Cancelled {action} @ {price}")
        order = LimitOrder(
            action=action,
            totalQuantity=float(size),  # Convert Decimal to float for IB API
            lmtPrice=float(price),  # Convert Decimal to float for IB API
            tif="GTC",  # Good-Till-Cancelled
            outsideRth=True,  # Allow trading outside regular trading hours
        )
        ib.placeOrder(contract, order)
        logger.info(f"Placed {action} GTC order: {size} @ {price}")


def place_limit_order(
    ib: IB, stock_ticker: Stock, action: str, size: Decimal, price: Decimal
) -> Trade:
    """
    Place a limit order with the given parameters using Decimal.
    """
    order = LimitOrder(
        action=action,
        totalQuantity=float(size),  # Convert Decimal to float for IB API
        lmtPrice=float(price),  # Convert Decimal to float for IB API
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
    last_traded_price: Decimal | None,
    current_price: Decimal,
    active_levels: int,
    step_size: Decimal,
    position_per_level: Decimal,
    timeout=60,
):
    """
    Execute the trading logic based on the price difference between last traded price and current price using Decimal.
    """
    if (
        last_traded_price
        and abs(current_price - last_traded_price) > active_levels * step_size
    ):
        # Calculate the number of levels and size
        size = (
            abs(current_price - last_traded_price) // step_size
        ) * position_per_level
        action = "BUY" if last_traded_price > current_price else "SELL"
        price = (
            current_price + step_size if action == "BUY" else current_price - step_size
        )

        # Place the initial order
        while size > position_per_level:
            trade = place_limit_order(ib, stock_ticker, action, size, price)
            if wait_for_order_execution(ib, trade, timeout):
                logger.info(
                    f"Order executed: {trade.order.action} {trade.order.totalQuantity} @ {trade.order.lmtPrice}"
                )
                break
            logger.warning(
                f"Order failed to execute fully: {trade.order.action} {trade.order.totalQuantity} @ {trade.order.lmtPrice}"
            )
            ib.cancelOrder(trade.order)
            logger.info(
                f"Cancelled order: {trade.order.action} {trade.order.totalQuantity} @ {trade.order.lmtPrice}"
            )
            # Handle any remaining quantity
            size -= Decimal(trade.filled()) + position_per_level
            price = price + step_size if action == "BUY" else price - step_size

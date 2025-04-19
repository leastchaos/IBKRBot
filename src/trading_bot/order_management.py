from ib_async import IB, Contract, LimitOrder, Stock, Ticker, Trade
import logging
from decimal import Decimal

from grid_calculations import get_current_grid_buy_and_sell_levels

logger = logging.getLogger()


def manage_orders(
    ib: IB,
    contract: Stock,
    buy_levels: dict[Decimal, Decimal],
    sell_levels: dict[Decimal, Decimal],
    step_size: Decimal,
) -> None:
    """Manage buy and sell orders using Decimal."""
    # Cancel out-of-range orders
    min_price = min(buy_levels.keys())
    max_price = max(sell_levels.keys())
    cancel_out_of_range_orders(ib, contract, min_price, max_price, step_size)

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
        levels=buy_levels,
        existing_orders=buy_orders,
    )

    # Process sell orders
    process_orders(
        ib=ib,
        contract=contract,
        action="SELL",
        levels=sell_levels,
        existing_orders=sell_orders,
    )


def cancel_out_of_range_orders(
    ib: IB,
    contract: Contract,
    min_price: Decimal,
    max_price: Decimal,
    step_size: Decimal,
) -> None:
    """Cancel out-of-range orders using Decimal."""
    # Generate valid price range using Decimal arithmetic
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
    levels: dict[Decimal, Decimal],
    existing_orders: dict[Decimal, Trade],
) -> None:
    """Process buy/sell orders using Decimal."""
    for price, size in levels.items():
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
    ib: IB, stock_ticker: Ticker, action: str, size: Decimal, price: Decimal
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


def cancel_all_orders(ib: IB, contract: Contract) -> None:
    for order in ib.reqAllOpenOrders():
        if order.contract.conId == contract.conId:
            ib.cancelOrder(order.order)
            logger.info(f"Canceled {order.order.action} order @ {order.order.lmtPrice}")

    logger.info(f"All orders in {contract.symbol} canceled.")


def execute_catch_up_trade(
    ib: IB,
    stock_ticker: Ticker,
    current_price: Decimal,
    last_traded_price: Decimal,
    grid: dict[Decimal, Decimal],
    timeout: int,
    current_pos: Decimal,
):
    """
    Execute the trading logic based on the price difference between last traded price and current price using Decimal.
    """
    nearest_price_in_grid = min(grid.keys(), key=lambda x: abs(x - last_traded_price))
    buy_last_traded_grid, sell_last_traded_grid = get_current_grid_buy_and_sell_levels(
        nearest_price_in_grid, grid, 1, current_pos
    )
    current_buy_level = min(buy_last_traded_grid.keys())
    current_sell_level = max(sell_last_traded_grid.keys())
    logger.info(
        f"Current price: {current_price}, Last traded price: {last_traded_price}"
    )
    logger.info(
        f"Current buy level: {current_buy_level}, Current sell level: {current_sell_level}"
    )
    if current_price >= current_buy_level and current_price <= current_sell_level:
        logger.info(
            f"No catch-up trade required: current_price={current_price}, current_buy_level={current_buy_level}, current_sell_level={current_sell_level}"
        )
        return
    logger.info(
        f"Executing catch-up trade: current_price={current_price}, current_buy_level={current_buy_level}, current_sell_level={current_sell_level}"
    )
    cancel_all_orders(ib, stock_ticker.contract)
    # Calculate the number of levels and size
    trade_grid = {}
    price_range = sorted(grid.keys())
    logger.info(f"Price range: {price_range}")
    if current_price < last_traded_price:
        action = "BUY"
        trade_grid = {
            price_range[idx]: grid[price_range[idx]]
            for idx in range(0, len(price_range))
            if price_range[idx] >= current_price
            and price_range[idx] <= last_traded_price
        }
        size = sum(trade_grid.values())
        trade_grid = dict(sorted(trade_grid.items(), key=lambda x: x[0], reverse=False))
    if current_price > last_traded_price:
        action = "SELL"
        trade_grid = {
            price_range[idx]: grid[price_range[idx - 1]]
            for idx in range(1, len(price_range))
            if price_range[idx] <= current_price
            and price_range[idx] >= last_traded_price
        }
        size = sum(trade_grid.values())
        size = min(size, current_pos)
        # sort grid with the highest price first
        trade_grid = dict(sorted(trade_grid.items(), key=lambda x: x[0], reverse=True))
    logger.info(f"Action: {action}")
    logger.info(f"Size: {size}")
    logger.info(f"Trade grid: {trade_grid}")
    for price, level_size in trade_grid.items():
        if size <= Decimal(0):
            break
        logger.info(f"Price: {price}, Size: {level_size}")

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
        size -= Decimal(trade.filled()) + level_size

    if size > 0:
        logger.warning(
            f"Order failed to execute fully: {trade.order.action} {trade.order.totalQuantity} @ {trade.order.lmtPrice}"
        )
        logger.info(f"Remaining quantity: {size}")

    return

from typing import Literal
from ib_async import IB, Contract, LimitOrder, Stock, Ticker, Trade
import logging
from decimal import Decimal

from grid_calculations import get_current_grid_buy_and_sell_levels

logger = logging.getLogger()


def fetch_existing_orders(
    ib: IB, contract: Contract
) -> tuple[dict[Decimal, Trade], dict[Decimal, Trade]]:
    """Fetch existing open orders and categorize them into buy/sell orders."""
    buy_orders, sell_orders = {}, {}
    for order in ib.reqAllOpenOrders():
        if order.contract.conId == contract.conId:
            price = Decimal(str(order.order.lmtPrice))
            (buy_orders if order.order.action == "BUY" else sell_orders)[price] = order
    return buy_orders, sell_orders


def manage_orders(
    ib: IB,
    contract: Stock,
    buy_levels: dict[Decimal, Decimal],
    sell_levels: dict[Decimal, Decimal],
) -> None:
    """Manage buy and sell orders using Decimal."""
    cancel_out_of_range_orders(ib, contract, buy_levels, sell_levels)

    buy_orders, sell_orders = fetch_existing_orders(ib, contract)
    process_orders(ib, contract, "BUY", buy_levels, buy_orders)
    process_orders(ib, contract, "SELL", sell_levels, sell_orders)


def cancel_out_of_range_orders(
    ib: IB,
    contract: Contract,
    buy_levels: dict[Decimal, Decimal],
    sell_levels: dict[Decimal, Decimal],
) -> None:
    """Cancel out-of-range orders using Decimal."""
    # Generate valid price range using Decimal arithmetic
    # Cancel out-of-range orders
    for order in ib.reqAllOpenOrders():
        if order.contract.conId == contract.conId:
            price = Decimal(str(order.order.lmtPrice))
            levels = buy_levels if order.order.action == "BUY" else sell_levels
            if price not in levels:
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
            handle_existing_order(ib, existing_orders[price], action, price, size)
        else:
            place_new_order(ib, contract, action, price, size)


def handle_existing_order(
    ib: IB, order: Trade, action: str, price: Decimal, size: Decimal
) -> None:
    """Handle an existing order by comparing its size with the desired size."""
    existing_size = Decimal(str(order.order.totalQuantity))
    if existing_size == size:
        logger.debug(f"Order exists: {action} {size} @ {price}")
        return
    ib.cancelOrder(order.order)
    logger.info(f"Cancelled {action} @ {price}")


def place_new_order(
    ib: IB, contract: Contract, action: str, price: Decimal, size: Decimal
) -> None:
    """Place a new limit order."""
    order = create_limit_order(action, float(size), float(price))
    ib.placeOrder(contract, order)
    logger.info(f"Placed {action} GTC order: {size} @ {price}")


def create_limit_order(
    action: str, total_quantity: float, lmt_price: float
) -> LimitOrder:
    """Create a limit order with common parameters."""
    return LimitOrder(
        action=action,
        totalQuantity=total_quantity,
        lmtPrice=lmt_price,
        tif="GTC",
        outsideRth=True,
    )


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


def wait_for_order_execution(ib: IB, trade: Trade, timeout: int = 60) -> bool:
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
    ensure_no_short_position: bool,
):
    """
    Execute the trading logic based on the price difference between last traded price and current price using Decimal.
    """
    nearest_last_traded_price_in_grid = min(
        grid.keys(), key=lambda x: abs(x - last_traded_price)
    )
    buy_last_traded_grid, sell_last_traded_grid = get_current_grid_buy_and_sell_levels(
        nearest_last_traded_price_in_grid, grid, 1, current_pos, False
    )
    current_buy_level = min(buy_last_traded_grid.keys())
    current_sell_level = max(sell_last_traded_grid.keys())
    if current_price >= current_buy_level and current_price <= current_sell_level:
        logger.info(
            f"No catch-up trade required: current_price={current_price}, "
            f"current_buy_level={current_buy_level}, "
            f"current_sell_level={current_sell_level}"
        )
        return
    logger.info(
        f"Executing catch-up trade: current_price={current_price}, "
        f"current_buy_level={current_buy_level}, "
        f"current_sell_level={current_sell_level}"
    )
    cancel_all_orders(ib, stock_ticker.contract)
    # Calculate the number of levels and size
    action = "BUY" if current_price < last_traded_price else "SELL"
    trade_grid = determine_catch_up_trade_grid(
        current_price, nearest_last_traded_price_in_grid, grid
    )
    size = determine_max_size(current_pos, action, trade_grid, ensure_no_short_position)
    print("TRADE GRID: ", trade_grid)
    print("SIZE: ", size)
    execute_catch_up_trade_grid(ib, stock_ticker, timeout, action, trade_grid, size)
    return


def execute_catch_up_trade_grid(
    ib: IB,
    stock_ticker: Ticker,
    timeout: int,
    action: Literal["BUY", "SELL"],
    trade_grid: dict[Decimal, Decimal],
    size: Decimal,
):
    trade = None
    for price, level_size in trade_grid.items():
        if size <= Decimal(0):
            logger.info("No more orders to execute.")
            return

        trade = place_limit_order(ib, stock_ticker, action, size, price)
        if wait_for_order_execution(ib, trade, timeout):
            logger.info(
                f"Order executed: {trade.order.action} {trade.order.totalQuantity} @ {trade.order.lmtPrice}"
            )
            return
        logger.warning(
            f"Order failed to execute fully: {trade.order.action} {trade.order.totalQuantity} @ {trade.order.lmtPrice}"
        )
        ib.cancelOrder(trade.order)
        logger.info(
            f"Cancelled order: {trade.order.action} {trade.order.totalQuantity} @ {trade.order.lmtPrice}"
        )
        # Handle any remaining quantity
        size -= Decimal(trade.filled()) + level_size
    if trade:
        logger.warning(
            f"Order failed to execute fully: {trade.order.action} {trade.order.totalQuantity} @ {trade.order.lmtPrice}"
            f"\nRemaining size: {size}"
        )


def determine_max_size(
    current_pos: Decimal,
    action: Literal["BUY", "SELL"],
    trade_grid: dict[Decimal, Decimal],
    ensure_no_short_position: bool = True,
):
    size = sum(trade_grid.values())
    if ensure_no_short_position and action == "SELL":
        size = min(size, current_pos)
    return size


def determine_catch_up_trade_grid(
    current_price: Decimal,
    last_traded_price: Decimal,
    grid: dict[Decimal, Decimal],
) -> dict[Decimal, Decimal]:
    trade_grid = {}
    price_range = sorted(grid.keys())
    if current_price < last_traded_price:
        trade_grid = {
            price_range[idx]: grid[price_range[idx]]
            for idx in range(0, len(price_range))
            if price_range[idx] > current_price and price_range[idx] < last_traded_price
        }
        trade_grid = dict(sorted(trade_grid.items(), key=lambda x: x[0], reverse=False))
    if current_price > last_traded_price:
        trade_grid = {
            price_range[idx]: grid[price_range[idx - 1]]
            for idx in range(1, len(price_range))
            if price_range[idx] < current_price and price_range[idx] > last_traded_price
        }
        # sort grid with the highest price first
        trade_grid = dict(sorted(trade_grid.items(), key=lambda x: x[0], reverse=True))
    return trade_grid

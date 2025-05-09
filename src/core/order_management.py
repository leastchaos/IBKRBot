from typing import Literal
from ib_async import IB, Contract, LimitOrder, Ticker, Trade
import logging
from decimal import Decimal

from src.models.models import OCAOrder, OCAType

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


def execute_oca_orders(
    ib: IB,
    oca_orders: list[OCAOrder],
) -> dict[OCAOrder, Trade]:
    trades = {}
    for oca_order in oca_orders:
        trade = ib.placeOrder(oca_order.contract, oca_order.trade.order)
        trades[oca_order] = trade
    return trades


def create_oca_order(
    contract: Contract,
    action: Literal["BUY", "SELL"],
    size: Decimal,
    price: Decimal,
    oca_group: str,
    oca_type: OCAType,
) -> OCAOrder:
    return OCAOrder(
        contract=contract,
        trade=LimitOrder(
            action=action,
            totalQuantity=float(size),  # Convert Decimal to float for IB API
            lmtPrice=float(price),  # Convert Decimal to float for IB API
            tif="GTC",  # Good-Till-Cancelled
            outsideRth=True,  # Allow trading outside regular trading hours
            ocaGroup=oca_group,
            ocaType=oca_type.value,
        ),
    )


def round_to_tick(price: Decimal, tick_size: Decimal) -> Decimal:
    return round(price / tick_size) * tick_size


# === ASYNC FUNCTIONS ===

async def async_fetch_existing_orders(
    ib: IB, contract: Contract
) -> tuple[dict[Decimal, Trade], dict[Decimal, Trade]]:
    """Fetch existing open orders and categorize them into buy/sell orders."""
    buy_orders, sell_orders = {}, {}
    for order in await ib.reqAllOpenOrdersAsync():
        if order.contract.conId == contract.conId:
            price = Decimal(str(order.order.lmtPrice))
            (buy_orders if order.order.action == "BUY" else sell_orders)[price] = order
    return buy_orders, sell_orders


async def async_cancel_all_orders(ib: IB, contract: Contract) -> None:
    for order in await ib.reqAllOpenOrdersAsync():
        if order.contract.conId == contract.conId:
            ib.cancelOrder(order.order)
            logger.info(f"Canceled {order.order.action} order @ {order.order.lmtPrice}")

    logger.info(f"All orders in {contract.symbol} canceled.")



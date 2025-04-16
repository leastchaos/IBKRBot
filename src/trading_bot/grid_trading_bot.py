from ib_async import (
    IB,
    Fill,
    LimitOrder,
    Order,
    Ticker,
    Stock,
    Execution,
    ExecutionFilter,
    Trade,
)
import numpy as np
import logging
from logger_config import setup_logger
import os
import json
from dataclasses import dataclass
from datetime import datetime

# Logger setup
logger = logging.getLogger()


# Dataclass for trade records
@dataclass
class TradeRecord:
    exec_id: str
    price: float
    side: str
    timestamp: float
    con_id: int  # Added contract ID for multi-symbol support


def connect_to_ibkr(host: str, port: int, client_id: int, readonly: bool) -> IB:
    """Connect to Interactive Brokers."""
    ib = IB()
    ib.connect(host, port, client_id, readonly=readonly)
    return ib


def get_stock_ticker(
    ib: IB, symbol: str, exchange: str, currency: str
) -> Ticker | None:
    """Get stock ticker from IB."""
    contract = Stock(symbol, exchange, currency)
    if qualified := ib.qualifyContracts(contract):
        return ib.reqMktData(qualified[0], "101")
    return None


def load_trade_history(filename: str) -> list[TradeRecord]:
    """Load trade history from file."""
    if not os.path.exists(filename):
        return []
    with open(filename, "r") as f:
        data = json.load(f)
        return [TradeRecord(**entry) for entry in data]


def save_trade_history(filename: str, history: list[TradeRecord]) -> None:
    """Save trade history to file."""
    with open(filename, "w") as f:
        json.dump([vars(record) for record in history], f, indent=2)


def resolve_execution_conflict(
    backup_history: list[TradeRecord], ib_executions: list[Fill]
) -> list[TradeRecord]:
    """Resolve conflicts between local backup and IB executions."""
    if not ib_executions:
        return backup_history

    latest_ib = max(ib_executions, key=lambda e: e.time)
    latest_backup = (
        max(backup_history, key=lambda t: t.timestamp) if backup_history else None
    )

    if not latest_backup or latest_ib.execution.execId == latest_backup.exec_id:
        return [
            TradeRecord(
                exec_id=e.execution.execId,
                price=e.execution.price,
                side=e.execution.side,
                timestamp=e.execution.time.timestamp(),
                con_id=e.contract.conId,
            )
            for e in ib_executions
        ]

    # Conflict detected - prompt user
    print("Execution history conflict detected!")
    print(
        f"1. Keep backup (last: {datetime.fromtimestamp(latest_backup.timestamp)} @ {latest_backup.price})"
    )
    print(
        f"2. Use IB data (last: {latest_ib.execution.time} @ {latest_ib.execution.price})"
    )
    choice = input("Choose (1/2): ")
    return (
        backup_history
        if choice == "1"
        else [
            TradeRecord(
                exec_id=e.execution.execId,
                price=e.execution.price,
                side=e.execution.side,
                timestamp=e.execution.time.timestamp(),
                con_id=e.contract.conId,
            )
            for e in ib_executions
        ]
    )


def evaluate_risks(
    min_price: float,
    max_price: float,
    step_size: float,
    positions_per_level: int,
    ib: IB,
    stock_ticker: Ticker,
) -> None:
    """Evaluate trading risks."""
    num_levels = int((max_price - min_price) // step_size) + 1
    max_shares = num_levels * positions_per_level
    max_risk = max_shares * (max_price - min_price)

    historical_data = ib.reqHistoricalData(
        stock_ticker.contract, "", "14 D", "1 day", "TRADES", False
    )
    daily_atr = (
        np.mean([bar.high - bar.low for bar in historical_data])
        if historical_data
        else 0.0
    )

    logger.info(
        f"Risk Assessment:\n"
        f"Max Shares: {max_shares}\n"
        f"Max Risk: ${max_risk:.2f}\n"
        f"Daily ATR: ${daily_atr:.2f}\n"
        f"Estimated Daily Profit: ${daily_atr * positions_per_level / step_size:.2f}"
    )


def calculate_grid_levels(
    current_price: float,
    min_price: float,
    max_price: float,
    step_size: float,
    active_levels: int,
    last_traded_price: float | None,
) -> tuple[list[float], list[float]]:
    """Calculate buy and sell grid levels with cooldown logic."""
    price_range = np.arange(min_price, max_price + step_size, step_size)
    grid_index = np.searchsorted(price_range, current_price) - 1

    buy_prices = [
        price_range[idx]
        for i in range(1, active_levels + 1, -1)
        if (idx := grid_index - i) >= 0
    ]
    sell_prices = [
        price_range[idx]
        for i in range(1, active_levels + 1)
        if (idx := grid_index + i) < len(price_range)
    ]

    # Apply cooldown rules
    if last_traded_price is not None:
        buy_prices = [p for p in buy_prices if p != last_traded_price]
        sell_prices = [p for p in sell_prices if p != last_traded_price]

    return buy_prices, sell_prices


def cancel_out_of_range_orders(
    ib: IB,
    contract: Stock,
    buy_prices: list[float],
    sell_prices: list[float],
) -> None:
    """Cancel out-of-range orders."""
    valid_prices = set(buy_prices + sell_prices)
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
    contract: Stock,
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
                logger.info(f"Order exists: {action} {size} @ {price}")
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


def calculate_level_sizes(
    position_per_level: int,
    max_position_per_level: int,
    current_pos: int,
    position_step: int,
    step_size: float,
    current_price: float,
    max_price: float,
    min_price: float,
    active_levels: int,
) -> tuple[list[float], list[float]]:
    """Calculate size per level."""
    num_levels_above_price = int((max_price - current_price) // step_size)
    num_levels_below_price = int((current_price - min_price) // step_size)
    target_position = position_per_level * num_levels_above_price
    target_position_after_buy = target_position + position_per_level
    target_position_after_sell = target_position - position_per_level
    buy_size_per_level = (
        max(
            min(
                max_position_per_level,
                (target_position_after_buy - current_pos) // num_levels_below_price,
            ),
            position_per_level,
        )
        // position_step
        * position_step
    )

    sell_size_per_level = (
        max(
            min(
                max_position_per_level,
                (current_pos - target_position_after_sell) // num_levels_above_price,
            ),
            position_per_level,
        )
        // position_step
        * position_step
    )
    now_pos = current_pos
    sell_sizes = []
    for i in range(active_levels):
        now_pos -= sell_size_per_level
        if now_pos < 0:
            sell_sizes.append(0)
            continue
        sell_sizes.append(sell_size_per_level)
    buy_sizes = [buy_size_per_level] * active_levels
    logger.info(
        f"Current position: {current_pos}, Target position: {target_position}\n"
        f"Buy size per level: {buy_size_per_level}, Sell size per level: {sell_size_per_level}"
        f"\nBuy sizes: {buy_sizes}, Sell sizes: {sell_sizes}"
    )
    return buy_sizes, sell_sizes


def manage_orders(
    ib: IB,
    contract: Stock,
    buy_prices: list[float],
    sell_prices: list[float],
    buy_sizes: list[float],
    sell_sizes: list[float],
) -> None:
    """Manage buy and sell orders."""
    cancel_out_of_range_orders(ib, contract, buy_prices, sell_prices)

    buy_orders, sell_orders = {}, {}
    for order in ib.reqAllOpenOrders():
        if order.contract.conId == contract.conId:
            (buy_orders if order.order.action == "BUY" else sell_orders)[
                order.order.lmtPrice
            ] = order

    process_orders(
        ib=ib,
        contract=contract,
        action="BUY",
        prices=buy_prices,
        existing_orders=buy_orders,
        sizes=buy_sizes,
    )
    process_orders(
        ib=ib,
        contract=contract,
        action="SELL",
        prices=sell_prices,
        existing_orders=sell_orders,
        sizes=sell_sizes,
    )


def run_grid_bot(
    host: str,
    port: int,
    client_id: int,
    readonly: bool,
    symbol: str,
    exchange: str,
    currency: str,
    min_price: float = 60.0,
    max_price: float = 140.0,
    step_size: float = 0.5,
    position_per_level: int = 200,
    max_position_per_level: int = 1000,
    position_step: int = 100,
    active_levels: int = 5,
    loop_interval: int = 10,
    trade_history_file: str = "trade_history.json",
) -> None:
    """Run the grid trading bot."""
    ib = connect_to_ibkr(host, port, client_id, readonly)
    ib.reqMarketDataType(2)

    stock_ticker = get_stock_ticker(ib, symbol, exchange, currency)
    if not stock_ticker:
        raise ValueError("Failed to get stock ticker")

    # Load and reconcile trade history
    backup_history = load_trade_history(trade_history_file)
    ib_executions = ib.reqExecutions(ExecutionFilter(clientId=client_id, symbol=symbol))
    trade_history = resolve_execution_conflict(backup_history, ib_executions)

    # Initialize last traded prices per contract
    last_traded_prices: dict[int, float | None] = {}  # Track last traded price per contract

    for record in reversed(trade_history):
        con_id = record.con_id

        if record.side in ("BOT", "SLD"):
            last_traded_prices[con_id] = record.price
    logger.info(f"Last traded prices: {last_traded_prices}")
    evaluate_risks(
        min_price, max_price, step_size, position_per_level, ib, stock_ticker
    )

    try:
        while True:
            ib.sleep(loop_interval)
            if not (current_price := stock_ticker.marketPrice()):
                logger.warning("Invalid stock price")
                continue

            current_pos = next(
                (
                    pos.position
                    for pos in ib.positions()
                    if pos.contract.conId == stock_ticker.contract.conId
                ),
                0,
            )

            # Check for new executions
            new_executions = ib.reqExecutions(ExecutionFilter(clientId=client_id))
            for exec_report in new_executions:
                exec_id = exec_report.execution.execId
                con_id = exec_report.contract.conId
                if exec_id in [t.exec_id for t in trade_history if t.con_id == con_id]:
                    continue

                new_trade = TradeRecord(
                    exec_id=exec_id,
                    price=exec_report.execution.price,
                    side=exec_report.execution.side,
                    timestamp=exec_report.execution.time.timestamp(),
                    con_id=con_id,
                )
                trade_history.append(new_trade)
                if new_trade.side in ("BOT", "SLD"):
                    last_traded_prices[con_id] = new_trade.price

            save_trade_history(trade_history_file, trade_history)

            logger.info(
                f"Last traded price: {last_traded_prices.get(stock_ticker.contract.conId)}, "
                f"Current position: {current_pos}"
            )

            # Calculate grid levels
            buy_prices, sell_prices = calculate_grid_levels(
                current_price=current_price,
                min_price=min_price,
                max_price=max_price,
                step_size=step_size,
                active_levels=active_levels,
                last_traded_price=last_traded_prices.get(
                    stock_ticker.contract.conId
                ),  # Use last traded price
            )
            buy_sizes, sell_sizes = calculate_level_sizes(
                position_per_level=position_per_level,
                max_position_per_level=max_position_per_level,
                current_pos=current_pos,
                position_step=position_step,
                step_size=step_size,
                current_price=current_price,
                max_price=max_price,
                min_price=min_price,
                active_levels=active_levels,
            )
            # Manage orders
            manage_orders(
                ib=ib,
                contract=stock_ticker.contract,
                buy_prices=buy_prices,
                sell_prices=sell_prices,
                buy_sizes=buy_sizes,
                sell_sizes=sell_sizes,
            )
    finally:
        save_trade_history(trade_history_file, trade_history)


if __name__ == "__main__":
    setup_logger(logging.INFO)
    run_grid_bot(
        host="127.0.0.1",
        port=7497,
        client_id=200,
        readonly=False,
        symbol="BABA",
        exchange="SMART",
        currency="USD",
        min_price=60.0,
        max_price=140.0,
        step_size=5,
        position_per_level=10,
        max_position_per_level=20,
        position_step=1,
        active_levels=5,
        loop_interval=10,
        trade_history_file="trade_history.json",
    )

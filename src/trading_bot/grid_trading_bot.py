from ib_async import ExecutionFilter
from ib_connector import connect_to_ibkr, get_stock_ticker
from logger_config import setup_logger
from trade_history import (
    check_for_new_executions,
    load_trade_history,
    save_trade_history,
    resolve_execution_conflict,
)
from grid_calculations import (
    calculate_grid_levels,
    calculate_grid_sizes,
    evaluate_risks,
)
from order_management import execute_catch_up_trade, manage_orders
from decimal import Decimal, getcontext

# Set global precision for Decimal
getcontext().prec = 6  # Adjust precision as needed

logger = setup_logger()


def run_grid_bot(
    host: str,
    port: int,
    client_id: int,
    readonly: bool,
    symbol: str,
    exchange: str,
    currency: str,
    min_price: Decimal,
    max_price: Decimal,
    step_size: Decimal,
    position_per_level: int,
    max_position_per_level: int,
    position_step: int,
    active_levels: int,
    loop_interval: int,
    trade_history_file: str = "trade_history.json",
    req_market_data_type: int = 1,
) -> None:
    """Run the grid trading bot using Decimal."""

    ib = connect_to_ibkr(host, port, client_id, readonly)
    ib.reqMarketDataType(req_market_data_type)
    stock_ticker = get_stock_ticker(ib, symbol, exchange, currency)
    if not stock_ticker:
        raise ValueError("Failed to get stock ticker")

    # Load and reconcile trade history
    backup_history = load_trade_history(trade_history_file)
    ib_executions = ib.reqExecutions(ExecutionFilter(clientId=client_id, symbol=symbol))
    trade_history = resolve_execution_conflict(backup_history, ib_executions)

    # Initialize last traded prices per contract
    last_traded_prices: dict[int, Decimal | None] = {}
    for record in trade_history:
        con_id = record.con_id
        last_traded_prices[con_id] = Decimal(str(record.price))
    logger.info(f"Last traded prices: {last_traded_prices}")

    # Evaluate risks
    evaluate_risks(
        min_price=min_price,
        max_price=max_price,
        step_size=step_size,
        positions_per_level=position_per_level,
        ib=ib,
        stock_ticker=stock_ticker,
    )

    # Get current price
    if not (current_price := stock_ticker.marketPrice()):
        raise ValueError("Invalid stock price at initialization")
    current_price = Decimal(str(current_price))

    last_traded_price = last_traded_prices.get(stock_ticker.contract.conId)
    # Catch up trades
    execute_catch_up_trade(
        ib=ib,
        stock_ticker=stock_ticker,
        last_traded_price=last_traded_price,
        current_price=current_price,
        active_levels=active_levels,
        step_size=step_size,
        position_per_level=position_per_level,
    )

    try:
        while True:
            ib.sleep(loop_interval)
            if not (current_price := stock_ticker.marketPrice()):
                logger.warning("Invalid stock price")
                continue
            current_price = Decimal(str(current_price))

            current_pos = next(
                (
                    pos.position
                    for pos in ib.positions()
                    if pos.contract.conId == stock_ticker.contract.conId
                ),
                0,
            )
            current_pos = Decimal(str(current_pos))

            # Check for new executions
            new_trades = check_for_new_executions(ib, client_id, trade_history)
            for new_trade in new_trades:
                trade_history.append(new_trade)
                last_traded_prices[new_trade.con_id] = Decimal(str(new_trade.price))
            save_trade_history(trade_history_file, trade_history)

            logger.info(
                f"Last traded price: {last_traded_prices.get(stock_ticker.contract.conId)}, "
                f"Current position: {current_pos}"
            )

            last_traded_price = last_traded_prices.get(stock_ticker.contract.conId)
            # Calculate grid levels
            buy_prices, sell_prices = calculate_grid_levels(
                current_price=last_traded_price or current_price,
                min_price=min_price,
                max_price=max_price,
                step_size=step_size,
                active_levels=active_levels,
            )

            buy_sizes, sell_sizes = calculate_grid_sizes(
                position_per_level=position_per_level,
                max_position_per_level=max_position_per_level,
                current_pos=current_pos,
                position_step=position_step,
                step_size=step_size,
                current_price=last_traded_price or current_price,
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
                step_size=step_size,
            )
    finally:
        save_trade_history(trade_history_file, trade_history)


if __name__ == "__main__":
    run_grid_bot(
        host="127.0.0.1",
        port=7497,
        client_id=200,
        readonly=False,
        symbol="BABA",
        exchange="SMART",
        currency="USD",
        min_price=Decimal("60.0"),
        max_price=Decimal("160.0"),
        step_size=Decimal("0.1"),
        position_per_level=10,
        max_position_per_level=20,
        position_step=1,
        active_levels=5,
        loop_interval=10,
        trade_history_file="trade_history.json",
        req_market_data_type=2,
    )
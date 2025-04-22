from pprint import pprint
import random
from ib_async import ExecutionFilter
from ib_connector import connect_to_ibkr, get_current_position, get_stock_ticker
from logger_config import setup_logger
from trade_history import (
    check_for_new_executions,
    load_trade_history,
    save_trade_history,
    resolve_execution_conflict,
)
from grid_calculations import (
    generate_grid,
    get_current_grid_buy_and_sell_levels,
)
from order_management import execute_catch_up_trade, manage_orders
from decimal import Decimal, getcontext

from notifications import send_email_alert
from evaluate_risk import evaluate_risks, get_historical_data, evaluate_risks

# Set global precision for Decimal


logger = setup_logger()


def run_grid_bot(
    host: str,
    port: int,
    client_id: int,
    readonly: bool,
    account: str,
    symbol: str,
    exchange: str,
    currency: str,
    min_price: Decimal,
    max_price: Decimal,
    step_size: Decimal,
    min_percentage_step: Decimal,
    start_value_at_min_price: Decimal,
    add_value_per_level: Decimal,
    min_position_per_level: Decimal,
    position_step: int,
    active_levels: int,
    loop_interval: int,
    catchup_trade_interval: int,
    trade_history_file: str = "trade_history.json",
    req_market_data_type: int = 1,
    decimal_precision: int = 6,
    fee_per_trade: Decimal = Decimal("3"),
    slippage_per_trade: Decimal = Decimal("0.01"),
    ensure_no_short_position: bool = True,
) -> None:
    """Run the grid trading bot using Decimal."""
    getcontext().prec = decimal_precision  # Adjust precision as needed
    ib = connect_to_ibkr(host, port, client_id, readonly, account)
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

    grid = generate_grid(
        min_price=min_price,
        max_price=max_price,
        step_size=step_size,
        min_percentage_step=min_percentage_step,
        start_value_at_min_price=start_value_at_min_price,
        add_value_per_level=add_value_per_level,
        position_step=position_step,
        min_position_per_level=min_position_per_level,
    )
    historical_data = get_historical_data(ib, stock_ticker, "30 D", "1 min")
    # risks = evaluate_risks(
    #     grid=grid,
    #     ticker=stock_ticker,
    #     historical_data=historical_data,
    #     fee_per_trade=fee_per_trade,
    #     slippage_per_trade=slippage_per_trade,
    # )
    # pprint(risks)
    if not (current_price := stock_ticker.marketPrice()):
        raise ValueError("Invalid stock price at initialization")
    if current_price == float("nan"):
        raise ValueError(f"Invalid stock price at initialization: {current_price}")
    logger.info(f"Current price: {current_price}")
    current_price = Decimal(str(current_price))  # Decimal(str(110.5))

    last_traded_price = last_traded_prices.get(
        stock_ticker.contract.conId, current_price
    )
    current_pos = get_current_position(ib, stock_ticker)

    # Catch up trades
    execute_catch_up_trade(
        ib=ib,
        stock_ticker=stock_ticker,
        last_traded_price=last_traded_price,
        current_price=current_price,
        grid=grid,
        timeout=catchup_trade_interval,
        current_pos=current_pos,
        ensure_no_short_position=ensure_no_short_position,
    )

    try:
        while True:
            ib.sleep(loop_interval)
            if not (current_price := stock_ticker.marketPrice()):
                logger.warning("Invalid stock price")
                continue
            print(stock_ticker.ask)
            logger.info(f"Current price: {current_price}")
            current_price = Decimal(str(current_price))  # Decimal(str(110.5))

            current_pos = get_current_position(ib, stock_ticker)

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

            last_traded_price = last_traded_prices.get(
                stock_ticker.contract.conId, current_price
            )
            # Calculate grid levels
            buy_levels, sell_levels = get_current_grid_buy_and_sell_levels(
                last_traded_price=last_traded_price,
                grid=grid,
                active_levels=active_levels,
                current_position=current_pos,
                ensure_no_short_position=ensure_no_short_position,
            )
            # Manage orders
            manage_orders(
                ib=ib,
                contract=stock_ticker.contract,
                buy_levels=buy_levels,
                sell_levels=sell_levels,
            )

            logger.info(
                "-------------------------------------------------------------------------------------------------"
            )
    finally:
        save_trade_history(trade_history_file, trade_history)
        send_email_alert(
            subject="Grid Trading Bot Stopped",
            body="Grid Trading Bot stopped successfully",
        )


if __name__ == "__main__":
    run_grid_bot(
        host="127.0.0.1",
        port=7497,
        client_id=200,
        account="",
        readonly=True,
        symbol="BABA",
        exchange="SMART",
        currency="USD",
        min_price=Decimal("60"),
        max_price=Decimal("180"),
        step_size=Decimal("0.2"),
        min_percentage_step=Decimal("0"),
        start_value_at_min_price=Decimal("4000"),
        add_value_per_level=Decimal("-200"),
        min_position_per_level=Decimal("5"),
        position_step=Decimal("1"),
        active_levels=5,
        loop_interval=10,
        catchup_trade_interval=60,
        trade_history_file="trade_history.json",
        req_market_data_type=2,
        ensure_no_short_position=True,
    )

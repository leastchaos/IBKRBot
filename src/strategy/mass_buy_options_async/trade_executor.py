import asyncio
from decimal import Decimal
from ib_async import IB, Contract, LimitOrder, Stock, Ticker, Trade
from src.core.ib_connector import (
    async_get_option_ticker_from_contract,
    async_get_options,
    async_get_stock_ticker,
    get_current_position,
    get_options,
    get_stock_ticker,
    get_option_ticker_from_contract,
    wait_for_subscription,
)
from src.core.order_management import execute_oca_orders
from src.models.models import Action, OCAOrder
from src.strategy.mass_buy_options_async.config import TradingConfig
from src.strategy.mass_buy_options_async.order_utils import (
    check_if_price_too_far,
    manage_open_order,
)
from src.strategy.mass_buy_options_async.price_utils import determine_price
import logging

logger = logging.getLogger()
OPTION_TIMEOUT = 1


async def _prepare_options(
    ib: IB, stock: Stock, config: TradingConfig
) -> list[Contract]:
    """Prepare and filter options based on config parameters."""
    [stock] = await ib.qualifyContractsAsync(stock)
    return await async_get_options(
        ib,
        stock,
        [config.right],
        config.min_dte,
        config.max_dte,
        config.min_strike,
        config.max_strike,
    )


def _should_skip_option(exec_ib: IB, option: Trade, config: TradingConfig) -> bool:
    """Determine if option should be skipped based on position requirements."""
    if not config.close_positions_only:
        return False

    current_pos = get_current_position(exec_ib, option.contract)
    return (config.action == Action.SELL and current_pos <= 0) or (
        config.action == Action.BUY and current_pos >= 0
    )


async def _calculate_price(
    ib: IB,
    stock_ticker: Ticker,
    option_ticker: Ticker,
    config: TradingConfig,
    trade: Trade | None,
) -> Decimal:
    """Calculate appropriate price for order placement."""
    price = await determine_price(ib, stock_ticker, option_ticker, config, trade)
    if price < Decimal("0"):
        return (
            Decimal(str(option_ticker.contract.strike))
            if config.action == Action.SELL
            else option_ticker.minTick
        )
    return price


def _create_limit_order(
    account: str,
    price: Decimal,
    config: TradingConfig,
) -> LimitOrder:
    """Create configured limit order."""
    return LimitOrder(
        action=config.action.value,
        totalQuantity=float(config.size),
        lmtPrice=price,
        outsideRth=True,
        ocaGroup=config.oca_group,
        ocaType=config.oca_type.value,
        tif="Day",
        account=account,
        transmit=False,
    )


def _place_and_transmit_order(ib: IB, option: Contract, order: LimitOrder) -> Trade:
    """Place and transmit order to IB. set transmit to True so that next order will then be transmitted"""
    placed_order = ib.placeOrder(option, order)
    placed_order.order.transmit = True
    return placed_order


def _wait_for_user_confirmation(ib: IB, oca_orders: list[OCAOrder]) -> bool:
    """Wait for user confirmation to proceed with orders."""
    try:
        input("Review orders and press Enter to continue...")
        return True
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt detected. Canceling orders...")
        for oca in oca_orders:
            ib.cancelOrder(oca.trade)
        return False


async def _monitor_order(
    ib: IB, exec_ib: IB, stock_ticker: Ticker, config: TradingConfig, order: Trade
):
    option_ticker = get_option_ticker_from_contract(ib, order.contract, OPTION_TIMEOUT)
    while True:
        if order.isDone():
            return
        await manage_open_order(ib, exec_ib, order, stock_ticker, option_ticker, config)
        await asyncio.sleep(config.loop_interval)


async def process_option(
    ib: IB,
    exec_ib: IB,
    stock_ticker: Ticker,
    config: TradingConfig,
    option: Contract,
) -> OCAOrder | None:
    option_ticker = await async_get_option_ticker_from_contract(
        ib, option, OPTION_TIMEOUT
    )
    if _should_skip_option(exec_ib, option, config):
        return None

    price = await _calculate_price(ib, stock_ticker, option_ticker, config, None)
    if await check_if_price_too_far(
        ib, option_ticker, config, stock_ticker.marketPrice()
    ):
        return None

    order = _create_limit_order(exec_ib.account, price, config)
    trade = _place_and_transmit_order(exec_ib, option, order)

    return OCAOrder(option, trade)
    


async def mass_trade_oca_option(
    ib: IB, exec_ib: IB, stock: Stock, config: TradingConfig
) -> None:
    """Execute mass trading of options with OCA logic."""
    options = await _prepare_options(ib, stock, config)
    stock_ticker = await async_get_stock_ticker(
        ib, stock.symbol, stock.exchange, stock.currency
    )
    tasks = [
        process_option(ib, exec_ib, stock_ticker, config, option)
        for option in options
    ]
    results = await asyncio.gather(*tasks)
    oca_orders = [result for result in results if result is not None]
    if not _wait_for_user_confirmation(ib, oca_orders):
        return

    active_orders = execute_oca_orders(exec_ib, oca_orders)
    active_tasks: list[asyncio.Task] = []
    for trade in active_orders.values():
        active_tasks.append(
            asyncio.create_task(
                _monitor_order(ib, exec_ib, stock_ticker, config, trade)
            )
        )

    await asyncio.gather(*active_tasks)

    for task in active_tasks:
        task.cancel()

    for trade in active_orders.values():
        ib.cancelOrder(trade)

    logger.info(f"All orders in {stock.symbol} executed.")


if __name__ == "__main__":
    from src.core.ib_connector import async_connect_to_ibkr
    from src.utils.logger_config import setup_logger

    setup_logger()

    async def main():
        ib = await async_connect_to_ibkr(
            "127.0.0.1", 7496, 666, readonly=True, account=""
        )
        ib.reqMarketDataType(1)
        await mass_trade_oca_option(
            ib,
            ib,
            Stock(
                symbol="TSLA",
                exchange="SMART",
                currency="USD",
            ),
            TradingConfig.generate_test_config(),
        )

    asyncio.run(main())

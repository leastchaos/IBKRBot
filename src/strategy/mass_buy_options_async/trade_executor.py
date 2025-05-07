from decimal import Decimal
from ib_async import IB, LimitOrder, Stock, Trade
from src.core.ib_connector import (
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

OPTION_TIMEOUT = 1


def mass_trade_oca_option(
    ib: IB, exec_ib: IB, stock: Stock, config: TradingConfig
) -> None:
    """Execute mass trading of options with OCA logic."""
    options = get_options(
        ib,
        stock,
        [config.right],
        config.min_dte,
        config.max_dte,
        config.min_strike,
        config.max_strike,
    )
    stock_ticker = get_stock_ticker(ib, stock.symbol, stock.exchange, stock.currency)
    oca_orders = []

    for option in options:
        option_ticker = get_option_ticker_from_contract(ib, option, OPTION_TIMEOUT)

        if config.close_positions_only:
            current_pos = get_current_position(exec_ib, option_ticker.contract)
            if (config.action == Action.SELL and current_pos <= 0) or (
                config.action == Action.BUY and current_pos >= 0
            ):
                continue

        price = determine_price(ib, stock_ticker, option_ticker, config.action, config)
        if price < Decimal("0"):
            price = (
                Decimal(str(option_ticker.contract.strike))
                if config.action == Action.SELL
                else option_ticker.minTick
            )

        if check_if_price_too_far(
            config.action, option_ticker, config, stock_ticker.marketPrice()
        ):
            continue

        order = LimitOrder(
            action=config.action.value,
            totalQuantity=float(config.size),
            lmtPrice=price,
            outsideRth=True,
            ocaGroup=config.oca_group,
            ocaType=config.oca_type.value,
            tif="Day",
            account=exec_ib.account,
            transmit=False,
        )
        placed_order = exec_ib.placeOrder(option, order)
        placed_order.order.transmit = True
        oca_orders.append(OCAOrder(contract=option, order=placed_order))

    try:
        input("Review orders and press Enter to continue...")
    except KeyboardInterrupt:
        for oca in oca_orders:
            exec_ib.cancelOrder(oca.order)
        return

    active_orders = execute_oca_orders(exec_ib, oca_orders)
    try:
        while True:
            for order in active_orders.values():
                if order.isDone():
                    for o in active_orders.values():
                        exec_ib.cancelOrder(o.order)
                    return
                ticker = get_option_ticker_from_contract(ib, order.contract, 0)
                manage_open_order(ib, exec_ib, order, stock_ticker, ticker, config)
            ib.sleep(config.loop_interval)
    finally:
        for o in active_orders.values():
            exec_ib.cancelOrder(o.order)

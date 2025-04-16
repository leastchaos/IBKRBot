from enum import Enum
from typing import Literal, Optional, Dict
from ib_async import IB, LimitOrder, Order, Ticker, Stock, Option, DOMLevel
import numpy as np
from scipy.stats import norm
import datetime
import logging
from logger_config import setup_logger
from dataclasses import dataclass
from py_vollib.black_scholes import black_scholes


logger = logging.getLogger()


class Action(Enum):
    BUY = "BUY"
    SELL = "SELL"


class Right(Enum):
    CALL = "C"
    PUT = "P"


@dataclass
class VolatilityCache:
    value: Optional[float] = None
    timestamp: Optional[datetime.datetime] = None


def get_effective_volatility(
    option_ticker: Ticker,
    volatility_cache: VolatilityCache,
    default_volatility: float,
    max_age_seconds: int,
) -> float:
    """Get valid volatility value with caching and fallback logic"""
    current_iv = option_ticker.impliedVolatility
    now = datetime.datetime.now()

    if current_iv:
        volatility_cache.value = current_iv
        volatility_cache.timestamp = now
        logger.debug(f"IV updated to {current_iv:.2%}")
        return current_iv

    if not volatility_cache.value:
        logger.warning(f"No IV available, using default {default_volatility:.2%}")
        return default_volatility

    cache_age = (now - volatility_cache.timestamp).total_seconds()
    if cache_age > max_age_seconds:
        logger.warning(f"IV cache expired ({cache_age:.0f}s old), using default")
        return default_volatility

    logger.debug(
        f"Using cached IV: {volatility_cache.value:.2%} ({cache_age:.0f}s old)"
    )
    return volatility_cache.value


def calculate_price_level(
    theoretical_price: float,
    min_range: float,
    max_range: float,
    depth_price: float,
    is_bid: bool,
    rounding: int,
) -> float:
    """Calculate and round bid/ask price level with consistent logic"""
    closest = theoretical_price - min_range if is_bid else theoretical_price + min_range
    furthest = (
        theoretical_price - max_range if is_bid else theoretical_price + max_range
    )

    price = min(closest, depth_price) if is_bid else max(closest, depth_price)
    price = furthest if depth_price == -1 else price

    return round(price, rounding)


def connect_to_ibkr(host: str, port: int, client_id: int, readonly: bool) -> IB:
    ib = IB()
    ib.connect(host, port, client_id, readonly=readonly)
    return ib


def get_stock_ticker(
    ib: IB, symbol: str, exchange: str, currency: str
) -> Optional[Ticker]:
    contract = Stock(symbol, exchange, currency)
    if qualified := ib.qualifyContracts(contract):
        return ib.reqMktData(qualified[0], "101")
    return None


def get_option_ticker(
    ib: IB, symbol: str, expiry: str, strike: float, right: Right, exchange: str
) -> Optional[Ticker]:
    contract = Option(symbol, expiry, strike, right.value, exchange)
    if qualified := ib.qualifyContracts(contract):
        return ib.reqMktData(qualified[0], "106")
    return None


def get_option_depth(
    ib: IB, symbol: str, expiry: str, strike: float, right: Right, exchange: str
) -> Optional[Ticker]:
    contract = Option(symbol, expiry, strike, right.value, exchange)
    if qualified := ib.qualifyContracts(contract):
        return ib.reqMktDepth(qualified[0])
    return None


def calculate_theoretical_price(
    stock_price: float,
    strike: float,
    right: Right,
    expiry: str,
    volatility: float,
    risk_free_rate: float,
    dividend_yield: float,
) -> float:

    time_to_exp = (
        datetime.datetime.strptime(expiry, "%Y%m%d") - datetime.datetime.now()
    ).days / 365.25
    adjusted_rate = risk_free_rate - dividend_yield
    return black_scholes(
        flag="c" if right == Right.CALL else "p",
        S=stock_price,
        K=strike,
        t=time_to_exp,
        r=adjusted_rate,
        sigma=volatility,
    )


def get_own_orders(ib: IB, con_id: int) -> dict[float, float]:
    return {
        order.order.lmtPrice: order.order.totalQuantity
        for order in ib.reqAllOpenOrders()
        if order.contract.conId == con_id
    }


def get_depth_price(
    own_orders: dict, dom_levels: list[DOMLevel], target_depth: int
) -> float:
    cum_depth = 0.0
    for level in dom_levels:
        available = level.size - own_orders.get(level.price, 0)
        if available <= 0:
            continue
        if cum_depth + available >= target_depth:
            return level.price
        cum_depth += available
    return -1


def run_market_making_bot(
    # Connection parameters
    host: str,
    port: int,
    client_id: int,
    readonly: bool,
    # Market data parameters
    symbol: str,
    exchange: str,
    currency: str,
    expiry: str,
    strike: float,
    right: Right,
    # Pricing parameters
    risk_free_rate: float,
    dividend_yield: float,
    # Trading parameters
    min_range: float,
    max_range: float,
    order_depth: int,
    rounding: int,
    # Volatility settings
    default_volatility: float = 0.4,  # 20% default IV
    max_volatility_age: int = 300,  # seconds
    # Loop settings
    loop_interval: int = 5,
    # Positions settings
    max_positions_per_level: int = 1,
    min_positions: int = 1,
    position_size: float = 1.0,
    min_price: float = 13.0,
    max_price: float = 23.0,
    step_size: float = 1.0,
):
    ib = connect_to_ibkr(host, port, client_id, readonly)

    stock_ticker = get_stock_ticker(ib, symbol, exchange, currency)
    option_ticker = get_option_ticker(ib, symbol, expiry, strike, right, exchange)
    option_depth = get_option_depth(ib, symbol, expiry, strike, right, exchange)

    if not all([stock_ticker, option_ticker, option_depth]):
        raise RuntimeError("Failed to initialize market data")

    volatility_cache: VolatilityCache = VolatilityCache()

    while True:
        ib.sleep(loop_interval)
        min_sell_price = get_last_bought_price(ib, option_ticker)
        if not (stock_price := stock_ticker.marketPrice()):
            logger.warning("Invalid stock price")
            continue

        if not (option_price := option_ticker.marketPrice()):
            logger.warning("Invalid option price")
            continue

        volatility = get_effective_volatility(
            option_ticker, volatility_cache, default_volatility, max_volatility_age
        )

        theoretical_price = calculate_theoretical_price(
            stock_price,
            strike,
            right,
            expiry,
            volatility,
            risk_free_rate,
            dividend_yield,
        )
        logger.info(
            f"Theoretical price: {theoretical_price:.2f}, "
            f"Stock: {stock_price:.2f}, IV: {volatility:.2%}, "
        )

        own_orders = get_own_orders(ib, option_ticker.contract.conId)

        bid_depth_price = get_depth_price(own_orders, option_depth.domBids, order_depth)
        ask_depth_price = get_depth_price(own_orders, option_depth.domAsks, order_depth)

        # Calculate and round prices in one step
        bid_price = calculate_price_level(
            theoretical_price,
            min_range,
            max_range,
            bid_depth_price,
            is_bid=True,
            rounding=rounding,
        )
        ask_price = calculate_price_level(
            theoretical_price,
            min_range,
            max_range,
            ask_depth_price,
            is_bid=False,
            rounding=rounding,
        )
        if ask_price < min_sell_price + min_range:
            ask_price = min_sell_price + min_range

        logger.info(f"Bid: {bid_price:.2f}, Ask: {ask_price:.2f}")
        position = 0
        current_position = [
            pos
            for pos in ib.positions()
            if pos.contract.conId == option_ticker.contract.conId
        ]
        if current_position:
            position = current_position[0].position

        max_position = (
            round(
                (max_price - max(min(max_price, option_price), min_price))
                / step_size
                * max_positions_per_level
            ,0)
            + min_positions
        )
        logger.info(f"Position: {position}, " f"Max position: {max_position}, ")
        buy_position = max_position - position
        sell_position = position

        if buy_position > 0:
            buy_order = LimitOrder("BUY", position_size, bid_price)
            logger.info(f"Placing buy order: {buy_order}")
        if sell_position > 0:
            sell_order = LimitOrder("SELL", position_size, ask_price)
            logger.info(f"Placing sell order: {sell_order}")


def get_last_bought_price(ib: IB, option_ticker: Ticker) -> Optional[float]:
    positions = [
        fill.execution
        for fill in ib.reqExecutions()
        if fill.contract.conId == option_ticker.contract.conId
    ]
    # sort positions by latest first
    positions.sort(
        key=lambda pos: pos.time,
        reverse=True,
    )
    min_sell_price = None
    if positions and positions[0].side == "BOT":
        min_sell_price = positions[0].price
    logger.info(f"last bought price: {min_sell_price}")
    return min_sell_price


# po

if __name__ == "__main__":
    setup_logger(logging.INFO)

    run_market_making_bot(
        # Connection
        host="127.0.0.1",
        port=7496,
        client_id=999,
        readonly=True,
        # Market data
        symbol="9988",
        exchange="SEHK",
        currency="HKD",
        expiry="20260330",
        strike=112.5,
        right=Right.CALL,
        # Pricing
        risk_free_rate=0.057,
        dividend_yield=0.01,
        # Trading
        min_range=0.5,
        max_range=5,
        order_depth=29,
        rounding=2,
        # Volatility
        default_volatility=0.20,
        max_volatility_age=300,
    )

from enum import Enum
from typing import Literal
from ib_async import IB, Ticker, Stock, Option, LimitOrder, Order, DOMLevel
import numpy as np
from scipy.stats import norm
import datetime
import logging

from logger_config import setup_logger


logger = logging.getLogger()


class Action(Enum):
    BUY = "BUY"
    SELL = "SELL"


class Right(Enum):
    CALL = "C"
    PUT = "P"


# Connect to IBKR
def connect_to_ibkr(host="127.0.0.1", port=7496, clientId=1000, readonly=False):
    ib = IB()
    ib.connect(host, port, clientId, readonly=readonly)
    return ib


# Fetch underlying stock price
def get_stock_ticker(
    ib: IB, symbol: str, exchange: str = "", currency: str = ""
) -> Ticker:
    [contract] = ib.qualifyContracts(Stock(symbol, exchange, currency))
    stock_ticker = ib.reqMktData(contract, "101")
    return stock_ticker


def get_option_ticker(
    ib: IB,
    symbol: str,
    expiry: str,
    strike: float,
    right: Literal["C", "P"],
    exchange: str,
) -> Ticker | None:
    option = Option(symbol, expiry, strike, right, exchange)
    contracts = ib.qualifyContracts(option)
    if not contracts:
        return None
    [contract] = contracts
    return ib.reqMktData(contract, "106")


def get_option_ticker_level_2(
    ib: IB,
    symbol: str,
    expiry: str,
    strike: float,
    right: Literal["C", "P"],
    exchange: str,
) -> Ticker | None:
    option = Option(symbol, expiry, strike, right, exchange)
    contracts = ib.qualifyContracts(option)
    if not contracts:
        return None
    [contract] = contracts
    return ib.reqMktDepth(contract)


# Black-Scholes pricing model
def calculate_option_price(
    stock_price: float,
    strike_price: float,
    time_to_expiration_in_years: float,
    risk_free_interest_rate: float,  # subtract dividend yield
    volatility: float,
    right: Right,
):
    d1 = (
        np.log(stock_price / strike_price)
        + (risk_free_interest_rate + 0.5 * volatility**2) * time_to_expiration_in_years
    ) / (volatility * np.sqrt(time_to_expiration_in_years))
    d2 = d1 - volatility * np.sqrt(time_to_expiration_in_years)
    if right == Right.CALL.value:
        return stock_price * norm.cdf(d1) - strike_price * np.exp(
            -risk_free_interest_rate * time_to_expiration_in_years
        ) * norm.cdf(d2)
    return strike_price * np.exp(
        -risk_free_interest_rate * time_to_expiration_in_years
    ) * norm.cdf(-d2) - stock_price * norm.cdf(-d1)


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


# Main function to run the bot
def run_market_making_bot(
    symbol: str,
    expiry: str,
    strike: float,
    right: Right,
    exchange: str,
    min_range: float,
    max_range: float,
    order_depth: int,
    risk_free_rate: float,
    dividend_yield: float,
    rounding: int,
    disable_uncovered_short: bool = True,
):
    # Parameters
    adjusted_risk_free_rate = risk_free_rate - dividend_yield

    ib = connect_to_ibkr(clientId=999, readonly=True)
    stock = get_stock_ticker(ib, symbol)
    option = get_option_ticker(ib, symbol, expiry, strike, right, exchange)
    option_depth = get_option_ticker_level_2(
        ib, symbol, expiry, strike, right, exchange
    )
    if not stock or not option or not option_depth:
        raise Exception("Failed to fetch stock or option data.")
    while True:
        ib.sleep(5)
        stock_price = stock.marketPrice()
        if not stock_price:
            logger.warning("Failed to fetch stock price.")
            continue
        time_to_expiration_in_years = (
            datetime.datetime.strptime(expiry, "%Y%m%d") - datetime.datetime.now()
        ).days / 365.25
        theoretical_option_price = calculate_option_price(
            stock.marketPrice(),
            strike,
            time_to_expiration_in_years,
            adjusted_risk_free_rate,
            option.impliedVolatility,
            right,
        )
        logging.info(
            f"Stock price: {stock_price}, Option price: {theoretical_option_price}, "
            f"time_to_expiration_in_years: {time_to_expiration_in_years}, "
            f"implied_volatility: {option.impliedVolatility}, "
            f"option_price: {theoretical_option_price}"
        )
        # get own orders in the same contract
        own_orders = ib.reqAllOpenOrders()
        own_order_bids = {}
        for order in own_orders:
            if (
                order.contract.conId == option.contract.conId
                and order.order.action == Action.BUY.value
            ):
                limit_price = order.order.lmtPrice
                own_order_bids[limit_price] = (
                    own_order_bids.get(limit_price, 0) + order.order.totalQuantity
                )
        bid_depth_price = get_depth_price(
            own_order_bids, option_depth.domBids, order_depth
        )
        own_order_asks = {}
        for order in own_orders:
            if order.contract.conId == option.contract.conId:
                if order.order.action == Action.SELL.value:
                    limit_price = order.order.lmtPrice
                    own_order_asks[limit_price] = (
                        own_order_asks.get(limit_price, 0) + order.order.totalQuantity
                    )

        ask_depth_price = get_depth_price(
            own_order_asks, option_depth.domAsks, order_depth
        )
        logging.info(
            f"bid_depth_price: {bid_depth_price}, ask_depth_price: {ask_depth_price}"
        )

        closest_bid_price = theoretical_option_price - min_range
        furthest_bid_price = theoretical_option_price - max_range
        closest_ask_price = theoretical_option_price + min_range
        furthest_ask_price = theoretical_option_price + max_range
        logging.info(
            f"closest_bid_price: {closest_bid_price}, furthest_bid_price: {furthest_bid_price}, "
            f"closest_ask_price: {closest_ask_price}, furthest_ask_price: {furthest_ask_price}"
        )
        bid_price = furthest_bid_price
        if bid_depth_price != -1:
            bid_price = min(closest_bid_price, bid_depth_price)
        ask_price = furthest_ask_price
        if ask_depth_price != -1:
            ask_price = max(closest_ask_price, ask_depth_price)

        bid_price = round(bid_price, rounding)
        ask_price = round(ask_price, rounding)
        logging.info(f"bid_price: {bid_price}, ask_price: {ask_price}")

        ib.sleep(1)


# Run the bot
if __name__ == "__main__":
    setup_logger(logging.INFO)
    run_market_making_bot(
        symbol="9988",
        expiry="20260330",
        strike=112.5,
        right="C",
        sides=[Action.BUY, Action.SELL],
        exchange="",
        currency="HKD",
        min_range=0.5,
        max_range=5,
        order_depth=29,
        risk_free_rate=0.057,
        dividend_yield=0.01,
        rounding=2,
    )

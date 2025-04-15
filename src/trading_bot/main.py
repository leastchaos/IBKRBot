from enum import Enum
from typing import Literal, Optional
from ib_async import IB, Ticker, Stock, Option, DOMLevel
import numpy as np
from scipy.stats import norm
import datetime
import logging
from logger_config import setup_logger

logger = setup_logger()

class Action(Enum):
    BUY = "BUY"
    SELL = "SELL"

class Right(Enum):
    CALL = "C"
    PUT = "P"

def connect_to_ibkr(host: str, port: int, client_id: int, readonly: bool) -> IB:
    ib = IB()
    ib.connect(host, port, client_id, readonly=readonly)
    return ib

def get_stock_ticker(ib: IB, symbol: str, exchange: str, currency: str) -> Optional[Ticker]:
    contract = Stock(symbol, exchange, currency)
    if qualified := ib.qualifyContracts(contract):
        return ib.reqMktData(qualified[0], "101")
    return None

def get_option_ticker(ib: IB, symbol: str, expiry: str, strike: float, 
                     right: Right, exchange: str) -> Optional[Ticker]:
    contract = Option(symbol, expiry, strike, right.value, exchange)
    if qualified := ib.qualifyContracts(contract):
        return ib.reqMktData(qualified[0], "106")
    return None

def get_option_depth(ib: IB, symbol: str, expiry: str, strike: float, 
                   right: Right, exchange: str) -> Optional[Ticker]:
    contract = Option(symbol, expiry, strike, right.value, exchange)
    if qualified := ib.qualifyContracts(contract):
        return ib.reqMktDepth(qualified[0])
    return None

def calculate_theoretical_price(
    stock_price: float,
    strike: float,
    right: Right,
    time_to_exp: float,
    volatility: float,
    risk_free_rate: float,
    dividend_yield: float
) -> float:
    adjusted_rate = risk_free_rate - dividend_yield
    d1 = (np.log(stock_price / strike) + 
         (adjusted_rate + 0.5 * volatility**2) * time_to_exp) / (volatility * np.sqrt(time_to_exp))
    d2 = d1 - volatility * np.sqrt(time_to_exp)
    
    if right == Right.CALL:
        return stock_price * norm.cdf(d1) - strike * np.exp(-adjusted_rate * time_to_exp) * norm.cdf(d2)
    return strike * np.exp(-adjusted_rate * time_to_exp) * norm.cdf(-d2) - stock_price * norm.cdf(-d1)

def get_own_orders(ib: IB, con_id: int) -> dict[float, float]:
    return {
        order.order.lmtPrice: order.order.totalQuantity
        for order in ib.reqAllOpenOrders()
        if order.contract.conId == con_id
    }

def get_depth_price(own_orders: dict, dom_levels: list[DOMLevel], target_depth: int) -> float:
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
    rounding: int
):
    ib = connect_to_ibkr(host, port, client_id, readonly)
    
    stock_ticker = get_stock_ticker(ib, symbol, exchange, currency)
    option_ticker = get_option_ticker(ib, symbol, expiry, strike, right, exchange)
    option_depth = get_option_depth(ib, symbol, expiry, strike, right, exchange)
    
    if not all([stock_ticker, option_ticker, option_depth]):
        raise RuntimeError("Failed to initialize market data")

    while True:
        ib.sleep(5)
        
        if not (stock_price := stock_ticker.marketPrice()):
            logger.warning("Invalid stock price")
            continue
        
        time_to_exp = (datetime.datetime.strptime(expiry, "%Y%m%d") 
                      - datetime.datetime.utcnow()).days / 365.25
        volatility = option_ticker.impliedVolatility or 0.0
        
        theoretical_price = calculate_theoretical_price(
            stock_price,
            strike,
            right,
            time_to_exp,
            volatility,
            risk_free_rate,
            dividend_yield
        )
        logger.info(f"Theoretical price: {theoretical_price:.2f}, "
                    f"Stock: {stock_price:.2f}, IV: {volatility:.2%}")

        own_orders = get_own_orders(ib, option_ticker.contract.conId)
        
        bid_depth_price = get_depth_price(own_orders, option_depth.domBids, order_depth)
        ask_depth_price = get_depth_price(own_orders, option_depth.domAsks, order_depth)

        closest_bid = theoretical_price - min_range
        furthest_bid = theoretical_price - max_range
        closest_ask = theoretical_price + min_range
        furthest_ask = theoretical_price + max_range

        bid_price = min(closest_bid, bid_depth_price) if bid_depth_price != -1 else furthest_bid
        ask_price = max(closest_ask, ask_depth_price) if ask_depth_price != -1 else furthest_ask

        logger.info(f"Bid: {round(bid_price, rounding):.2f}, "
                    f"Ask: {round(ask_price, rounding):.2f}")

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
        rounding=2
    )
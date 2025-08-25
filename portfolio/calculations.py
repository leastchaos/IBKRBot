import logging
from datetime import datetime
from typing import Literal

import numpy as np
from scipy.stats import norm

from .models import PositionRow

logger = logging.getLogger()

# --- Calculation Functions ---


def black_scholes_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    pv_dividend: float = 0.0,
    option_type: Literal["C", "P"] = "C",
) -> float:
    """Calculates the theoretical price of a European option."""
    if T <= 0:
        return max(S - K, 0) if option_type == "C" else max(K - S, 0)

    S_adj = max(S - pv_dividend, 1e-8)
    d1 = (np.log(S_adj / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == "C":
        return S_adj * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    elif option_type == "P":
        return K * np.exp(-r * T) * norm.cdf(-d2) - S_adj * norm.cdf(-d1)
    raise ValueError("Invalid option_type: must be 'C' or 'P'")


def calculate_var(row: PositionRow, price_factor: float) -> float:
    """Calculates the Value at Risk (VaR) for a position."""
    underlying_price = row["underlyingPrice"]
    if not isinstance(underlying_price, (int, float)):
        return 0.0

    if row["secType"] == "STK":
        delta = (underlying_price * price_factor) - underlying_price
        return delta * row["position"] * row["multiplier"] * row["forexRate"]

    if row["secType"] == "OPT":
        if row["right"] not in ("C", "P"):
            return 0.0

        expiry_str = str(row["lastTradeDateOrContractMonth"])
        expiry = datetime.strptime(expiry_str, "%Y%m%d")
        days_to_expiration = max((expiry - datetime.today()).days / 365.0, 0)

        current_price = black_scholes_price(
            S=underlying_price,
            K=row["strike"],
            T=days_to_expiration,
            r=row["riskFreeRate"],
            sigma=row["iv"],
            pv_dividend=row["pvDividend"],
            option_type=row["right"],
        )
        new_price = black_scholes_price(
            S=underlying_price * price_factor,
            K=row["strike"],
            T=days_to_expiration,
            r=row["riskFreeRate"],
            sigma=row["iv"],
            pv_dividend=row["pvDividend"],
            option_type=row["right"],
        )
        change = new_price - current_price
        return change * row["position"] * row["multiplier"] * row["forexRate"]

    return 0.0


def determine_position_type(row: PositionRow) -> str:
    """Determines the type of position (e.g., Stock, Long Call)."""
    secType = row["secType"]
    position = row["position"]
    right = row["right"]

    if secType == "STK":
        return "Stock"
    if secType == "OPT":
        if right == "C":
            return "Long Call" if position > 0 else "Short Call"
        if right == "P":
            return "Long Put" if position > 0 else "Short Put"
    return "Unknown"


def calculate_initial_risk(row: PositionRow) -> float | None:
    """Calculates the initial maximum risk for a position."""
    position = row["position"]
    avgCost = row["avgCost"]
    forexRate = row["forexRate"]
    secType = row["secType"]
    multiplier = float(row.get("multiplier", 1.0) or 1.0)
    strike = row["strike"]
    right = row["right"]
    symbol = row["symbol"]

    if secType == "OPT" and right == "P" and position > 0 and symbol != "TSLA":
        return (
            -position * strike * multiplier * forexRate + position * avgCost * forexRate
        )
    if position > 0:
        return avgCost * position * forexRate
    if secType == "OPT" and right == "P" and position < 0:
        return (
            -position * strike * multiplier * forexRate + position * avgCost * forexRate
        )
    if secType == "OPT" and right == "C" and position < 0:
        return position * avgCost * forexRate
    return None


def calculate_notional_exposure(row: PositionRow) -> float | None:
    """Calculates the current notional exposure for a position."""
    position = row["position"]
    marketPrice = row["marketPrice"]
    forexRate = row["forexRate"]
    secType = row["secType"]
    multiplier = float(row.get("multiplier", 1.0) or 1.0)
    strike = row["strike"]
    right = row["right"]

    if secType == "OPT" and right == "P" and position > 0:
        return (
            -position * strike * multiplier * forexRate
            + position * marketPrice * forexRate
        )
    if position > 0:
        return marketPrice * position * multiplier * forexRate
    if secType == "OPT" and right == "P":
        return (
            -position * strike * multiplier + position * marketPrice * multiplier
        ) * forexRate
    if secType == "OPT" and right == "C":
        return position * marketPrice * forexRate * multiplier
    return None


def calculate_worst_case_risk(row: PositionRow) -> float | None:
    """Calculates the worst-case scenario risk for a position."""
    position = row["position"]
    marketPrice = row["marketPrice"]
    forexRate = row["forexRate"]
    secType = row["secType"]
    multiplier = float(row.get("multiplier", 1.0) or 1.0)
    strike = row["strike"]
    right = row["right"]
    notionalExposure = row.get("notionalExposure", 0.0)

    if secType == "STK" and position > 0:
        return (marketPrice * 0.2) * position * forexRate
    if secType == "OPT" and right == "P" and position < 0:
        return (
            -position * (strike * 0.2) * multiplier * forexRate
        ) + (position * marketPrice * forexRate)

    return notionalExposure


def calculate_target_profit(row: PositionRow) -> float:
    """Calculates the potential profit if the target price is reached."""
    avgCost = row["avgCost"]
    position = row["position"]
    targetPrice = row.get("targetPrice", 0.0)
    positionType = row["positionType"]
    strike = row["strike"]
    multiplier = float(row.get("multiplier", 1.0) or 1.0)
    forexRate = row["forexRate"]

    position_cost = avgCost * position * forexRate
    if positionType == "Stock":
        return targetPrice * position * forexRate - position_cost
    if positionType == "Long Call":
        return (targetPrice - strike) * multiplier * position * forexRate - position_cost
    if positionType in ["Short Call", "Short Put"]:
        return -position_cost
    if positionType == "Long Put":
        return (
            max(strike - targetPrice, 0) * position * multiplier * forexRate
            - position_cost
        )
    return 0.0


def calculate_intrinsic_value(row: PositionRow) -> float:
    """Calculates the intrinsic value of an option."""
    if row["secType"] == "STK":
        # Calculate the intrinsic value (market value) directly to remove dependency
        # on the order of column creation in the portfolio manager.
        return (
            row["marketPrice"]
            * row["position"]
            * float(row.get("multiplier", 1.0) or 1.0)
            * row["forexRate"]
        )

    underlying_price = row["underlyingPrice"]
    if not isinstance(underlying_price, (int, float)):
        return 0.0

    return (
        row["position"]
        * max(underlying_price - row["strike"], 0)
        * row["multiplier"]
        * row["forexRate"]
        if row["right"] == "C"
        else row["position"]
        * max(row["strike"] - underlying_price, 0)
        * row["multiplier"]
        * row["forexRate"]
    )
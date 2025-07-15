from typing import Literal
import pandas as pd
import logging
from scipy.stats import norm
import numpy as np
from datetime import datetime

# Access the already-configured logger
logger = logging.getLogger()


def calculate_initial_risk(row: pd.Series) -> float | None:
    position = row["Position"]
    avg_cost = row["AvgCost"]
    forex_rate = row["ForexRate"]
    sec_type = row["SecType"]
    multiplier = float(row["Multiplier"]) if row["Multiplier"] else 1
    strike = row["Strike"]
    right = row["Right"]
    underlying = row["UnderlyingSymbol"]

    # long puts are considered as puts that protects against long stocks downside
    if sec_type == "OPT" and right == "P" and position > 0 and not underlying == "TSLA":
        return (
            -position * strike * multiplier * forex_rate
            + position * avg_cost * forex_rate
        )
    if position > 0:
        return avg_cost * position * forex_rate
    if sec_type == "OPT" and right == "P" and position < 0:
        return (
            -position * strike * multiplier * forex_rate
            + position * avg_cost * forex_rate
        )
    # short calls are considered as covered calls which reduces the long call risks towards downside
    if sec_type == "OPT" and right == "C" and position < 0:
        return position * avg_cost * forex_rate
    return None


def calculate_current_risk(row) -> float | None:
    position = row["Position"]
    market_price = row["MarketPrice"]
    forex_rate = row["ForexRate"]
    sec_type = row["SecType"]
    multiplier = float(row["Multiplier"]) if row["Multiplier"] else 1
    strike = row["Strike"]
    right = row["Right"]
    underlying = row["UnderlyingSymbol"]

    # long puts are considered as puts that protects against long stocks downside
    if sec_type == "OPT" and right == "P" and position > 0 and not underlying == "TSLA":
        return (
            -position * strike * multiplier * forex_rate
            + position * market_price * forex_rate
        )
    if position > 0:
        return market_price * position * multiplier * forex_rate
    if sec_type == "OPT" and right == "P" and position < 0:
        current_risk = (
            -position * strike * multiplier + position * market_price * multiplier
        )
        return current_risk * forex_rate
    if sec_type == "OPT" and right == "C" and position < 0:
        return position * market_price * forex_rate * multiplier
    return None


def calculate_worst_case_risk(row) -> float | None:
    position = row["Position"]
    market_price = row["MarketPrice"]
    forex_rate = row["ForexRate"]
    sec_type = row["SecType"]
    multiplier = float(row["Multiplier"]) if row["Multiplier"] else 1
    strike = row["Strike"]
    right = row["Right"]
    lowest_price = row["LowestPrice"]  # Get the worst-case price

    if sec_type == "STK" and position > 0:  # Long stock
        # Assume the market price drops to the worst-case price
        return (
            (market_price - min(lowest_price, 0.8 * market_price))
            * position
            * forex_rate
        )
    if sec_type == "OPT" and right == "P" and position < 0:  # Short put
        # Assume the market price drops to the worst-case price
        return (
            -position
            * (strike - min(lowest_price, 0.8 * strike))
            * multiplier
            * forex_rate
            + position * market_price * forex_rate
        )
    return row["CurrentMaxRisk"]


def determine_position_type(row: pd.Series) -> str:
    """
    Determines the type of position based on SecType, Right, and Position.
    """
    sec_type = row["SecType"]
    right = row["Right"]
    position = row["Position"]

    if sec_type == "STK":
        return "Stock"
    if sec_type != "OPT":
        return "Unknown"
    if right == "C":
        return "Long Call" if position > 0 else "Short Call"
    if right == "P":
        return "Long Put" if position > 0 else "Short Put"
    return "Unknown"


def calculate_target_profit(row: pd.Series) -> float:
    avg_cost = row["AvgCost"]
    position = row["Position"]
    target_price = row["TargetPrice"]
    position_type = row["PositionType"]
    strike = row["Strike"]
    multiplier = float(row["Multiplier"]) if row["Multiplier"] else 1
    forex_rate = row["ForexRate"]

    position_cost = avg_cost * position * forex_rate
    if position_type == "Stock":
        return target_price * position * forex_rate - position_cost
    if position_type == "Long Call":
        return (
            target_price - strike
        ) * multiplier * position * forex_rate - position_cost
    if position_type == "Short Call":
        return -position_cost
    if position_type == "Long Put":
        return (
            max(strike - target_price, 0) * position * multiplier * forex_rate
            - position_cost
        )
    if position_type == "Short Put":
        return -position_cost
    return 0


def black_scholes_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    pv_dividend: float = 0.0,  # New: present value of dividends
    option_type: Literal["C", "P"] = "C",
) -> float:
    """
    Calculate the theoretical price of a European option using the Black-Scholes formula,
    adjusted for discrete dividends via present value subtraction.

    Parameters:
    - S: Current underlying price
    - K: Option strike price
    - T: Time to expiration in years
    - r: Risk-free interest rate (annual)
    - sigma: Volatility of the underlying asset (annual)
    - pv_dividend: Present value of expected dividends during option's lifetime
    - option_type: 'C' for call, 'P' for put

    Returns:
    - Option price
    """
    if T <= 0:
        if option_type == "C":
            return max(S - K, 0)
        if option_type == "P":
            return max(K - S, 0)
        raise ValueError("Invalid option_type: must be 'C' or 'P'")

    # Adjust underlying price for dividends
    S_adj = max(S - pv_dividend, 1e-8)

    d1 = (np.log(S_adj / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == "C":
        price = S_adj * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    elif option_type == "P":
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S_adj * norm.cdf(-d1)
    else:
        raise ValueError("Invalid option_type: must be 'C' or 'P'")

    return price


def calculate_var(row: pd.Series, price_factor: float) -> float:
    """
    Calculate Value at Risk (VaR) for a position based on a price shock (price_factor).

    Parameters:
    - row: A pandas Series containing position details
    - price_factor: Multiplier to shock the underlying price (e.g., 1.05 for +5%)
    - current_date: Optional current date (YYYY-MM-DD) for time-to-expiry calculation

    Returns:
    - VaR in monetary terms
    """
    underlying_price = row["UnderlyingPrice"]
    position = row["Position"]
    multiplier = float(row["Multiplier"]) if row["Multiplier"] else 1
    sec_type = row["SecType"]
    right = row["Right"]
    strike = row["Strike"]
    risk_free_rate = row["RiskFreeRate"]
    pv_dividend = row["PVDividend"]
    implied_vol = row["IV"]
    expiration_date = row["LastTradeDateOrContractMonth"]  # Format: yyyymmdd
    forex_rate = row["ForexRate"]

    if pd.isna(underlying_price) or underlying_price <= 0:
        return 0.0

    new_underlying_price = underlying_price * price_factor

    if sec_type == "STK":
        delta = new_underlying_price - underlying_price
        return delta * position * multiplier * forex_rate

    if sec_type == "OPT":
        current = datetime.today()
        expiry_str = str(expiration_date)
        expiry = datetime.strptime(expiry_str, "%Y%m%d")
        days_to_expiration = max((expiry - current).days / 365.0, 0)  # Avoid negative T
        # Map position type to option type

        # Current price
        current_price = black_scholes_price(
            S=underlying_price,
            K=strike,
            T=days_to_expiration,
            r=risk_free_rate,
            sigma=implied_vol,
            pv_dividend=pv_dividend,
            option_type=right,
        )

        # New price after shock
        new_price = black_scholes_price(
            S=new_underlying_price,
            K=strike,
            T=days_to_expiration,
            r=risk_free_rate,
            sigma=implied_vol,
            pv_dividend=pv_dividend,
            option_type=right,
        )
        change = new_price - current_price
        return change * position * multiplier * forex_rate

    logger.warning(f"Invalid position type: {sec_type} for symbol: {row['Symbol']}")
    return 0.0


def calculate_instrinsic_value(row: pd.Series) -> float:
    if row["SecType"] == "STK":
        return row["MarketValue"]
    position = row["Position"]
    multiplier = float(row["Multiplier"]) if row["Multiplier"] else 1
    underlying_price = row["UnderlyingPrice"]
    strike_price = row["Strike"]
    right = row["Right"]
    forex_rate = row["ForexRate"]

    if right == "C":
        return (
            position * max(underlying_price - strike_price, 0) * multiplier * forex_rate
        )
    if right == "P":
        return (
            position * max(strike_price - underlying_price, 0) * multiplier * forex_rate
        )
    logger.warning(
        f"Invalid position type: {row['SecType']} for symbol: {row['Symbol']}"
    )
    return 0


def process_positions_data(
    positions_df: pd.DataFrame,
    scenario_df: pd.DataFrame,
) -> pd.DataFrame:
    logger.info("Processing positions data...")
    # Merge scenario prices into positions_df
    positions_df = positions_df.merge(
        scenario_df,
        left_on="Symbol",
        right_on="UnderlyingSymbol",
        how="left",
    )
    positions_df["StockEquivalentMovement"] = (
        positions_df["Delta"] * positions_df["Position"] * positions_df["Multiplier"]
    )

    positions_df["PositionType"] = positions_df.apply(determine_position_type, axis=1)
    positions_df["WorstCaseStockMovement"] = (
        positions_df["Position"]
        * positions_df["Multiplier"]
        * positions_df["PositionType"].isin(["Stock"])
        - positions_df["PositionType"].isin(["Short Put"])
        * positions_df["Position"]
        * positions_df["Multiplier"]
    )
    positions_df["LowestPrice"] = positions_df["LowestPrice"].fillna(0)
    positions_df["InitialMaxRisk"] = positions_df.apply(calculate_initial_risk, axis=1)
    positions_df["CurrentMaxRisk"] = positions_df.apply(calculate_current_risk, axis=1)
    positions_df["WorstCaseRisk"] = positions_df.apply(
        calculate_worst_case_risk, axis=1
    )
    positions_df["TargetProfit"] = positions_df.apply(calculate_target_profit, axis=1)
    # 20% drop
    positions_df["Value_At_Risk_99%"] = positions_df.apply(
        calculate_var, axis=1, args=(0.01,)
    )
    positions_df["Value_At_Risk_40%"] = positions_df.apply(
        calculate_var, axis=1, args=(0.6,)
    )

    # 40% drop
    positions_df["Value_At_Risk_20%"] = positions_df.apply(
        calculate_var, axis=1, args=(0.8,)
    )

    # 20% gain
    positions_df["Value_At_Gain_20%"] = positions_df.apply(
        calculate_var, axis=1, args=(1.2,)
    )

    # 40% gain
    positions_df["Value_At_Gain_40%"] = positions_df.apply(
        calculate_var, axis=1, args=(1.4,)
    )

    # strike * position
    positions_df["StrikePositions"] = positions_df["Strike"] * positions_df["Position"]

    positions_df["CostBasis"] = (
        positions_df["AvgCost"]
        * positions_df["Position"]
        * positions_df["ForexRate"]
    )

    positions_df["MarketValue"] = (
        positions_df["MarketPrice"]
        * positions_df["Position"]
        * positions_df["Multiplier"]
        * positions_df["ForexRate"]
    )

    positions_df["InstrinsicValue"] = positions_df.apply(
        calculate_instrinsic_value, axis=1
    )
    positions_df["TimeValue"] = (
        positions_df["MarketValue"] - positions_df["InstrinsicValue"]
    )

    logger.info("Positions data processed successfully.")
    return positions_df

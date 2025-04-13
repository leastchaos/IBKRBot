import pandas as pd
import logging

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

    if position > 0:
        initial_risk = avg_cost * position * forex_rate
    elif sec_type == "OPT" and right == "P" and position < 0:
        initial_risk = (
            -position * strike * multiplier * forex_rate + position * avg_cost * forex_rate
        )
    elif sec_type == "OPT" and right == "C" and position < 0:
        initial_risk = position * avg_cost * forex_rate
    else:
        initial_risk = None
    return initial_risk


def calculate_current_risk(row) -> float | None:
    position = row["Position"]
    market_price = row["MarketPrice"]
    forex_rate = row["ForexRate"]
    sec_type = row["SecType"]
    multiplier = float(row["Multiplier"]) if row["Multiplier"] else 1
    strike = row["Strike"]
    right = row["Right"]

    if position > 0:
        current_risk = market_price * position * multiplier
    elif sec_type == "OPT" and right == "P" and position < 0:
        current_risk = -position * strike * multiplier + position * market_price
    elif sec_type == "OPT" and right == "C" and position < 0:
        current_risk = position * market_price
    else:
        current_risk = None
    return current_risk * forex_rate


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
        worst_case_risk = (market_price - min(lowest_price, 0.8*market_price)) * position * forex_rate
    elif sec_type == "OPT" and right == "P" and position < 0:  # Short put
        # Assume the market price drops to the worst-case price
        worst_case_risk = (
            -position * (strike - min(lowest_price, 0.8 * strike)) * multiplier * forex_rate
            + position * market_price * forex_rate
        )
    elif sec_type == "OPT" and right == "C" and position > 0:  # Long call
        # Worst-case risk is already calculated as CurrentMaxRisk
        worst_case_risk = row["CurrentMaxRisk"]
    elif sec_type == "OPT" and right == "P" and position > 0:  # Long put
        # Worst-case risk is already calculated as CurrentMaxRisk
        worst_case_risk = row["CurrentMaxRisk"]
    elif sec_type == "OPT" and right == "C" and position < 0:  # Short call
        # Worst-case risk is already calculated as CurrentMaxRisk
        worst_case_risk = row["CurrentMaxRisk"]
    else:
        worst_case_risk = None

    return worst_case_risk


def process_positions_data(
    positions_df: pd.DataFrame, worst_case_df: pd.DataFrame
) -> pd.DataFrame:
    logger.info("Processing positions data...")
    # Merge worst-case prices into positions_df
    positions_df = positions_df.merge(
        worst_case_df,
        left_on="Symbol",
        right_on="UnderlyingSymbol",
        how="left",
    )
    positions_df["LowestPrice"] = positions_df["LowestPrice"].fillna(0)
    positions_df["InitialMaxRisk"] = positions_df.apply(calculate_initial_risk, axis=1)
    positions_df["CurrentMaxRisk"] = positions_df.apply(calculate_current_risk, axis=1)
    positions_df["WorstCaseRisk"] = positions_df.apply(
        calculate_worst_case_risk, axis=1
    )
    logger.info("Positions data processed successfully.")
    return positions_df

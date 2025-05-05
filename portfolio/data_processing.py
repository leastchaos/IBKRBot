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

    # # long puts are considered as puts that protects against long stocks downside
    # if sec_type == "OPT" and right == "P" and position > 0:
    #     return (
    #         -position * strike * multiplier * forex_rate
    #         + position * avg_cost * forex_rate
    #     )
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

    # long puts are considered as puts that protects against long stocks downside
    # if sec_type == "OPT" and right == "P" and position > 0:
    #     return (
    #         -position * strike * multiplier * forex_rate
    #         + position * market_price * forex_rate
    #     )
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
    logger.info("Positions data processed successfully.")
    return positions_df

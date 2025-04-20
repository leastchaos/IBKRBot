from itertools import product
import logging
from decimal import Decimal

from ib_async import IB, BarDataList, Contract, Ticker

from grid_calculations import generate_grid
from get_historical_data import get_historical_data


logger = logging.getLogger()

def evaluate_risks(
    grid: dict[
        Decimal, Decimal
    ],  # Grid dictionary with price levels as keys and positions as values
    historical_data: BarDataList,
    ticker: Ticker,
    fee_per_trade: Decimal = Decimal("3"),  # Fee per trade (adjust as needed)
    slippage_per_trade: Decimal = Decimal(
        "0.01"
    ),  # Slippage per trade (adjust as needed)
) -> dict[str, float]:
    """Evaluate trading risks and simulate daily profits using Decimal."""
    # Extract grid parameters
    price_levels = sorted(grid.keys())  # Sorted list of price levels
    max_shares = sum(grid.values())  # Total maximum shares across all levels
    min_price = min(price_levels)  # Minimum price level

    if not historical_data:
        logger.warning("No historical data available for risk evaluation.")
        return

    # Simulate grid strategy on historical data
    simulated_profit = Decimal(0.0)
    trade_count = 0
    current_level_index = None
    multiplier = Decimal(ticker.contract.multiplier or 1)

    for bar in historical_data:
        current_price = Decimal(bar.close)
        if not current_price:
            logger.warning("Skipping bar with missing price.")
            continue

        # Determine the current grid level index
        for i, level in enumerate(price_levels):
            if current_price <= level:
                new_level_index = i
                if current_level_index is None:
                    current_level_index = new_level_index
                break
        else:
            # If price exceeds the highest grid level, set to the last level
            new_level_index = len(price_levels) - 1
            if current_level_index is None:
                current_level_index = new_level_index

        if new_level_index > current_level_index:
            # Price crossed one or more grid levels upward
            levels_crossed = new_level_index - current_level_index
            logger.debug(f"Price crossed {levels_crossed} level(s) upward.")

            # Update simulated profit based on the number of shares traded at each level
            for i in range(current_level_index, new_level_index):
                positions_at_level = grid[price_levels[i - 1]]
                simulated_profit += (
                    (price_levels[i + 1] - price_levels[i])
                    * positions_at_level
                    * multiplier
                )
            trade_count += levels_crossed
            current_level_index = new_level_index

        if new_level_index < current_level_index - 1:
            current_level_index = new_level_index

    # Adjust for slippage and fees
    total_trading_costs = trade_count * (fee_per_trade + slippage_per_trade)
    adjusted_profit = simulated_profit - total_trading_costs

    # Calculate risk metrics
    min_price = min(price_levels)
    max_bar_price = Decimal(max(bar.high for bar in historical_data))
    min_bar_price = Decimal(min(bar.low for bar in historical_data))
    # find the sum of position bought from min_bar_price to max_bar_price
    max_drawdown = (
        sum(
            price * positions * multiplier
            for price, positions in grid.items()
            if min_bar_price <= price <= max_bar_price
        )
        - sum(
            positions * multiplier
            for price, positions in grid.items()
            if min_bar_price <= price <= max_bar_price
        )
        * min_bar_price
    ) - total_trading_costs
    max_drawdown = max(max_drawdown, 1)
    max_risk = sum(price * positions * multiplier for price, positions in grid.items())
    loss_at_min_price = max(max_risk - max_shares * min_price * multiplier, 1)
    # Estimate ROI
    estimated_roi = (adjusted_profit / loss_at_min_price) * 100


    return {
        "max_shares": max_shares,
        "max_risk": max_risk,
        "loss_at_min_price": loss_at_min_price,
        "max_drawdown": round(max_drawdown, 2),
        "simulated_profit": simulated_profit,
        "trade_count": trade_count,
        "adjusted_profit": adjusted_profit,
        "estimated_roi": round(estimated_roi, 2),
        "profit/drawdown": round(adjusted_profit / max_drawdown, 2),
    }


if __name__ == "__main__":
    from ib_connector import connect_to_ibkr, get_stock_ticker
    from logger_config import setup_logger
    from pprint import pprint

    ib = connect_to_ibkr("127.0.0.1", 7497, 222, readonly=True)
    stock_name = "BABA"
    exchange = "SMART"
    currency = "USD"
    min_price = Decimal("60")
    max_price = Decimal("180.0")
    max_value_per_level = Decimal("2000")
    add_value_per_level = Decimal("-100")
    min_position_per_level = Decimal("5")
    position_step = Decimal("1")
    fee_per_trade = Decimal("3")
    slippage_per_trade = Decimal("0.01")
    simulation_days = "10 Y"
    bar_size = "1 min"
    step_range = [1, 2]
    percent_range = [1,2]


    stock = get_stock_ticker(ib, stock_name, exchange, currency)
    setup_logger()
    results = []

    historical_data = get_historical_data(ib, stock, simulation_days, bar_size)
    for step, percent in product(step_range, percent_range):
        grid = generate_grid(
            min_price=min_price,
            max_price=max_price,
            min_percentage_step=Decimal(str(percent)),
            step_size=Decimal(str(step)),
            start_value_at_min_price=max_value_per_level,
            add_value_per_level=add_value_per_level,
            position_step=position_step,
            min_position_per_level=min_position_per_level,
        )
        pprint(grid)
        result = evaluate_risks(
            grid=grid,
            ticker=stock,
            historical_data=historical_data,
            fee_per_trade=fee_per_trade,
            slippage_per_trade=slippage_per_trade,
        )
        if not result:
            continue
        result["step_size"] = step
        result["percentage_step"] = percent
        results.append(result)
    import pandas as pd
    from pprint import pprint

    df = pd.DataFrame(results).sort_values("profit/drawdown", ascending=False)
    pprint(df)

from ib_async import IB, Stock
import numpy as np
import logging
from decimal import Decimal, getcontext

logger = logging.getLogger()


def calculate_grid_levels(
    current_price: Decimal,
    min_price: Decimal,
    max_price: Decimal,
    step_size: Decimal,
    active_levels: int,
) -> tuple[list[Decimal], list[Decimal]]:
    """Calculate buy and sell grid levels using Decimal."""
    price_range = [
        min_price + i * step_size
        for i in range(int((max_price - min_price) / step_size) + 1)
    ]
    grid_index = (
        next((i for i, price in enumerate(price_range) if price >= current_price), 0)
        - 1
    )
    logger.info(
        f"Current price: {current_price}, Grid index: {grid_index}, idx price {price_range[grid_index]}"
    )

    # Calculate buy and sell prices
    buy_prices = [
        price_range[idx]
        for i in range(-1, active_levels)
        if (idx := grid_index - i) >= 0
    ]
    sell_prices = [
        price_range[idx]
        for i in range(0, active_levels + 1)
        if (idx := grid_index + i) < len(price_range)
    ]
    logger.info(f"Buy: {buy_prices}, Sell: {sell_prices}")

    # Apply cooldown rules
    buy_prices = [p for p in buy_prices if p < current_price]
    sell_prices = [p for p in sell_prices if p > current_price]
    logger.info(f"Filtered Buy: {buy_prices}, Filtered Sell: {sell_prices}")
    return buy_prices, sell_prices


def calculate_grid_sizes(
    position_per_level: Decimal,
    max_position_per_level: Decimal,
    current_pos: Decimal,
    position_step: Decimal,
    step_size: Decimal,
    current_price: Decimal,
    max_price: Decimal,
    min_price: Decimal,
    active_levels: int,
) -> tuple[list[Decimal], list[Decimal]]:
    """Calculate size per level using Decimal."""
    num_levels_above_price = int((max_price - current_price) // step_size)
    num_levels_below_price = int((current_price - min_price) // step_size)

    target_position = position_per_level * Decimal(num_levels_above_price)
    buy_size_per_level = (
        min(
            max_position_per_level,
            position_per_level
            + max(target_position - current_pos, Decimal(0))
            // Decimal(num_levels_below_price),
        )
        // position_step
        * position_step
    )
    sell_size_per_level = (
        min(
            max_position_per_level,
            position_per_level
            + max(current_pos - target_position, Decimal(0))
            // Decimal(num_levels_above_price),
        )
        // position_step
        * position_step
    )

    now_pos = current_pos
    sell_sizes = []
    for i in range(active_levels):
        now_pos -= sell_size_per_level
        if now_pos < Decimal(0):
            sell_sizes.append(Decimal(0))
            continue
        sell_sizes.append(sell_size_per_level)

    buy_sizes = [buy_size_per_level] * active_levels
    logger.info(
        f"Current position: {current_pos}, Target position: {target_position}\n"
        f"Buy size per level: {buy_size_per_level}, Sell size per level: {sell_size_per_level}"
        f"\nBuy sizes: {buy_sizes}, Sell sizes: {sell_sizes}"
    )
    return buy_sizes, sell_sizes


def evaluate_risks(
    min_price: Decimal,
    max_price: Decimal,
    step_size: Decimal,
    positions_per_level: int,
    ib: IB,
    stock_ticker: Stock,
) -> None:
    """Evaluate trading risks using Decimal."""
    num_levels = int((max_price - min_price) // step_size) + 1
    max_shares = num_levels * positions_per_level

    price_range = [min_price + i * step_size for i in range(num_levels)]
    max_risk = sum(price * Decimal(positions_per_level) for price in price_range)
    loss_at_min_price = sum(
        (price - min_price) * Decimal(positions_per_level) for price in price_range
    )

    historical_data = ib.reqHistoricalData(
        stock_ticker.contract, "", "14 D", "1 day", "TRADES", False
    )
    daily_atr = (
        Decimal(np.mean([bar.high - bar.low for bar in historical_data]))
        if historical_data
        else Decimal(0.0)
    )

    logger.info(
        f"Risk Assessment:\n"
        f"Max Shares: {max_shares}\n"
        f"Max Risk: ${max_risk:.2f}\n"
        f"Loss at Min Price: ${loss_at_min_price:.2f}\n"
        f"Daily ATR: ${daily_atr:.2f}\n"
        f"Estimated Daily Profit: ${(daily_atr * Decimal(positions_per_level) / step_size):.2f}"
    )

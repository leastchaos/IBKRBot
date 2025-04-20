import logging
from decimal import Decimal

logger = logging.getLogger()


def generate_grid(
    min_price: Decimal,
    max_price: Decimal,
    step_size: Decimal,
    min_percentage_step: Decimal,
    start_value_at_min_price: Decimal,
    add_value_per_level: Decimal,
    min_position_per_level: Decimal,
    position_step: Decimal,
) -> dict[Decimal, Decimal]:
    """Generate an entire grid of prices using Decimal."""

    def calculate_position_size(
        value_per_level: Decimal,
        price: Decimal,
    ) -> Decimal:
        return max(
            (value_per_level / price) // position_step * position_step,
            min_position_per_level,
        )

    logger.info(
        f"Grid Parameters: \n"
        f"  Min Price: {min_price}\n"
        f"  Max Price: {max_price}\n"
        f"  Min Percentage Step: {min_percentage_step}\n"
        f"  Step Size: {step_size}\n"
        f"  Add Value per Level: {add_value_per_level}\n"
        f"  Max Value per Level: {start_value_at_min_price}\n"
        f"  Position Step: {position_step}\n"
    )
    grid_levels = {
        min_price: calculate_position_size(start_value_at_min_price, min_price)
    }
    prev_price = min_price
    value_per_level = start_value_at_min_price

    for i in range(int((max_price - min_price) // step_size) + 1):
        price = min_price + i * step_size
        if price < prev_price * (Decimal("1") + min_percentage_step / 100):
            continue
        prev_price = price
        value_per_level += add_value_per_level
        grid_levels[price] = calculate_position_size(value_per_level, price)
    return grid_levels


def get_current_position_index(
    current_price: Decimal, grid: dict[Decimal, Decimal]
) -> int:
    grid_levels = sorted(list(grid.keys()))
    return (
        next((i for i, price in enumerate(grid_levels) if price >= current_price), 0)
        - 1
    )


def get_current_grid_buy_and_sell_levels(
    last_traded_price: Decimal,
    grid: dict[Decimal, Decimal],
    active_levels: int,
    current_position: Decimal,
) -> tuple[dict[Decimal, Decimal], dict[Decimal, Decimal]]:
    """Calculate buy and sell grid levels using Decimal."""
    nearest_price = min(grid.keys(), key=lambda x: abs(x - last_traded_price))
    grid_index = get_current_position_index(nearest_price, grid) + 1
    logger.info(f"Current price: {last_traded_price}, Grid index: {grid_index}")
    price_range = sorted(grid.keys())
    target_position = calculate_target_position(last_traded_price, grid)
    additional_buy = max(0, target_position - current_position) // grid_index
    additional_sell = max(0, current_position - target_position) // (
        len(price_range) - grid_index
    )
    logger.info(
        f"Current position: {current_position}, Target position: {target_position}, Additional buy: {additional_buy}, Additional sell: {additional_sell}"
    )
    # Calculate buy and sell prices
    buy_levels = {
        price_range[idx]: grid[price_range[idx]] + additional_buy
        for i in range(1, active_levels + 1)
        if (idx := grid_index - i) >= 0
    }
    sell_levels = {
        # need to sell same amount as the buy level below
        price_range[idx]: grid[price_range[idx - 1]] + additional_sell
        for i in range(1, active_levels + 1)
        if (idx := grid_index + i) < len(price_range)
    }
    logger.info(f"\nBuy: {buy_levels}\nSell: {sell_levels}")

    return buy_levels, sell_levels


def calculate_target_position(
    current_price: Decimal,
    grid: dict[Decimal, Decimal],
) -> Decimal:
    """Calculate target position using Decimal."""
    target_position = 0
    for grid_level, grid_size in sorted(grid.items(), reverse=True):
        if current_price >= grid_level:
            return target_position
        target_position += grid_size
    return target_position


if __name__ == "__main__":
    from logger_config import setup_logger
    from pprint import pprint

    setup_logger()

    grid = generate_grid(
        min_price=Decimal("60"),
        max_price=Decimal("160.0"),
        min_percentage_step=Decimal("2"),
        step_size=Decimal("2"),
        start_value_at_min_price=Decimal("1000"),
        add_value_per_level=Decimal("0"),
        position_step=Decimal("1"),
    )
    pprint(grid)
    buy_prices, sell_prices = get_current_grid_buy_and_sell_levels(
        last_traded_price=Decimal("100.5"),
        grid=grid,
        active_levels=1,
        current_position=Decimal("0"),
    )

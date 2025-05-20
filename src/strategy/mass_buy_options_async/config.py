from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
import logging
from src.models.models import Action, Rights, OCAType
from functools import cached_property


@dataclass
class TradingConfig:
    # Strategy Parameters
    action: Action
    right: Rights
    min_dte: int
    max_dte: int
    min_strike: Decimal
    max_strike: Decimal
    size: Decimal
    min_distance: Decimal
    min_update_size: Decimal
    volatility: float
    aggressive: bool
    skip_too_far_away: bool
    min_ask_price: Decimal
    max_bid_price: Decimal
    determine_price_timeout: int = 5
    manual_min_tick: Decimal | None = None
    depth: int = 5
    loop_interval: int = 5
    close_positions_only: bool = False
    oca_type: OCAType = OCAType.REDUCE_WITH_NO_BLOCK
    default_stock_price: Decimal | None = None
    option_timeout: int = 1
    stock_timeout: int = 5
    min_underlying_price: Decimal | None = None
    max_underlying_price: Decimal | None = None

    def __post_init__(self):
        if (
            self.action == Action.BUY
            and self.right == Rights.PUT
            and self.max_underlying_price is not None
        ):
            self.underlying_warning(warn_max_underlying_price=False)
        if (
            self.action == Action.SELL
            and self.right == Rights.PUT
            and self.min_underlying_price is not None
        ):
            self.underlying_warning(warn_max_underlying_price=True)
        if (
            self.action == Action.BUY
            and self.right == Rights.CALL
            and self.min_underlying_price is not None
        ):
            self.underlying_warning(warn_max_underlying_price=False)
        if (
            self.action == Action.SELL
            and self.right == Rights.CALL
            and self.max_underlying_price is not None
        ):
            self.underlying_warning(warn_max_underlying_price=True)

    def underlying_warning(self, warn_max_underlying_price: bool = False):
        logging.warning(
            f"You are setting up to {self.action.value} a {self.right.value} option with a specified "
            f"{'max_underlying_price' if warn_max_underlying_price else 'min_underlying_price'} "
            f"({self.max_underlying_price if warn_max_underlying_price else self.min_underlying_price}). "
            f"This configuration might lead to {"selling" if self.action == Action.SELL else "buying"} at a "
            f"{'lower' if self.action == Action.SELL else 'higher'} price than "
            f"necessary if the underlying price is expected to be {'lower' if warn_max_underlying_price else 'higher'}."
        )
        input("Press Enter to continue...")

    # Default OCA group name
    @cached_property
    def oca_group(self) -> str:
        if self.oca_type == OCAType.MANUAL:
            return ""
        return f"Mass Trade {datetime.now().strftime('%Y%m%d %H:%M:%S')}"

    @classmethod
    def generate_test_config(cls) -> "TradingConfig":
        return TradingConfig(
            action=Action.BUY,
            right=Rights.CALL,
            min_dte=200,
            max_dte=400,
            min_strike=Decimal("160"),
            max_strike=Decimal("200"),
            size=Decimal("1"),
            manual_min_tick=Decimal("0.01"),
            min_update_size=Decimal("0.05"),
            min_distance=Decimal("0.1"),
            volatility=0.5,
            aggressive=True,
            skip_too_far_away=True,
            oca_type=OCAType.REDUCE_WITH_NO_BLOCK,
            min_ask_price=Decimal("0"),
            max_bid_price=Decimal("100"),
            stock_timeout=1,
            default_stock_price=Decimal("100"),
        )


if __name__ == "__main__":
    print(TradingConfig.generate_test_config())

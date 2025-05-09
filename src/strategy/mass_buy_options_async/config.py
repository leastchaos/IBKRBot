from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from src.models.models import Action, Rights, OCAType

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

    # Default OCA group name
    @property
    def oca_group(self):
        from datetime import datetime
        return f"Mass Trade {datetime.now().strftime('%Y%m%d %H:%M:%S')}"

    @classmethod
    def generate_test_config(cls) -> 'TradingConfig':
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
        )


if __name__ == "__main__":
    print(TradingConfig.generate_test_config())
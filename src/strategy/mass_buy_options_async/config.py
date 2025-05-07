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
from dataclasses import dataclass
from enum import Enum

from ib_async import Contract, LimitOrder


class Rights(Enum):
    CALL = "C"
    PUT = "P"


class Action(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OCAType(Enum):
    CANCEL_ALL_WITH_BLOCK = 1
    REDUCE_WITH_BLOCK = 2
    REDUCE_WITH_NO_BLOCK = 3
    MANUAL = 0


@dataclass(frozen=True)
class OCAOrder:
    contract: Contract
    order: LimitOrder

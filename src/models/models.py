from enum import Enum


class Rights(Enum):
    CALL = "C"
    PUT = "P"


class Action(Enum):
    BUY = "BUY"
    SELL = "SELL"



from decimal import Decimal
from enum import Enum
from ib_async import IB, Contract, Option, Stock

from core.ib_connector import get_options



def mass_trade_option(
    ib: IB,
    stock: Stock,
    options: list[Option],
    quantity: Decimal,
    side: Literal["BUY", "SELL"],











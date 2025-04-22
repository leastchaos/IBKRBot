from typing import Protocol
from ib_async import IB

class Strategy(Protocol):
    def run(self, ib: IB) -> None:
def run_trading_bot(ib: IB, strategy: ) -> None:
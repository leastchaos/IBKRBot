from decimal import Decimal
from typing import Literal
from ib_async import IB, Contract, Option, Stock, Ticker


def connect_to_ibkr(host: str, port: int, client_id: int, readonly: bool) -> IB:
    """Connect to Interactive Brokers."""
    ib = IB()
    ib.connect(host, port, client_id, readonly=readonly)
    return ib


def get_stock_ticker(
    ib: IB, symbol: str, exchange: str, currency: str
) -> Ticker | None:
    """Get stock ticker from IB."""
    contract = Stock(symbol, exchange, currency)
    if qualified := ib.qualifyContracts(contract):
        return ib.reqMktData(qualified[0], "101")
    return None


def get_option_ticker(
    ib: IB,
    symbol: str,
    last_trade_date: str,
    strike_price: Decimal,
    right: Literal["C", "P"],
    exchange: str = "",
    multiplier: int = "",
    currency: str = "",
) -> Ticker | None:
    """Get option ticker from IB."""
    contract = Option(
        symbol,
        last_trade_date,
        float(strike_price),
        right,
        exchange,
        multiplier,
        currency,
    )
    if qualified := ib.qualifyContracts(contract):
        return ib.reqMktData(qualified[0], "101")
    return None


def get_option_chain(ib: IB, contract: Contract) -> list[Option]:
    return ib.reqSecDefOptParams(contract.symbol, "", "STK", contract.conId)


def get_current_position(ib: IB, stock_ticker: Stock) -> Decimal:
    current_pos = next(
        (
            pos.position
            for pos in ib.positions()
            if pos.contract.conId == stock_ticker.contract.conId
        ),
        0,
    )
    current_pos = Decimal(str(current_pos))
    return current_pos


if __name__ == "__main__":
    from logger_config import setup_logger
    setup_logger()
    ib = connect_to_ibkr("127.0.0.1", 7497, 222, readonly=True)
    stock = get_stock_ticker(ib, "9988", "", "HKD")
    option_chain = get_option_chain(ib, stock.contract)
    option = get_option_ticker(
        ib,
        "BABA",
        "20250620",
        Decimal("100"),
        "C",
        "SMART",
        "",
        "USD",
    )
    ib.reqMarketDataType(1)
    print(stock.last)
    # print(option_chain)
    # print(get_current_position(ib, stock))
    # print(option)
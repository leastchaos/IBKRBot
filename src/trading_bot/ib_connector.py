from ib_async import IB, Stock, Ticker


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

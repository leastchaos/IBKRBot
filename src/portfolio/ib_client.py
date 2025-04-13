from ib_async import IB, Forex
import pandas as pd
import logging

logger = logging.getLogger()


def fetch_balance(ib_client: IB) -> pd.DataFrame:
    """
    Fetch all account-related data (e.g., NetLiquidation, CashBalance) and return it as a DataFrame.
    """
    # Retrieve all account values
    logger.info("Fetching account data from TWS...")
    account_values = ib_client.accountValues()

    # Organize data into a dictionary of dictionaries
    account_data = {}
    for value in account_values:
        account = value.account
        tag = value.tag
        try:
            numeric_value = float(value.value)  # Convert to float if possible
        except ValueError:
            numeric_value = value.value  # Keep as string if conversion fails

        if account not in account_data:
            account_data[account] = {}
        account_data[account][tag] = numeric_value

    # Convert the dictionary to a DataFrame
    df = pd.DataFrame.from_dict(account_data, orient="index")
    df.index.name = "Account"
    df.reset_index(inplace=True)
    logger.info("Account data fetched successfully.")
    return df


def fetch_historical_prices(ib_client: IB, contracts: list) -> dict[int, float]:
    logger.info("Fetching historical prices from TWS...")
    historical_prices = {}
    contracts = ib_client.qualifyContracts(*contracts)
    ib_client.reqMarketDataType(4)
    for contract in contracts:
        try:
            bars = ib_client.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr="1 D",
                barSizeSetting="1 hour",
                whatToShow="TRADES",
                useRTH=False,
            )
            if bars:
                historical_prices[contract.conId] = bars[-1].close
                continue
            bars = ib_client.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr="30 S",
                barSizeSetting="1 secs",
                whatToShow="BID_ASK",
                useRTH=False,
            )
            if bars:
                historical_prices[contract.conId] = bars[-1].close
                continue
            historical_prices[contract.conId] = None
        except Exception as e:
            print(f"Error fetching historical data for {contract.symbol}: {e}")
            historical_prices[contract.conId] = None
    logger.info("Historical prices fetched successfully.")
    return historical_prices


def fetch_currency_rate(
    ib_client: IB, currency: str, base_currency: str = "SGD"
) -> float:
    if currency == base_currency:
        return 1
    forex_contract = Forex(f"{currency}{base_currency}")
    bars = ib_client.reqHistoricalData(
        forex_contract,
        endDateTime="",
        durationStr="1 D",
        barSizeSetting="1 day",
        whatToShow="MIDPOINT",
        useRTH=True,
    )
    if bars:
        return bars[-1].close
    forex_contract = Forex(f"{base_currency}{currency}")
    bars = ib_client.reqHistoricalData(
        forex_contract,
        endDateTime="",
        durationStr="30 S",
        barSizeSetting="1 secs",
        whatToShow="MIDPOINT",
        useRTH=True,
    )
    if bars:
        return 1 / bars[-1].close
    return None


def fetch_positions(ib_client: IB, base_currency: str = "SGD") -> pd.DataFrame:
    logger.info("Fetching positions from TWS...")
    positions = ib_client.positions()
    position_data = []
    unique_currencies = set()
    contracts = []
    for pos in positions:
        contract = pos.contract
        contracts.append(contract)
        unique_currencies.add(contract.currency)
        position_data.append(
            {
                "Account": pos.account,
                "Symbol": contract.symbol,
                "SecType": contract.secType,
                "Currency": contract.currency,
                "Position": pos.position,
                "AvgCost": pos.avgCost,
                "ConId": contract.conId,
                "Exchange": contract.exchange,
                "LocalSymbol": getattr(contract, "localSymbol", None),
                "TradingClass": getattr(contract, "tradingClass", None),
                "LastTradeDateOrContractMonth": getattr(
                    contract, "lastTradeDateOrContractMonth", None
                ),
                "Strike": getattr(contract, "strike", None),
                "Right": getattr(contract, "right", None),
                "Multiplier": getattr(contract, "multiplier", None),
            }
        )
    logger.info("Positions fetched successfully.")
    df = pd.DataFrame(position_data)
    forex_rates = {
        currency: fetch_currency_rate(ib_client, currency, base_currency)
        for currency in unique_currencies
    }
    df["ForexRate"] = df["Currency"].map(forex_rates)
    market_prices = fetch_historical_prices(ib_client, contracts)
    df["MarketPrice"] = df["ConId"].map(market_prices)
    return df


if __name__ == "__main__":
    ib_client = IB()
    ib_client.connect("127.0.0.1", 7496, clientId=1)
    balance = fetch_balance(ib_client)
    print(balance)

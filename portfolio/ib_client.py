import json
from pathlib import Path
from ib_async import IB, Contract, Forex, Stock, Ticker
import pandas as pd
import logging

logger = logging.getLogger()
# Define the cache file path
SCRIPT_DIR = Path(__file__).parent.parent.parent
CACHE_DIR = SCRIPT_DIR / "cache"
CACHE_FILE = CACHE_DIR / "model_greeks_cache.json"
# Ensure the cache directory exists
CACHE_DIR.mkdir(parents=True, exist_ok=True)
RISK_FREE_RATES = {
    "HKD": 0.03032,
    "USD": 0.0453,
    "SGD": 0.02559,
}
SPECIAL_SYMBOL = {
    "BABA2": "BABA",
}

# Load the cache from the file if it exists
def load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


# Save the cache to the file
def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


# Initialize the cache
model_greeks_cache = load_cache()


def get_underlying_symbol(symbol: str):
    if symbol in SPECIAL_SYMBOL:
        return SPECIAL_SYMBOL[symbol]
    return symbol

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
    # shift NetLiquidation in the first column
    df.insert(0, "NetLiquidation", df.pop("NetLiquidation"))
    logger.info(df)
    logger.info("Account data fetched successfully.")
    return df


def fetch_historical_prices(
    ib_client: IB, contracts: list[Contract]
) -> dict[int, float]:
    logger.info("Fetching historical prices from TWS...")
    historical_prices = {}
    contracts = ib_client.qualifyContracts(*contracts)
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
            print(f"Error fetching historical data for {get_underlying_symbol(contract.symbol)}: {e}")
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


def fetch_iv_rank_percentile(ib_client: IB, contract: Contract) -> tuple[float, float]:
    bars = ib_client.reqHistoricalData(
        contract,
        endDateTime="",
        durationStr="52 W",
        barSizeSetting="1 day",
        whatToShow="OPTION_IMPLIED_VOLATILITY",
        useRTH=False,
    )
    if not bars:
        return -1, -1
    min_iv = min(bars, key=lambda bar: bar.close)
    max_iv = max(bars, key=lambda bar: bar.close)
    current_iv = bars[-1].close
    iv_rank = (current_iv - min_iv.close) / (max_iv.close - min_iv.close)
    # find the percentile where the current iv is located
    sorted_ivs = sorted(bars, key=lambda bar: bar.close)
    percentile = (sorted_ivs.index(bars[-1]) + 1) / len(sorted_ivs)
    return iv_rank, percentile


def fetch_positions(ib_client: IB, base_currency: str = "SGD") -> pd.DataFrame:
    logger.info("Fetching positions from TWS...")
    positions = ib_client.positions()
    position_data = []
    unique_currencies = set()
    contracts = [pos.contract for pos in positions]
    qualified_contracts = ib_client.qualifyContracts(*contracts)

    unique_stocks = [
        Stock(get_underlying_symbol(pos.contract.symbol), pos.contract.exchange, pos.contract.currency)
        for pos in positions
    ]
    qualified_stocks = ib_client.qualifyContracts(*unique_stocks)
    # unclear why individual contract able to get model greeks while all at once could not hence this was switched to single
    ib_client.reqMarketDataType(2)
    tickers = ib_client.reqTickers(*qualified_contracts)
    stock_tickers = ib_client.reqTickers(*qualified_stocks)
    ib_client.reqMarketDataType(4)
    tickers_backup = ib_client.reqTickers(*qualified_contracts)
    stock_tickers_backup = ib_client.reqTickers(*qualified_stocks)
    stock_tickers_dict = {
        get_underlying_symbol(stock_ticker.contract.symbol): stock_ticker for stock_ticker in stock_tickers
    }
    stock_tickers_backup_dict = {
        get_underlying_symbol(stock_ticker_backup.contract.symbol): stock_ticker_backup
        for stock_ticker_backup in stock_tickers_backup
    }
    iv_rank_percentile_dict = {
        get_underlying_symbol(stock_ticker.contract.symbol): fetch_iv_rank_percentile(
            ib_client, stock_ticker.contract
        )
        for stock_ticker in stock_tickers
    }
    for pos, ticker, ticker_backup in zip(positions, tickers, tickers_backup):
        contract = pos.contract
        contracts.append(contract)
        unique_currencies.add(contract.currency)
        delta, gamma, theta, vega, iv, pvDividend = 1, 0, 0, 0, 0, 0
        iv_rank, iv_percentile = iv_rank_percentile_dict.get(get_underlying_symbol(contract.symbol), (-1, -1))
        model_greeks = (
            ticker.modelGreeks if ticker.modelGreeks else ticker_backup.modelGreeks
        )
        if model_greeks:
            model_greeks = {
                "delta": model_greeks.delta,
                "gamma": model_greeks.gamma,
                "theta": model_greeks.theta,
                "vega": model_greeks.vega,
                "impliedVol": model_greeks.impliedVol,
                "pvDividend": model_greeks.pvDividend,
                "ivRank_52w": iv_rank,
                "ivPercentile_52w": iv_percentile,
            }

        if model_greeks is None and contract.secType == "OPT":
            logger.info(
                f"Fetching cached model greeks for {get_underlying_symbol(contract.symbol)} with conId {contract.conId}..."
            )
            model_greeks = model_greeks_cache.get(str(contract.conId))
            print(model_greeks)

        if model_greeks:
            logger.info(
                f"Model greeks for {get_underlying_symbol(contract.symbol)} with conId {contract.conId} fetched successfully."
            )
            delta = model_greeks["delta"]
            gamma = model_greeks["gamma"]
            theta = model_greeks["theta"]
            vega = model_greeks["vega"]
            iv = model_greeks["impliedVol"]
            pvDividend = model_greeks["pvDividend"]
            iv_rank = model_greeks.get("ivRank_52w", -1)
            iv_percentile = model_greeks.get("ivPercentile_52w", -1)

            # Update cache with newly fetched model Greeks
            model_greeks_cache[str(contract.conId)] = {
                "delta": delta,
                "gamma": gamma,
                "theta": theta,
                "vega": vega,
                "impliedVol": iv,
                "pvDividend": pvDividend,
                "ivRank_52w": iv_rank,
                "ivPercentile_52w": iv_percentile,
            }
            save_cache(model_greeks_cache)  # Save updated cache
        multiplier = contract.multiplier if contract.multiplier != "" else 1
        position_data.append(
            {
                "Account": pos.account,
                "Symbol": get_underlying_symbol(contract.symbol),
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
                "Multiplier": float(multiplier),
                "MarketPrice": ticker.marketPrice() or ticker_backup.marketPrice(),
                "Delta": delta,
                "Gamma": gamma,
                "Theta": theta,
                "Vega": vega,
                "IV": iv,
                "PVDividend": pvDividend,
                "IVRank_52W": iv_rank,
                "IVPercentile_52W": iv_percentile,
                "RiskFreeRate": RISK_FREE_RATES[contract.currency],
                "UnderlyingPrice": stock_tickers_dict[get_underlying_symbol(contract.symbol)].marketPrice()
                or stock_tickers_backup_dict[get_underlying_symbol(contract.symbol)].marketPrice(),
            }
        )
    logger.info("Positions fetched successfully.")
    df = pd.DataFrame(position_data)
    forex_rates = {
        currency: fetch_currency_rate(ib_client, currency, base_currency)
        for currency in unique_currencies
    }
    df["ForexRate"] = df["Currency"].map(forex_rates)
    print(df.head())
    df["MarketPrice"] = df["MarketPrice"].fillna(df["AvgCost"] / df["Multiplier"])
    return df


if __name__ == "__main__":
    ib_client = IB()
    ib_client.connect("127.0.0.1", 7496, clientId=1, readonly=True)
    ib_client.reqMarketDataType(4)
    contract = Contract(
        symbol="9988",
        secType="STK",
        exchange="",
        currency="HKD",
    )
    balance = fetch_balance(ib_client)
    print(balance)
    position = fetch_positions(ib_client)
    print(position)

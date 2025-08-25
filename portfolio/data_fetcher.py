import logging
from typing import Dict, List, Tuple
from ib_async import IB, Contract, Forex, Stock
import pandas as pd

from portfolio.models import Position, MarketData, ContractDetails

logger = logging.getLogger()

# --- Constants ---
RISK_FREE_RATES = {"HKD": 0.03032, "USD": 0.0453, "SGD": 0.02559}
SPECIAL_SYMBOL_MAP = {"BABA2": "BABA"}
EXCHANGE_OVERRIDES = {"HKD": "SEHK", "SGD": "SGX", "USD": "NYSE"}
def _get_underlying_symbol(symbol: str) -> str:
    """Returns the correct underlying symbol, handling special cases."""
    return SPECIAL_SYMBOL_MAP.get(symbol, symbol)


def fetch_positions_and_contracts(ib_client: IB) -> Tuple[List[Position], List[ContractDetails], List[Contract]]:
    """
    Fetches core positions and extracts their static contract details and
    the original contract objects.

    Args:
        ib_client: An initialized and connected IB client instance.

    Returns:
        A tuple of (positions, contract_details, original_contracts).
    """
    logger.info("Fetching core positions and contract details...")
    positions = []
    contract_details = []
    original_contracts = []
    
    seen_con_ids = set()

    for pos in ib_client.positions():
        contract = pos.contract
        if contract and contract.conId:
            original_contracts.append(contract)
            positions.append(
                Position(
                    account=pos.account,
                    conId=contract.conId,
                    quantity=pos.position,
                    avgCost=pos.avgCost
                )
            )
            if contract.conId not in seen_con_ids:
                underlying_conId = None
                # qualify Stock of the underlying if option
                if contract.secType == "OPT":
                    underlying_symbol = _get_underlying_symbol(contract.symbol)
                    underlying_contract = Stock(underlying_symbol, EXCHANGE_OVERRIDES.get(contract.currency, contract.exchange), contract.currency)
                    ib_client.qualifyContracts(underlying_contract)
                    underlying_conId = underlying_contract.conId if underlying_contract.conId else None
                contract_details.append(
                    ContractDetails(
                        conId=contract.conId,
                        symbol=_get_underlying_symbol(contract.symbol),
                        secType=contract.secType,
                        currency=contract.currency,
                        exchange=EXCHANGE_OVERRIDES.get(contract.currency, contract.exchange),
                        lastTradeDateOrContractMonth=getattr(contract, "lastTradeDateOrContractMonth", None),
                        strike=getattr(contract, "strike", 0.0),
                        right=getattr(contract, "right", ''),
                        multiplier=float(getattr(contract, 'multiplier', 1) or 1),
                        underlyingConId=underlying_conId
                    )
                )
                seen_con_ids.add(contract.conId)

    logger.info(f"Fetched {len(positions)} positions and {len(contract_details)} unique contracts.")
    return positions, contract_details, original_contracts

# Mapping of Market Data Type IDs to a descriptive name
MARKET_DATA_TYPES = {
    1: "Real-time",
    2: "Frozen",
    3: "Delayed",
    4: "Delayed-frozen",
}

def fetch_market_data(ib_client: IB, contracts: List[Contract]) -> List[MarketData]:
    """
    Fetches market data for contracts by iterating through all market data types
    to ensure model greeks and market price are populated, using a single IB client.

    Args:
        ib_client: The single IB client instance.
        contracts: A list of ib_async.Contract objects to fetch market data for.

    Returns:
        A list of MarketData objects.
    """
    logger.info(f"Fetching market data for {len(contracts)} contracts...")
    if not contracts:
        return []

    # Use the single client for all qualification and data requests
    qualified_contracts = ib_client.qualifyContracts(*contracts)
    
    unique_stock_tuples = {(_get_underlying_symbol(c.symbol), c.exchange, c.currency) for c in qualified_contracts if c}
    underlying_stocks = [Stock(symbol, ex, curr) for symbol, ex, curr in unique_stock_tuples]
    qualified_underlyings = ib_client.qualifyContracts(*underlying_stocks)

    # Fetch underlying data once
    underlying_tickers = {}
    ib_client.reqMarketDataType(3)  # Use Delayed (3) for underlying data
    for s in qualified_underlyings:
        if s:
            ticker = ib_client.reqMktData(s, "", False, False)
            ib_client.sleep(0.1)
            underlying_tickers[s.symbol] = ticker
    
    # Fetch IV Rank/Percentile once
    iv_rank_map = {s.symbol: fetch_iv_rank_percentile(ib_client, s) for s in qualified_underlyings if s}

    market_data_list = []
    
    for contract in qualified_contracts:
        market_price = None
        greeks = None
        
        # Iteratively try each market data type from 1 (Real-time) to 4 (Delayed-frozen)
        for data_type_id, data_type_name in MARKET_DATA_TYPES.items():
            ib_client.reqMarketDataType(data_type_id)
            ticker = ib_client.reqMktData(contract, "", False, False)
            ib_client.sleep(0.1)
            
            # Check if we have a valid market price and Greeks from this request
            if ticker.marketPrice():
                market_price = ticker.marketPrice()
            if ticker.modelGreeks:
                greeks = ticker.modelGreeks
            
            # If both are found, we can break the inner loop and proceed
            if market_price is not None and greeks is not None:
                logger.info(f"Market data for {contract.symbol} found with {data_type_name} data.")
                break
        
        # If no data found after all attempts, log a warning
        if market_price is None or greeks is None:
            logger.warning(f"Could not fetch complete market data for {contract.symbol} after all attempts.")
            
        underlying_symbol = _get_underlying_symbol(contract.symbol)
        underlying_ticker = underlying_tickers.get(underlying_symbol)
        iv_rank, iv_percentile = iv_rank_map.get(underlying_symbol, (-1.0, -1.0))
        
        market_data_list.append(MarketData(
            conId=contract.conId,
            marketPrice=market_price or 0.0,
            underlyingPrice=underlying_ticker.marketPrice() if underlying_ticker else None,
            delta=greeks.delta if greeks and greeks.delta is not None else (1.0 if contract.secType == 'STK' else 0.0),
            gamma=greeks.gamma if greeks and greeks.gamma is not None else 0.0,
            theta=greeks.theta if greeks and greeks.theta is not None else 0.0,
            vega=greeks.vega if greeks and greeks.vega is not None else 0.0,
            iv=greeks.impliedVol if greeks and greeks.impliedVol is not None else 0.0,
            pvDividend=greeks.pvDividend if greeks and greeks.pvDividend is not None else 0.0,
            ivRank_52w=iv_rank,
            ivPercentile_52w=iv_percentile
        ))
        
    logger.info("Market data fetched successfully.")
    return market_data_list

def fetch_balance(ib_client: IB) -> pd.DataFrame:
    """Fetches all account-related data from TWS."""
    logger.info("Fetching account data from TWS...")
    account_values = ib_client.accountValues()
    account_data = {}
    for value in account_values:
        account = value.account
        if account not in account_data:
            account_data[account] = {}
        try:
            account_data[account][value.tag] = float(value.value)
        except ValueError:
            account_data[account][value.tag] = value.value

    df = pd.DataFrame.from_dict(account_data, orient="index").reset_index()
    df.rename(columns={'index': 'account'}, inplace=True)
    if "netLiquidation" in df.columns:
        df.insert(0, "netLiquidation", df.pop("netLiquidation"))
    logger.info("Account data fetched successfully.")
    return df


def fetch_currency_rate(ib_client: IB, currency: str, base_currency: str = "SGD") -> float:
    """Fetches exchange rate. Returns 1.0 if rate not found."""
    if currency == base_currency:
        return 1.0
    
    for pair in [f"{currency}{base_currency}", f"{base_currency}{currency}"]:
        contract = Forex(pair)
        bars = ib_client.reqHistoricalData(
            contract, endDateTime="", durationStr="1 D", barSizeSetting="1 day",
            whatToShow="MIDPOINT", useRTH=True
        )
        if bars:
            rate = bars[-1].close
            return rate if pair.startswith(currency) else 1 / rate
    
    logger.warning(f"Could not find forex rate for {currency}{base_currency}. Defaulting to 1.0.")
    return 1.0


def fetch_iv_rank_percentile(ib_client: IB, contract: Contract) -> tuple[float, float]:
    """Fetches 52-week IV Rank and Percentile."""
    bars = ib_client.reqHistoricalData(
        contract, endDateTime="", durationStr="52 W", barSizeSetting="1 day",
        whatToShow="OPTION_IMPLIED_VOLATILITY", useRTH=False
    )
    if not bars or len(bars) < 2:
        return -1.0, -1.0
    
    ivs = [bar.close for bar in bars]
    min_iv, max_iv, current_iv = min(ivs), max(ivs), ivs[-1]
    
    iv_rank = (current_iv - min_iv) / (max_iv - min_iv) if max_iv > min_iv else 0.0
    iv_percentile = sum(1 for iv in ivs if iv < current_iv) / len(ivs)
    
    return iv_rank, iv_percentile
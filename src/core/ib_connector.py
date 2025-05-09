from datetime import datetime
from decimal import Decimal
from typing import Literal
from ib_async import IB, Contract, Option, OptionChain, Stock, Ticker
import math
import logging
import asyncio
from src.models.models import Rights

logger = logging.getLogger()


def connect_to_ibkr(
    host: str, port: int, client_id: int, readonly: bool, account: str
) -> IB:
    """Connect to Interactive Brokers."""
    ib = IB()
    ib.connect(host, port, client_id, readonly=readonly, account=account)
    ib.account = account
    return ib


def wait_for_subscription(ib: IB, ticker: Ticker, timeout: int = 10) -> None:
    for _ in range(timeout):
        if not math.isnan(ticker.marketPrice()):
            logger.info(
                f"Subscription loaded. Market price: {Decimal(str(ticker.marketPrice()))}"
            )
            return
        logger.info("Waiting for subscription to load...")
        ib.sleep(1)


def get_stock_ticker(
    ib: IB, symbol: str, exchange: str, currency: str, timeout: int = 10
) -> Ticker | None:
    """Get stock ticker from IB."""
    contract = Stock(symbol, exchange, currency)
    if qualified := ib.qualifyContracts(contract):
        ticker = ib.reqMktData(qualified[0], "101")
        wait_for_subscription(ib, ticker, timeout)
        return ticker
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
    timeout: int = 10,
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
        ticker = ib.reqMktData(qualified[0], "101")
        if timeout > 0:
            wait_for_subscription(ib, ticker, timeout)
        return ticker
    return None


def get_option_ticker_from_contract(
    ib: IB, contract: Contract, timeout: int = 0, include_depth: bool = False
) -> Ticker | None:
    if qualified := ib.qualifyContracts(contract):
        logger.debug(f"Qualified contract: {qualified[0]}")
        ticker = ib.reqMktData(qualified[0], "101")

        if include_depth:
            ticker = ib.reqMktDepth(qualified[0], numRows=5, isSmartDepth=True)
        if timeout > 0:
            wait_for_subscription(ib, ticker, timeout)
        return ticker
    return None


def get_option_ticker_depth_from_contract(
    ib: IB, contract: Contract, timeout: int = 0
) -> Ticker | None:
    if qualified := ib.qualifyContracts(contract):
        logger.debug(f"Qualified contract: {qualified[0]}")
        ticker = ib.reqMktDepth(qualified[0], numRows=5, isSmartDepth=True)
        if timeout > 0:
            wait_for_subscription(ib, ticker, timeout)
        return ticker


def get_option_chain(ib: IB, contract: Contract) -> list[OptionChain]:
    logger.info(f"Retrieving option chain for {contract.symbol}")
    return ib.reqSecDefOptParams(contract.symbol, "", "STK", contract.conId)


def get_dte(expiration: str) -> int:
    """Calculate days to expiration (DTE) from an expiration date string."""
    return (datetime.strptime(expiration, "%Y%m%d").date() - datetime.now().date()).days


def filter_strikes(
    strikes: list[Decimal], min_strike: Decimal, max_strike: Decimal
) -> list[Decimal]:
    """Filter strikes within the specified range."""
    return [strike for strike in strikes if min_strike <= strike <= max_strike]


def filter_expirations(expirations: list[str], min_dte: int, max_dte: int) -> list[str]:
    """Filter expirations based on the DTE range."""
    return [exp for exp in expirations if min_dte <= get_dte(exp) <= max_dte]


def generate_options(
    symbol: str,
    exchange: str,
    expirations: list[str],
    strikes: list[Decimal],
    rights: list[Rights],
) -> list[Contract]:
    """Generate all possible option contracts for the given parameters."""
    return [
        Option(symbol, exp, strike, right.value, exchange)
        for exp in expirations
        for strike in strikes
        for right in rights
    ]


def get_options(
    ib: IB,
    contract: Contract,
    rights: list[Rights],
    min_dte: int,
    max_dte: int,
    min_strike: Decimal,
    max_strike: Decimal,
) -> list[Contract]:
    """
    Retrieve qualified option contracts based on the given criteria.

    Args:
        ib (IB): Interactive Brokers client instance.
        contract (Contract): The underlying asset contract.
        rights (List[str]): List of option rights (e.g., ["C", "P"]).
        min_dte (int): Minimum days to expiration.
        max_dte (int): Maximum days to expiration.
        min_strike (Decimal): Minimum strike price.
        max_strike (Decimal): Maximum strike price.

    Returns:
        List[Contract]: A list of qualified option contracts.
    """
    # Step 1: Get the option chain for the contract's exchange
    option_chains = get_option_chain(ib, contract)
    option_chain = next(
        (chain for chain in option_chains if chain.exchange == contract.exchange), None
    )
    if option_chain is None:
        logger.warning("No option chain found for contract")
        return []

    # Step 2: Filter strikes and expirations
    strikes = filter_strikes(option_chain.strikes, min_strike, max_strike)
    expirations = filter_expirations(option_chain.expirations, min_dte, max_dte)

    # Step 3: Generate all possible options
    options = generate_options(
        contract.symbol, contract.exchange, expirations, strikes, rights
    )
    logger.info(f"Generated {len(options)} raw options")

    # Step 4: Qualify contracts
    # try:
    #     qualified_options = ib.qualifyContracts(*options)
    # except Exception as e:
    #     logger.error(f"Failed to qualify contracts: {e}")
    #     return []
    qualified_options = ib.qualifyContracts(*options)
    logger.info(f"Qualified {len(qualified_options)} options")
    return qualified_options


def get_current_position(ib: IB, contract: Contract) -> Decimal:
    current_pos = next(
        (
            pos.position
            for pos in ib.positions()
            if pos.contract.conId == contract.conId
        ),
        0,
    )
    current_pos = Decimal(str(current_pos))
    return current_pos


# === ASYNC FUNCTIONS ===
async def async_connect_to_ibkr(
    host: str, port: int, client_id: int, readonly: bool, account: str
) -> IB:
    """Connect to Interactive Brokers."""
    ib = IB()
    await ib.connectAsync(host, port, client_id, readonly=readonly, account=account)
    ib.account = account
    return ib


async def async_wait_for_subscription(
    ib: IB, ticker: Ticker, timeout: int = 10
) -> None:
    for _ in range(timeout):
        if not math.isnan(ticker.marketPrice()):
            logger.info(
                f"Subscription loaded. Market price: {Decimal(str(ticker.marketPrice()))}"
            )
            return
        logger.info("Waiting for subscription to load...")
        await asyncio.sleep(1)


async def async_get_stock_ticker(
    ib: IB, symbol: str, exchange: str, currency: str, timeout: int = 10
) -> Ticker | None:
    contract = Stock(symbol, exchange, currency)
    logger.info(f"Retrieving stock ticker for {contract.symbol}")
    qualified = await ib.qualifyContractsAsync(contract)
    if qualified:
        logger.info(f"Retrieved stock ticker for {contract.symbol}")
        ticker = ib.reqMktData(qualified[0], "101")
        await async_wait_for_subscription(ib, ticker, timeout)
        return ticker
    return None


async def async_get_option_ticker(
    ib: IB,
    symbol: str,
    last_trade_date: str,
    strike_price: Decimal,
    right: Literal["C", "P"],
    exchange: str = "",
    multiplier: int = "",
    currency: str = "",
    timeout: int = 10,
) -> Ticker | None:
    contract = Option(
        symbol,
        last_trade_date,
        float(strike_price),
        right,
        exchange,
        multiplier,
        currency,
    )
    if qualified := await ib.qualifyContractsAsync(contract):
        ticker = ib.reqMktData(qualified[0], "101")
        if timeout > 0:
            await async_wait_for_subscription(ib, ticker, timeout)
        return ticker
    return None


async def async_get_option_ticker_from_contract(
    ib: IB, contract: Contract, timeout: int = 0, include_depth: bool = False
) -> Ticker | None:
    if qualified := await ib.qualifyContractsAsync(contract):
        logger.debug(f"Qualified contract: {qualified[0]}")
        ticker = ib.reqMktData(qualified[0], "101")
        if include_depth:
            ticker = ib.reqMktDepth(qualified[0], numRows=5, isSmartDepth=True)
        if timeout > 0:
            await async_wait_for_subscription(ib, ticker, timeout)
        return ticker
    return None


async def async_get_option_ticker_depth_from_contract(
    ib: IB, contract: Contract, timeout: int = 0
) -> Ticker | None:
    if qualified := await ib.qualifyContractsAsync(contract):
        logger.debug(f"Qualified contract: {qualified[0]}")
        ticker = ib.reqMktDepth(qualified[0], numRows=5, isSmartDepth=True)
        if timeout > 0:
            await async_wait_for_subscription(ib, ticker, timeout)
        return ticker


async def async_get_option_chain(ib: IB, contract: Contract) -> list[OptionChain]:
    logger.info(f"Retrieving option chain for {contract.symbol}")
    results = await ib.reqSecDefOptParamsAsync(
        contract.symbol, "", "STK", contract.conId
    )
    return results


async def async_get_options(
    ib: IB,
    contract: Contract,
    rights: list[Rights],
    min_dte: int,
    max_dte: int,
    min_strike: Decimal,
    max_strike: Decimal,
) -> list[Contract]:
    option_chains = await async_get_option_chain(ib, contract)
    option_chain = next(
        (chain for chain in option_chains if chain.exchange == contract.exchange), None
    )
    if option_chain is None:
        logger.warning("No option chain found for contract")
        return []

    strikes = filter_strikes(option_chain.strikes, min_strike, max_strike)
    expirations = filter_expirations(option_chain.expirations, min_dte, max_dte)

    options = generate_options(
        contract.symbol, contract.exchange, expirations, strikes, rights
    )
    logger.info(f"Generated {len(options)} raw options")

    # try:
        # qualified_options = await ib.qualifyContractsAsync(*options)
    # except Exception as e:
    #     logger.error(f"Failed to qualify contracts: {e}")
    #     return []
    qualified_options = await ib.qualifyContractsAsync(*options)
    logger.info(f"Qualified {len(qualified_options)} options")
    return qualified_options


if __name__ == "__main__":
    from src.utils.logger_config import setup_logger

    setup_logger()
    ib = connect_to_ibkr("127.0.0.1", 7496, 444, readonly=True, account="")
    stock = get_stock_ticker(ib, "BABA", "SMART", "USD")
    option_chain = get_option_chain(ib, stock.contract)
    print(get_options(ib, stock.contract, [Rights.CALL, Rights.PUT], 300, 365, 90, 100))
    option = get_option_ticker(
        ib,
        "9988",
        "20250529",
        Decimal("100"),
        "C",
        "SMART",
        "",
        "USD",
    )
    ib.reqMarketDataType(1)

    # print(option_chain)
    # print(get_current_position(ib, stock))
    # print(option)
    async def main():
        ib = await async_connect_to_ibkr(
            "127.0.0.1", 7496, 555, readonly=True, account=""
        )
        # ib_async = connect_to_ibkr("127.0.0.1", 7496, 222, readonly=True, account="")
        stock_async = await async_get_stock_ticker(ib, "BABA", "SMART", "USD")
        option_async = await async_get_option_ticker(
            ib,
            "9988",
            "20250529",
            Decimal("100"),
            "C",
            "",
            "",
            "HKD",
        )
        print(option_async.marketPrice())
        print(stock_async.marketPrice())

    asyncio.run(main())

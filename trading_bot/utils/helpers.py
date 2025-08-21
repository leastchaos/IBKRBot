import logging
import json
from decimal import Decimal
from ib_async import DOMLevel, Contract

ACCOUNT_LOCATION = "./credentials/ibkr_accounts.json"
logger = logging.getLogger()

def get_price_at_depth(levels: list[DOMLevel], depth: int) -> Decimal | None:
    """Get the price at the specified depth."""
    if not levels:
        return None
    current_depth = 0
    for level in levels:
        current_depth += level.size
        if current_depth >= depth:
            break
    else:
        logger.warning(f"Depth {depth} not found in DOM levels.")
    return Decimal(str(level.price))


def option_display(option_contract: Contract) -> str:
    """A pretty printer for option contracts in single line."""
    return (
        f"{option_contract.symbol} "
        f"{option_contract.lastTradeDateOrContractMonth} "
        f"{option_contract.strike} "
        f"{option_contract.right} "
        f"{option_contract.currency}"
    )

def get_ibkr_account(strategy: str) -> str:
    with open(ACCOUNT_LOCATION, "r") as f:
        accounts = json.load(f)
    return accounts[strategy]


if __name__ == "__main__":
    print(get_ibkr_account("mass_buy_options"))

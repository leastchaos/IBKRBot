import logging
from decimal import Decimal
from ib_async import DOMLevel, Contract


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


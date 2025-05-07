from decimal import Decimal
import logging
from src.models.models import Action, OCAType, Rights
from src.strategy.mass_buy_options_async.config import TradingConfig
from src.strategy.mass_buy_options_async.trade_executor import mass_trade_oca_option
from src.core.ib_connector import connect_to_ibkr, get_stock_ticker

# Configure logging
logging.basicConfig(level=logging.INFO)

# Configuration
TRADE_CONFIG = TradingConfig(
    action=Action.SELL,
    right=Rights.PUT,
    min_dte=200,
    max_dte=400,
    min_strike=Decimal("160"),
    max_strike=Decimal("200"),
    size=Decimal("1"),
    manual_min_tick=Decimal("0.01"),
    min_update_size=Decimal("0.05"),
    min_distance=Decimal("0.1"),
    volatility=0.5,
    aggressive=True,
    skip_too_far_away=False,
    oca_type=OCAType.REDUCE_WITH_NO_BLOCK
)

if __name__ == "__main__":
    # Connect to IBKR
    ib = connect_to_ibkr("127.0.0.1", 7496, 222, readonly=True)
    exec_ib = connect_to_ibkr("127.0.0.1", 7496, 333, readonly=False)
    
    # Qualify stock contract
    stock = get_stock_ticker(ib, "9988", "SEHK", "HKD")
    
    # Run strategy
    mass_trade_oca_option(ib, exec_ib, stock.contract, TRADE_CONFIG)
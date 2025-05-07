# test_determine_price.py

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from src.strategy.mass_buy_options_async.price_utils import determine_price
from src.models.models import Action
from src.strategy.mass_buy_options_async.config import TradingConfig
from ib_async import Ticker, IB, LimitOrder, Contract, Trade


@pytest.mark.asyncio
async def test_determine_price_buy():
    # Mocking objects
    mock_ib = AsyncMock(spec=IB)
    mock_stock_ticker = AsyncMock(spec=Ticker)
    mock_option_ticker = AsyncMock(spec=Ticker)

    # Set up ticker return values
    mock_stock_ticker.marketPrice.return_value = 180.0

    mock_option_ticker.bid = 1.5
    mock_option_ticker.ask = 2.0
    mock_option_ticker.minTick = "0.01"
    mock_option_ticker.contract.strike = 190

    # Patch get_depth_price
    with patch(
        "src.strategy.mass_buy_options_async.price_utils.get_depth_price",
        new=AsyncMock(return_value=(Decimal("1.6"), Decimal("1.9"))),
    ):
        # Patch calculateOptionPriceAsync
        mock_ib.calculateOptionPriceAsync = AsyncMock(
            return_value=AsyncMock(optPrice=1.75)
        )

        config = TradingConfig(
            action=Action.BUY,
            right="C",
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
            oca_type="REDUCE_WITH_NO_BLOCK",
            min_ask_price=Decimal("0"),
            max_bid_price=Decimal("100"),
            depth=2,
            determine_price_timeout=5,
        )

        order = Trade(order=LimitOrder(action=config.action, totalQuantity=1, lmtPrice=100))

        price = await determine_price(mock_ib, mock_stock_ticker, mock_option_ticker, config, order)

        assert price > Decimal("0")
        assert price <= Decimal("1.75")  # capped by calculated price
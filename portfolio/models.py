from dataclasses import dataclass, fields
from ib_async import Contract
from typing import Literal, TypedDict, Optional
from datetime import datetime


class PositionRow(TypedDict):
    """
    Represents the flattened structure of a single portfolio position row.
    Uses camelCase to match the ib_async library's conventions.
    """

    # --- Keys from initial data fetch ---
    account: str
    symbol: str
    secType: str
    currency: str
    position: float
    avgCost: float
    conId: int
    exchange: str
    lastTradeDateOrContractMonth: Optional[str]
    strike: float
    right: Literal["C", "P", ""]
    multiplier: float
    marketPrice: float
    underlyingPrice: Optional[float]
    delta: float
    gamma: float
    theta: float
    vega: float
    iv: float
    pvDividend: float
    ivRank_52w: float
    ivPercentile_52w: float
    forexRate: float
    riskFreeRate: float

    # --- Keys added during scenario merge ---
    targetPrice: float

    # --- Keys added during calculation pipeline ---
    positionType: str
    marketValueBase: float
    initialMaxRisk: Optional[float]
    notionalExposure: Optional[float]
    intrinsicValue: float
    worstCaseRisk: Optional[float]
    targetProfit: float
    timeValue: float


@dataclass
class Position:
    """Holds the absolute core data for a single portfolio position."""

    account: str
    conId: int
    quantity: float
    avgCost: float


@dataclass
class ContractDetails:
    """Holds the static, descriptive details of a contract."""

    conId: int
    symbol: str
    secType: str
    currency: str
    exchange: str
    lastTradeDateOrContractMonth: Optional[str]
    strike: float
    right: str
    multiplier: float
    underlyingConId: Optional[int] = None  # New field


@dataclass
class MarketData:
    """Holds dynamic, real-time market data for a contract."""

    conId: int
    marketPrice: float = 0.0
    underlyingPrice: float | None = None
    delta: float = -1.0
    gamma: float = -1.0
    theta: float = -1.0
    vega: float = -1.0
    iv: float = -1.0
    pvDividend: float = -1.0
    ivRank_52w: float = -1.0
    ivPercentile_52w: float = -1.0
    date_updated: datetime | None = None
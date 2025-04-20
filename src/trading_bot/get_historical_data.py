from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
from time import sleep

from ib_async import IB, BarData, Ticker
from ib_insync import BarDataList

logger = logging.getLogger()


def load_day_cache(cache_path: Path) -> BarDataList:
    """Load cached data for a single day."""
    if not cache_path.exists():
        return BarDataList()

    with open(cache_path, "r") as f:
        cached_data = json.load(f)
    return BarDataList([BarData(**bar) for bar in cached_data])


def save_day_cache(cache_path: Path, data: BarDataList):
    """Save data for a single day to a JSON file."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump([bar.__dict__ for bar in data], f, default=str)


def get_historical_data(
    ib: IB,
    ticker: Ticker,
    total_duration: str = "90 D",  # Total duration of historical data to fetch
    bar_size: str = "1 min",
) -> BarDataList:
    """Fetch historical data in daily chunks with caching support."""
    logger.info(f"Fetching {total_duration} historical data for {ticker.contract}...")

    # Parse total duration into a timedelta object
    total_days = parse_duration(total_duration)

    # Calculate the requested time range
    end_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)  # End of today
    start_date = end_date - timedelta(days=total_days)  # Start date based on total_duration

    all_bars = BarDataList()

    # Fetch data day by day
    current_date = end_date
    while current_date > start_date:
        day_start = current_date - timedelta(days=1)
        cache_key = f"{ticker.contract.symbol}_{day_start.strftime('%Y-%m-%d')}.json"
        cache_path = Path("historical_data_cache") / cache_key

        # Load cached data for the day
        cached_bars = load_day_cache(cache_path)
        if cached_bars:
            logger.info(f"Loaded cached data for {day_start.date()}")
        else:
            logger.info(f"Fetching data for {day_start.date()}...")
            bars = fetch_historical_data_chunk(
                ib,
                ticker.contract,
                endDateTime=current_date.strftime("%Y%m%d %H:%M:%S"),
                durationStr="1 D",
                barSizeSetting=bar_size,
            )
            cached_bars = BarDataList(bars)
            save_day_cache(cache_path, cached_bars)
            # sleep(1)  # Avoid hitting rate limits

        all_bars.extend(cached_bars)
        current_date -= timedelta(days=1)

    logger.info(f"Fetched {len(all_bars)} bars in total.")
    return all_bars


def fetch_historical_data_chunk(
    ib: IB,
    contract,
    endDateTime: str,
    durationStr: str,
    barSizeSetting: str,
) -> BarDataList:
    """Fetch a single chunk of historical data."""
    return ib.reqHistoricalData(
        contract,
        endDateTime=endDateTime,
        durationStr=durationStr,
        barSizeSetting=barSizeSetting,
        whatToShow="TRADES",
        useRTH=True,
    )


def parse_duration(duration_str: str) -> int:
    """Convert a duration string (e.g., '30 D') to an integer number of days."""
    value, unit = duration_str.split()
    value = int(value)
    if unit.upper() == "D":
        return value
    elif unit.upper() == "W":
        return value * 7
    elif unit.upper() == "M":
        return value * 30  # Approximation for months
    elif unit.upper() == "Y":
        return value * 365  # Approximation for years
    else:
        raise ValueError(f"Unsupported duration unit: {unit}")
import os
import json
from dataclasses import dataclass
from datetime import datetime
import logging

from ib_async import IB, ExecutionFilter, Fill

logger = logging.getLogger()


@dataclass
class TradeRecord:
    exec_id: str
    price: float
    side: str
    timestamp: float
    con_id: int  # Added contract ID for multi-symbol support
    size: float


def load_trade_history(filename: str) -> list[TradeRecord]:
    """Load trade history from file."""
    if not os.path.exists(filename):
        return []
    with open(filename, "r") as f:
        data = json.load(f)
        return [TradeRecord(**entry) for entry in data]


def save_trade_history(filename: str, history: list[TradeRecord]) -> None:
    """Save trade history to file."""
    with open(filename, "w") as f:
        json.dump([vars(record) for record in history], f, indent=2)


def resolve_execution_conflict(
    backup_history: list[TradeRecord], ib_executions: list[Fill]
) -> list[TradeRecord]:
    """Resolve conflicts between local backup and IB executions."""
    if not ib_executions:
        return backup_history
    latest_ib = max(ib_executions, key=lambda e: e.time)
    latest_backup = (
        max(backup_history, key=lambda t: t.timestamp) if backup_history else None
    )
    if not latest_backup or latest_ib.execution.execId == latest_backup.exec_id:
        return [
            TradeRecord(
                exec_id=e.execution.execId,
                price=e.execution.price,
                side=e.execution.side,
                timestamp=e.execution.time.timestamp(),
                con_id=e.contract.conId,
                size=e.execution.cumQty,
            )
            for e in ib_executions
        ]
    # Conflict detected - prompt user
    logger.error("Execution history conflict detected!")
    logger.error(
        f"1. Keep backup (last: {datetime.fromtimestamp(latest_backup.timestamp)} @ {latest_backup.price})"
    )
    logger.error(
        f"2. Use IB data (last: {latest_ib.execution.time} @ {latest_ib.execution.price})"
    )
    choice = input("Choose (1/2): ")
    return (
        backup_history
        if choice == "1"
        else [
            TradeRecord(
                exec_id=e.execution.execId,
                price=e.execution.price,
                side=e.execution.side,
                timestamp=e.execution.time.timestamp(),
                con_id=e.contract.conId,
            )
            for e in ib_executions
        ]
    )


def check_for_new_executions(
    ib: IB,
    client_id: int,
    trade_history: list[TradeRecord],
) -> list[TradeRecord]:
    """Check for new executions and update trade history."""
    new_trades = []
    new_executions = [
        exec for exec in ib.fills() if exec.execution.clientId == client_id
    ]
    for exec_report in new_executions:
        exec_id = exec_report.execution.execId
        con_id = exec_report.contract.conId
        # Skip already recorded executions
        if exec_id in [t.exec_id for t in trade_history if t.con_id == con_id]:
            continue
        # Create a new trade record
        new_trade = TradeRecord(
            exec_id=exec_id,
            price=exec_report.execution.price,
            side=exec_report.execution.side,
            timestamp=exec_report.execution.time.timestamp(),
            con_id=con_id,
            size=exec_report.execution.cumQty,
        )
        new_trades.append(new_trade)
        logger.info(f"Detected new execution: {new_trade}")
    return new_trades

# genai/models.py
from dataclasses import dataclass, field
from typing import Any, Dict, TypedDict

from genai.common.config import Settings
from genai.browser_actions import Browser
from genai.constants import TaskType

# --- Data Models ---


@dataclass
class ResearchJob:
    """Represents a single, active research task."""

    task_id: int
    handle: str
    company_name: str
    task_type: TaskType
    account_name: str
    requested_by: str | None
    started_at: float
    status: str = "processing"
    error_recovery_attempted: bool = False


class ProcessingResult(TypedDict, total=False):
    """A dictionary for the results of post-processing a completed job."""

    report_url: str
    summary: str
    error_message: str


# --- State Management Models ---

BrowserPool = Dict[str, Browser]
ActiveJobs = Dict[int, ResearchJob]  # Now uses the dataclass
JobCounts = Dict[str, int]
OriginalTabs = Dict[str, str]


@dataclass
class WorkerState:
    """A dataclass to hold the mutable state of the worker."""

    config: Settings
    active_jobs: ActiveJobs = field(default_factory=dict)
    browser_pool: BrowserPool = field(default_factory=dict)
    original_tabs: OriginalTabs = field(default_factory=dict)
    account_job_counts: JobCounts = field(default_factory=dict)

    def __post_init__(self):
        """Initialize job counts after the object is created."""
        self.account_job_counts = {acc.name: 0 for acc in self.config.chrome.accounts}

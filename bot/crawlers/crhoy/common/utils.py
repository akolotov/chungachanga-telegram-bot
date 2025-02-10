"""Common utility functions for CRHoy crawler components."""

import time
from .logger import get_component_logger
from .state import state

logger = get_component_logger("utils")


def sleep_until_next_check(interval: float) -> None:
    """
    Sleep until next check interval or until exit is requested.
    Breaks early if shutdown is requested.
    
    Args:
        interval: Time to sleep in seconds
    """
    # Sleep in small intervals to check exit flag more frequently
    remaining = interval
    while remaining > 0 and not state.is_shutdown_requested():
        sleep_time = min(1, remaining)  # Sleep max 1 second at a time
        time.sleep(sleep_time)
        remaining -= sleep_time 
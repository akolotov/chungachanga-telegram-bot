"""Common utility functions for CRHoy crawler components."""

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from .logger import get_component_logger
from .state import state
from ..settings import settings
from .constants import COSTA_RICA_TIMEZONE

logger = get_component_logger("utils")


@dataclass
class TriggerTimeInfo:
    """Information about trigger times and intervals relative to a given time.
    
    Fields:
        previous: Full datetime of the previous trigger
        current: Full datetime of the current interval's start
        next: Full datetime of the next trigger
        shifted_previous: Full datetime of the previous trigger shifted back by 
                         2 * check_updates_interval to account for async nature
                         of synchronizer and downloader
    
    The shifted_previous field is necessary to handle the asynchronous nature of the 
    crawler components (synchronizer, downloader, and notifier) and prevent missing news:
    
    Example scenario without shift:
    1. Let X be a trigger time (e.g., 12:00)
    2. Synchronizer runs with period P (e.g., 5 minutes):
       - First run at X-P-1 sec (11:54:59)
       - Second run at X-1 sec (11:59:59)
    3. Downloader invoked after X-1 sec will receive news between X-P and X
       (11:55:00 to 12:00:00)
    4. Notifier at time X (12:00:00) might miss these news in this run due to
       processing delays on the downloader
    5. Next notifier run at time Y (e.g., 12:05) will look for news from X to Y,
       missing news from X-P to X (11:55:00 to 12:00:00)
    
    Solution:
    shifted_previous = previous - 2*P ensures the notifier looks back far enough
    to include news that might have been processed by the downloader just before
    the previous trigger time. This creates an overlap in the time windows and
    prevents news from being missed due to component asynchronicity.
    """
    previous: datetime  # Full datetime of the previous trigger
    current: datetime   # Full datetime of the current interval's start
    next: datetime     # Full datetime of the next trigger
    shifted_previous: datetime  # Previous trigger shifted back by 2 * check_updates_interval


def with_shifted_previous(
    previous: datetime,
    current: datetime,
    next: datetime
) -> TriggerTimeInfo:
    """Create TriggerTimeInfo with shifted_previous calculated from previous trigger time.
    
    Args:
        previous: Full datetime of the previous trigger
        current: Full datetime of the current interval's start
        next: Full datetime of the next trigger
        
    Returns:
        TriggerTimeInfo with all fields set including shifted_previous
    """
    shifted = previous - timedelta(seconds=2 * settings.check_updates_interval)
    return TriggerTimeInfo(
        previous=previous,
        current=current,
        next=next,
        shifted_previous=shifted
    )


def get_trigger_time_info(current_time: Optional[datetime] = None) -> TriggerTimeInfo:
    """
    Get information about trigger times and intervals relative to the given time.
    
    Args:
        current_time: Time to check against trigger times. If None, uses current time.
            The time should be in Costa Rica timezone.
            
    Returns:
        TriggerTimeInfo object containing:
        - previous: Full datetime of the previous trigger
        - current: Full datetime of the current interval's start
        - next: Full datetime of the next trigger
        - shifted_previous: previous trigger shifted back by 2 * check_updates_interval
        
    Example:
        If trigger times are [6:00, 12:00, 16:30] and current time is:
        - 13.02.2025 06:00:00 -> previous=12.02.2025 16:30, current=13.02.2025 06:00, next=13.02.2025 12:00
        - 13.02.2025 06:00:01 -> previous=12.02.2025 16:30, current=13.02.2025 06:00, next=13.02.2025 12:00
        - 13.02.2025 11:59:59 -> previous=12.02.2025 16:30, current=13.02.2025 06:00, next=13.02.2025 12:00
        - 13.02.2025 12:00:00 -> previous=13.02.2025 06:00, current=13.02.2025 12:00, next=13.02.2025 16:30
    """
    # Get current time in Costa Rica timezone if not provided
    if current_time is None:
        current_time = datetime.now(COSTA_RICA_TIMEZONE)
    elif current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=COSTA_RICA_TIMEZONE)
    
    # Get sorted trigger times
    trigger_times = sorted(settings.notifier_trigger_times)
    if not trigger_times:
        raise ValueError("No trigger times configured")
    
    # Special case: only one trigger time
    if len(trigger_times) == 1:
        trigger = trigger_times[0]
        # Find the last occurrence of the trigger time
        if current_time.time() < trigger:
            # We're before today's trigger
            current_date = current_time.date() - timedelta(days=1)
            next_date = current_time.date()
            prev_date = current_time.date() - timedelta(days=2)
        else:
            # We're after today's trigger
            current_date = current_time.date()
            next_date = current_time.date() + timedelta(days=1)
            prev_date = current_time.date() - timedelta(days=1)
            
        return with_shifted_previous(
            previous=datetime.combine(prev_date, trigger, COSTA_RICA_TIMEZONE),
            current=datetime.combine(current_date, trigger, COSTA_RICA_TIMEZONE),
            next=datetime.combine(next_date, trigger, COSTA_RICA_TIMEZONE)
        )
    
    # Find which interval we're in
    current_date = current_time.date()
    current_time_obj = current_time.time()
    
    # First check if we're before the first trigger of the day
    if current_time_obj < trigger_times[0]:
        # We're in the interval that started with the last trigger of previous day
        return with_shifted_previous(
            previous=datetime.combine(current_date - timedelta(days=1), trigger_times[-2], COSTA_RICA_TIMEZONE),
            current=datetime.combine(current_date - timedelta(days=1), trigger_times[-1], COSTA_RICA_TIMEZONE),
            next=datetime.combine(current_date, trigger_times[0], COSTA_RICA_TIMEZONE)
        )
    
    # Check each interval
    for i in range(len(trigger_times)):
        current_trigger = trigger_times[i]
        next_idx = (i + 1) % len(trigger_times)
        next_trigger = trigger_times[next_idx]
        prev_trigger = trigger_times[i-1]
        
        # If this is the last interval of the day
        if next_trigger < current_trigger:
            if current_time_obj >= current_trigger:
                # We're in the last interval of the day
                return with_shifted_previous(
                    previous=datetime.combine(current_date, prev_trigger, COSTA_RICA_TIMEZONE),
                    current=datetime.combine(current_date, current_trigger, COSTA_RICA_TIMEZONE),
                    next=datetime.combine(current_date + timedelta(days=1), next_trigger, COSTA_RICA_TIMEZONE)
                )
        # If we're in this interval
        elif current_time_obj >= current_trigger and current_time_obj < next_trigger:
            # For the first interval of the day, previous trigger was yesterday
            prev_date = current_date - timedelta(days=1) if i == 0 else current_date
            return with_shifted_previous(
                previous=datetime.combine(prev_date, prev_trigger, COSTA_RICA_TIMEZONE),
                current=datetime.combine(current_date, current_trigger, COSTA_RICA_TIMEZONE),
                next=datetime.combine(current_date, next_trigger, COSTA_RICA_TIMEZONE)
            )
    
    # If we haven't returned yet, we must be in the last interval
    return with_shifted_previous(
        previous=datetime.combine(current_date, trigger_times[-2], COSTA_RICA_TIMEZONE),
        current=datetime.combine(current_date, trigger_times[-1], COSTA_RICA_TIMEZONE),
        next=datetime.combine(current_date + timedelta(days=1), trigger_times[0], COSTA_RICA_TIMEZONE)
    )


def sleep_until_next_check(interval: float) -> None:
    """
    Sleep until next check interval or until exit is requested.
    Breaks early if shutdown is requested.
    Uses monotonic clock to handle system sleep/hibernate and time adjustments correctly.
    
    Args:
        interval: Time to sleep in seconds
    """
    target_time = time.monotonic() + interval

    logger.info("Sleeping until %s", datetime.now(COSTA_RICA_TIMEZONE) + timedelta(seconds=interval))
    
    while time.monotonic() < target_time and not state.is_shutdown_requested():
        remaining = target_time - time.monotonic()
        sleep_time = min(1, remaining)  # Sleep max 1 second at a time
        if sleep_time > 0:
            time.sleep(sleep_time)


def ensure_costa_rica_timezone(dt: datetime) -> datetime:
    """Ensure datetime is in Costa Rica timezone.
    
    Args:
        dt: Datetime to convert
        
    Returns:
        Datetime in Costa Rica timezone
    """
    if dt.tzinfo != COSTA_RICA_TIMEZONE:
        return dt.astimezone(COSTA_RICA_TIMEZONE)
    return dt 